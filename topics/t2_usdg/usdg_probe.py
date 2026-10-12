"""t2_usdg — USDG ↔ OKX (BRL pairs) probe / collector. READ-ONLY (public REST + eth_call; nothing signed).

Strategies, per DEX venue v and stable X ∈ {USDC, USDT}, size S ∈ {$1k, $10k, $100k}, VIP 9 fees:
  dex_buy   DEX: S X → USDG ;  OKX: sell USDG on USDG-BRL (taker 2) → buy X on X-BRL (taker 2) → X_back
  dex_sell  OKX: sell S X on X-BRL → buy USDG on USDG-BRL ;  DEX: USDG → X → X_back
  net_bps = (X_back / S − 1)·1e4 − gas ;  net_bps_maker = both BRL legs as maker at the touch (−1.5 each, upper bound)
  okx_tri   BRL → USDT → USDG → BRL (and reverse): USDG-USDT non-BRL (11 bps)
DEX quotes: Ethereum/Arbitrum KyberSwap aggregator (executable routes, public), Ethereum Curve get_dy
(reference), X Layer Uniswap v3 QuoterV2 0.01% USDG/USD₮0, Solana Jupiter lite.

    python usdg_probe.py                 # one shot, prints + json
    python usdg_probe.py --loop 60 --hours 24   # collector -> data.db (write .pid; stop: delete usdg.stop or -Stop)
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import requests  # noqa: E402
from eth_abi import decode as abi_decode  # noqa: E402

from cycle_common import CS, build_w3, encode  # noqa: E402
from xvenue_collector import buy_base, buy_with_quote, sell_base  # noqa: E402

SIZES = (1_000, 10_000, 100_000)
FEE_BRL, FEE_NB, MAKER_BRL = 2e-4, 11e-4, -1.5e-4
OKX = "https://www.okx.com/api/v5"
INSTS = ["USDG-BRL", "USDG-USDT", "USDT-BRL", "USDC-BRL", "USDC-USDT"]
S = requests.Session()

EVM = {  # Kyber chain slug, USDG, USDC, USDT (all 6 dec)
    "ethereum": ("0xe343167631d89B6Ffc58B88d6b7fB0228795491D", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                 "0xdAC17F958D2ee523a2206206994597C13D831ec7"),
    "arbitrum": ("0x004b506865409877c9fa29bfb1eba929984b9bbc", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                 "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"),
}
XLAYER_RPCS = ["https://rpc.xlayer.tech", "https://xlayerrpc.okx.com"]
XL_QUOTER = "0xd1b797d92d87b688193a2b976efc8d577d204343"
XL_USDG, XL_USDT0, XL_FEE = "0x4ae46a509f6b1d9056937ba4500cb143933d2dc8", "0x779ded0c9e1022225f8e0630b35a9b54be713736", 100
ETH_RPC = "https://ethereum-rpc.publicnode.com"
CURVE_USDG_USDC = "0xc061caa073f3d95f80f8e5428d32d2d76f5e1622"
SOL = {"USDG": "2u1tszSeqZ3qBWF3uNGPFc8TzMk2tdiwknnRMWGWjGWH", "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
       "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}
SOL_GAS_USD = 0.002
XL_GAS_USD = 0.01  # X Layer: OKB gas, ~150k gas at very low gwei (measured below when possible)

SCHEMA = """
CREATE TABLE IF NOT EXISTS opps (ts TEXT, strategy TEXT, venue TEXT, stable TEXT, size_usd INTEGER,
  gross_bps REAL, net_bps REAL, net_bps_maker REAL, gas_usd REAL, dex_px REAL,
  PRIMARY KEY (ts, strategy, venue, stable, size_usd));
