"""On-chain NAV readers for the t6_rwa candidates (READ-ONLY eth_call, public RPC by default).

    python topics/t6_rwa/nav.py            # print NAVs at latest block (Ethereum)
    from nav import read_navs; read_navs(block=...)

NAV = underlying units per 1 token (USD for USDC/USDS/frxUSD/crvUSD-denominated vaults).
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import chains  # noqa: E402  (read-only import: rpc_list/alchemy_url)
from cycle_common import CS, abi_decode, build_w3, encode, multicall  # noqa: E402

# name -> (contract, signature, arg, out_decimals, note)
ETH_NAVS = {
    "syrupUSDC_exit": ("0x80ac24aA929eaF5013f6436cdA2a7ba190f5Cc0b", "convertToExitAssets(uint256)", 10**6, 6, "USDC per syrupUSDC (net unrealized losses)"),
    "syrupUSDC": ("0x80ac24aA929eaF5013f6436cdA2a7ba190f5Cc0b", "convertToAssets(uint256)", 10**6, 6, "USDC per syrupUSDC"),
    "syrupUSDT_exit": ("0x356b8d89c1e1239cbbb9de4815c39a1474d5ba7d", "convertToExitAssets(uint256)", 10**6, 6, "USDT per syrupUSDT"),
    "USDY": ("0xA0219AA5B31e65Bc920B5b6DFb8EdF0988121De0", "getPrice()", None, 18, "RWADynamicOracle USD per USDY"),
    "sfrxUSD": ("0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6", "convertToAssets(uint256)", 10**18, 18, "frxUSD per sfrxUSD"),
    "sUSDS": ("0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD", "convertToAssets(uint256)", 10**18, 18, "USDS per sUSDS"),
    "sDAI": ("0x83F20F44975D03b1b09e64809B757c47f942BEeA", "convertToAssets(uint256)", 10**18, 18, "DAI per sDAI"),
    "scrvUSD": ("0x0655977FEb2f289A4aB78af67BAB0d17aAb84367", "convertToAssets(uint256)", 10**18, 18, "crvUSD per scrvUSD"),
    "cUSDO": ("0xaD55aebc9b8c03FC43cd9f62260391c13c23e7c0", "convertToAssets(uint256)", 10**18, 18, "USDO per cUSDO"),
    "USTB": ("0xe4fa682f94610ccd170680cc3b045d77d9e528a8", "latestRoundData()", None, None, "Superstate continuous oracle (ref only)"),
}


def _cd(sig, arg):
    if arg is None:
        return encode(sig, [], [])
    return encode(sig, ["uint256"], [arg])


def read_navs(w3=None, block="latest", names=None) -> dict:
    w3 = w3 or build_w3(chains.rpc_list("ethereum")[0])
    names = names or list(ETH_NAVS)
    calls = [(ETH_NAVS[n][0], _cd(ETH_NAVS[n][1], ETH_NAVS[n][2])) for n in names]
    res = multicall(w3, calls, block)
    out = {}
    for n, (ok, raw) in zip(names, res):
        addr, sig, arg, dec, _ = ETH_NAVS[n]
        if not ok or not raw:
            out[n] = None
            continue
        if sig == "latestRoundData()":
            _, ans, _, upd, _ = abi_decode(["uint80", "int256", "uint256", "uint256", "uint80"], raw)
            dec_ = abi_decode(["uint8"], w3.eth.call({"to": CS(addr), "data": encode("decimals()", [], [])}, block))[0]
            out[n] = ans / 10**dec_
        else:
            out[n] = abi_decode(["uint256"], raw)[0] / 10**dec
    return out


if __name__ == "__main__":
    w3 = build_w3(chains.rpc_list("ethereum")[0])
    b = w3.eth.block_number
    navs = read_navs(w3, b)
    print("block", b)
    print(json.dumps(navs, indent=1))
