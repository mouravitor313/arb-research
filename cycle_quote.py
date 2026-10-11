"""Quote engine for the Polygon atomic cycle USDC→BRLA→BRZ→USDT0→USDC (and reverse).

READ-ONLY: every quote is an eth_call (QuoterV2 / V4Quoter / Curve get_dy) batched via Multicall3
and pinned to one block. Pool fees and price impact are already inside the quotes.

Legs (pools verified by cycle_discover.py, see cycle_discovery.json):
  USDC<->BRLA   Uni v3 0.05%  0x0e77…c956
  BRLA<->BRZ    'uni'  : Uni v3 0.05% 0x6e05…fb86 (thin: ~$8k, skewed)
                'curve': Curve stableswap-ng 'DFB BRL Pool v1' 0xc89f…9735 (fee 0.03%)
  BRZ<->USDT0   Uni v3 0.05%  0x4af6…0817
  USDT0<->USDC  'v3'   : Uni v3 0.01% 0x3108…81B7
                'v4'   : Uni v4 fee 8 (0.0008%), tickSpacing 1, no hooks (pool id 0xa37d…a399)

Forward (fwd):  USDC -> BRLA -> BRZ -> USDT0 -> USDC   (close leg = USDT0->USDC, best of v3/v4)
Reverse (rev):  USDC -> USDT0 -> BRZ -> BRLA -> USDC   (open leg  = USDC->USDT0, best of v3/v4)
Route = bridge venue for BRLA<->BRZ ('uni' = all-Uniswap, fits a router multi-hop / UniversalRouter;
'curve' = needs an executor contract, RECAP §6 level 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from eth_abi import decode as abi_decode
from web3 import Web3

from cycle_common import (
    CS, POOL_TESOURO, QUOTER_V2, UNI_V3_FACTORY, USDC, USDT0, encode, multicall, try_call,
)

BRLA = "0xE6A537a407488807F0bbeb0038B79004f19DDDFb"
BRZ = "0x4eD141110F6EeeAbA9A1df36d8c26f684d2475Dc"
WPOL = "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"
V4_QUOTER = "0xb3d5c3dfc3a7aebff71895a7191796bffc2c81b9"
V4_POOL_ID = "0xa37d3e6da98dfeb7dc8103a6614f586916a6e04d41ea0a929bc19a029de1a399"
V4_KEY = (CS(USDC), CS(USDT0), 8, 1, "0x0000000000000000000000000000000000000000")

CURVE_IDX = {BRZ: 1, BRLA: 3}  # coins: 0 TESOURO, 1 BRZ, 2 stBRZ, 3 BRLA
FEE = {"usdc_brla": 500, "brz_brla": 500, "brz_usdt0": 500, "usdt0_usdc": 100}
DEC = {USDC: 6, USDT0: 6, BRLA: 18, BRZ: 18}

MIN_SQRT = 4295128739
MAX_SQRT = 1461446703485210103287273052203988822378723970342

# Gas assumptions for legs without an on-chain gas estimate (documented in PROJECT.md).
CURVE_SWAP_GAS = 160_000      # stableswap-ng exchange, 4 coins
TX_OVERHEAD_GAS = 21_000 + 60_000  # base tx + router/executor transfers & calldata

SIZES_USD = (1_000, 10_000, 100_000)
ROUTES = ("uni", "curve")


@dataclass
class Leg:
    venue: str
    amount_in: int
    amount_out: int = 0
    gas: int = 0
    exhausted: bool = False  # v3 price hit MIN/MAX sqrt -> pool drained, quote is partial
    ok: bool = True


@dataclass
class CycleQuote:
    direction: str
    route: str
    size_usd: int
    amount_in: int
    legs: list[Leg] = field(default_factory=list)

    @property
    def amount_out(self) -> int:
        return self.legs[-1].amount_out if self.legs else 0

    @property
    def ok(self) -> bool:
        return all(lg.ok for lg in self.legs) and len(self.legs) == 4

    @property
    def exhausted(self) -> bool:
        return any(lg.exhausted for lg in self.legs)

    @property
    def gas(self) -> int:
        return sum(lg.gas for lg in self.legs) + TX_OVERHEAD_GAS

    @property
    def gross_bps(self) -> float:
        return (self.amount_out - self.amount_in) / self.amount_in * 1e4

    def net_bps(self, gas_usd: float) -> float:
        return ((self.amount_out - self.amount_in) / 1e6 - gas_usd) / (self.amount_in / 1e6) * 1e4

    @property
    def venues(self) -> str:
        return ">".join(lg.venue for lg in self.legs)


# ---------- calldata builders (target, calldata, decoder) ----------

def _v3_single(tin: str, tout: str, fee: int, amt: int):
    cd = encode("quoteExactInputSingle((address,address,uint256,uint24,uint160))",
                ["(address,address,uint256,uint24,uint160)"], [(CS(tin), CS(tout), amt, fee, 0)])

    def dec(raw: bytes):
        out, sp, _ticks, gas = abi_decode(["uint256", "uint160", "uint32", "uint256"], raw)
        return out, gas, sp <= MIN_SQRT + 1 or sp >= MAX_SQRT - 1
    return QUOTER_V2, cd, dec


def _v4_single(tin: str, amt: int):
    zero_for_one = CS(tin) == V4_KEY[0]
    cd = encode("quoteExactInputSingle(((address,address,uint24,int24,address),bool,uint128,bytes))",
                ["((address,address,uint24,int24,address),bool,uint128,bytes)"],
                [(V4_KEY, zero_for_one, amt, b"")])

    def dec(raw: bytes):
        out, gas = abi_decode(["uint256", "uint256"], raw)
        return out, gas, False
    return V4_QUOTER, cd, dec


def _curve(tin: str, tout: str, amt: int):
    cd = encode("get_dy(int128,int128,uint256)", ["int128", "int128", "uint256"],
                [CURVE_IDX[tin], CURVE_IDX[tout], amt])

    def dec(raw: bytes):
        (out,) = abi_decode(["uint256"], raw)
        return out, CURVE_SWAP_GAS, False
    return CS(POOL_TESOURO), cd, dec


def _leg_call(venue: str, tin: str, tout: str, amt: int):
    if venue == "curve":
        return _curve(tin, tout, amt)
    if venue == "v4":
        return _v4_single(tin, amt)
    fee = {"uni": FEE["brz_brla"], "v3": FEE["usdt0_usdc"]}.get(venue)
    if fee is None:  # fixed legs named by pair
        fee = FEE[venue]
    return _v3_single(tin, tout, fee, amt)


def _run(w3: Web3, jobs: list[tuple[str, str, str, int]], block: int) -> list[tuple[int, int, bool, bool]]:
    """jobs = [(venue, tin, tout, amt)] -> [(out, gas, exhausted, ok)]"""
    if not jobs:
        return []
    built = [_leg_call(v, a, b, amt) for v, a, b, amt in jobs]
    res = multicall(w3, [(t, cd) for t, cd, _ in built], block=block)
    out = []
    for (success, raw), (_, _, dec) in zip(res, built):
        if not success or not raw:
            out.append((0, 0, False, False))
            continue
        try:
            o, g, ex = dec(raw)
            out.append((int(o), int(g), bool(ex), True))
        except Exception:  # noqa: BLE001
            out.append((0, 0, False, False))
    return out


# Path of each direction: list of (tin, tout, venue options). 'BRIDGE' = route-specific venue.
PATHS = {
    "fwd": [(USDC, BRLA, ["usdc_brla"]), (BRLA, BRZ, ["BRIDGE"]),
            (BRZ, USDT0, ["brz_usdt0"]), (USDT0, USDC, ["v3", "v4"])],
    "rev": [(USDC, USDT0, ["v3", "v4"]), (USDT0, BRZ, ["brz_usdt0"]),
            (BRZ, BRLA, ["BRIDGE"]), (BRLA, USDC, ["usdc_brla"])],
}


def quote_cycles(w3: Web3, block: int, sizes=SIZES_USD) -> list[CycleQuote]:
    """All (direction × route × size) cycles, 4 multicalls total, pinned to `block`.

    Where a leg has several venues (USDT0<->USDC: v3 0.01% vs v4), the best output is kept.
    """
    cycles = [CycleQuote(d, r, s, s * 10**6) for d in PATHS for r in ROUTES for s in sizes]
    for step in range(4):
        jobs, owners = [], []
        for ci, c in enumerate(cycles):
            if step > 0 and not c.legs[-1].ok:
                continue
            tin, tout, venues = PATHS[c.direction][step]
            amt = c.amount_in if step == 0 else c.legs[-1].amount_out
            for v in venues:
                v = c.route if v == "BRIDGE" else v
                jobs.append((v, tin, tout, amt))
                owners.append((ci, v, amt))
        results = _run(w3, jobs, block)
        best: dict[int, Leg] = {}
        for (ci, v, amt), (o, g, ex, ok) in zip(owners, results):
            leg = Leg(v, amt, o, g, ex, ok)
            cur = best.get(ci)
            if cur is None or (leg.ok and (not cur.ok or leg.amount_out > cur.amount_out)):
                best[ci] = leg
        for ci, c in enumerate(cycles):
            if ci in best:
                c.legs.append(best[ci])
            elif c.legs and len(c.legs) == step:  # skipped because prior leg failed
                c.legs.append(Leg("skip", 0, ok=False))
    return cycles


# ---------- gas price & POL/USD ----------

_wpol_pool: str | None = None


def pol_usd(w3: Web3, block: int | str = "latest") -> float:
    """POL price in USDC from the Uni v3 WPOL/USDC 0.05% pool slot0."""
    global _wpol_pool
    if _wpol_pool is None:
        (p,) = try_call(w3, UNI_V3_FACTORY, "getPool(address,address,uint24)",
                        ["address", "address", "uint24"], [CS(WPOL), CS(USDC), 500], ["address"])
        _wpol_pool = CS(p)
    s0 = try_call(w3, _wpol_pool, "slot0()", [], [],
                  ["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"], block)
    p_t0_t1 = (s0[0] / 2**96) ** 2  # raw
    # token0 = WPOL (0x0d5… < 0x3c4…), 18 dec; token1 = USDC 6 dec
    return p_t0_t1 * 10 ** (18 - 6)


def gas_usd(gas: int, gas_price_wei: int, pol_price: float) -> float:
    return gas * gas_price_wei / 1e18 * pol_price


def v3_multihop_quote(w3: Web3, tokens: list[str], fees: list[int], amt: int, block: int):
    """Cross-check: QuoterV2.quoteExactInput(path) for an all-v3 path -> (out, gasEstimate)."""
    from cycle_common import v3_path
    r = try_call(w3, QUOTER_V2, "quoteExactInput(bytes,uint256)", ["bytes", "uint256"],
                 [v3_path(tokens, fees), amt], ["uint256", "uint160[]", "uint32[]", "uint256"], block)
    return (r[0], r[3]) if r else (None, None)
