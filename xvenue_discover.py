"""Discover/validate Uni v3 BTC & ETH pools vs USDC on Polygon / Arbitrum / Base (item 1).

READ-ONLY (eth_call). For each (chain, asset) lists every fee tier with reserves, liquidity and a
$10k QuoterV2 round-trip impact, then picks the best pool. Writes xvenue_discovery.json.

    python xvenue_discover.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from chains import CHAINS, rpc_list
from cycle_common import CS, build_w3, try_call

ZERO = "0x0000000000000000000000000000000000000000"
ASSETS = {"BTC": ("WBTC", "cbBTC"), "ETH": ("WETH",)}


def main():
    rep = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "chains": {}}
    for chain, cfg in CHAINS.items():
        w3 = build_w3(rpc_list(chain)[0])
        assert w3.eth.chain_id == cfg["chain_id"], chain
        usdc, usdc_dec = cfg["tokens"]["USDC"]
        out = {}
        for asset, syms in ASSETS.items():
            sym = next((s for s in syms if s in cfg["tokens"]), None)
            if not sym:
                continue
            tok, dec = cfg["tokens"][sym]
            tiers = {}
            for fee in (100, 500, 3000, 10000):
                r = try_call(w3, cfg["v3_factory"], "getPool(address,address,uint24)",
                             ["address", "address", "uint24"], [CS(tok), CS(usdc), fee], ["address"])
                if not r or CS(r[0]) == ZERO:
                    continue
                pool = CS(r[0])
                bt = try_call(w3, tok, "balanceOf(address)", ["address"], [pool], ["uint256"])
                bu = try_call(w3, usdc, "balanceOf(address)", ["address"], [pool], ["uint256"])
                # $10k USDC -> asset -> USDC round trip via QuoterV2 (fee + impact, both ways)
                q1 = try_call(w3, cfg["quoter_v2"],
                              "quoteExactInputSingle((address,address,uint256,uint24,uint160))",
                              ["(address,address,uint256,uint24,uint160)"],
                              [(CS(usdc), CS(tok), 10_000 * 10**usdc_dec, fee, 0)],
                              ["uint256", "uint160", "uint32", "uint256"])
                rt = None
                if q1 and q1[0]:
                    q2 = try_call(w3, cfg["quoter_v2"],
                                  "quoteExactInputSingle((address,address,uint256,uint24,uint160))",
                                  ["(address,address,uint256,uint24,uint160)"],
                                  [(CS(tok), CS(usdc), q1[0], fee, 0)],
                                  ["uint256", "uint160", "uint32", "uint256"])
                    if q2:
                        rt = (q2[0] / (10_000 * 10**usdc_dec) - 1) * 1e4
                tiers[str(fee)] = {"pool": pool,
                                   "reserve_asset": (bt[0] / 10**dec) if bt else None,
                                   "reserve_usdc": (bu[0] / 10**usdc_dec) if bu else None,
                                   "roundtrip_10k_bps": rt,
                                   "price_usdc": (10_000 / (q1[0] / 10**dec)) if q1 and q1[0] else None}
            best = max((t for t in tiers.items() if t[1]["roundtrip_10k_bps"] is not None),
                       key=lambda t: t[1]["roundtrip_10k_bps"], default=None)
            out[asset] = {"token": sym, "address": CS(tok), "decimals": dec, "tiers": tiers,
                          "best_fee": int(best[0]) if best else None}
            print(chain, asset, sym, {k: (round(v["reserve_usdc"] or 0), v["roundtrip_10k_bps"] and
                                         round(v["roundtrip_10k_bps"], 1)) for k, v in tiers.items()},
                  "best", out[asset]["best_fee"], flush=True)
        rep["chains"][chain] = out
    with open("xvenue_discovery.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)


if __name__ == "__main__":
    main()
