"""Small-ticket / optimal-swap-size study ($20..$500) over data.db (offline, READ-ONLY, no RPC).

Extends backtest.py (fixed-ticket bursts that walk the pool curve = the bot's own impact) to a ticket grid and adds:
  * DEX curve below $500: CL pools use an exact single-range constant-product branch fitted to the stored
    dex_mid x (1-fee) (exact marginal rate at 0) and the exact $500 point; Curve (no mid) uses backtest.py's linear
    average-rate extrapolation from $500/$1k. Above $500: the stored grid (piecewise linear, as backtest.py).
    Validated against data.db:small_resim (exact re-simulation, optimal_size_resim.py) when present.
  * Q1 fixed ticket x min bps x pool, 3 regimes (lower = 1x per episode, flow-capped, upper = every sample).
  * Q2 per-sample optimal single swap X* (dense search) and the regret of each fixed ticket vs X*.
  * Q3 one swap vs N tickets: with a path-additive curve, N tickets of k == one swap of N*k minus (N-1)*gas.
  * Q4 gas in bps per ticket and as a share of gross profit.
  * Q5 calibration vs the real Polygon bot ($200: R$1.20/trade, ~75 trades/day, R$89.50/day on 28/08).
  * live (15 s) check: amounts rebuilt from stored net bps + top of book, same curve machinery, 1x per episode.

    python optimal_size.py [--tickets 20 50 100 150 200 300 500] [--min-bps 0 5 10]
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
import sqlite3
from collections import defaultdict

import numpy as np

from analyze import GAS_USD, pct, spread_calibration
from backtest import GRID, flow_gross_per_day
from l2common import HERE, OKX_FEE_BRL_TAKER as FEE, POOLS

KEYS = ["gnosis_oku_005", "gnosis_curve", "base_aero_005", "polygon_uni_005"]
CAP_USD = 50_000  # max cumulative size per sample (as backtest.py: 250 x $200)
REAL_BOT = {"brl_per_trade": 1.20, "trades_day": 75, "brl_day": 89.5}  # xend-arb brla, Polygon, $200, 28/08


# ---------------------------------------------------------------- DEX curve per sample/direction
class Curve:
    """out(x) for cumulative input x (USD for usd2brla, BRLA for brla2usd). nan beyond the last usable point."""

    def __init__(self, q, d, mid, fee_pips, mode="cl"):
        pts = []
        for s in GRID:
            if (d, s) not in q:
                break
            ain, aout, ex = q[(d, s)]
            if ex or not aout:
                break
            pts.append((ain, aout))
        self.ok = len(pts) >= 2
        if not self.ok:
            return
        self.xp = np.array([p[0] for p in pts])
        self.yp = np.array([p[1] for p in pts])
        a1, o1 = pts[0]
        self.a1, self.o1 = a1, o1
        self.xmax = self.xp[-1]
        self.mode = "lin"
        if mode == "cl" and mid and fee_pips is not None:
            P = mid if d == "usd2brla" else 1 / mid
            f = fee_pips / 1e6
            ap = a1 * (1 - f)
            den = P * ap / o1 - 1
            if den > 1e-9:
                self.mode, self.P, self.f, self.Xv = "cl", P, f, ap / den
        if self.mode == "lin":
            a2, o2 = pts[1]
            r1, r2 = o1 / a1, o2 / a2
            self.r1, self.r0 = r1, r1 - (r2 - r1) * a1 / (a2 - a1)

    def __call__(self, x):
        x = np.asarray(x, dtype=float)
        if self.mode == "cl":
            xe = x * (1 - self.f)
            small = self.P * xe / (1 + xe / self.Xv)
        else:
            small = x * (self.r0 + (self.r1 - self.r0) * x / self.a1)
        big = np.interp(x, self.xp, self.yp)
        y = np.where(x <= self.a1, small, big)
        return np.where(x <= self.xmax + 1e-9, y, np.nan)


class Sample:
    """one time point of one pool: curves for both directions + OKX reference."""

    def __init__(self, unix, q, mid, fee, bid, ask, ref, kind):
        self.unix, self.bid, self.ask, self.ref = unix, bid, ask, ref
        mode = "cl" if kind == "cl" else "lin"
        self.c = {d: Curve(q, d, mid, fee, mode) for d in ("usd2brla", "brla2usd")}

    def gross(self, d, x):
        """BRL profit before gas of cumulative input x in direction d."""
        y = self.c[d](x)
        if d == "usd2brla":
            return y - x * self.ask * (1 + FEE)
        return y * self.bid * (1 - FEE) - x

    def unit(self, d):  # input-token units per USD of notional
        return 1.0 if d == "usd2brla" else self.ref


def burst(s: Sample, ticket, gas_brl, min_bps):
    """fixed tickets fired while the marginal ticket nets > min_bps. -> (profits array, direction)"""
    best, bd = np.zeros(0), None
    for d, c in s.c.items():
        if not c.ok:
            continue
        step = ticket * s.unit(d)
        k = int(min(c.xmax, CAP_USD * s.unit(d)) // step)
        if k < 1:
            continue
        g = s.gross(d, step * np.arange(k + 1))
        p = np.diff(g) - gas_brl
        ok = np.nan_to_num(p / (ticket * s.ref) * 1e4, nan=-1e9) > min_bps
        n = k if ok.all() else int(np.argmin(ok))
        if p[:n].sum() > best.sum():
            best, bd = p[:n], d
    return best, bd


def optimal(s: Sample, gas_brl, min_bps, npts=320):
    """profit-maximising single swap. -> (profit BRL, X* USD, direction) or (0, 0, None)"""
    best = (0.0, 0.0, None)
    for d, c in s.c.items():
        if not c.ok:
            continue
        u = s.unit(d)
        hi = min(c.xmax, CAP_USD * u)
        if hi <= 10 * u:
            continue
        xs = np.geomspace(10 * u, hi, npts)
        g = s.gross(d, xs) - gas_brl
        bps = g / (xs / u * s.ref) * 1e4
        g = np.where(np.nan_to_num(bps, nan=-1e9) > min_bps, g, -np.inf)
        i = int(np.argmax(g))
        if g[i] > best[0]:
            best = (float(g[i]), float(xs[i] / u), d)
    return best


def paced(seq, ticket, gas_fn, min_bps, days):
    """rate-limited bot (live only): at most 1 ticket per tick. The bot's own impact accumulates (cum input in the
    direction it is trading) and is assumed NOT refilled until the gap closes at size 0 (then cum resets).
    Approximation: the observed pool path already excludes our bot; organic refill within an episode is ignored."""
    cum, dcur, brl, n = 0.0, None, 0.0, 0
    for s in seq:
        gas = gas_fn(s)
        fired = False
        for d in ([dcur] if dcur else list(s.c)):
            c = s.c[d]
            if not c.ok:
                continue
            step = ticket * s.unit(d)
            g = s.gross(d, np.array([cum, cum + step]))
            p = float(g[1] - g[0]) - gas
            if np.isfinite(p) and p / (ticket * s.ref) * 1e4 > min_bps:
                brl, n, cum, dcur, fired = brl + p, n + 1, cum + step, d, True
                break
        if not fired and dcur:
            c = s.c[dcur]
            step = ticket * s.unit(dcur)
            g0 = float(s.gross(dcur, np.array([0.0, step]))[1]) - gas if c.ok else -1
            if not (np.isfinite(g0) and g0 / (ticket * s.ref) * 1e4 > min_bps):
                cum, dcur = 0.0, None
    return {"brl_day": brl / days, "trades_day": n / days, "brl_per_trade": brl / n if n else None}


# ---------------------------------------------------------------- regimes
def regimes(per_sample, days, vol_per_sample, flow):
    """per_sample: list of (brl, n_trades). lower = best burst per episode; upper = all; flow-capped."""
    up_brl = sum(b for b, _ in per_sample)
    up_tr = sum(n for _, n in per_sample)
    lo_brl = lo_tr = 0.0
    cur = (0.0, 0)
    for b, n in per_sample + [(0.0, 0)]:
        if n:
            if b > cur[0]:
                cur = (b, n)
        else:
            lo_brl += cur[0]
            lo_tr += cur[1]
            cur = (0.0, 0)
    vol_day = sum(vol_per_sample) / days
    scale = min(1.0, flow / vol_day) if flow and vol_day else None
    return {"lower": {"brl_day": lo_brl / days, "trades_day": lo_tr / days},
            "upper": {"brl_day": up_brl / days, "trades_day": up_tr / days},
            "flow_capped": ({"brl_day": up_brl / days * scale, "trades_day": up_tr / days * scale}
                            if scale is not None else None),
            "upper_vol_usd_day": vol_day}


def episodes(series, step_s):
    """series [(unix, bool)] -> (n episodes, median duration min); gap > 3 steps breaks an episode."""
    eps, durs, start, last = 0, [], None, None
    for u, on in series:
        if last is not None and u - last > 3 * step_s and start is not None:
            durs.append((last - start) / 60)
            start = None
        if on and start is None:
            start, eps = u, eps + 1
        if not on and start is not None:
            durs.append((u - start) / 60)
            start = None
        last = u
    if start is not None:
        durs.append((last - start) / 60)
    return eps, (pct(durs, .5) if durs else None)


# ---------------------------------------------------------------- loading
def load_hist(db, cal, candles):
    pmap = {p.key: p for p in POOLS}
    raw, meta = defaultdict(dict), {}
    for pool, block, unix, d, s, ain, aout, ex, mid, fee in db.execute(
            "SELECT pool, block, unix, dir, size, amount_in, amount_out, exhausted, dex_mid, fee_pips FROM dex_hist"):
        if pool in KEYS:
            raw[pool].setdefault(block, {})[(d, s)] = (ain, aout, ex)
            meta[(pool, block)] = (unix, mid, fee)
    out = {}
    for key, blocks in raw.items():
        p = pmap[key]
        hs = (cal.get(p.okx_ref, {}).get("half_spread_bps") or 0.5) / 1e4
        cts, ccl = candles[p.okx_ref]["ts"], candles[p.okx_ref]["c"]
        seq = []
        for block, q in sorted(blocks.items()):
            unix, mid, fee = meta[(key, block)]
            k = bisect.bisect_right(cts, unix * 1000) - 1
            if k < 0 or unix * 1000 - cts[k] > 120_000:
                continue
            ref = ccl[k]
            seq.append((block, Sample(unix, q, mid, fee, ref * (1 - hs), ref * (1 + hs), ref, p.kind)))
        out[key] = seq
    return out


def load_live(db):
    """rebuild DEX amounts from the stored net bps (collector: top-of-book cost, gas = GAS_USD x okx mid)."""
    pmap = {p.key: p for p in POOLS}
    rows = db.execute("SELECT unix, pool, size, usd2brla, brla2usd, dex_mid, okx_bid, okx_ask FROM live "
                      "ORDER BY unix").fetchall()
    by = defaultdict(dict)
    for unix, pool, s, a, b, dmid, bid, ask in rows:
        by[pool].setdefault(unix, {"dmid": dmid, "bid": bid, "ask": ask, "q": {}})
        e = by[pool][unix]
        mid = (bid + ask) / 2
        gas = GAS_USD[pmap[pool].chain] * mid
        if a is None:
            e["q"][("usd2brla", s)] = (s, 0.0, 1)
        else:
            e["q"][("usd2brla", s)] = (s, a / 1e4 * s * mid + s * ask * (1 + FEE) + gas, 0)
        bin_ = s * mid
        if b is None:
            e["q"][("brla2usd", s)] = (bin_, 0.0, 1)
        else:
            e["q"][("brla2usd", s)] = (bin_, (b / 1e4 * bin_ + bin_ + gas) / (bid * (1 - FEE)), 0)
    out = {}
    for pool, ticks in by.items():
        p = pmap[pool]
        fee = 500 if p.kind == "cl" else None  # live has no fee column; all three CL pools are 0.05%
        out[pool] = [Sample(u, e["q"], e["dmid"], fee, e["bid"], e["ask"], (e["bid"] + e["ask"]) / 2, p.kind)
                     for u, e in sorted(ticks.items())]
    return out


# ---------------------------------------------------------------- validation vs exact re-sim
def validate(db, hist):
    try:
        rows = db.execute("SELECT pool, block, dir, size, amount_out, exhausted FROM small_resim").fetchall()
    except sqlite3.OperationalError:
        return None
    smap = {k: dict(v) for k, v in hist.items()}
    errs = defaultdict(lambda: defaultdict(list))
    for pool, block, d, s, exact, ex in rows:
        sm = smap.get(pool, {}).get(block)
        if sm is None or ex or not exact or not sm.c[d].ok:
            continue
        x = s * (1 if d == "usd2brla" else 5.0)  # resim/backfill convention: brla2usd input = size * 5 BRLA
        for mode in ("cl", "lin"):
            if mode == "cl" and sm.c[d].ok and sm.c[d].mode != "cl":
                continue
            c = sm.c[d] if mode == sm.c[d].mode else Curve(_q_of(sm, d), d, None, None, "lin")
            if not c.ok:
                continue
            errs[pool][(mode, s)].append(float((c(x) / exact - 1) * 1e4))
    res = {}
    for pool, e in errs.items():
        res[pool] = {f"{m}@{s}": {"n": len(v), "abs_p50": pct([abs(x) for x in v], .5),
                                   "abs_p95": pct([abs(x) for x in v], .95), "bias_p50": pct(v, .5)}
                     for (m, s), v in sorted(e.items(), key=lambda kv: (kv[0][0], kv[0][1]))}
    return res


def _q_of(sm: Sample, d):
    c = sm.c[d]
    return {(d, int(GRID[i])): (float(c.xp[i]), float(c.yp[i]), 0) for i in range(len(c.xp))}


# ---------------------------------------------------------------- main
def run_pool(seq, gas_brl_fn, tickets, thresholds, days, flow, step_s, with_upper=True):
    pr = {"days": days, "n_samples": len(seq), "flow_gross_usd_day": flow, "fixed": {}, "optimal": {}}
    opts = {}
    for th in thresholds:
        o = [optimal(s, gas_brl_fn(s), th) for s in seq]
        opts[th] = o
        xs = [x for g, x, d in o if d]
        reg = regimes([(g, 1 if d else 0) for g, x, d in o], days, [x for g, x, d in o if d], flow)
        pr["optimal"][th] = {"pct_samples": len(xs) / len(seq) * 100 if seq else None,
                             "xstar_usd_p25": pct(xs, .25), "xstar_usd_p50": pct(xs, .5),
                             "xstar_usd_p75": pct(xs, .75), "xstar_usd_p95": pct(xs, .95),
                             "brl_per_swap_mean": float(np.mean([g for g, x, d in o if d])) if xs else None,
                             **reg,
                             "episodes": episodes([(s.unix, bool(d)) for s, (g, x, d) in zip(seq, o)], step_s)}
    for t in tickets:
        pr["fixed"][t] = {}
        for th in thresholds:
            bs = [burst(s, t, gas_brl_fn(s), th)[0] for s in seq]
            per_tr = np.concatenate(bs) if bs else np.zeros(0)
            refs = np.mean([s.ref for s in seq])
            o = opts[th]
            opt_sum = sum(g for g, x, d in o if d)
            gas_extra = sum(max(len(b) - 1, 0) * gas_brl_fn(s) for b, s in zip(bs, seq))
            reg = regimes([(float(b.sum()), len(b)) for b in bs], days, [len(b) * t for b in bs], flow)
            gas_sum = sum(len(b) * gas_brl_fn(s) for b, s in zip(bs, seq))
            ep = episodes([(s.unix, len(b) > 0) for s, b in zip(seq, bs)], step_s)
            # lower-regime regret: per episode best burst vs best optimal single swap
            d = {"pct_samples_with_trade": sum(1 for b in bs if len(b)) / len(bs) * 100 if bs else None,
                 "brl_per_trade_mean": float(per_tr.mean()) if len(per_tr) else None,
                 "brl_per_trade_p50": pct(per_tr.tolist(), .5),
                 "bps_per_trade_mean": float(per_tr.mean() / (t * refs) * 1e4) if len(per_tr) else None,
                 "tickets_per_burst_p50": pct([len(b) for b in bs if len(b)], .5),
                 "tickets_per_burst_p95": pct([len(b) for b in bs if len(b)], .95),
                 **reg,
                 "episodes_n_median_min": ep,
                 "capture_upper_vs_optimal": (float(sum(b.sum() for b in bs)) / opt_sum) if opt_sum else None,
                 "q3_extra_gas_vs_one_swap_brl_day": gas_extra / days,
                 "q3_extra_gas_pct_of_profit": (gas_extra / float(sum(b.sum() for b in bs)) * 100
                                                if sum(b.sum() for b in bs) > 0 else None),
                 "q4_gas_bps": None, "q4_gas_share_of_gross_pct": (gas_sum / (float(per_tr.sum()) + gas_sum) * 100
                                                                    if len(per_tr) else None)}
            if not with_upper:
                d["paced_1_per_tick"] = paced(seq, t, gas_brl_fn, th, days)
            pr["fixed"][t][th] = d
    if not with_upper:
        for blk in list(pr["fixed"].values()) + [pr["optimal"]]:
            for d in blk.values():
                d.pop("upper", None)
                d.pop("flow_capped", None)
    return pr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickets", type=float, nargs="+", default=[20, 50, 100, 150, 200, 300, 500])
    ap.add_argument("--min-bps", type=float, nargs="+", default=[0, 5, 10])
    ap.add_argument("--no-live", action="store_true")
    a = ap.parse_args()
    tickets = [int(t) if float(t).is_integer() else t for t in a.tickets]
    db = sqlite3.connect(f"file:{os.path.join(HERE, 'data.db')}?mode=ro", uri=True)
    candles = {}
    for inst in ("USDC-BRL", "USDT-BRL"):
        r = db.execute("SELECT ts_ms, c FROM okx_candles WHERE inst=? ORDER BY ts_ms", (inst,)).fetchall()
        candles[inst] = {"ts": [x[0] for x in r], "c": [x[1] for x in r]}
    cal = spread_calibration(candles)
    pmap = {p.key: p for p in POOLS}
    hist = load_hist(db, cal, candles)

    res = {"tickets": tickets, "min_bps": a.min_bps, "real_bot": REAL_BOT, "gas_usd": GAS_USD,
           "validation_vs_resim": validate(db, hist), "pools": {}, "live": {}}
    for key in KEYS:
        seq = [s for _, s in hist.get(key, [])]
        if not seq:
            continue
        p = pmap[key]
        days = (seq[-1].unix - seq[0].unix) / 86400
        pr = run_pool(seq, lambda s, c=p.chain: GAS_USD[c] * s.ref, tickets, a.min_bps, days,
                      flow_gross_per_day(db, p), 1800)
        cm = {"cl": 0, "lin": 0, "none": 0}
        for s in seq:
            c = s.c["usd2brla"]
            cm[c.mode if c.ok else "none"] += 1
        pr["small_branch_modes_usd2brla"] = cm
        for t in tickets:
            for th in a.min_bps:
                pr["fixed"][t][th]["q4_gas_bps"] = GAS_USD[p.chain] / t * 1e4
        res["pools"][key] = pr

    # Q5 calibration on Polygon @ $200, min 0
    try:
        poly = res["pools"]["polygon_uni_005"]["fixed"][200][a.min_bps[0]]
        k = {"k_brl_per_trade": REAL_BOT["brl_per_trade"] / poly["brl_per_trade_mean"],
             "k_trades_day": REAL_BOT["trades_day"] / poly["lower"]["trades_day"],
             "k_brl_day": REAL_BOT["brl_day"] / poly["lower"]["brl_day"]}
    except (KeyError, TypeError, ZeroDivisionError):
        k = None
    res["calibration"] = k
    if k:
        for pr in res["pools"].values():
            for t, by in pr["fixed"].items():
                for th, d in by.items():
                    d["calibrated"] = {"brl_per_trade": (d["brl_per_trade_mean"] or 0) * k["k_brl_per_trade"],
                                       "trades_day": d["lower"]["trades_day"] * k["k_trades_day"],
                                       "brl_day": d["lower"]["brl_day"] * k["k_brl_day"]}
            for th, d in pr["optimal"].items():
                d["calibrated_brl_day"] = d["lower"]["brl_day"] * k["k_brl_day"]

    if not a.no_live:
        live = load_live(db)
        for key in KEYS:
            seq = live.get(key, [])
            if len(seq) < 2:
                continue
            p = pmap[key]
            hours = (seq[-1].unix - seq[0].unix) / 3600
            lr = run_pool(seq, lambda s, c=p.chain: GAS_USD[c] * s.ref, tickets, a.min_bps, hours / 24, None, 15,
                          with_upper=False)
            lr["hours"] = hours
            lr["first_unix"], lr["last_unix"] = seq[0].unix, seq[-1].unix
            # single-ticket net bps distribution (first ticket only) and % of time above thresholds
            for t in tickets:
                nets = []
                for s in seq:
                    best = None
                    for d, c in s.c.items():
                        if not c.ok:
                            continue
                        x = t * s.unit(d)
                        g = float(s.gross(d, np.array([0.0, x]))[1]) - GAS_USD[p.chain] * s.ref
                        if np.isfinite(g):
                            v = g / (t * s.ref) * 1e4
                            best = v if best is None else max(best, v)
                    nets.append(best)
                vv = [x for x in nets if x is not None]
                lr["fixed"][t]["first_ticket_net_bps"] = {
                    "p50": pct(vv, .5), "p95": pct(vv, .95),
                    **{f"pct_time_gt{th}": sum(1 for x in vv if x > th) / len(nets) * 100 for th in a.min_bps}}
            res["live"][key] = lr

    with open(os.path.join(HERE, "optimal_size.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    report(res, a.min_bps)


def report(res, thresholds):
    f = lambda x, n=1: "n/a" if x is None else f"{x:,.{n}f}"  # noqa: E731
    print("calibração:", {k: round(v, 3) for k, v in (res["calibration"] or {}).items()})
    v = res["validation_vs_resim"] or {}
    for pool, e in v.items():
        print(f"valid {pool:16s} " + " ".join(f"{k}:{f(d['abs_p95'], 2)}" for k, d in e.items()))
    for key, pr in res["pools"].items():
        print(f"\n== {key}  {pr['days']:.1f} d n={pr['n_samples']} fluxo ${f(pr['flow_gross_usd_day'], 0)}/d "
              f"ramo pequeno {pr['small_branch_modes_usd2brla']}")
        for th in thresholds:
            o = pr["optimal"][th]
            print(f"  min {th:>3} ÓTIMO X* p25/50/75/95 {f(o['xstar_usd_p25'], 0)}/{f(o['xstar_usd_p50'], 0)}/"
                  f"{f(o['xstar_usd_p75'], 0)}/{f(o['xstar_usd_p95'], 0)}  R$/swap {f(o['brl_per_swap_mean'], 2)} "
                  f"R$/d inf {f(o['lower']['brl_day'], 0)} ({f(o['lower']['trades_day'], 0)}) sup "
                  f"{f(o['upper']['brl_day'], 0)} fluxo {f((o['flow_capped'] or {}).get('brl_day'), 0)}")
            for t, by in pr["fixed"].items():
                d = by[th]
                fc, cb = d["flow_capped"] or {}, d.get("calibrated") or {}
                print(f"   ${t:>4} R$/tr {f(d['brl_per_trade_mean'], 2)} ({f(d['bps_per_trade_mean'])} bps) "
                      f"tk/burst {f(d['tickets_per_burst_p50'], 0)}/{f(d['tickets_per_burst_p95'], 0)} | inf "
                      f"{f(d['lower']['brl_day'], 0)} ({f(d['lower']['trades_day'], 0)} tr) fluxo "
                      f"{f(fc.get('brl_day'), 0)} ({f(fc.get('trades_day'), 0)}) sup {f(d['upper']['brl_day'], 0)} "
                      f"({f(d['upper']['trades_day'], 0)}) | calib {f(cb.get('brl_day'), 0)} R$/d "
                      f"{f(cb.get('trades_day'), 0)} tr | captura {f(d['capture_upper_vs_optimal'], 2)} "
                      f"gás {f(d['q4_gas_bps'], 2)} bps ({f(d['q4_gas_share_of_gross_pct'])}% bruto) "
                      f"N-1 gás {f(d['q3_extra_gas_pct_of_profit'])}%")
    for key, lr in res["live"].items():
        print(f"\nlive {key} {lr['hours']:.1f} h")
        for th in thresholds:
            o = lr["optimal"][th]
            print(f"  min {th:>3} ÓTIMO X* p50 {f(o['xstar_usd_p50'], 0)} p95 {f(o['xstar_usd_p95'], 0)} "
                  f"R$/d inf {f(o['lower']['brl_day'], 0)} eps {o['episodes']}")
            for t, by in lr["fixed"].items():
                d = by[th]
                ft = by["first_ticket_net_bps"]
                print(f"   ${t:>4} R$/tr {f(d['brl_per_trade_mean'], 2)} inf R$/d {f(d['lower']['brl_day'], 0)} "
                      f"({f(d['lower']['trades_day'], 0)} tr) eps(n, med min) {d['episodes_n_median_min']} | 1/tick "
                      f"{f(d['paced_1_per_tick']['brl_day'], 0)} R$/d ({f(d['paced_1_per_tick']['trades_day'], 0)} tr, "
                      f"{f(d['paced_1_per_tick']['brl_per_trade'], 2)}/tr) | 1º ticket "
                      f"p50 {f(ft['p50'])} p95 {f(ft['p95'])} %t>{th} {f(ft[f'pct_time_gt{th}'])}")


if __name__ == "__main__":
    main()
