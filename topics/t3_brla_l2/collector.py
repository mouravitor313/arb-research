"""Live collector: BRLA pools (Gnosis Oku + Curve, Base Aerodrome, Polygon ref) vs OKX USDC-BRL book.

READ-ONLY, public RPCs (latest block) + OKX public book. One tick every --interval s (>= 5 s per OKX book rule).
Per tick and pool: executable net bps at SIZES, both directions, against the *live* book (taker 2 bps, gas).
Stores data.db:live. Stops by itself after --hours.

    python collector.py --interval 15 --hours 24
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from l2common import (HERE, POOLS, RPC, curve_calls, fetch_cl_states, mid_brla_per_usd, multicall, net_bps_book,
                      okx_book, quote_pool)

SIZES = [500, 1_000, 2_000, 5_000, 10_000]
KEYS = ["gnosis_oku_005", "gnosis_curve", "base_aero_005", "polygon_uni_005"]
GAS_USD = {"base": 0.005, "gnosis": 0.0005, "polygon": 0.004}
SCHEMA = """
CREATE TABLE IF NOT EXISTS live (
  ts TEXT, unix INTEGER, pool TEXT, block INTEGER, size INTEGER,
  usd2brla REAL, brla2usd REAL, dex_mid REAL, okx_bid REAL, okx_ask REAL,
  PRIMARY KEY (unix, pool, size));
"""
log = logging.getLogger("collector")


def chain_tick(chain, rpc, pools, mid, hints):
    block = rpc.run(lambda w3: w3.eth.block_number)
    cl = [p for p in pools if p.kind == "cl"]
    states = fetch_cl_states(rpc, cl, block, hints.get(chain)) if cl else {}
    hints[chain] = {k: s.tick for k, s in states.items()}
    out = {}
    for p in pools:
        st = states.get(p.key)
        cres = rpc.run(lambda w3: multicall(w3, curve_calls(p, SIZES, mid), block)) if p.kind == "curve" else None
        q = quote_pool(p, st, cres, SIZES, mid)
        out[p.key] = (block, q, mid_brla_per_usd(p, st) if st else None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=15)
    ap.add_argument("--hours", type=float, default=24)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(HERE, "collector.log"), encoding="utf-8")])
    pools = [p for p in POOLS if p.key in KEYS]
    by_chain = {}
    for p in pools:
        by_chain.setdefault(p.chain, []).append(p)
    rpcs = {c: RPC(c) for c in by_chain}  # public only
    db = sqlite3.connect(os.path.join(HERE, "data.db"), timeout=60)
    db.executescript(SCHEMA)
    hints: dict = {}
    end = time.time() + a.hours * 3600
    n = 0
    ex = ThreadPoolExecutor(max_workers=len(by_chain))
    while time.time() < end:
        t0 = time.time()
        try:
            book = okx_book("USDC-BRL")
            mid = (book["bids"][0][0] + book["asks"][0][0]) / 2
            futs = {c: ex.submit(chain_tick, c, rpcs[c], ps, mid, hints) for c, ps in by_chain.items()}
            unix = int(t0)
            ts = datetime.fromtimestamp(unix, timezone.utc).isoformat(timespec="seconds")
            rows = []
            for c, f in futs.items():
                try:
                    res = f.result(timeout=max(a.interval * 2, 30))
                except Exception as e:  # noqa: BLE001
                    log.warning("%s tick failed: %s", c, str(e)[:160])
                    continue
                for key, (block, q, dmid) in res.items():
                    gas_brl = GAS_USD[c] * mid
                    for s in SIZES:
                        nb = net_bps_book(q, book, s, gas_brl)
                        rows.append((ts, unix, key, block, s, nb["usd2brla"], nb["brla2usd"], dmid,
                                     book["bids"][0][0], book["asks"][0][0]))
            with db:
                db.executemany("INSERT OR REPLACE INTO live VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
            n += 1
            if n % 40 == 1:
                best = {r[2]: max(x for x in (r[5], r[6], -999) if x is not None) for r in rows if r[4] == 1000}
                log.info("tick %d okx mid %.4f best@1k %s", n, mid,
                         {k: round(v, 1) for k, v in best.items()})
        except Exception as e:  # noqa: BLE001
            log.warning("tick error: %s", str(e)[:200])
        time.sleep(max(0.0, a.interval - (time.time() - t0)))
    log.info("done after %d ticks", n)


if __name__ == "__main__":
    main()
