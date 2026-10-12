"""t2_usdg — analyse data.db: (1) full ticks (opps) and (2) fast OKX ticks × latest DEX quote. Writes analysis.json."""
from __future__ import annotations

import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def stats(v, ts=None, gap_s=60):
    v = np.array(v, float)
    out = {"n": len(v), "p50": round(float(np.median(v)), 2), "p95": round(float(np.percentile(v, 95)), 2),
           "max": round(float(v.max()), 2), "pct_pos": round(float((v > 0).mean() * 100), 2)}
    if ts is not None:  # episodes = runs of consecutive positive ticks (gap ≤ gap_s)
        eps, cur, last = [], None, None
        for t, x in zip(ts, v):
            t = datetime.fromisoformat(t).timestamp()
            if x > 0:
                if cur and t - last <= gap_s:
                    cur[1], cur[2] = t, max(cur[2], x)
                else:
                    cur = [t, t, x]
                    eps.append(cur)
                last = t
            else:
                cur = None
        out["episodes"] = len(eps)
        out["ep_dur_s_med"] = float(np.median([e[1] - e[0] for e in eps])) if eps else None
        out["ep_peak_bps_med"] = round(float(np.median([e[2] for e in eps])), 2) if eps else None
    return out


def main():
    db = sqlite3.connect(os.path.join(HERE, "data.db"))
    res = {"full": {}, "fast": {}}
    span = db.execute("select min(ts), max(ts), count(distinct ts) from opps").fetchone()
    res["full_span"] = span
    g = defaultdict(lambda: ([], [], []))
    for strat, ven, x, sz, net, mk, ts in db.execute(
            "select strategy, venue, stable, size_usd, net_bps, net_bps_maker, ts from opps where net_bps is not null order by ts"):
        k = f"{strat}|{ven}|{x}|{sz}"
        g[k][0].append(net); g[k][1].append(mk if mk is not None else np.nan); g[k][2].append(ts)
    for k, (n, m, ts) in sorted(g.items()):
        res["full"][k] = {"net": stats(n, ts, gap_s=400), "maker_p50": round(float(np.nanmedian(m)), 2) if not np.all(np.isnan(m)) else None}
    # fast: OKX leg every ~10 s × most recent DEX price for (venue, x, size, direction)
    dex = defaultdict(list)  # (strat, venue, x, size) -> [(ts, dex_px, gas_bps)]
    for strat, ven, x, sz, px, gas, ts in db.execute(
            "select strategy, venue, stable, size_usd, dex_px, gas_usd, ts from opps where strategy like 'dex_%' and dex_px is not null order by ts"):
        dex[(strat, ven, x, sz)].append((ts, px, gas / sz * 1e4))
    fast = db.execute("select ts, x, size_usd, sell_g_x, buy_g_x from fast order by ts").fetchall()
    res["fast_span"] = (fast[0][0], fast[-1][0], len(fast) // 6) if fast else None
    acc = defaultdict(lambda: ([], []))
    for (strat, ven, x, sz), q in dex.items():
        qi = 0
        for ts, fx, fsz, sgx, bgx in fast:
            if fx != x or fsz != sz:
                continue
            while qi + 1 < len(q) and q[qi + 1][0] <= ts:
                qi += 1
            if q[qi][0] > ts:
                continue
            _, px, gb = q[qi]
            if strat == "dex_buy" and sgx:
                v = (sgx / px - 1) * 1e4 - gb      # px = X paid per USDG on DEX
            elif strat == "dex_sell" and bgx:
                v = (bgx * px - 1) * 1e4 - gb      # px = X received per USDG on DEX
            else:
                continue
            acc[f"{strat}|{ven}|{x}|{sz}"][0].append(v)
            acc[f"{strat}|{ven}|{x}|{sz}"][1].append(ts)
    for k, (v, ts) in sorted(acc.items()):
        res["fast"][k] = stats(v, ts, gap_s=30)
    json.dump(res, open(os.path.join(HERE, "analysis.json"), "w"), indent=1)
    print("full span", span, "| fast span", res["fast_span"])
    print(f"{'key':42} {'n':>5} {'p50':>7} {'p95':>7} {'max':>7} {'%>0':>6} {'eps':>4} {'dur_s':>6} {'mk_p50':>7}")
    for k, s in res["fast"].items():
        mk = res["full"].get(k, {}).get("maker_p50")
        print(f"{k:42} {s['n']:>5} {s['p50']:>7} {s['p95']:>7} {s['max']:>7} {s['pct_pos']:>6} {s['episodes']:>4} "
              f"{str(s['ep_dur_s_med']):>6} {str(mk):>7}")


if __name__ == "__main__":
    main()
