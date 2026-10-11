"""Historical backfill of the Polygon cycle quotes (archive eth_call at past blocks).

READ-ONLY. Samples one block every --step blocks over the last --days days and writes to
cycle_quotes_hist / cycle_ticks_hist (same columns as the live tables). Needs an archive-capable
RPC (polygon.drpc.org works; publicnode does not). Gas price/POL are the *current* values
(historical gas is negligible here: ~$0.02/cycle). Resumable: skips blocks already stored.

    python cycle_backfill.py --days 14 --step 300
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone

from cycle_collector import mid_prices, tick_row
from cycle_common import build_w3
from cycle_quote import gas_usd, pol_usd, quote_cycles

DB = "arb_tracker.db"
ARCHIVE_RPC = os.environ.get("POLYGON_ARCHIVE_RPC_URL", "https://polygon.drpc.org")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cycle_quotes_hist (
    ts TEXT, block INTEGER, route TEXT, direction TEXT, size_usd INTEGER,
    amount_in REAL, amount_out REAL, gross_bps REAL, gas_units INTEGER, gas_usd REAL,
    net_bps REAL, venues TEXT, exhausted INTEGER, ok INTEGER,
    gas_price_gwei REAL, pol_usd REAL,
    PRIMARY KEY (block, route, direction, size_usd)
);
CREATE TABLE IF NOT EXISTS cycle_ticks_hist (
    ts TEXT, block INTEGER PRIMARY KEY,
    brla_per_usdc REAL, brz_per_usdt0 REAL, brla_per_brz_v3 REAL,
    brla_per_brz_curve REAL, brz_per_brla_curve REAL, usdt0_per_usdc_v3 REAL,
    mid_cycle_fwd_bps REAL, mid_cycle_fwd_curve_bps REAL, mid_cycle_rev_curve_bps REAL
);
"""
log = logging.getLogger("backfill")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=14)
    ap.add_argument("--step", type=int, default=300)
    ap.add_argument("--sleep", type=float, default=0.3)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler("cycle_backfill.log", encoding="utf-8"),
                                  logging.StreamHandler()])
    w3 = build_w3(ARCHIVE_RPC, timeout_s=30)
    db = sqlite3.connect(DB, timeout=30)
    db.executescript(SCHEMA)
    head = w3.eth.block_number - 10
    gp = w3.eth.gas_price
    pol = pol_usd(w3, head)
    n_blocks = int(a.days * 86400 / 2.0)
    have = {r[0] for r in db.execute("SELECT block FROM cycle_ticks_hist")}
    blocks = [b for b in range(head, head - n_blocks, -a.step) if b not in have]
    log.info("head %d, %d samples to fetch (step %d, %.1f d), gas %.0f gwei POL $%.4f",
             head, len(blocks), a.step, a.days, gp / 1e9, pol)
    for i, b in enumerate(blocks):
        for attempt in range(4):
            try:
                tsv = w3.eth.get_block(b)["timestamp"]
                ts = datetime.fromtimestamp(tsv, timezone.utc).isoformat(timespec="seconds")
                cycles = quote_cycles(w3, b)
                mids = mid_prices(w3, b)
                break
            except Exception as e:  # noqa: BLE001
                log.warning("block %d attempt %d: %s", b, attempt, str(e)[:200])
                time.sleep(5 * (attempt + 1))
        else:
            continue
        rows = []
        for c in cycles:
            gu = gas_usd(c.gas, gp, pol)
            rows.append((ts, b, c.route, c.direction, c.size_usd, c.amount_in / 1e6,
                         c.amount_out / 1e6, c.gross_bps if c.ok else None, c.gas, gu,
                         c.net_bps(gu) if c.ok else None, c.venues, int(c.exhausted), int(c.ok),
                         gp / 1e9, pol))
        with db:
            db.executemany("INSERT OR REPLACE INTO cycle_quotes_hist VALUES "
                           "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
            db.execute("INSERT OR REPLACE INTO cycle_ticks_hist VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       tick_row(ts, b, mids))
        if i % 25 == 0:
            best = max((r[10] for r in rows if r[10] is not None and not r[12]), default=None)
            log.info("%d/%d block %d %s best_net %s", i, len(blocks), b, ts,
                     f"{best:.1f}" if best is not None else "n/a")
        time.sleep(a.sleep)
    log.info("done")


if __name__ == "__main__":
    main()
