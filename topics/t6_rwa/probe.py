"""One-shot probe: executable DEX quote vs on-chain NAV for the t6_rwa candidates, $1k/$10k/$100k,
both directions. READ-ONLY (quote APIs + eth_call). No signing, no tx.

Quotes: KyberSwap aggregator /routes (EVM, includes gasUsd) and Jupiter lite /quote (Solana).
NAV: Ethereum eth_call via nav.py (same token bridged elsewhere -> same NAV).

edge_buy  = tokens_out * NAV / usd_in - 1      (>0 = bought below NAV)
edge_sell = usd_out / (tokens_in * NAV) - 1     (>0 = sold above NAV)
Both net of gas (gasUsd / size). Stable quote leg (USDC/USDT) taken at $1.

    python topics/t6_rwa/probe.py [--only syrupUSDC,USDY]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nav import read_navs  # noqa: E402

SIZES = [1_000, 10_000, 100_000]
KYBER = "https://aggregator-api.kyberswap.com/{chain}/api/v1/routes"
JUP = "https://lite-api.jup.ag/swap/v1/quote"
KH = {"x-client-id": "arb-readonly"}

EVM_USDC = {"ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"}
EVM_USDT = {"ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7"}
SOL_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# (label, venue, chain, token, decimals, nav_key or float, quote, quote_decimals)
CANDS = [
    ("syrupUSDC", "kyber", "ethereum", "0x80ac24aA929eaF5013f6436cdA2a7ba190f5Cc0b", 6, "syrupUSDC_exit", EVM_USDC["ethereum"], 6),
    ("syrupUSDC", "kyber", "base", "0x660975730059246A68521a3e2FBD4740173100f5", 6, "syrupUSDC_exit", EVM_USDC["base"], 6),
    ("syrupUSDC", "jup", "solana", "AvZZF1YaZDziPY2RCK4oJrRVrbN3mTD9NL24hPeaZeUj", 6, "syrupUSDC_exit", SOL_USDC, 6),
    ("syrupUSDT", "kyber", "ethereum", "0x356B8d89c1e1239Cbbb9dE4815c39A1474d5BA7D", 6, "syrupUSDT_exit", EVM_USDT["ethereum"], 6),
    ("USDY", "jup", "solana", "A1KLoBrKBde8Ty9qtNQUtq3C2ortoC3u7twggz7sEto6", 6, "USDY", SOL_USDC, 6),
    ("USDY", "kyber", "ethereum", "0x96F6eF951840721AdBF46Ac996b59E0235CB985C", 18, "USDY", EVM_USDC["ethereum"], 6),
    ("USDY", "kyber", "arbitrum", "0x35e050d3C0eC2d29D269a8EcEa763a183bDF9A9D", 18, "USDY", EVM_USDC["arbitrum"], 6),
    ("sfrxUSD", "kyber", "ethereum", "0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6", 18, "sfrxUSD", EVM_USDC["ethereum"], 6),
    ("sUSDS", "kyber", "ethereum", "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD", 18, "sUSDS", EVM_USDC["ethereum"], 6),
    ("sDAI", "kyber", "ethereum", "0x83F20F44975D03b1b09e64809B757c47f942BEeA", 18, "sDAI", EVM_USDC["ethereum"], 6),
    ("scrvUSD", "kyber", "ethereum", "0x0655977FEb2f289A4aB78af67BAB0d17aAb84367", 18, "scrvUSD", EVM_USDC["ethereum"], 6),
    ("cUSDO", "kyber", "ethereum", "0xaD55aebc9b8c03FC43cd9f62260391c13c23e7c0", 18, "cUSDO", EVM_USDC["ethereum"], 6),
    ("bUSD0", "kyber", "ethereum", "0x35D8949372D46B7a3D5A56006AE77B215fc69bC0", 18, 1.0, EVM_USDC["ethereum"], 6),
]


def kyber(chain, tin, tout, amt):
    for i in range(3):
        try:
            r = requests.get(KYBER.format(chain=chain), params={"tokenIn": tin, "tokenOut": tout, "amountIn": str(int(amt))},
                             headers=KH, timeout=25)
            d = r.json()
            time.sleep(1.0)
            if d.get("code") == 0:
                s = d["data"]["routeSummary"]
                ex = sorted({h["exchange"] for path in s["route"] for h in path})
                return int(s["amountOut"]), float(s.get("gasUsd") or 0) + float(s.get("l1FeeUsd") or 0), ex
            return None
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    return None


def jup(tin, tout, amt):
    for i in range(3):
        try:
            r = requests.get(JUP, params={"inputMint": tin, "outputMint": tout, "amount": str(int(amt)), "slippageBps": 50},
                             timeout=25)
            time.sleep(2.2)
            d = r.json()
            if "outAmount" in d:
                return int(d["outAmount"]), 0.002, sorted({x["swapInfo"]["label"] for x in d.get("routePlan", [])})
            return None
        except Exception:  # noqa: BLE001
            time.sleep(4 * (i + 1))
    return None


def quote(venue, chain, tin, tout, amt):
    return jup(tin, tout, amt) if venue == "jup" else kyber(chain, tin, tout, amt)


def run(only=None):
    navs = read_navs()
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    rows = []
    for label, venue, chain, tok, dec, navk, q, qdec in CANDS:
        if only and label not in only:
            continue
        nav = navs.get(navk) if isinstance(navk, str) else navk
        if not nav:
            print("no NAV", label)
            continue
        for s in SIZES:
            b = quote(venue, chain, q, tok, s * 10**qdec)
            sl = quote(venue, chain, tok, q, s / nav * 10**dec)
            row = {"token": label, "chain": chain, "venue": venue, "size": s, "nav": nav}
            if b:
                out, gas, ex = b
                row.update(buy_bps=round(((out / 10**dec) * nav / s - 1 - gas / s) * 1e4, 2), buy_gas=round(gas, 3), buy_route=ex)
            if sl:
                out, gas, ex = sl
                row.update(sell_bps=round(((out / 10**qdec) / s - 1 - gas / s) * 1e4, 2), sell_gas=round(gas, 3), sell_route=ex)
            rows.append(row)
            print(f"{label:9s} {chain:9s} ${s:>7,} NAV {nav:.6f} buy {row.get('buy_bps')!s:>9} sell {row.get('sell_bps')!s:>9}"
                  f"  {row.get('sell_route') or row.get('buy_route')}")
    path = os.path.join(HERE, f"probe_{ts.replace(':', '')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"ts": ts, "navs": navs, "rows": rows}, f, indent=1)
    print("->", os.path.basename(path))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a = ap.parse_args()
    run(set(a.only.split(",")) if a.only else None)
