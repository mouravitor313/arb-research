"""Shared read-only helpers for topic t3 (BRLA on Base / Gnosis / Celo vs OKX, Polygon as reference).

READ-ONLY: eth_call only (multicall3, fixed block). No signing, no tx.
CL pools (Uni v3, Oku, Aerodrome Slipstream) are quoted with a local exact-input swap simulator built from
on-chain slot0/liquidity/tickBitmap/ticks at a fixed block, so it works the same on every fork and at past
blocks (archive). Curve twocrypto-ng is quoted with get_dy(uint256,...). Cross-checked vs QuoterV2 in probe.py.

Chain config is local to this topic (chains.py is only imported to read the Alchemy URL helper).
"""

from __future__ import annotations

import math
import os
import sys
import time
from dataclasses import dataclass, field

import requests
from eth_abi import decode as abi_decode
from web3 import Web3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import chains  # noqa: E402  (read-only: alchemy_url)
from cycle_common import CS, build_w3, encode  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"  # same address on all four chains
Q96 = 2 ** 96

CHAIN_CFG = {
    "base": {"rpcs": ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://base.drpc.org"],
             "block_s": 2.0, "gas_token_usd": None, "gas_okx": "ETH-USDT", "swap_gas": 160_000,
             "l1_fee_usd": 0.002},
    "gnosis": {"rpcs": ["https://gnosis-rpc.publicnode.com", "https://rpc.gnosischain.com", "https://gnosis.drpc.org"],
               "block_s": 5.0, "gas_token_usd": 1.0, "gas_okx": None, "swap_gas": 160_000, "l1_fee_usd": 0.0},
    "celo": {"rpcs": ["https://forno.celo.org", "https://celo.drpc.org"],
             "block_s": 1.0, "gas_token_usd": None, "gas_okx": "CELO-USDT", "swap_gas": 160_000,
             "l1_fee_usd": 0.0},
    "polygon": {"rpcs": ["https://polygon-bor-rpc.publicnode.com", "https://polygon.drpc.org"],
                "block_s": 2.0, "gas_token_usd": None, "gas_okx": "POL-USDT", "swap_gas": 160_000,
                "l1_fee_usd": 0.0},
}


@dataclass
class Pool:
    key: str
    chain: str
    address: str
    kind: str  # "cl" (Uni v3 style) or "curve"
    usd_token: str
    usd_sym: str
    brla: str
    okx_ref: str  # OKX BRL book used to close the dollar leg
    note: str = ""
    usd_dec: int = 6
    brla_dec: int = 18
    # filled at runtime for CL pools
    usd_is_token0: bool = True
    curve_idx: tuple[int, int] = (0, 1)  # (i_usd, i_brla) for curve


POOLS = [
    Pool("base_aero_005", "base", "0x1c33aa5cc206ed3d9e29fb136796a8815e48af58", "cl",
         "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "USDC",
         "0xfcb34c47f850f452c15ea1b84d51231c38a61783", "USDC-BRL", "Aerodrome Slipstream (CL factory 0xade6…716a) ts=10"),
    Pool("gnosis_oku_005", "gnosis", "0x576bf065cbc15cb2d61affb156118fcff01a8238", "cl",
         "0x2a22f9c3b484c3629090feed35f17ff8f88f76f0", "USDC.e",
         "0xfecb3f7c54e2caae9dc6ac9060a822d47e053760", "USDC-BRL", "Oku = Uniswap v3 oficial na Gnosis"),
    Pool("gnosis_curve", "gnosis", "0xfb8b95fb2296a0ad4b6b1419fdaa5aa5f13e4009", "curve",
         "0x2a22f9c3b484c3629090feed35f17ff8f88f76f0", "USDC.e",
         "0xfecb3f7c54e2caae9dc6ac9060a822d47e053760", "USDC-BRL", "Curve twocrypto-ng (get_dy uint256; coins BRLA, USDC.e; fee dinâmica)",
         curve_idx=(1, 0)),
    Pool("celo_uni_001", "celo", "0x14e577e42d45fd2200a9b0e31d87fe826467111a", "cl",
         "0x48065fbbe25f71c9282ddf5e1cd6d6a887483d5e", "USD₮",
         "0xfecb3f7c54e2caae9dc6ac9060a822d47e053760", "USDT-BRL", "Uniswap v3 Celo 0,01%"),
    Pool("polygon_uni_005", "polygon", "0x0e7754127dedd4097be750825dbb4669bc32c956", "cl",
         "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "USDC",
         "0xE6A537a407488807F0bbeb0038B79004f19DDDFb", "USDC-BRL", "pool do bot brla (referência)"),
]
for _p in POOLS:
    _p.usd_is_token0 = int(_p.usd_token, 16) < int(_p.brla, 16)
