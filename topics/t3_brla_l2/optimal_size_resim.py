"""Exact small-size re-simulation on a subsample of dex_hist blocks (validation for optimal_size.py).

READ-ONLY, public archive RPCs only (same filter as backfill.py). For ~--n blocks per chain (evenly spaced over the
blocks already in dex_hist) re-fetches the CL state / Curve get_dy at that block and quotes SMALL sizes in both
directions (brla2usd input = size * 5 BRLA, same convention as backfill.py). Stores data.db:small_resim. Resumable.

    python optimal_size_resim.py --chain gnosis --n 100
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone

from l2common import HERE, PAID, POOLS, RPC, curve_calls, fetch_cl_states, multicall, quote_pool

SMALL = [20, 50, 100, 150, 200, 300, 500]
REF_BRLA_PER_USD = 5.0
DB = os.path.join(HERE, "data.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS small_resim (
  unix INTEGER, chain TEXT, block INTEGER, pool TEXT, dir TEXT, size INTEGER,
  amount_in REAL, amount_out REAL, exhausted INTEGER,
  PRIMARY KEY (pool, block, dir, size));
CREATE TABLE IF NOT EXISTS rpc_usage (ts TEXT, script TEXT, chain TEXT, paid_calls INTEGER);
"""
log = logging.getLogger("resim")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=0.3)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(HERE, f"resim_{a.chain}.log"), encoding="utf-8"),
                                  logging.StreamHandler()])
    pools = [p for p in POOLS if p.chain == a.chain and p.key != "celo_uni_001"]
    cl = [p for p in pools if p.kind == "cl"]
    rpc = RPC(a.chain)  # public only
    keep = [i for i, u in enumerate(rpc.urls) if "publicnode" not in u and "gnosis.drpc" not in u]
    rpc.urls = [rpc.urls[i] for i in keep]
    rpc.w3s = [rpc.w3s[i] for i in keep]
    db = sqlite3.connect(DB, timeout=60)
    db.executescript(SCHEMA)
    allb = [r for r in db.execute("SELECT DISTINCT block, unix FROM dex_hist WHERE chain=? ORDER BY block", (a.chain,))]
    stepi = max(1, len(allb) // a.n)
    pick = allb[::stepi][:a.n]
    have = {r[0] for r in db.execute("SELECT DISTINCT block FROM small_resim WHERE chain=?", (a.chain,))}
    todo = [(b, u) for b, u in pick if b not in have]
    log.info("%s: %d picked, %d to fetch via %s", a.chain, len(pick), len(todo), [rpc.label(i) for i in range(len(rpc.urls))])
    hints: dict[str, int] = {}
    for i, (b, u) in enumerate(todo):
        try:
            states = fetch_cl_states(rpc, cl, b, hints) if cl else {}
            hints = {k: s.tick for k, s in states.items()}
            rows = []
            for p in pools:
                st = states.get(p.key)
                cres = (rpc.run(lambda w3: multicall(w3, curve_calls(p, SMALL, REF_BRLA_PER_USD), b))
                        if p.kind == "curve" else None)
                for (d, s), (ain, aout, ex) in quote_pool(p, st, cres, SMALL, REF_BRLA_PER_USD).items():
                    rows.append((u, a.chain, b, p.key, d, s, ain, aout, int(ex)))
        except Exception as e:  # noqa: BLE001
            log.warning("block %d failed: %s", b, str(e)[:200])
            continue
        with db:
            db.executemany("INSERT OR REPLACE INTO small_resim VALUES (?,?,?,?,?,?,?,?,?)", rows)
        if i % 10 == 0:
            log.info("%d/%d block %d paid_calls %d", i, len(todo), b, PAID["n"])
        time.sleep(a.sleep)
    with db:
        db.execute("INSERT INTO rpc_usage VALUES (?,?,?,?)",
                   (datetime.now(timezone.utc).isoformat(timespec="seconds"), "optimal_size_resim.py", a.chain, PAID["n"]))
    log.info("done, paid calls %d", PAID["n"])


if __name__ == "__main__":
    main()
