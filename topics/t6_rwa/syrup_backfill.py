"""Coarse archive backfill (Ethereum): Uniswap v4 mid price of syrupUSDC/USDC and syrupUSDT/USDT vs on-chain NAV
(convertToExitAssets), plus the USDY oracle, one multicall per sampled block.

READ-ONLY eth_call. Archive needs the paid RPC: opt-in with --paid (counts requests; URL never printed).
Cached per block in syrup_backfill_cache.json so re-runs cost nothing.

mid_dev = pool mid / NAV - 1. The pool's lp fee is 8 bps, so a buy edge exists only when mid_dev < -fee
(USDC -> syrup below NAV), and a sell edge when mid_dev > +fee.

    python topics/t6_rwa/syrup_backfill.py --paid [--days 14] [--step-min 60]
"""

from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import chains  # noqa: E402
from cycle_common import abi_decode, build_w3, encode, multicall  # noqa: E402

STATEVIEW = "0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227"
POOLS = {  # name: (v4 pool id, NAV contract; syrup token is currency0, both 6 dec)
    "syrupUSDC": ("0xcdb422a853a4fa2deb364317db92ad76d1cb7a8e1b82a32219bcb41720a90228", "0x80ac24aA929eaF5013f6436cdA2a7ba190f5Cc0b"),
    "syrupUSDT": ("0xd861038a98942312d1495dd1313fb66c7e7de48f549a15edf3a45decf7338e1d", "0x356B8d89c1e1239Cbbb9dE4815c39A1474d5BA7D"),
}
USDY_ORACLE = "0xA0219AA5B31e65Bc920B5b6DFb8EdF0988121De0"
CACHE = os.path.join(HERE, "syrup_backfill_cache.json")


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paid", action="store_true")
    ap.add_argument("--days", type=float, default=14)
    ap.add_argument("--step-min", type=int, default=60)
    a = ap.parse_args()
    if not a.paid:
        sys.exit("archive needs --paid (Alchemy)")
    w3 = build_w3(chains.rpc_list("ethereum", paid=True)[0], timeout_s=30)
    paid = 0
    head = w3.eth.block_number
    paid += 1
    step = a.step_min * 5  # 12 s blocks
    blocks = list(range(head, head - int(a.days * 7200), -step))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

    calls = []
    for name, (pid, navc) in POOLS.items():
        calls.append((STATEVIEW, encode("getSlot0(bytes32)", ["bytes32"], [bytes.fromhex(pid[2:])])))
        calls.append((navc, encode("convertToExitAssets(uint256)", ["uint256"], [10**6])))
    calls.append((USDY_ORACLE, encode("getPrice()", [], [])))
    calls.append(("0xcA11bde05977b3631167028862bE2a173976CA11", encode("getCurrentBlockTimestamp()", [], [])))

    errors = 0
    for b in blocks:
        if str(b) in cache:
            continue
        try:
            res = multicall(w3, calls, b)
            paid += 1
        except Exception as e:  # noqa: BLE001  (never print e: may embed the URL)
            paid += 1
            errors += 1
            print("error at block", b, type(e).__name__)
            continue
        row, k = {}, 0
        for name in POOLS:
            ok0, r0 = res[k]
            ok1, r1 = res[k + 1]
            k += 2
            if ok0 and r0 and ok1 and r1:
                sq = abi_decode(["uint160", "int24", "uint24", "uint24"], r0)[0]
                mid = (sq / 2**96) ** 2
                nav = abi_decode(["uint256"], r1)[0] / 1e6
                row[name] = {"mid": mid, "nav": nav, "dev_bps": (mid / nav - 1) * 1e4}
        if res[k][0]:
            row["USDY_nav"] = abi_decode(["uint256"], res[k][1])[0] / 1e18
        row["ts"] = abi_decode(["uint256"], res[k + 1][1])[0]
        cache[str(b)] = row
    json.dump(cache, open(CACHE, "w"), indent=0)

    summary = {}
    sel = [cache[str(b)] for b in blocks if str(b) in cache]
    for name in POOLS:
        xs = [r[name]["dev_bps"] for r in sel if name in r]
        if not xs:
            continue
        summary[name] = {"n": len(xs), "p05": round(pct(xs, .05), 2), "p50": round(pct(xs, .5), 2),
                         "p95": round(pct(xs, .95), 2), "min": round(min(xs), 2), "max": round(max(xs), 2),
                         "pct_below_-8bps": round(100 * sum(x < -8 for x in xs) / len(xs), 1),
                         "pct_above_+8bps": round(100 * sum(x > 8 for x in xs) / len(xs), 1),
                         "mean": round(st.mean(xs), 2)}
    u = [(r["ts"], r["USDY_nav"]) for r in sel if "USDY_nav" in r]
    if len(u) > 2:
        u.sort()
        summary["USDY_nav_apr_pct"] = round(((u[-1][1] / u[0][1]) ** (365 * 86400 / (u[-1][0] - u[0][0])) - 1) * 100, 2)
    print(json.dumps(summary, indent=1))
    print(f"paid requests this run: {paid}  (errors {errors})")
    with open(os.path.join(HERE, "syrup_backfill_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"days": a.days, "step_min": a.step_min, "paid_requests": paid, "summary": summary}, f, indent=1)


if __name__ == "__main__":
    main()
