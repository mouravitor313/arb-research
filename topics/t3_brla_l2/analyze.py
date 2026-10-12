"""Analysis for topic t3: backfill (DEX executable quotes) x OKX 1m candles, + swap-flow summary.

OKX reference at each sample = close of the 1m candle containing the block timestamp, +- median half-spread
(measured in arb_tracker.db:xvenue_ticks, read-only), + depth slippage per size taken from the *current*
OKX book (no historical books exist). Taker 2 bps (BRL pair). Gas from the probe (constant per chain).
Also calibrates the candle-close error vs the live book mid where both exist.

    python analyze.py  -> analysis.json + console tables
"""

from __future__ import annotations

import bisect
import json
import os
import sqlite3
import statistics as stx
from collections import defaultdict

from l2common import HERE, OKX_FEE_BRL_TAKER, POOL_BY_KEY, POOLS, okx_book, okx_buy_base, okx_sell_base

ROOT_DB = os.path.join(os.path.dirname(os.path.dirname(HERE)), "arb_tracker.db")
GAS_USD = {"base": 0.005, "gnosis": 0.0005, "celo": 0.004, "polygon": 0.004}  # probe values, rounded up
SIZES = [500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    f = int(k)
    return xs[f] + (xs[min(f + 1, len(xs) - 1)] - xs[f]) * (k - f)


def spread_calibration(candles):
    """median half-spread (bps) of the live books + |candle close - book mid| error, from xvenue_ticks."""
    out = {}
    try:
        db = sqlite3.connect(f"file:{ROOT_DB}?mode=ro", uri=True)
        ticks = db.execute("SELECT ts, data FROM xvenue_ticks").fetchall()
    except Exception:  # noqa: BLE001
        return {"USDC-BRL": {"half_spread_bps": 0.7}, "USDT-BRL": {"half_spread_bps": 0.1}}
    from datetime import datetime
    for inst in ("USDC-BRL", "USDT-BRL"):
        hs, err = [], []
        cts = candles[inst]["ts"]
        for ts, d in ticks:
            bb = json.loads(d).get(inst)
            if not bb:
                continue
            bid, ask = bb[:2]
            mid = (bid + ask) / 2
            hs.append((ask - bid) / 2 / mid * 1e4)
            unix = datetime.fromisoformat(ts).timestamp()
            k = bisect.bisect_right(cts, unix * 1000) - 1
            if k >= 0 and unix * 1000 - cts[k] < 60_000:
                err.append((candles[inst]["c"][k] / mid - 1) * 1e4)
        out[inst] = {"n": len(hs), "half_spread_bps": stx.median(hs) if hs else None,
                     "candle_close_minus_mid_bps_p50": pct(err, .5), "abs_err_p95": pct([abs(e) for e in err], .95)}
    return out


def depth_slip_bps(book):
    """extra cost vs top of book for buying / selling each size (bps), current book."""
    out = {}
    a0, b0 = book["asks"][0][0], book["bids"][0][0]
    for s in SIZES:
        c = okx_buy_base(book["asks"], s)
        g = okx_sell_base(book["bids"], s)
        out[s] = ((c / s / a0 - 1) * 1e4 if c else None, (1 - g / s / b0) * 1e4 if g else None)
    return out


def main():
    db = sqlite3.connect(os.path.join(HERE, "data.db"))
    candles = {}
    for inst in ("USDC-BRL", "USDT-BRL"):
        r = db.execute("SELECT ts_ms, c FROM okx_candles WHERE inst=? ORDER BY ts_ms", (inst,)).fetchall()
        candles[inst] = {"ts": [x[0] for x in r], "c": [x[1] for x in r]}
    cal = spread_calibration(candles)
    books = {i: okx_book(i) for i in candles}
    slip = {i: depth_slip_bps(b) for i, b in books.items()}
    print("calibração:", json.dumps(cal, indent=1))

    res = {"calibration": cal, "okx_slip_bps_now": {i: {str(k): v for k, v in s.items()} for i, s in slip.items()},
           "pools": {}}
    rows = db.execute("SELECT pool, block, unix, dir, size, amount_in, amount_out, exhausted, dex_mid FROM dex_hist")
    samples = defaultdict(dict)  # pool -> block -> {(dir,size): (...)}
    meta = {}
    for pool, block, unix, d, s, ain, aout, ex, mid in rows:
        samples[pool].setdefault(block, {})[(d, s)] = (ain, aout, ex)
        meta[(pool, block)] = (unix, mid)
    for p in POOLS:
        if p.key not in samples:
            continue
        inst = p.okx_ref
        hs = (cal.get(inst, {}).get("half_spread_bps") or 0.5) / 1e4
        cts, ccl = candles[inst]["ts"], candles[inst]["c"]
        series = defaultdict(list)  # (dir,size) -> [(unix, net)]
        devs = []
        for block, q in sorted(samples[p.key].items()):
            unix, mid_dex = meta[(p.key, block)]
            k = bisect.bisect_right(cts, unix * 1000) - 1
            if k < 0 or unix * 1000 - cts[k] > 120_000:
                continue
            ref = ccl[k]
            bid, ask = ref * (1 - hs), ref * (1 + hs)
            gas_brl = GAS_USD[p.chain] * ref
            for s in SIZES:
                sa, sb = slip[inst][s]
                ain, aout, ex = q[("usd2brla", s)]
                if not ex and sa is not None:
                    cost = ain * ask * (1 + sa / 1e4) * (1 + OKX_FEE_BRL_TAKER)
                    series[("usd2brla", s)].append((unix, (aout - cost - gas_brl) / (ain * ref) * 1e4))
                else:
                    series[("usd2brla", s)].append((unix, None))
                ain, aout, ex = q[("brla2usd", s)]
                if not ex and sb is not None and aout > 0:
                    got = aout * bid * (1 - sb / 1e4) * (1 - OKX_FEE_BRL_TAKER)
                    series[("brla2usd", s)].append((unix, (got - ain - gas_brl) / ain * 1e4))
                else:
                    series[("brla2usd", s)].append((unix, None))
            if mid_dex:
                devs.append((mid_dex / ref - 1) * 1e4)
            else:  # curve: geometric mid of the 500-size quotes (includes the fee both ways)
                a1, o1, _ = q[("usd2brla", 500)]
                a2, o2, _ = q[("brla2usd", 500)]
                if o2:
                    devs.append(((o1 / a1 * a2 / o2) ** 0.5 / ref - 1) * 1e4)
        pr = {"n_samples": len(series[("usd2brla", 500)]),
              "dex_mid_vs_okx_bps": {"p5": pct(devs, .05), "p50": pct(devs, .5), "p95": pct(devs, .95)},
              "by_size": {}}
        step = 1800
        for s in SIZES:
            best = []
            for (u1, x1), (u2, x2) in zip(series[("usd2brla", s)], series[("brla2usd", s)]):
                xs = [x for x in (x1, x2) if x is not None]
                best.append((u1, max(xs) if xs else None))
            d = {}
            for name, ser in (("usd2brla", series[("usd2brla", s)]), ("brla2usd", series[("brla2usd", s)]),
                              ("best", best)):
                v = [x for _, x in ser if x is not None]
                pos = [x for x in v if x > 0]
                # episodes: runs of consecutive samples with net>0
                eps, run, runs = 0, 0, []
                for _, x in ser:
                    if x is not None and x > 0:
                        run += 1
                    else:
                        if run:
                            eps += 1
                            runs.append(run)
                        run = 0
                if run:
                    eps += 1
                    runs.append(run)
                d[name] = {"n_valid": len(v), "n_exhausted": len(ser) - len(v), "p50": pct(v, .5),
                           "p95": pct(v, .95), "p5": pct(v, .05), "pct_pos": (len(pos) / len(v) * 100) if v else None,
                           "episodes": eps, "median_episode_h": (stx.median(runs) * step / 3600) if runs else None,
                           "mean_pos_bps": stx.mean(pos) if pos else None}
            pr["by_size"][s] = d
        # capturable P&L: s* = largest grid size with best net > 0 at the sample; profit = s* x net.
        # upper = re-captured every 30-min sample; lower = once per episode (best sample of the run).
        days = max((max(u for u, _ in series[("usd2brla", 500)]) - min(u for u, _ in series[("usd2brla", 500)]))
                   / 86400, 1e-9)
        per_sample = []
        for idx in range(len(series[("usd2brla", 500)])):
            best_p, best_s = 0.0, 0
            for s in SIZES:
                xs = [series[(d, s)][idx][1] for d in ("usd2brla", "brla2usd")]
                xs = [x for x in xs if x is not None and x > 0]
                if xs and s * max(xs) / 1e4 > best_p:
                    best_p, best_s = s * max(xs) / 1e4, s
            per_sample.append((best_p, best_s))
        lower, cur = 0.0, 0.0
        for bp, _ in per_sample + [(0.0, 0)]:
            if bp > 0:
                cur = max(cur, bp)
            else:
                lower += cur
                cur = 0.0
        pr["pnl_usd_per_day"] = {"upper_every_sample": sum(b for b, _ in per_sample) / days,
                                 "lower_once_per_episode": lower / days,
                                 "median_best_size_when_pos": pct([s for b, s in per_sample if b > 0], .5),
                                 "volume_usd_per_day_upper": sum(s for b, s in per_sample if b > 0) / days}
        res["pools"][p.key] = pr

    # --- swap flow (14 d)
    flow = {}
    for p in POOLS:
        r = db.execute("SELECT block, sender, usd_delta, brla_delta, tx FROM swaps WHERE pool=?", (p.key,)).fetchall()
        if not r:
            continue
        span_blocks = max(x[0] for x in r) - min(x[0] for x in r)
        from l2common import CHAIN_CFG
        days = max(span_blocks * CHAIN_CFG[p.chain]["block_s"] / 86400, 1e-9)
        gross = sum(abs(x[2]) for x in r)
        net_usd_in = sum(x[2] for x in r)  # + = USD into pool (BRLA bought from pool)
        by_sender = defaultdict(float)
        for x in r:
            by_sender[x[1]] += abs(x[2])
        top = sorted(by_sender.items(), key=lambda kv: -kv[1])[:5]
        txs = defaultdict(int)
        for x in r:
            txs[x[1]] += 1
        flow[p.key] = {"days": days, "swaps": len(r), "swaps_per_day": len(r) / days,
                       "gross_usd_per_day": gross / days, "net_usd_in_per_day": net_usd_in / days,
                       "usd_into_pool_per_day": sum(x[2] for x in r if x[2] > 0) / days,
                       "usd_out_of_pool_per_day": -sum(x[2] for x in r if x[2] < 0) / days,
                       "senders": len(by_sender),
                       "top_senders": [(a, v / gross * 100, txs[a]) for a, v in top]}
    res["flow"] = flow

    # --- live collector (15 s ticks vs live OKX book): episode durations at fine resolution
    live = {}
    for key in [r[0] for r in db.execute("SELECT DISTINCT pool FROM live")] if db.execute(
            "SELECT name FROM sqlite_master WHERE name='live'").fetchone() else []:
        lp = {"by_size": {}}
        for s in (500, 1_000, 2_000, 5_000, 10_000):
            r = db.execute("SELECT unix, usd2brla, brla2usd FROM live WHERE pool=? AND size=? ORDER BY unix",
                           (key, s)).fetchall()
            if not r:
                continue
            hours = (r[-1][0] - r[0][0]) / 3600
            best = [(u, max([x for x in (a, b) if x is not None], default=None)) for u, a, b in r]
            v = [x for _, x in best if x is not None]
            durs, start, prev, sum_bps = [], None, None, []
            for u, x in best:
                pos = x is not None and x > 0
                if pos and start is None:
                    start, peak = u, x
                if pos:
                    peak = max(peak, x)
                if start is not None and (not pos or (prev is not None and u - prev > 90)):
                    durs.append(((prev or u) - start) / 60)
                    sum_bps.append(peak)
                    start = None if not pos else u
                prev = u
            if start is not None:
                durs.append((prev - start) / 60)
                sum_bps.append(peak)
            lp["by_size"][s] = {"hours": hours, "ticks": len(r), "p50": pct(v, .5), "p95": pct(v, .95),
                                "pct_pos": len([x for x in v if x > 0]) / len(v) * 100 if v else None,
                                "pct_gt10": len([x for x in v if x > 10]) / len(v) * 100 if v else None,
                                "episodes": len(durs), "episodes_per_day": len(durs) / max(hours / 24, 1e-9),
                                "ep_dur_min_p50": pct(durs, .5), "ep_dur_min_p95": pct(durs, .95),
                                "ep_peak_bps_p50": pct(sum_bps, .5),
                                "pnl_usd_per_day_once_per_episode": sum(sum_bps) * s / 1e4 / max(hours / 24, 1e-9)}
        live[key] = lp
    res["live"] = live
    f = lambda x: "  n/a" if x is None else f"{x:+6.1f}"  # noqa: E731
    for k, lp in live.items():
        for s, d in lp["by_size"].items():
            print(f"live {k:16s} ${s:>6,} {d['hours']:.1f} h p50 {f(d['p50'])} p95 {f(d['p95'])} %>0 "
                  f"{d['pct_pos']:5.1f} %>10 {d['pct_gt10']:5.1f} eps/d {d['episodes_per_day']:5.1f} dur p50 "
                  f"{d['ep_dur_min_p50'] or 0:.1f} min p95 {d['ep_dur_min_p95'] or 0:.1f} pico p50 {f(d['ep_peak_bps_p50'])}"
                  f" P&L/d ${d['pnl_usd_per_day_once_per_episode']:.0f}")
    json.dump(res, open(os.path.join(HERE, "analysis.json"), "w"), indent=1, default=str)

    f = lambda x: "  n/a" if x is None else f"{x:+6.1f}"  # noqa: E731
    for k, pr in res["pools"].items():
        dm = pr["dex_mid_vs_okx_bps"]
        print(f"\n== {k}  n={pr['n_samples']}  mid DEX vs OKX (bps, + = BRLA barato no DEX): "
              f"p5 {f(dm['p5'])} p50 {f(dm['p50'])} p95 {f(dm['p95'])}")
        pl = pr["pnl_usd_per_day"]
        print(f"  P&L/dia: ${pl['lower_once_per_episode']:.0f} (1x por episódio) .. ${pl['upper_every_sample']:.0f}"
              f" (a cada 30 min); tamanho mediano lucrativo ${pl['median_best_size_when_pos'] or 0:,.0f};"
              f" volume teto ${pl['volume_usd_per_day_upper']:,.0f}/dia")
        for s, d in pr["by_size"].items():
            b = d["best"]
            print(f"  ${s:>7,}  best p50 {f(b['p50'])} p95 {f(b['p95'])} %>0 {b['pct_pos'] or 0:5.1f} eps {b['episodes']:3d}"
                  f" (med {b['median_episode_h'] or 0:.1f} h) | usd2brla p50 {f(d['usd2brla']['p50'])} %>0 "
                  f"{d['usd2brla']['pct_pos'] or 0:5.1f} exh {d['usd2brla']['n_exhausted']} | brla2usd p50 "
                  f"{f(d['brla2usd']['p50'])} %>0 {d['brla2usd']['pct_pos'] or 0:5.1f} exh {d['brla2usd']['n_exhausted']}")
    print()
    for k, v in flow.items():
        print(f"{k:18s} {v['days']:.1f} d swaps/d {v['swaps_per_day']:6.1f} gross ${v['gross_usd_per_day']:>9,.0f}/d "
              f"USD in ${v['usd_into_pool_per_day']:>8,.0f} out ${v['usd_out_of_pool_per_day']:>8,.0f} "
              f"net in ${v['net_usd_in_per_day']:>+8,.0f}/d senders {v['senders']} top "
              + ", ".join(f"{a[:8]} {s:.0f}% ({n})" for a, s, n in v["top_senders"][:3]))


if __name__ == "__main__":
    main()
