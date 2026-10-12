"""Fixed-ticket backtester (bot-style, default $200) over data.db:dex_hist (30-min archive samples) + data.db:live.

READ-ONLY, offline (no RPC; current OKX book only for the depth check, which is ~0 at $200).
Models the CEX-DEX bot of xend-arb: fixed USD ticket, fires while the *marginal* ticket nets > --min-bps after
OKX taker 2 bps + per-tx gas. Per sample the DEX output curve out(cum_in) is rebuilt from the stored grid
(500..100k) plus a $200 point extrapolated from the average rate at 500/1000 (checked against the CL mid x fee).
Each extra ticket at the same sample walks further down the curve (the bot's own price impact).

Regimes per pool (USD/day and trades/day):
  lower : once per episode (episode = consecutive samples with >=1 ticket), burst at the episode's best sample
  upper : burst at every 30-min sample (gap fully refilled every 30 min)
  flow  : upper scaled down so ticket volume <= organic gross swap volume/day (data.db:swaps, 14 d)
Live (15 s, sizes 500/1000): net at the ticket extrapolated from the stored net bps (gas handled per size).

    python backtest.py [--ticket 200] [--min-bps 0 5 10]
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
import sqlite3
import statistics as stx
from collections import defaultdict

from analyze import GAS_USD, pct, spread_calibration
from l2common import CHAIN_CFG, HERE, OKX_FEE_BRL_TAKER, POOLS

REF_BRLA_PER_USD = 5.0  # backfill.py sizing of the brla2usd leg (amount_in = size * 5 BRLA)
GRID = [500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]


def curve_points(q, d):
    """[(cum_in, cum_out)] for one direction, starting at (0,0), with an extrapolated small-size point."""
    pts = []
    for s in GRID:
        ain, aout, ex = q[(d, s)]
        if ex or not aout:
            break
        pts.append((ain, aout))
    if len(pts) < 2:
        return None
    (a1, o1), (a2, o2) = pts[0], pts[1]
    r1, r2 = o1 / a1, o2 / a2
    r0 = r1 - (r2 - r1) * a1 / (a2 - a1)  # avg rate extrapolated to size 0 (= marginal rate at 0)
    return [(0.0, 0.0)] + pts, r0


def out_at(pts, r0, x):
    """piecewise: below the first grid point use avg rate linear in size (r0 -> r1); then linear in out."""
    a1, o1 = pts[1]
    if x <= a1:
        r1 = o1 / a1
        return x * (r0 + (r1 - r0) * x / a1)
    for (xa, ya), (xb, yb) in zip(pts[1:], pts[2:]):
        if x <= xb:
            return ya + (yb - ya) * (x - xa) / (xb - xa)
    return None  # beyond last non-exhausted grid point


def burst(q, ref, hs, gas_brl, ticket, min_bps, max_tickets):
    """tickets fired at one sample: list of net profits (BRL) per ticket, best direction only."""
    bid, ask = ref * (1 - hs), ref * (1 + hs)
    best = []
    for d in ("usd2brla", "brla2usd"):
        c = curve_points(q, d)
        if not c:
            continue
        pts, r0 = c
        step = ticket if d == "usd2brla" else ticket * ref  # brla2usd input is BRLA (~ticket in BRL)
        prof, x = [], 0.0
        for _ in range(max_tickets):
            o0, o1 = out_at(pts, r0, x), out_at(pts, r0, x + step)
            if o0 is None or o1 is None:
                break
            dout = o1 - o0
            if d == "usd2brla":  # buy BRLA on DEX with `step` USD, re-buy the USD on OKX asks
                p = dout - step * ask * (1 + OKX_FEE_BRL_TAKER) - gas_brl
            else:  # sell `step` BRLA on DEX for USD, sell the USD on OKX bids
                p = dout * bid * (1 - OKX_FEE_BRL_TAKER) - step - gas_brl
            if p / (ticket * ref) * 1e4 <= min_bps:
                break
            prof.append(p)
            x += step
        if sum(prof) > sum(best):
            best = prof
    return best


def r0_check(q, mid, fee_pips):
    """bps error of the extrapolated marginal rate at 0 vs CL mid x (1-fee), usd2brla leg."""
    c = curve_points(q, "usd2brla")
    if not c or not mid or fee_pips is None:
        return None
    return (c[1] / (mid * (1 - fee_pips / 1e6)) - 1) * 1e4


def flow_gross_per_day(db, p):
    r = db.execute("SELECT MIN(block), MAX(block), SUM(ABS(usd_delta)), COUNT(*) FROM swaps WHERE pool=?",
                   (p.key,)).fetchone()
    if not r or not r[3]:
        return None
    days = max((r[1] - r[0]) * CHAIN_CFG[p.chain]["block_s"] / 86400, 1e-9)
    return r[2] / days


def live_section(db, ticket, thresholds):
    out = {}
    rows = db.execute("SELECT pool, unix, size, usd2brla, brla2usd, okx_bid, okx_ask FROM live "
                      "WHERE size IN (500, 1000) ORDER BY unix").fetchall()
    by = defaultdict(dict)
    for pool, unix, s, a, b, *_ in rows:
        by[pool].setdefault(unix, {})[s] = (a, b)
    pmap = {p.key: p for p in POOLS}
    for pool, ticks in by.items():
        gas = GAS_USD[pmap[pool].chain]
        ser = []
        for unix, v in sorted(ticks.items()):
            if 500 not in v or 1000 not in v:
                continue
            best = None
            for i in (0, 1):
                x5, x10 = v[500][i], v[1000][i]
                if x5 is None or x10 is None:
                    continue
                g5, g10, gt = gas / 500 * 1e4, gas / 1000 * 1e4, gas / ticket * 1e4
                y5, y10 = x5 + g5, x10 + g10  # gross of gas, ~linear in size
                yt = y5 + (y10 - y5) * (ticket - 500) / 500 - gt
                best = yt if best is None else max(best, yt)
            ser.append((unix, best))
        hours = (ser[-1][0] - ser[0][0]) / 3600 if len(ser) > 1 else 0
        d = {"hours": hours, "n": len(ser), "net_bps_p50": pct([x for _, x in ser if x is not None], .5),
             "net_bps_p95": pct([x for _, x in ser if x is not None], .95)}
        for th in thresholds:
            eps, prev_on, last_u = 0, False, None
            on = 0
            for u, x in ser:
                ok = x is not None and x > th
                gap = last_u is not None and u - last_u > 90
                if ok and (not prev_on or gap):
                    eps += 1
                on += ok
                prev_on, last_u = ok, u
            d[f"gt{th}"] = {"pct_time": on / len(ser) * 100 if ser else None,
                            "episodes_per_day": eps / hours * 24 if hours else None}
        out[pool] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket", type=float, default=200)
    ap.add_argument("--min-bps", type=float, nargs="+", default=[0, 5, 10])
    ap.add_argument("--max-tickets", type=int, default=250, help="cap per sample ($50k at $200)")
    a = ap.parse_args()
    db = sqlite3.connect(os.path.join(HERE, "data.db"))
    candles = {}
    for inst in ("USDC-BRL", "USDT-BRL"):
        r = db.execute("SELECT ts_ms, c FROM okx_candles WHERE inst=? ORDER BY ts_ms", (inst,)).fetchall()
        candles[inst] = {"ts": [x[0] for x in r], "c": [x[1] for x in r]}
    cal = spread_calibration(candles)

    samples, meta = defaultdict(dict), {}
    for pool, block, unix, d, s, ain, aout, ex, mid, fee in db.execute(
            "SELECT pool, block, unix, dir, size, amount_in, amount_out, exhausted, dex_mid, fee_pips FROM dex_hist"):
        samples[pool].setdefault(block, {})[(d, s)] = (ain, aout, ex)
        meta[(pool, block)] = (unix, mid, fee)

    res = {"ticket_usd": a.ticket, "min_bps": a.min_bps, "pools": {}, "live": live_section(db, a.ticket, a.min_bps)}
    for p in POOLS:
        if p.key not in samples:
            continue
        inst = p.okx_ref
        hs = (cal.get(inst, {}).get("half_spread_bps") or 0.5) / 1e4
        cts, ccl = candles[inst]["ts"], candles[inst]["c"]
        flow = flow_gross_per_day(db, p)
        seq, chk = [], []
        for block, q in sorted(samples[p.key].items()):
            unix, mid, fee = meta[(p.key, block)]
            k = bisect.bisect_right(cts, unix * 1000) - 1
            if k < 0 or unix * 1000 - cts[k] > 120_000:
                continue
            seq.append((unix, q, ccl[k]))
            e = r0_check(q, mid, fee)
            if e is not None:
                chk.append(abs(e))
        days = max((seq[-1][0] - seq[0][0]) / 86400, 1e-9)
        pr = {"days": days, "n_samples": len(seq), "flow_gross_usd_day": flow,
              "extrap_r0_vs_mid_abs_bps_p50": pct(chk, .5), "extrap_r0_vs_mid_abs_bps_p95": pct(chk, .95),
              "by_min_bps": {}}
        for th in a.min_bps:
            bursts = [burst(q, ref, hs, GAS_USD[p.chain] * ref, a.ticket, th, a.max_tickets) for _, q, ref in seq]
            refs = [ref for _, _, ref in seq]
            up_tr = sum(len(b) for b in bursts)
            up_brl = sum(sum(b) for b in bursts)
            lo_tr = lo_brl = 0.0
            cur = []
            for b in bursts + [[]]:
                if b:
                    if sum(b) > sum(cur):
                        cur = b
                else:
                    lo_tr += len(cur)
                    lo_brl += sum(cur)
                    cur = []
            per_tr = [x for b in bursts for x in b]
            ref_avg = stx.mean(refs)
            up_vol_day = up_tr * a.ticket / days
            scale = min(1.0, flow / up_vol_day) if flow and up_vol_day else None
            pr["by_min_bps"][th] = {
                "pct_samples_with_trade": sum(1 for b in bursts if b) / len(bursts) * 100,
                "brl_per_trade_mean": stx.mean(per_tr) if per_tr else None,
                "brl_per_trade_p50": pct(per_tr, .5),
                "bps_per_trade_mean": stx.mean(per_tr) / (a.ticket * ref_avg) * 1e4 if per_tr else None,
                "tickets_per_burst_p50": pct([len(b) for b in bursts if b], .5),
                "tickets_per_burst_p95": pct([len(b) for b in bursts if b], .95),
                "lower": {"trades_day": lo_tr / days, "brl_day": lo_brl / days},
                "upper": {"trades_day": up_tr / days, "brl_day": up_brl / days},
                "flow_capped": ({"trades_day": up_tr / days * scale, "brl_day": up_brl / days * scale}
                                if scale is not None else None),
            }
        res["pools"][p.key] = pr

    with open(os.path.join(HERE, f"backtest_{int(a.ticket)}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    f = lambda x, n=1: "n/a" if x is None else f"{x:,.{n}f}"  # noqa: E731
    print(f"ticket ${a.ticket:,.0f}")
    for k, pr in res["pools"].items():
        print(f"\n== {k}  {pr['days']:.1f} d, n={pr['n_samples']}, fluxo ${f(pr['flow_gross_usd_day'], 0)}/d, "
              f"extrap r0 vs mid |err| p50 {f(pr['extrap_r0_vs_mid_abs_bps_p50'], 2)} p95 "
              f"{f(pr['extrap_r0_vs_mid_abs_bps_p95'], 2)} bps")
        for th, d in pr["by_min_bps"].items():
            fc = d["flow_capped"] or {}
            print(f"  min {th:>4} bps | amostras c/ trade {f(d['pct_samples_with_trade'])}% | R$/trade média "
                  f"{f(d['brl_per_trade_mean'], 2)} p50 {f(d['brl_per_trade_p50'], 2)} ({f(d['bps_per_trade_mean'])} bps)"
                  f" | tickets/burst p50 {f(d['tickets_per_burst_p50'], 0)} p95 {f(d['tickets_per_burst_p95'], 0)}"
                  f" | R$/dia inf {f(d['lower']['brl_day'], 0)} ({f(d['lower']['trades_day'], 0)} tr)"
                  f" sup {f(d['upper']['brl_day'], 0)} ({f(d['upper']['trades_day'], 0)} tr)"
                  f" fluxo {f(fc.get('brl_day'), 0)} ({f(fc.get('trades_day'), 0)} tr)")
    print("\nlive (15 s):")
    for k, d in res["live"].items():
        print(f"  {k:16s} {d['hours']:.1f} h net@ticket p50 {f(d['net_bps_p50'])} p95 {f(d['net_bps_p95'])} | " +
              " | ".join(f">{th}: {f(d[f'gt{th}']['pct_time'])}% tempo, {f(d[f'gt{th}']['episodes_per_day'])} eps/d"
                         for th in a.min_bps))


if __name__ == "__main__":
    main()
