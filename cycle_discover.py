"""Step 0 — discover/validate the pools of the Polygon cycle USDC→BRLA→BRZ→USDT0→USDC.

READ-ONLY (eth_call only). Prints a report and writes cycle_discovery.json.

    python cycle_discover.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from cycle_common import (
    CS, POOL_BRZ_BRLA, POOL_BRZ_USDT0, POOL_TESOURO, POOL_USDC_BRLA, UNI_V3_FACTORY,
    USDC, USDC_E, USDT0, build_w3, call, try_call,
)

ZERO = "0x0000000000000000000000000000000000000000"


def erc20(w3, addr):
    sym = try_call(w3, addr, "symbol()", [], [], ["string"])
    dec = try_call(w3, addr, "decimals()", [], [], ["uint8"])
    return {"address": CS(addr), "symbol": sym[0] if sym else None,
            "decimals": dec[0] if dec else None}


def bal(w3, token, holder):
    r = try_call(w3, token, "balanceOf(address)", ["address"], [CS(holder)], ["uint256"])
    return r[0] if r else None


def v3_pool(w3, pool):
    out = {"address": CS(pool), "code_bytes": len(w3.eth.get_code(CS(pool)))}
    fac = try_call(w3, pool, "factory()", [], [], ["address"])
    t0 = try_call(w3, pool, "token0()", [], [], ["address"])
    t1 = try_call(w3, pool, "token1()", [], [], ["address"])
    fee = try_call(w3, pool, "fee()", [], [], ["uint24"])
    ts = try_call(w3, pool, "tickSpacing()", [], [], ["int24"])
    liq = try_call(w3, pool, "liquidity()", [], [], ["uint128"])
    s0 = try_call(w3, pool, "slot0()", [], [],
                  ["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"])
    if not (fac and t0 and t1 and fee):
        out["is_uniswap_v3_interface"] = False
        return out
    out.update(factory=CS(fac[0]), fee=fee[0], tickSpacing=ts[0] if ts else None,
               liquidity=liq[0] if liq else None)
    tok0, tok1 = erc20(w3, t0[0]), erc20(w3, t1[0])
    out["token0"], out["token1"] = tok0, tok1
    out["is_uniswap_v3_interface"] = True
    out["factory_is_uniswap_v3"] = CS(fac[0]) == CS(UNI_V3_FACTORY)
    gp = try_call(w3, UNI_V3_FACTORY, "getPool(address,address,uint24)",
                  ["address", "address", "uint24"], [CS(t0[0]), CS(t1[0]), fee[0]], ["address"])
    out["factory_getPool_matches"] = bool(gp and CS(gp[0]) == CS(pool))
    if s0:
        sp = s0[0]
        # price of token0 in token1, decimal-adjusted
        p = (sp / 2**96) ** 2 * 10 ** (tok0["decimals"] - tok1["decimals"])
        out["slot0"] = {"sqrtPriceX96": sp, "tick": s0[1], "price_t0_in_t1": p}
    out["reserves"] = {tok0["symbol"]: (bal(w3, t0[0], pool) or 0) / 10 ** tok0["decimals"],
                       tok1["symbol"]: (bal(w3, t1[0], pool) or 0) / 10 ** tok1["decimals"]}
    return out


def stable_pool(w3, pool):
    """Probe a multi-token stable pool: Curve (int128/uint256 variants) and Balancer."""
    out = {"address": CS(pool), "code_bytes": len(w3.eth.get_code(CS(pool)))}
    for sig in ("name()", "symbol()"):
        r = try_call(w3, pool, sig, [], [], ["string"])
        out[sig] = r[0] if r else None
    coins = []
    for idx_t in ("uint256", "int128"):
        coins = []
        for i in range(8):
            r = try_call(w3, pool, f"coins({idx_t})", [idx_t], [i], ["address"])
            if not r:
                break
            coins.append(CS(r[0]))
        if coins:
            out["coins_index_type"] = idx_t
            break
    out["coins"] = [erc20(w3, c) for c in coins]
    for c in out["coins"]:
        c["pool_balance"] = (bal(w3, c["address"], pool) or 0) / 10 ** (c["decimals"] or 18)
    for sig, outt in (("N_COINS()", ["uint256"]), ("A()", ["uint256"]), ("fee()", ["uint256"]),
                      ("offpeg_fee_multiplier()", ["uint256"]), ("get_virtual_price()", ["uint256"]),
                      ("factory()", ["address"]), ("getPoolId()", ["bytes32"]),
                      ("getVault()", ["address"]), ("lp_token()", ["address"]),
                      ("stored_rates()", ["uint256[]"]), ("version()", ["string"])):
        r = try_call(w3, pool, sig, [], [], outt)
        out[sig] = (r[0].hex() if isinstance(r[0], bytes) else
                    (CS(r[0]) if outt == ["address"] else r[0])) if r else None
    # get_dy probe (1 unit of coin i -> coin j), both index encodings
    if len(coins) >= 2:
        dec0 = out["coins"][0]["decimals"] or 18
        for sig in ("get_dy(int128,int128,uint256)", "get_dy(uint256,uint256,uint256)"):
            t = "int128" if "int128" in sig else "uint256"
            r = try_call(w3, pool, sig, [t, t, "uint256"], [0, 1, 10 ** dec0], ["uint256"])
            if r:
                out["get_dy_signature"] = sig
                out["get_dy_0to1_1unit"] = r[0] / 10 ** (out["coins"][1]["decimals"] or 18)
                break
    # EIP-1167 minimal proxy?
    code = w3.eth.get_code(CS(pool))
    if len(code) == 45 and code[:10].hex() == "363d3d373d3d3d363d73":
        out["eip1167_impl"] = CS("0x" + code[10:30].hex())
    return out


def main():
    w3 = build_w3()
    blk = w3.eth.block_number
    rep = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "block": blk,
           "chain_id": w3.eth.chain_id, "tokens": {}, "pools": {}, "closing_leg": {}}
    for name, a in (("USDC", USDC), ("USDC.e", USDC_E), ("USDT0", USDT0)):
        rep["tokens"][name] = erc20(w3, a)
    for name, p in (("USDC/BRLA", POOL_USDC_BRLA), ("BRZ/USDT0", POOL_BRZ_USDT0),
                    ("BRZ/BRLA", POOL_BRZ_BRLA)):
        rep["pools"][name] = v3_pool(w3, p)
    rep["pools"]["TESOURO_stable"] = stable_pool(w3, POOL_TESOURO)

    # Pull BRLA/BRZ addresses from the verified pools
    brla = rep["pools"]["USDC/BRLA"]["token1"]["address"]
    brz = rep["pools"]["BRZ/USDT0"]["token0"]["address"]
    rep["tokens"]["BRLA"] = erc20(w3, brla)
    rep["tokens"]["BRZ"] = erc20(w3, brz)

    # Every v3 pool among the cycle tokens, all fee tiers
    pairs = {"USDT0/USDC": (USDT0, USDC), "USDT0/USDC.e": (USDT0, USDC_E),
             "USDC/USDC.e": (USDC, USDC_E), "BRZ/BRLA": (brz, brla), "USDC/BRLA": (USDC, brla),
             "USDC.e/BRLA": (USDC_E, brla), "BRZ/USDT0": (brz, USDT0), "BRZ/USDC": (brz, USDC),
             "USDT0/BRLA": (USDT0, brla), "BRZ/USDC.e": (brz, USDC_E)}
    for name, (a, b) in pairs.items():
        found = {}
        for fee in (100, 500, 3000, 10000):
            r = try_call(w3, UNI_V3_FACTORY, "getPool(address,address,uint24)",
                         ["address", "address", "uint24"], [CS(a), CS(b), fee], ["address"])
            if r and CS(r[0]) != ZERO:
                pi = v3_pool(w3, r[0])
                found[str(fee)] = {"pool": CS(r[0]), "liquidity": pi.get("liquidity"),
                                   "reserves": pi.get("reserves"),
                                   "price_t0_in_t1": pi.get("slot0", {}).get("price_t0_in_t1")}
        rep["closing_leg"][name] = found

    with open("cycle_discovery.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, default=str)
    print(json.dumps(rep, indent=2, default=str))


if __name__ == "__main__":
    main()
