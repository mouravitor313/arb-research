"""Analysis for item 1 (xvenue_opps live + xvenue_hist backfill). READ-ONLY on arb_tracker.db.

Per (strategy, asset, venue, route, size): net-bps quantiles, % > 0, % > 5 bps, episodes (> 0) and
their duration. Backfill: cbBTC/BTC basis distribution and approx BRL-route net.

    python xvenue_analyze.py [--since 2026-10-11T00:00] [--size 10000]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

import pandas as pd

from cycle_analyze import episodes

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DB = "arb_tracker.db"
BRL_ROUTE_COST = 5.0  # 2+2 bps BRL taker + ~1 bp BTC-BRL half-spread vs BTC-USDC (live)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None)
    ap.add_argument("--size", type=int, default=None, help="only this size")
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    where = f"WHERE ts >= '{a.since}'" if a.since else ""
    df = pd.read_sql(f"SELECT * FROM xvenue_opps {where}", con)
    summary = {"live": [], "hist": []}
    if not df.empty:
        n_ticks = df.ts.nunique()
        gap = pd.to_datetime(pd.Series(sorted(df.ts.unique()))).diff().dt.total_seconds().median()
        print(f"live: {n_ticks} ticks, {df.ts.min()} → {df.ts.max()}, median gap {gap:.0f}s\n")
        df = df[df.ok == 1]
        if a.size:
            df = df[df.size_usd == a.size]
        df = df.assign(block=pd.factorize(df.ts, sort=True)[0])  # episodes() orders by 'block'
        print(f"{'strategy':10} {'asset':9} {'venue':15} {'route':34} {'size':>7} {'p50':>7} {'p95':>7}"
              f" {'max':>7} {'>0%':>6} {'>5%':>6} {'eps':>4} {'medDur':>6}  maker_p50")
        for k, g in df.groupby(["strategy", "asset", "venue", "route", "size_usd"]):
            x = g.net_bps
            ep = episodes(g[["ts", "block", "net_bps"]], 0, max(30, 2.5 * gap))
            st = dict(zip(["strategy", "asset", "venue", "route", "size_usd"], k))
            st.update(n=len(x), p50=x.median(), p95=x.quantile(.95), max=x.max(),
                      pct_gt0=100 * (x > 0).mean(), pct_gt5=100 * (x > 5).mean(), episodes=len(ep),
                      ep_med_dur_s=float(ep.duration_s.median()) if len(ep) else None,
                      gross_p50=g.gross_bps.median(), maker_p50=g.net_bps_maker.median())
            summary["live"].append(st)
            print(f"{k[0]:10} {k[1]:9} {k[2]:15} {k[3]:34} {k[4]:>7,} {st['p50']:7.1f} {st['p95']:7.1f}"
                  f" {st['max']:7.1f} {st['pct_gt0']:6.1f} {st['pct_gt5']:6.1f} {len(ep):4d}"
                  f" {st['ep_med_dur_s'] or 0:6.0f}  "
                  f"{'' if pd.isna(st['maker_p50']) else round(st['maker_p50'], 1)}")
    h = pd.read_sql("SELECT * FROM xvenue_hist", con)
    if not h.empty:
        print(f"\nbackfill cbBTC (Base) vs OKX BTC-USDC: {h.block.nunique()} samples, "
              f"{h.ts.min()} → {h.ts.max()}")
        for s, g in h.groupby("size_usd"):
            basis = ((g.dex_ask + g.dex_bid) / 2 / g.okx_px - 1) * 1e4
            for side, col in (("dex_buy>okx_sell", "buy_gross_bps"), ("okx_buy>dex_sell", "sell_gross_bps")):
                net = g[col] - BRL_ROUTE_COST
                st = {"size_usd": int(s), "route": side, "gross_p50": g[col].median(),
                      "net_brl_p50": net.median(), "net_brl_p95": net.quantile(.95), "net_brl_max": net.max(),
                      "pct_gt0": 100 * (net > 0).mean(), "pct_gt5": 100 * (net > 5).mean(),
                      "basis_p5": basis.quantile(.05), "basis_p50": basis.median(),
                      "basis_p95": basis.quantile(.95)}
                summary["hist"].append(st)
                print(f"  ${s:>7,} {side:18} gross p50 {st['gross_p50']:6.1f} | approx net(BRL) p50 "
                      f"{st['net_brl_p50']:6.1f} p95 {st['net_brl_p95']:6.1f} max {st['net_brl_max']:6.1f}"
                      f" | >0 {st['pct_gt0']:5.1f}% >5 {st['pct_gt5']:5.1f}%")
            print(f"  ${s:>7,} cbBTC mid basis vs BTC (bps): p5 {basis.quantile(.05):.1f} | "
                  f"p50 {basis.median():.1f} | p95 {basis.quantile(.95):.1f}")
    with open("xvenue_analysis.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=float)


if __name__ == "__main__":
    main()
