"""14-day history of the DFB TESOURO/BRZ oracle (drives the Curve DFB BRL Pool v1 price) vs Etherfuse NAV and FX.

READ-ONLY. Oracle rounds via getRoundData on a public Polygon RPC (no archive needed: rounds are stored state).
NAV_BRL(t) reconstructed by compounding back from today's Etherfuse NAV at current_basis_points (approximation:
ignores LTN mark-to-market). Official USD/BRL: frankfurter.app (ECB daily). Crypto FX: OKX USDC-BRL 1H candles.

Series (per sampled round):
  prem_nav  = DFB / NAV_BRL - 1                  -> Curve TESOURO->BRLA edge before slippage (BRL loop, needs Etherfuse BRL rail)
  fx_impl   = DFB * FX_off / NAV_BRL             -> USD/BRL implied by the pool
  usd_loop  = fx_impl / OKX_close - 1 - 2bps     -> mint TESOURO with USDC at NAV, sell to Curve, BRLA->BRL, buy USDC on OKX

    python topics/t6_rwa/tesouro_hist.py [--days 14] [--step 4]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics as st
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import chains  # noqa: E402
from cycle_common import abi_decode, build_w3, encode, multicall  # noqa: E402

ORACLE = "0xc1df935339989f398c59af034fdfc13b2a84c4f2"
RD = ["uint80", "int256", "uint256", "uint256", "uint80"]


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))]


def okx_candles(inst, since_ms):
    out, after = {}, None
    for _ in range(10):
        params = {"instId": inst, "bar": "1H", "limit": "100"}
        if after:
            params["after"] = after
        d = requests.get("https://www.okx.com/api/v5/market/history-candles", params=params, timeout=20).json()["data"]
        time.sleep(0.5)
        if not d:
            break
        for c in d:
            out[int(c[0]) // 1000] = float(c[4])
        after = d[-1][0]
        if int(after) < since_ms:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=14)
    ap.add_argument("--step", type=int, default=4)
    a = ap.parse_args()

    ef = requests.get("https://api.etherfuse.com/lookup/tokens/cost/TESOURO", timeout=20).json()
    nav_now, bps = float(ef["token_cost_in_fiat"]), ef["current_basis_points"]
    t_now = time.time()

    w3 = build_w3(chains.rpc_list("polygon")[0])
    last = abi_decode(RD, multicall(w3, [(ORACLE, encode("latestRoundData()", [], []))])[0][1])
    last_id, last_ts = last[0], last[3]
    rounds = []
    rid = last_id
    while True:
        ids = list(range(rid, max(1, rid - 100 * a.step), -a.step))
        res = multicall(w3, [(ORACLE, encode("getRoundData(uint80)", ["uint80"], [i])) for i in ids])
        stop = False
        for i, (ok, raw) in zip(ids, res):
            if ok and raw:
                r = abi_decode(RD, raw)
                rounds.append((r[3], r[1] / 1e8, i))
                if r[3] < t_now - a.days * 86400:
                    stop = True
        rid = ids[-1] - a.step
        if stop or rid < 1:
            break
    rounds.sort()
    t0 = rounds[0][0]

    d0 = dt.datetime.utcfromtimestamp(t0 - 5 * 86400).date().isoformat()
    fxd = requests.get(f"https://api.frankfurter.app/{d0}..", params={"from": "USD", "to": "BRL"}, timeout=20).json()["rates"]
    fx_days = sorted((k, v["BRL"]) for k, v in fxd.items())
    okx = okx_candles("USDC-BRL", t0 * 1000)

    def fx_off(ts):
        day = dt.datetime.utcfromtimestamp(ts).date().isoformat()
        v = None
        for k, r in fx_days:
            if k <= day:
                v = r
        return v

    rows = []
    for ts, dfb, rid in rounds:
        nav = nav_now / (1 + bps / 1e4) ** ((t_now - ts) / (365 * 86400))
        fo = fx_off(ts)
        hk = int(ts // 3600 * 3600)
        oc = okx.get(hk) or okx.get(hk - 3600)
        row = {"ts": ts, "round": rid, "dfb": dfb, "nav_brl": nav, "prem_nav_bps": (dfb / nav - 1) * 1e4}
        if fo and oc:
            fi = dfb * fo / nav
            row.update(fx_off=fo, okx=oc, fx_impl=fi, okx_vs_off_bps=(oc / fo - 1) * 1e4,
                       usd_loop_bps=(fi / oc - 1 - 2e-4) * 1e4)
        rows.append(row)

    def summ(key):
        xs = [r[key] for r in rows if key in r]
        return {"n": len(xs), "p05": round(pct(xs, .05), 1), "p50": round(pct(xs, .5), 1), "p95": round(pct(xs, .95), 1),
                "min": round(min(xs), 1), "max": round(max(xs), 1), "pct_pos": round(100 * sum(x > 0 for x in xs) / len(xs), 1),
                "mean": round(st.mean(xs), 1)}

    summary = {k: summ(k) for k in ("prem_nav_bps", "okx_vs_off_bps", "usd_loop_bps")}
    span = (rounds[-1][0] - rounds[0][0]) / 86400
    print(f"{len(rounds)} rounds sampled (every {a.step}), span {span:.1f} d, last round {last_id}")
    print(json.dumps(summary, indent=1))
    with open(os.path.join(HERE, "tesouro_hist.json"), "w", encoding="utf-8") as f:
        json.dump({"nav_now": nav_now, "bps": bps, "summary": summary, "rows": rows}, f, indent=0)


if __name__ == "__main__":
    main()
