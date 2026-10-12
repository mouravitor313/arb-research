"""Archive backfill of executable DEX quotes for the BRLA pools (one chain per process).

READ-ONLY. Samples one block every --step-min minutes over --days, quotes every pool of the chain at
SIZES in both directions (local CL simulator / Curve get_dy at that block) and stores raw DEX amounts in
data.db:dex_hist. The OKX side is applied later in analyze.py (1m candles, see okx_candles.py).
Public archive RPCs first; Alchemy only with --paid (appended as last fallback, calls counted).
Resumable (skips stored blocks).

    python backfill.py --chain gnosis --days 14 --step-min 30
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone

from l2common import (CHAIN_CFG, HERE, PAID, POOLS, RPC, curve_calls, fetch_cl_states, mid_brla_per_usd,
                      multicall, quote_pool)

SIZES = [500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]
REF_BRLA_PER_USD = 5.0  # BRLA-in sizing only (sell size*5 BRLA); analyze.py normalises by actual notional
DB = os.path.join(HERE, "data.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS dex_hist (
  ts TEXT, unix INTEGER, chain TEXT, block INTEGER, pool TEXT, dir TEXT, size INTEGER,
  amount_in REAL, amount_out REAL, exhausted INTEGER, dex_mid REAL, fee_pips INTEGER,
  PRIMARY KEY (pool, block, dir, size));
CREATE TABLE IF NOT EXISTS rpc_usage (ts TEXT, script TEXT, chain TEXT, paid_calls INTEGER);
"""
log = logging.getLogger("backfill")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True)
    ap.add_argument("--days", type=float, default=14)
    ap.add_argument("--step-min", type=float, default=30)
    ap.add_argument("--paid", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--extend", action="store_true", help="only blocks older than what is already stored")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(HERE, f"backfill_{a.chain}.log"), encoding="utf-8"),
                                  logging.StreamHandler()])
    pools = [p for p in POOLS if p.chain == a.chain]
    cl = [p for p in pools if p.kind == "cl"]
    rpc = RPC(a.chain, paid=a.paid)
    # archive-capable public endpoints only (publicnode / gnosis.drpc are not archive)
    keep = [i for i, u in enumerate(rpc.urls) if "publicnode" not in u and "gnosis.drpc" not in u]
    rpc.urls = [rpc.urls[i] for i in keep]
    rpc.w3s = [rpc.w3s[i] for i in keep]
    db = sqlite3.connect(DB, timeout=60)
    db.executescript(SCHEMA)
    head = rpc.run(lambda w3: w3.eth.block_number) - 5
    step = int(a.step_min * 60 / CHAIN_CFG[a.chain]["block_s"])
    n = int(a.days * 86400 / CHAIN_CFG[a.chain]["block_s"] / step)
    have = {r[0] for r in db.execute("SELECT DISTINCT block FROM dex_hist WHERE chain=?", (a.chain,))}
    blocks = [head - i * step for i in range(n + 1) if head - i * step not in have]
    if a.extend and have:
        blocks = [b for b in blocks if b < min(have) - step // 2]
    log.info("%s head %d step %d blocks, %d samples to fetch via %s", a.chain, head, step, len(blocks),
             [rpc.label(i) for i in range(len(rpc.urls))])
    hints: dict[str, int] = {}
    for i, b in enumerate(blocks):
        try:
            tsv = rpc.run(lambda w3: w3.eth.get_block(b)["timestamp"])
            states = fetch_cl_states(rpc, cl, b, hints) if cl else {}
            hints = {k: s.tick for k, s in states.items()}
            rows = []
            for p in pools:
                st = states.get(p.key)
                cres = (rpc.run(lambda w3: multicall(w3, curve_calls(p, SIZES, REF_BRLA_PER_USD), b))
                        if p.kind == "curve" else None)
                q = quote_pool(p, st, cres, SIZES, REF_BRLA_PER_USD)
                mid = mid_brla_per_usd(p, st) if st else None
                for (d, s), (ain, aout, ex) in q.items():
                    rows.append((datetime.fromtimestamp(tsv, timezone.utc).isoformat(timespec="seconds"), tsv,
                                 a.chain, b, p.key, d, s, ain, aout, int(ex), mid, st.fee if st else None))
        except Exception as e:  # noqa: BLE001
            log.warning("block %d failed: %s", b, str(e)[:200])
            continue
        with db:
            db.executemany("INSERT OR REPLACE INTO dex_hist VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        if i % 50 == 0:
            log.info("%d/%d block %d ts %d paid_calls %d", i, len(blocks), b, tsv, PAID["n"])
        time.sleep(a.sleep)
    with db:
        db.execute("INSERT INTO rpc_usage VALUES (?,?,?,?)",
                   (datetime.now(timezone.utc).isoformat(timespec="seconds"), "backfill.py", a.chain, PAID["n"]))
    log.info("done, paid calls %d", PAID["n"])


if __name__ == "__main__":
    main()
