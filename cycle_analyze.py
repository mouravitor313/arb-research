"""Step 3 — analysis of the Polygon cycle data (cycle_quotes / cycle_quotes_hist).

READ-ONLY on arb_tracker.db. Prints:
  * net-bps distribution per (direction, route, size): quantiles, % > 0, % > 5 bps, text histogram
  * "best of anything" per sample and size (max over direction × route)
  * profitable episodes (consecutive samples > threshold): count and duration
  * mid-price drivers: which pool explains the mid-cycle deviation
  * (live only) correlation with swaps on the cycle pools (tx.from → xend-arb bots)

    python cycle_analyze.py                # live table
    python cycle_analyze.py --hist         # backfill table
    python cycle_analyze.py --since 2026-10-10T00:00
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = "arb_tracker.db"
BINS = [-1e9, -100, -50, -40, -30, -20, -10, -5, 0, 5, 10, 20, 50, 1e9]


def text_hist(s: pd.Series) -> str:
    cats = pd.cut(s, BINS, right=False).value_counts(sort=False)
    tot = max(1, len(s))
    lines = []
    for iv, n in cats.items():
        lo = "-inf" if iv.left < -1e8 else f"{iv.left:g}"
        hi = "+inf" if iv.right > 1e8 else f"{iv.right:g}"
        lines.append(f"    [{lo:>5},{hi:>5}) {n:6d} {100*n/tot:5.1f}% {'#' * int(50*n/tot)}")
    return "\n".join(lines)


def episodes(df: pd.DataFrame, thr: float, gap_s: float) -> pd.DataFrame:
    """Runs of consecutive samples with net_bps > thr. Returns start, end, n, duration_s, peak."""
    d = df.sort_values("block")
    t = pd.to_datetime(d["ts"])
    above = d["net_bps"] > thr
    out, start, last_t, peak, n = [], None, None, None, 0
    for ti, a, v, b in zip(t, above, d["net_bps"], d["block"]):
        if a and start is not None and (ti - last_t).total_seconds() <= gap_s:
            last_t, peak, n = ti, max(peak, v), n + 1
            continue
        if start is not None:
            out.append((start, last_t, n, (last_t - start).total_seconds(), peak))
            start = None
        if a:
            start, last_t, peak, n = ti, ti, v, 1
    if start is not None:
        out.append((start, last_t, n, (last_t - start).total_seconds(), peak))
    return pd.DataFrame(out, columns=["start", "end", "n", "duration_s", "peak_bps"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hist", action="store_true")
    ap.add_argument("--since", default=None)
    a = ap.parse_args()
    qt, tt = ("cycle_quotes_hist", "cycle_ticks_hist") if a.hist else ("cycle_quotes", "cycle_ticks")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    where = f"WHERE ts >= '{a.since}'" if a.since else ""
    q = pd.read_sql(f"SELECT * FROM {qt} {where}", con)
    ticks = pd.read_sql(f"SELECT * FROM {tt} {where}", con)
    if q.empty:
        print("no data")
        return
    n_samples = q["block"].nunique()
    t0, t1 = q["ts"].min(), q["ts"].max()
    med_gap = pd.to_datetime(ticks.sort_values("block")["ts"]).diff().dt.total_seconds().median()
    gap_s = max(30.0, 2.5 * (med_gap or 12))
    print(f"table {qt}: {n_samples} samples, {t0} → {t1}, median sample gap {med_gap:.0f}s\n")
    summary = {"table": qt, "samples": int(n_samples), "from": t0, "to": t1, "groups": [], "best": []}

    valid = q[(q["ok"] == 1) & (q["exhausted"] == 0)]
    print("=== net bps per (direction, route, size) — excl. failed/exhausted quotes ===")
    for (d, r, s), g in valid.groupby(["direction", "route", "size_usd"]):
        n_all = len(q[(q.direction == d) & (q.route == r) & (q.size_usd == s)])
        x = g["net_bps"]
        st = {"direction": d, "route": r, "size_usd": int(s), "n": int(len(x)),
              "exhausted_or_failed_pct": round(100 * (1 - len(x) / max(1, n_all)), 1),
              "p5": x.quantile(.05), "p25": x.quantile(.25), "p50": x.median(),
              "p75": x.quantile(.75), "p95": x.quantile(.95), "max": x.max(),
              "pct_gt0": 100 * (x > 0).mean(), "pct_gt5": 100 * (x > 5).mean(),
              "gas_usd_med": g["gas_usd"].median()}
        summary["groups"].append(st)
        print(f"\n{d} {r} ${s:,}: n={st['n']} (exhausted/failed {st['exhausted_or_failed_pct']}%)  "
              f"p5 {st['p5']:.1f} | p50 {st['p50']:.1f} | p95 {st['p95']:.1f} | max {st['max']:.1f} bps"
              f"  | >0: {st['pct_gt0']:.2f}%  >5: {st['pct_gt5']:.2f}%  | gas ${st['gas_usd_med']:.4f}")
        if s <= 10_000:
            print(text_hist(x))

    print("\n=== best of anything per sample (max over direction × route), per size ===")
    for s, g in valid.groupby("size_usd"):
        b = g.groupby("block").agg(ts=("ts", "first"), net_bps=("net_bps", "max")).reset_index()
        ep0, ep5 = episodes(b, 0, gap_s), episodes(b, 5, gap_s)
        st = {"size_usd": int(s), "p50": b.net_bps.median(), "p95": b.net_bps.quantile(.95),
              "max": b.net_bps.max(), "pct_gt0": 100 * (b.net_bps > 0).mean(),
              "pct_gt5": 100 * (b.net_bps > 5).mean(), "episodes_gt0": len(ep0),
              "episodes_gt5": len(ep5),
              "ep_gt0_median_dur_s": float(ep0.duration_s.median()) if len(ep0) else None,
              "ep_gt0_max_dur_s": float(ep0.duration_s.max()) if len(ep0) else None}
        summary["best"].append(st)
        print(f"${s:>7,}: p50 {st['p50']:.1f} | p95 {st['p95']:.1f} | max {st['max']:.1f} bps | "
              f">0 {st['pct_gt0']:.2f}% ({len(ep0)} episodes) | >5 {st['pct_gt5']:.2f}% ({len(ep5)} episodes)")
        if len(ep0):
            print(f"         episode duration (s): median {st['ep_gt0_median_dur_s']:.0f}, "
                  f"max {st['ep_gt0_max_dur_s']:.0f}; top peaks:")
            print(ep0.sort_values("peak_bps", ascending=False).head(5).to_string(index=False))

    if not ticks.empty:
        print("\n=== mid-price drivers (spot, no fees) ===")
        m = ticks["mid_cycle_fwd_bps"]
        print(f"mid_cycle_fwd (v3 bridge) bps: p5 {m.quantile(.05):.1f} | p50 {m.median():.1f} | "
              f"p95 {m.quantile(.95):.1f} | min {m.min():.1f} | max {m.max():.1f}")
        for col, lab in (("mid_cycle_fwd_curve_bps", "fwd, curve bridge BRLA->BRZ"),
                         ("mid_cycle_rev_curve_bps", "rev, curve bridge BRZ->BRLA")):
            mc = ticks[col].dropna()
            if len(mc):
                print(f"mid_cycle {lab} (1 unit, incl. 0.03% curve fee) bps: p5 {mc.quantile(.05):.1f}"
                      f" | p50 {mc.median():.1f} | p95 {mc.quantile(.95):.1f} | max {mc.max():.1f}")
        import numpy as np
        lg = pd.DataFrame({
            "usdc_brla": np.log(ticks.brla_per_usdc), "brz_usdt0": np.log(ticks.brz_per_usdt0),
            "brz_brla_v3": np.log(ticks.brla_per_brz_v3), "usdt0_usdc": np.log(ticks.usdt0_per_usdc_v3)})
        dev = lg - lg.median()
        print("std of each pool's log-price deviation (bps):",
              {k: round(float(v) * 1e4, 1) for k, v in dev.std().items()})
        summary["mid"] = {"p5": m.quantile(.05), "p50": m.median(), "p95": m.quantile(.95)}

    if not a.hist:
        sw = pd.read_sql("SELECT * FROM cycle_pool_swaps", con)
        if not sw.empty:
            print("\n=== swaps on cycle pools (live window) ===")
            print(sw.groupby("pool").size().to_string())
            top = (sw[sw.pool != "usdc_usdt0_v4"].groupby(["pool", "tx_from"]).size()
                   .rename("n").reset_index().sort_values("n", ascending=False))
            print("\ntop tx.from per pool (likely xend-arb bots = dominant senders on brz_usdt0 / usdc_brla):")
            print(top.groupby("pool").head(3).to_string(index=False))
            # net bps of best $1k cycle within 3 blocks after a swap on a BRL pool vs elsewhere
            b1 = valid[valid.size_usd == 1000].groupby("block").net_bps.max()
            brl_blocks = set(sw[sw.pool != "usdc_usdt0_v4"].block)
            near = b1[[any((bb - k) in brl_blocks for k in range(0, 4)) for bb in b1.index]]
            far = b1.drop(near.index)
            if len(near) and len(far):
                print(f"\nbest $1k net bps: ≤3 blocks after a BRL-pool swap: median {near.median():.1f} "
                      f"(n={len(near)}), p95 {near.quantile(.95):.1f} | otherwise: median "
                      f"{far.median():.1f} (n={len(far)}), p95 {far.quantile(.95):.1f}")
            summary["swaps_by_pool"] = sw.groupby("pool").size().to_dict()

    with open("cycle_analysis_hist.json" if a.hist else "cycle_analysis.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=float)


if __name__ == "__main__":
    main()