CREATE TABLE IF NOT EXISTS ticks (ts TEXT PRIMARY KEY, data TEXT);
"""


# ---------------- OKX ----------------
def books():
    out = {}
    for i in INSTS:
        d = S.get(f"{OKX}/market/books", params={"instId": i, "sz": 400}, timeout=8).json()["data"][0]
        out[i] = {k: [(float(p), float(q)) for p, q, *_ in d[k]] for k in ("asks", "bids")}
    return out


def mid(b):
    return (b["asks"][0][0] + b["bids"][0][0]) / 2


# ---------------- DEX quotes: amount in (units, 6 dec) -> amount out (float) or None ----------------
def kyber(chain, tin, tout, amt):
    try:
        r = S.get(f"https://aggregator-api.kyberswap.com/{chain}/api/v1/routes",
                  params={"tokenIn": tin, "tokenOut": tout, "amountIn": str(int(amt * 1e6))},
                  headers={"x-client-id": "readonly-research"}, timeout=15).json()
        rs = r["data"]["routeSummary"]
        return int(rs["amountOut"]) / 1e6, float(rs.get("gasUsd") or 0)
    except Exception:  # noqa: BLE001
        return None, None
    finally:
        time.sleep(0.4)


def jup(tin, tout, amt):
    try:
        r = S.get("https://lite-api.jup.ag/swap/v1/quote",
                  params={"inputMint": SOL[tin], "outputMint": SOL[tout], "amount": int(amt * 1e6), "slippageBps": 5},
                  timeout=15).json()
        return int(r["outAmount"]) / 1e6, SOL_GAS_USD
    except Exception:  # noqa: BLE001
        return None, None
    finally:
        time.sleep(2.1)  # Jupiter lite ≤ 0.5 req/s


_xl = None


def xlayer(tin, tout, amt):
    global _xl
    for url in XLAYER_RPCS:
        try:
            _xl = _xl or build_w3(url)
            cd = encode("quoteExactInputSingle((address,address,uint256,uint24,uint160))",
                        ["(address,address,uint256,uint24,uint160)"], [(CS(tin), CS(tout), int(amt * 1e6), XL_FEE, 0)])
            raw = _xl.eth.call({"to": CS(XL_QUOTER), "data": cd})
            return abi_decode(["uint256", "uint160", "uint32", "uint256"], raw)[0] / 1e6, XL_GAS_USD
        except Exception:  # noqa: BLE001
            _xl = None
    return None, None


_eth = None


def curve(i, j, amt):
    """Curve USDG/USDC (ETH) get_dy, reference only (gas from Kyber ETH estimate)."""
    global _eth
    try:
        _eth = _eth or build_w3(ETH_RPC)
        raw = _eth.eth.call({"to": CS(CURVE_USDG_USDC),
                             "data": encode("get_dy(int128,int128,uint256)", ["int128", "int128", "uint256"],
                                            [i, j, int(amt * 1e6)])})
        return abi_decode(["uint256"], raw)[0] / 1e6
    except Exception:  # noqa: BLE001
        return None


def curve_coins():
    w3 = build_w3(ETH_RPC)
    return [("0x" + w3.eth.call({"to": CS(CURVE_USDG_USDC), "data": encode("coins(uint256)", ["uint256"], [k])})[-20:].hex())
            for k in (0, 1)]


def venues(with_jup=True):
    """(venue, stable) -> quote fn(direction, amount) ; direction 'buy' = stable→USDG, 'sell' = USDG→stable."""
    v = {}
    for ch, (g, c, t) in EVM.items():
        for name, x in (("USDC", c), ("USDT", t)):
            v[(f"kyber_{ch}", name)] = (lambda d, a, ch=ch, g=g, x=x: kyber(ch, x, g, a) if d == "buy" else kyber(ch, g, x, a))
    v[("xlayer_univ3_1bp", "USDT")] = lambda d, a: xlayer(XL_USDT0, XL_USDG, a) if d == "buy" else xlayer(XL_USDG, XL_USDT0, a)
    for name in (("USDC", "USDT") if with_jup else ()):
        v[("jup_solana", name)] = (lambda d, a, n=name: jup(n, "USDG", a) if d == "buy" else jup("USDG", n, a))
    return v


# ---------------- strategies ----------------
def okx_sell_usdg_buy_x(bk, g, x, maker=False):
    """sell g USDG on USDG-BRL, buy X with the BRL on X-BRL -> X (taker, or maker at touch)."""
    f = MAKER_BRL if maker else FEE_BRL
    if maker:
        brl = g * bk["USDG-BRL"]["asks"][0][0] * (1 - f)
        return brl / bk[f"{x}-BRL"]["bids"][0][0] * (1 - f)
    brl = sell_base(bk["USDG-BRL"]["bids"], g)
    if brl is None:
        return None
    got = buy_with_quote(bk[f"{x}-BRL"]["asks"], brl * (1 - f))
    return None if got is None else got * (1 - f)


def okx_sell_x_buy_usdg(bk, s, x, maker=False):
    f = MAKER_BRL if maker else FEE_BRL
    if maker:
        brl = s * bk[f"{x}-BRL"]["asks"][0][0] * (1 - f)
        return brl / bk["USDG-BRL"]["bids"][0][0] * (1 - f)
    brl = sell_base(bk[f"{x}-BRL"]["bids"], s)
    if brl is None:
        return None
    got = buy_with_quote(bk["USDG-BRL"]["asks"], brl * (1 - f))
    return None if got is None else got * (1 - f)


def tick(ts, verbose=True, with_jup=True):
    bk = books()
    rows, info = [], {"okx_mid": {i: mid(b) for i, b in bk.items()}}
    m = info["okx_mid"]
    info["okx_implied"] = {"USDG/USDT_viaBRL": m["USDG-BRL"] / m["USDT-BRL"], "USDG/USDC_viaBRL": m["USDG-BRL"] / m["USDC-BRL"],
                           "USDG-USDT": m["USDG-USDT"], "USDG/USDC_direct": m["USDG-USDT"] / m["USDC-USDT"]}
    # OKX-internal triangle BRL→USDT→USDG→BRL (cw) and reverse, taker
    for sz in SIZES:
        brl0 = sz * m["USDT-BRL"]
        u = buy_with_quote(bk["USDT-BRL"]["asks"], brl0) * (1 - FEE_BRL)
        g = buy_with_quote(bk["USDG-USDT"]["asks"], u) * (1 - FEE_NB)
        b1 = sell_base(bk["USDG-BRL"]["bids"], g)
        if b1:
            rows.append((ts, "okx_tri_cw", "okx", "USDT", sz, None, (b1 * (1 - FEE_BRL) / brl0 - 1) * 1e4, None, 0, None))
        g = buy_with_quote(bk["USDG-BRL"]["asks"], brl0)
        if g:
            u = sell_base(bk["USDG-USDT"]["bids"], g * (1 - FEE_BRL)) * (1 - FEE_NB)
            b1 = sell_base(bk["USDT-BRL"]["bids"], u) * (1 - FEE_BRL)
            rows.append((ts, "okx_tri_ccw", "okx", "USDT", sz, None, (b1 / brl0 - 1) * 1e4, None, 0, None))
    dex_mid = {}
    for (ven, x), q in venues(with_jup).items():
        for sz in SIZES:
            # dex_buy: X -> USDG on DEX, sell USDG via BRL back to X
            g, gas = q("buy", sz)
            if g:
                if sz == SIZES[0]:
                    dex_mid[f"{ven}:{x}:buy_px"] = sz / g
                back, back_m = okx_sell_usdg_buy_x(bk, g, x), okx_sell_usdg_buy_x(bk, g, x, True)
                gross = (g * m["USDG-BRL"] / m[f"{x}-BRL"] / sz - 1) * 1e4
                gb = gas / sz * 1e4
                rows.append((ts, "dex_buy", ven, x, sz, gross, None if back is None else (back / sz - 1) * 1e4 - gb,
                             (back_m / sz - 1) * 1e4 - gb, gas, sz / g))
            # dex_sell: OKX X -> BRL -> USDG, DEX USDG -> X
            g2, g2m = okx_sell_x_buy_usdg(bk, sz, x), okx_sell_x_buy_usdg(bk, sz, x, True)
            if g2:
                back, gas = q("sell", g2)
                if back:
                    if sz == SIZES[0]:
                        dex_mid[f"{ven}:{x}:sell_px"] = back / g2
                    gb = gas / sz * 1e4
                    gross = (back / g2 * m[f"{x}-BRL"] / m["USDG-BRL"] - 1) * 1e4
                    rows.append((ts, "dex_sell", ven, x, sz, gross, (back / sz - 1) * 1e4 - gb,
                                 (back / g2 * g2m / sz - 1) * 1e4 - gb, gas, back / g2))
    c = {sz: (curve(0, 1, sz), curve(1, 0, sz)) for sz in SIZES}
    info["curve_eth_usdg_usdc_getdy"] = c
    info["dex_px_1k"] = dex_mid
    if verbose:
        print(json.dumps(info, indent=1, default=str))
        print(f"{'strategy':12} {'venue':18} {'X':5} {'size':>7} {'gross':>7} {'net':>7} {'maker':>7} {'gas$':>6} {'dex_px':>9}")
        for r in rows:
            f = lambda v, n=2: "   —   " if v is None else f"{v:7.{n}f}"
            print(f"{r[1]:12} {r[2]:18} {r[3]:5} {r[4]:>7} {f(r[5])} {f(r[6])} {f(r[7])} {f(r[8])} {f(r[9], 5)}")
    return rows, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0, help="seconds between ticks (0 = one shot)")
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--jup-every", type=int, default=3, help="query Jupiter every N ticks (shared 0.5 req/s budget)")
    a = ap.parse_args()
    os.chdir(HERE)
    db = sqlite3.connect("data.db")
    db.executescript(SCHEMA)
    if not a.loop:
        print("curve coins:", curve_coins())
    pidf = "usdg_probe.pid"
    if a.loop:
        open(pidf, "w").write(str(os.getpid()))
    end = time.time() + a.hours * 3600
    n = 0
    try:
        while True:
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            try:
                rows, info = tick(ts, verbose=not a.loop, with_jup=(not a.loop) or n % a.jup_every == 0)
                n += 1
                db.executemany("INSERT OR REPLACE INTO opps VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
                db.execute("INSERT OR REPLACE INTO ticks VALUES (?,?)", (ts, json.dumps(info, default=str)))
                db.commit()
                if not a.loop:
                    json.dump({"ts": ts, "info": info, "rows": rows}, open(f"probe_{ts[:19].replace(':', '')}.json", "w"),
                              indent=1, default=str)
                else:
                    best = max((r[6] for r in rows if r[6] is not None and r[1].startswith("dex")), default=None)
                    print(ts, "rows", len(rows), "best_net", best, flush=True)
            except Exception as e:  # noqa: BLE001
                print(ts, "tick error", repr(e), flush=True)
            if not a.loop or time.time() > end or os.path.exists("usdg.stop"):
                break
            time.sleep(a.loop)
    finally:
        if a.loop and os.path.exists(pidf):
            os.remove(pidf)


if __name__ == "__main__":
    main()