POOL_BY_KEY = {p.key: p for p in POOLS}
SIZES = [1_000, 10_000, 100_000]

# --- RPC accounting (paid calls counted per process, persisted by caller) ---
PAID = {"n": 0}


class RPC:
    """Rotating Web3 over public RPCs; Alchemy appended last (or first with paid_first) when paid=True."""

    def __init__(self, chain: str, paid: bool = False, paid_first: bool = False, timeout_s: int = 25):
        self.chain = chain
        urls = list(CHAIN_CFG[chain]["rpcs"])
        a = chains.alchemy_url(chain) if paid else None
        if a:
            urls = [a] + urls if paid_first else urls + [a]
        self.urls = urls
        self.paid_url = a
        self.w3s = [build_w3(u, timeout_s) for u in urls]
        self.i = 0

    def label(self, i=None):
        i = self.i if i is None else i
        return "alchemy" if self.urls[i] == self.paid_url else self.urls[i].split("//")[1].split("/")[0]

    def run(self, fn, tries: int | None = None):
        tries = tries or len(self.w3s) * 2
        last = None
        for k in range(tries):
            j = (self.i + k) % len(self.w3s)
            try:
                if self.urls[j] == self.paid_url:
                    PAID["n"] += 1
                out = fn(self.w3s[j])
                self.i = j
                return out
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(0.5 * (k + 1))
        raise last  # type: ignore[misc]


def multicall(w3: Web3, calls, block):
    data = encode("aggregate3((address,bool,bytes)[])", ["(address,bool,bytes)[]"],
                  [[(CS(t), True, cd) for t, cd in calls]])
    raw = w3.eth.call({"to": CS(MULTICALL3), "data": data}, block_identifier=block)
    (res,) = abi_decode(["(bool,bytes)[]"], raw)
    return [(bool(s), bytes(r)) for s, r in res]


def word(raw: bytes, i: int, signed=False) -> int:
    return int.from_bytes(raw[32 * i:32 * i + 32], "big", signed=signed)


# ---------------------------------------------------------------- CL (Uniswap v3 style) simulator
@dataclass
class CLState:
    sqrtP: int
    tick: int
    L: int
    fee: int  # pips (1e6)
    ts: int
    ticks: dict[int, int] = field(default_factory=dict)  # initialized tick -> liquidityNet


def tick_sqrt(t: int) -> int:
    return int(math.sqrt(1.0001 ** t) * Q96)


def bitmap_ticks(words: dict[int, int], ts: int) -> list[int]:
    out = []
    for w, bits in words.items():
        b = 0
        while bits:
            if bits & 1:
                out.append(((w << 8) + b) * ts)
            bits >>= 1
            b += 1
    return sorted(out)


