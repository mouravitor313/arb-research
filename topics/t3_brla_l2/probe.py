"""One-shot executable probe: every BRLA pool (Base/Gnosis/Celo + Polygon ref) vs OKX BRL books.

READ-ONLY, public RPCs + OKX public API. Net of OKX taker (2 bps, BRL pair), pool fee (inside quote), gas.
BRLA = R$1. Writes probe_<ts>.json and appends to data.db (table probe).

    python topics/t3_brla_l2/probe.py [--sizes 250,500,1000,...]
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone

import requests

from l2common import (CHAIN_CFG, HERE, POOLS, RPC, curve_calls, fetch_cl_states, mid_brla_per_usd, multicall,
                      net_bps_book, okx_book, quote_pool)

GRID = [250, 500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]


def okx_last(inst):
    return float(requests.get("https://www.okx.com/api/v5/market/ticker", params={"instId": inst},
                              timeout=10).json()["data"][0]["last"])


def gas_usd(chain, rpc, block):
    c = CHAIN_CFG[chain]
    gp = rpc.run(lambda w3: w3.eth.gas_price)
    px = c["gas_token_usd"] or okx_last(c["gas_okx"])
    return gp * c["swap_gas"] / 1e18 * px + c["l1_fee_usd"], gp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default=",".join(map(str, GRID)))
    a = ap.parse_args()
    sizes = [int(x) for x in a.sizes.split(",")]
    books = {i: okx_book(i) for i in ("USDC-BRL", "USDT-BRL")}
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {"ts": ts, "okx": {i: {"bid": b["bids"][0][0], "ask": b["asks"][0][0],
                                  "bid_depth_usd_20": sum(q for _, q in b["bids"][:20]),
                                  "ask_depth_usd_20": sum(q for _, q in b["asks"][:20])} for i, b in books.items()},
           "pools": {}}
    for chain in dict.fromkeys(p.chain for p in POOLS):
        rpc = RPC(chain)
        block = rpc.run(lambda w3: w3.eth.block_number) - 2
        gusd, gp = gas_usd(chain, rpc, block)
        cl = [p for p in POOLS if p.chain == chain and p.kind == "cl"]
        states = fetch_cl_states(rpc, cl, block) if cl else {}
        for p in [q for q in POOLS if q.chain == chain]:
            book = books[p.okx_ref]
            okx_mid = (book["bids"][0][0] + book["asks"][0][0]) / 2
            st = states.get(p.key)
            cres = None
            if p.kind == "curve":
                cres = rpc.run(lambda w3: multicall(w3, curve_calls(p, sizes, okx_mid), block))
            q = quote_pool(p, st, cres, sizes, okx_mid)
            if p.kind == "cl":
                pm = mid_brla_per_usd(p, st)
            else:  # marginal from the smallest size, both ways (fee-inclusive)
                s0 = sizes[0]
                pm = ((q[("usd2brla", s0)][1] / s0) * (q[("brla2usd", s0)][0] / q[("brla2usd", s0)][1])) ** 0.5
            gas_brl = gusd * okx_mid
            rows = []
            for s in sizes:
                n = net_bps_book(q, book, s, gas_brl)
                rows.append({"size": s, "usd2brla_net_bps": n["usd2brla"], "brla2usd_net_bps": n["brla2usd"],
                             "dex_brla_out": q[("usd2brla", s)][1], "dex_usd_out": q[("brla2usd", s)][1],
                             "exhausted": [q[("usd2brla", s)][2], q[("brla2usd", s)][2]]})
            dev = (pm / okx_mid - 1) * 1e4
            out["pools"][p.key] = {"chain": chain, "block": block, "okx_ref": p.okx_ref, "dex_mid_brla_per_usd": pm,
                                   "okx_mid": okx_mid, "dex_vs_okx_mid_bps": dev, "gas_usd": gusd,
                                   "fee_pips": st.fee if st else None, "rows": rows}
            print(f"\n{p.key} blk {block} DEX mid {pm:.4f} vs OKX {p.okx_ref} {okx_mid:.4f} -> {dev:+.1f} bps "
                  f"(BRLA {'barato' if dev > 0 else 'caro'} no DEX), gas ${gusd:.4f}")
            for r in rows:
                f = lambda x: "   n/a" if x is None else f"{x:+6.1f}"  # noqa: E731
                print(f"  ${r['size']:>7,}  USD->BRLA(DEX)+compra USD OKX {f(r['usd2brla_net_bps'])}   "
                      f"BRLA->USD(DEX)+vende USD OKX {f(r['brla2usd_net_bps'])}")
    path = os.path.join(HERE, f"probe_{ts.replace(':', '').replace('-', '')[:15]}.json")
    json.dump(out, open(path, "w"), indent=1)
    db = sqlite3.connect(os.path.join(HERE, "data.db"))
    db.execute("CREATE TABLE IF NOT EXISTS probe (ts TEXT, pool TEXT, size INTEGER, usd2brla REAL, brla2usd REAL,"
               " dev_mid_bps REAL, PRIMARY KEY (ts, pool, size))")
    with db:
        for k, v in out["pools"].items():
            for r in v["rows"]:
                db.execute("INSERT OR REPLACE INTO probe VALUES (?,?,?,?,?,?)",
                           (ts, k, r["size"], r["usd2brla_net_bps"], r["brla2usd_net_bps"], v["dex_vs_okx_mid_bps"]))
    print("\nOKX:", json.dumps(out["okx"]), "\n->", path)


if __name__ == "__main__":
    main()
