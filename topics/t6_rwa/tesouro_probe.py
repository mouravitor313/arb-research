"""One-shot probe for TESOURO (Etherfuse BR sovereign stablebond): executable quotes vs Etherfuse NAV.

READ-ONLY: Etherfuse public NAV API, Polygon eth_call (Curve get_dy, DFB oracle), KyberSwap /routes (Polygon),
Jupiter lite /quote (Solana), OKX public book USDC-BRL. No signing, no tx.

Legs measured at $1k/$10k/$100k (BRL-converted with Etherfuse FX):
  curve_sell  TESOURO -> BRLA   on DFB BRL Pool v1   (edge vs NAV_BRL, BRLA = 1 BRL)
  curve_buy   BRLA -> TESOURO
  poly_*      USDC <-> TESOURO  Polygon via Kyber    (edge vs NAV_USD)
  sol_*       USDC <-> TESOURO  Solana via Jupiter
  loop        USDC -> TESOURO (Polygon/Kyber) -> BRLA (Curve) -> BRL -> USDC at OKX USDC-BRL ask, taker 2 bps
              (BRLA->BRL 1:1 at Avenia assumed; inventory model)

    python topics/t6_rwa/tesouro_probe.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import chains  # noqa: E402
from cycle_common import CS, abi_decode, build_w3, encode, multicall  # noqa: E402
from probe import jup, kyber  # noqa: E402

SIZES = [1_000, 10_000, 100_000]
POOL = "0xc89f31f74573cc19fffc06108601c1ac71ba9735"
ORACLE = "0xc1df935339989f398c59af034fdfc13b2a84c4f2"
T_POLY = "0xd574b191B5a00262Ff19953d3CE25543AB7C8098"  # 6 dec
T_SOL = "BRNTNaZeTJANz9PeuD8drNbBHwGgg7ZTjiQYrFgWQ48p"
BRLA = "0xE6A537a407488807F0bbeB0038B79004f19DDDFb"  # 18 dec
USDC_POLY = chains.CHAINS["polygon"]["tokens"]["USDC"][0]
SOL_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
I_T, I_BRLA = 0, 3
OKX_FEE_BRL_TAKER = 2e-4


def etherfuse_nav():
    d = requests.get("https://api.etherfuse.com/lookup/tokens/cost/TESOURO", timeout=20).json()
    return float(d["token_cost_in_fiat"]), float(d["token_cost_in_usd"]), float(d["fiat_exchange_rate_with_usd"]), d


def okx_book(inst="USDC-BRL"):
    d = requests.get("https://www.okx.com/api/v5/market/books", params={"instId": inst, "sz": "50"}, timeout=20).json()
    b = d["data"][0]
    return [(float(p), float(q)) for p, q, *_ in b["asks"]], [(float(p), float(q)) for p, q, *_ in b["bids"]]


def buy_with_quote(asks, quote_amt):
    """Spend quote_amt BRL buying USDC from asks; returns USDC received (None if book too thin)."""
    got, left = 0.0, quote_amt
    for p, q in asks:
        take = min(left, p * q)
        got += take / p
        left -= take
        if left <= 1e-9:
            return got
    return None


def curve_dy(w3, i, j, dx, block):
    cd = encode("get_dy(int128,int128,uint256)", ["int128", "int128", "uint256"], [i, j, int(dx)])
    return cd


def main():
    nav_brl, nav_usd, fx, raw = etherfuse_nav()
    w3 = build_w3(chains.rpc_list("polygon")[0])
    blk = w3.eth.block_number
    asks, bids = okx_book()
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")

    calls = [(ORACLE, encode("latestRoundData()", [], []))]
    for s in SIZES:
        brl = s * fx
        calls.append((POOL, curve_dy(w3, I_T, I_BRLA, brl / nav_brl * 1e6, blk)))
        calls.append((POOL, curve_dy(w3, I_BRLA, I_T, brl * 1e18, blk)))
    res = multicall(w3, calls, blk)
    _, ans, _, upd, _ = abi_decode(["uint80", "int256", "uint256", "uint256", "uint80"], res[0][1])
    dfb = ans / 1e8
    bal = [abi_decode(["uint256"], w3.eth.call({"to": CS(POOL), "data": encode("balances(uint256)", ["uint256"], [k])}, blk))[0]
           for k in range(4)]
    print(f"block {blk}  NAV {nav_brl:.6f} BRL / ${nav_usd:.6f}  FX {fx:.4f}  DFB oracle {dfb:.6f} "
          f"({(dfb / nav_brl - 1) * 1e4:+.1f} bps vs NAV, upd {time.strftime('%H:%M:%S', time.gmtime(upd))}Z)")
    print(f"pool balances: TESOURO {bal[0]/1e6:,.0f}  BRZ {bal[1]/1e18:,.0f}  stBRZ {bal[2]/1e18:,.0f}  BRLA {bal[3]/1e18:,.0f}")
    print(f"OKX USDC-BRL best ask {asks[0][0]} bid {bids[0][0]}  (vs Etherfuse FX {fx:.4f})")

    rows = []
    for k, s in enumerate(SIZES):
        brl = s * fx
        r = {"size_usd": s, "size_brl": round(brl, 2)}
        ok_s, raw_s = res[1 + 2 * k]
        ok_b, raw_b = res[2 + 2 * k]
        brla_out = abi_decode(["uint256"], raw_s)[0] / 1e18 if ok_s and raw_s else None
        t_out = abi_decode(["uint256"], raw_b)[0] / 1e6 if ok_b and raw_b else None
        r["curve_sell_bps"] = round((brla_out / brl - 1) * 1e4, 1) if brla_out else None
        r["curve_buy_bps"] = round((t_out * nav_brl / brl - 1) * 1e4, 1) if t_out else None
        # Polygon (Kyber) USDC <-> TESOURO
        pb = kyber("polygon", USDC_POLY, T_POLY, s * 1e6)
        ps = kyber("polygon", T_POLY, USDC_POLY, s / nav_usd * 1e6)
        if pb:
            r["poly_buy_bps"] = round(((pb[0] / 1e6) * nav_usd / s - 1 - pb[1] / s) * 1e4, 1)
            r["poly_buy_route"] = pb[2]
            r["poly_buy_tokens"] = pb[0] / 1e6
        if ps:
            r["poly_sell_bps"] = round(((ps[0] / 1e6) / s - 1 - ps[1] / s) * 1e4, 1)
            r["poly_sell_route"] = ps[2]
        sb = jup(SOL_USDC, T_SOL, s * 1e6)
        ss = jup(T_SOL, SOL_USDC, s / nav_usd * 1e6)
        if sb:
            r["sol_buy_bps"] = round(((sb[0] / 1e6) * nav_usd / s - 1) * 1e4, 1)
            r["sol_buy_route"] = sb[2]
        if ss:
            r["sol_sell_bps"] = round(((ss[0] / 1e6) / s - 1) * 1e4, 1)
            r["sol_sell_route"] = ss[2]
        # loop: USDC -> TESOURO (Polygon best) -> BRLA (Curve) -> BRL -> USDC on OKX (buy USDC with BRL, taker)
        if pb:
            tok = pb[0]  # 6-dec units
            q = multicall(w3, [(POOL, curve_dy(w3, I_T, I_BRLA, tok, blk))], blk)[0]
            if q[0] and q[1]:
                brl_out = abi_decode(["uint256"], q[1])[0] / 1e18
                usdc_back = buy_with_quote(asks, brl_out * (1 - OKX_FEE_BRL_TAKER))
                if usdc_back:
                    r["loop_poly_bps"] = round((usdc_back / s - 1 - pb[1] / s) * 1e4, 1)
        rows.append(r)
        print(json.dumps(r))

    out = {"ts": ts, "block": blk, "nav_brl": nav_brl, "nav_usd": nav_usd, "fx": fx, "dfb_oracle": dfb,
           "dfb_vs_nav_bps": (dfb / nav_brl - 1) * 1e4, "pool_bal": [bal[0] / 1e6] + [b / 1e18 for b in bal[1:]],
           "okx_usdc_brl": {"ask": asks[0][0], "bid": bids[0][0]}, "rows": rows}
    with open(os.path.join(HERE, f"tesouro_probe_{ts.replace(':', '')}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