def cl_simulate(st: CLState, amount_in: int, zero_for_one: bool) -> tuple[int, bool]:
    """Exact-input swap. Returns (amount_out, exhausted) — exhausted if the known tick range ran out."""
    sqrtP, L, rem, out = st.sqrtP, st.L, amount_in, 0
    fee = st.fee
    ticks = sorted(st.ticks)
    if zero_for_one:
        nxt = [t for t in ticks if t <= st.tick][::-1]
    else:
        nxt = [t for t in ticks if t > st.tick]
    for t in nxt + [None]:
        if rem <= 0:
            break
        if t is None:  # beyond fetched range: treat as wall
            return out, True
        target = tick_sqrt(t)
        if L > 0:
            rem_less_fee = rem * (10 ** 6 - fee) // 10 ** 6
            if zero_for_one:
                need = -(-L * Q96 * (sqrtP - target) // (sqrtP * target))  # amount0 to reach target (round up)
                if rem_less_fee >= need:
                    nsp = target
                    ain = need
                else:
                    num = L * Q96 * sqrtP
                    den = L * Q96 + rem_less_fee * sqrtP
                    nsp = -(-num // den)
                    ain = rem_less_fee
                aout = L * (sqrtP - nsp) // Q96
            else:
                need = -(-L * (target - sqrtP) // Q96)
                if rem_less_fee >= need:
                    nsp = target
                    ain = need
                else:
                    nsp = sqrtP + rem_less_fee * Q96 // L
                    ain = rem_less_fee
                aout = L * Q96 * (nsp - sqrtP) // (nsp * sqrtP)
            fee_amt = (-(-ain * fee // (10 ** 6 - fee))) if nsp == target else rem - ain
            rem -= ain + fee_amt
            out += aout
            sqrtP = nsp
            if nsp != target:
                break
        else:
            sqrtP = target
        ln = st.ticks[t]
        L = L - ln if zero_for_one else L + ln
    return out, False


def _span(ts: int) -> int:
    """bitmap words each side so the fetched range covers >= ~+-25% price (2300 ticks)."""
    return max(2, -(-2300 // (256 * ts)))


def fetch_cl_states(rpc: RPC, pools: list[Pool], block, tick_hints: dict[str, int] | None = None):
    """slot0/liquidity/fee/tickSpacing (+ bitmap words around the hinted tick) -> ticks.
    Two multicalls per block when hints are good (backfill passes the previous sample's tick), else three."""
    tick_hints = tick_hints or {}
    calls, meta = [], []
    for p in pools:
        for sig in ("slot0()", "liquidity()", "fee()", "tickSpacing()"):
            calls.append((p.address, encode(sig, [], [])))
            meta.append((p.key, sig))
        if p.key in tick_hints:
            ts = TICK_SPACING[p.key]
            w0, span = (tick_hints[p.key] // ts) >> 8, _span(ts)
            for w in range(w0 - span, w0 + span + 1):
                calls.append((p.address, encode("tickBitmap(int16)", ["int16"], [w])))
                meta.append((p.key, w))
    res = rpc.run(lambda w3: multicall(w3, calls, block))
    vals: dict[str, dict] = {p.key: {} for p in pools}
    for (k, m), (ok, raw) in zip(meta, res):
        vals[k][m] = raw if ok else None
    states, words = {}, {}
    for p in pools:
        v = vals[p.key]
        st = CLState(sqrtP=word(v["slot0()"], 0), tick=word(v["slot0()"], 1, signed=True),
                     L=word(v["liquidity()"], 0), fee=word(v["fee()"], 0),
                     ts=word(v["tickSpacing()"], 0, signed=True))
        TICK_SPACING[p.key] = st.ts
        states[p.key] = st
        words[p.key] = {m: word(r, 0) for m, r in v.items() if isinstance(m, int) and r is not None}
    # (re)fetch bitmap words not covered (need +-span around the actual tick)
    bm_calls, bm_meta = [], []
    for p in pools:
        st = states[p.key]
        w0, span = (st.tick // st.ts) >> 8, _span(st.ts)
        for w in range(w0 - span, w0 + span + 1):
            if w not in words[p.key]:
                bm_calls.append((p.address, encode("tickBitmap(int16)", ["int16"], [w])))
                bm_meta.append((p.key, w))
    if bm_calls:
        res = rpc.run(lambda w3: multicall(w3, bm_calls, block))
        for (k, w), (ok, raw) in zip(bm_meta, res):
            words[k][w] = word(raw, 0) if ok else 0
    t_calls, t_meta = [], []
    for p in pools:
        st = states[p.key]
        span = _span(st.ts)
        lo, hi = ((st.tick // st.ts) >> 8) - span, ((st.tick // st.ts) >> 8) + span
        for t in bitmap_ticks({w: b for w, b in words[p.key].items() if lo <= w <= hi}, st.ts):
            t_calls.append((p.address, encode("ticks(int24)", ["int24"], [t])))
            t_meta.append((p.key, t))
    for i in range(0, len(t_calls), 400):
        res = rpc.run(lambda w3: multicall(w3, t_calls[i:i + 400], block))
        for (k, t), (ok, raw) in zip(t_meta[i:i + 400], res):
            states[k].ticks[t] = word(raw, 1, signed=True)
    return states


TICK_SPACING: dict[str, int] = {}


# ---------------------------------------------------------------- Curve
def curve_calls(p: Pool, sizes_usd, brla_per_usd: float):
    iu, ib = p.curve_idx
    c = []
    for s in sizes_usd:
        c.append((p.address, encode("get_dy(uint256,uint256,uint256)", ["uint256", "uint256", "uint256"],
                                    [iu, ib, int(s * 10 ** p.usd_dec)])))
        c.append((p.address, encode("get_dy(uint256,uint256,uint256)", ["uint256", "uint256", "uint256"],
                                    [ib, iu, int(s * brla_per_usd * 10 ** p.brla_dec)])))
    return c


# ---------------------------------------------------------------- quoting both directions
def quote_pool(p: Pool, st: CLState | None, curve_res, sizes_usd, brla_per_usd: float):
    """Returns {(dir, size): (amount_in_float, amount_out_float, exhausted)}.
    dir 'usd2brla' : spend size USD on DEX -> BRLA ; 'brla2usd' : sell size*brla_per_usd BRLA -> USD."""
    out = {}
    for j, s in enumerate(sizes_usd):
        ain_u = int(s * 10 ** p.usd_dec)
        ain_b = int(s * brla_per_usd * 10 ** p.brla_dec)
        if p.kind == "cl":
            o1, e1 = cl_simulate(st, ain_u, zero_for_one=p.usd_is_token0)
            o2, e2 = cl_simulate(st, ain_b, zero_for_one=not p.usd_is_token0)
        else:
            (k1, r1), (k2, r2) = curve_res[2 * j], curve_res[2 * j + 1]
            o1, e1 = (word(r1, 0) if k1 else 0), not k1
            o2, e2 = (word(r2, 0) if k2 else 0), not k2
        out[("usd2brla", s)] = (s, o1 / 10 ** p.brla_dec, e1)
        out[("brla2usd", s)] = (ain_b / 10 ** p.brla_dec, o2 / 10 ** p.usd_dec, e2)
    return out


def mid_brla_per_usd(p: Pool, st: CLState) -> float:
    if p.kind == "cl":
        r = (st.sqrtP / Q96) ** 2 * 10 ** (p.usd_dec - p.brla_dec)  # token1 per token0
        return r if p.usd_is_token0 else 1 / r
    raise ValueError("curve: use smallest-size quotes")


# ---------------------------------------------------------------- OKX
OKX_FEE_BRL_TAKER = 0.0002
OKX_BOOK = "https://www.okx.com/api/v5/market/books"


def okx_book(inst: str, sz: int = 400):
    r = requests.get(OKX_BOOK, params={"instId": inst, "sz": sz}, timeout=10).json()
    d = r["data"][0]
    return {"bids": [(float(p), float(q)) for p, q, *_ in d["bids"]],
            "asks": [(float(p), float(q)) for p, q, *_ in d["asks"]], "ts": int(d["ts"])}


def okx_buy_base(asks, qty):
    """BRL cost to buy qty USD-stable (None if book too thin)."""
    cost, left = 0.0, qty
    for p, q in asks:
        t = min(q, left)
        cost += t * p
        left -= t
        if left <= 1e-9:
            return cost
    return None


def okx_sell_base(bids, qty):
    got, left = 0.0, qty
    for p, q in bids:
        t = min(q, left)
        got += t * p
        left -= t
        if left <= 1e-9:
            return got
    return None


def net_bps_book(quotes, book, s, gas_brl, fee=OKX_FEE_BRL_TAKER):
    """Net edge in bps of the BRL notional for both directions using an OKX book.
    usd2brla: DEX USD->BRLA, OKX buys back USD with BRL (asks).  brla2usd: DEX BRLA->USD, OKX sells USD (bids)."""
    mid = (book["bids"][0][0] + book["asks"][0][0]) / 2
    res = {}
    ain, bout, ex = quotes[("usd2brla", s)]
    cost = okx_buy_base(book["asks"], ain)
    res["usd2brla"] = (None if cost is None or ex else
                       (bout - cost * (1 + fee) - gas_brl) / (ain * mid) * 1e4)
    bin_, uout, ex = quotes[("brla2usd", s)]
    got = okx_sell_base(book["bids"], uout)
    res["brla2usd"] = (None if got is None or ex else
                       (got * (1 - fee) - bin_ - gas_brl) / bin_ * 1e4)
    return res


def net_bps_ref(quotes, ref_bid, ref_ask, s, gas_brl, fee=OKX_FEE_BRL_TAKER):
    """Same, against a single reference price (historical candle close +/- half spread)."""
    mid = (ref_bid + ref_ask) / 2
    ain, bout, ex = quotes[("usd2brla", s)]
    a = None if ex else (bout - ain * ref_ask * (1 + fee) - gas_brl) / (ain * mid) * 1e4
    bin_, uout, ex = quotes[("brla2usd", s)]
    b = None if ex else (uout * ref_bid * (1 - fee) - bin_ - gas_brl) / bin_ * 1e4
    return {"usd2brla": a, "brla2usd": b}
