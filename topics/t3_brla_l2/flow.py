"""Swap-flow scan (14 d) for the BRLA pools: gross volume, net direction, tx count, distinct senders.

READ-ONLY public RPC eth_getLogs in chunks. The net one-way flow is what an arb instance can actually
capture per day once the pool sits at the OKX price (each organic sale of BRLA re-opens the gap).
Stores data.db:swaps (one row per swap) and prints a per-pool/day summary.

    python flow.py --days 14
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import time

from web3 import Web3

from l2common import CHAIN_CFG, CS, HERE, PAID, POOLS, RPC, build_w3, word

SWAP_V3 = "0x" + Web3.keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex().removeprefix("0x")
TOKEN_EXCHANGE = "0x" + Web3.keccak(
    text="TokenExchange(address,uint256,uint256,uint256,uint256,uint256,uint256)").hex().removeprefix("0x")
CHUNK = {"base": 10_000, "gnosis": 10_000, "polygon": 5_000, "celo": 20_000}
LOG_RPC = {"base": ["https://mainnet.base.org", "https://base.drpc.org"],
           "gnosis": ["https://rpc.gnosischain.com", "https://gnosis-rpc.publicnode.com"],
           "polygon": ["https://polygon.drpc.org", "https://polygon-bor-rpc.publicnode.com"],
           "celo": ["https://forno.celo.org"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=14)
    ap.add_argument("--chains", default="gnosis,base,celo,polygon")
    ap.add_argument("--paid", action="store_true", help="Alchemy only, 200k-block chunks (counted)")
    a = ap.parse_args()
    db = sqlite3.connect(os.path.join(HERE, "data.db"), timeout=60)
    db.execute("CREATE TABLE IF NOT EXISTS swaps (pool TEXT, block INTEGER, log_index INTEGER, tx TEXT, sender TEXT,"
               " usd_delta REAL, brla_delta REAL, PRIMARY KEY (pool, block, log_index))")
    for chain in a.chains.split(","):
        pools = [p for p in POOLS if p.chain == chain]
        rpc = RPC(chain, paid=a.paid)
        if a.paid:
            rpc.urls, rpc.w3s = rpc.urls[-1:], rpc.w3s[-1:]  # alchemy only
        else:
            rpc.urls = LOG_RPC[chain]
            rpc.w3s = [build_w3(u, 30) for u in rpc.urls]
        head = rpc.run(lambda w3: w3.eth.block_number)
        start = head - int(a.days * 86400 / CHAIN_CFG[chain]["block_s"])
        done = db.execute("SELECT MAX(block) FROM swaps WHERE pool IN (%s)" % ",".join("?" * len(pools)),
                          [p.key for p in pools]).fetchone()[0]
        lo = max(start, (done or 0) + 1)
        addr = {p.address.lower(): p for p in pools}
        n = 0
        ch = 200_000 if a.paid else CHUNK[chain]
        while lo <= head:
            hi = min(lo + ch - 1, head)
            try:
                logs = rpc.run(lambda w3: w3.eth.get_logs({"address": [CS(x) for x in addr], "fromBlock": lo,
                                                           "toBlock": hi, "topics": [[SWAP_V3, TOKEN_EXCHANGE]]}))
            except Exception as e:  # noqa: BLE001
                if ch > 500:
                    ch //= 2
                    continue
                raise e
            rows = []
            for lg in logs:
                p = addr[lg["address"].lower()]
                d = bytes(lg["data"])
                t0 = "0x" + bytes(lg["topics"][0]).hex()
                if t0 == SWAP_V3:
                    a0, a1 = word(d, 0, True), word(d, 1, True)  # pool deltas (+ = into pool)
                    du, db_ = (a0, a1) if p.usd_is_token0 else (a1, a0)
                    sender = "0x" + bytes(lg["topics"][1])[-20:].hex()
                else:  # Curve: sold_id, tokens_sold, bought_id, tokens_bought
                    sid, sold, bid, bought = word(d, 0), word(d, 1), word(d, 2), word(d, 3)
                    iu, ib = p.curve_idx
                    du = sold if sid == iu else -bought
                    db_ = sold if sid == ib else -bought
                    sender = "0x" + bytes(lg["topics"][1])[-20:].hex()
                rows.append((p.key, lg["blockNumber"], lg["logIndex"], "0x" + bytes(lg["transactionHash"]).hex(),
                             sender, du / 10 ** p.usd_dec, db_ / 10 ** p.brla_dec))
            with db:
                db.executemany("INSERT OR REPLACE INTO swaps VALUES (?,?,?,?,?,?,?)", rows)
            n += len(rows)
            lo = hi + 1
            time.sleep(0.2)
        print(chain, "swaps stored", n, "blocks", start, head, "paid calls so far", PAID["n"])
        with db:
            db.execute("CREATE TABLE IF NOT EXISTS rpc_usage (ts TEXT, script TEXT, chain TEXT, paid_calls INTEGER)")
            db.execute("INSERT INTO rpc_usage VALUES (datetime('now'),'flow.py',?,?)", (chain, PAID["n"]))
            PAID["n"] = 0


if __name__ == "__main__":
    main()
