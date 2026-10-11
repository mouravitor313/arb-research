"""Historical cbBTC (Base, Uni v3 0.05%) vs OKX BTC basis — item 1b backfill.

READ-ONLY: archive eth_call (QuoterV2 at past blocks) + OKX public 1m candles (BTC-USDC, liquid).
For each sample block: DEX ask (USDC->cbBTC) and bid (cbBTC->USDC) for $10k vs the OKX BTC-USDC
1m close at that minute. gross = before OKX fees; approx BRL-route net = gross − 4 bps (BRL taker
2+2) − 1 bp (BTC-BRL half-spread vs BTC-USDC, measured live ~1 bp). Gas ignored (~$0.002 on Base).
Arbitrum WBTC: public RPCs have no archive state → live only (xvenue_collector.py).

    python xvenue_backfill.py --days 14 --step-min 10
Table: xvenue_hist (ts, chain, asset, size_usd, okx_px, dex_ask, dex_bid, buy_gross_bps, sell_gross_bps)
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import time
from datetime import datetime, timezone

import requests

from chains import CHAINS
from cycle_common import CS, build_w3, try_call

DB = "arb_tracker.db"
RPC = "https://mainnet.base.org"
SCHEMA = """CREATE TABLE IF NOT EXISTS xvenue_hist (
    ts TEXT, block INTEGER, chain TEXT, asset TEXT, size_usd INTEGER, okx_px REAL,
    dex_ask REAL, dex_bid REAL, buy_gross_bps REAL, sell_gross_bps REAL,
    PRIMARY KEY (chain, block, size_usd))"""
log = logging.getLogger("xbackfill")


def okx_candles(inst: str, start_ms: int) -> dict[int, float]:
    """minute_ms -> close, paginating history-candles backwards until start_ms."""
    out, after = {}, None
    while True:
        p = {"instId": inst, "bar": "1m", "limit": 100}
        if after:
            p["after"] = after
        d = requests.get("https://www.okx.com/api/v5/market/history-candles", params=p, timeout=10).json()["data"]
        if not d:
            break
        for c in d:
            out[int(c[0])] = float(c[4])
        after = d[-1][0]
        if int(after) < start_ms:
            break
        time.sleep(0.12)
    return out


def q(w3, quoter, tin, tout, amt, block):
    r = try_call(w3, quoter, "quoteExactInputSingle((address,address,uint256,uint24,uint160))",
                 ["(address,address,uint256,uint24,uint160)"], [(CS(tin), CS(tout), int(amt), 500, 0)],
                 ["uint256", "uint160", "uint32", "uint256"], block)
    return r[0] if r else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=14)
    ap.add_argument("--step-min", type=float, default=10)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler("xvenue_backfill.log", encoding="utf-8"),
                                  logging.StreamHandler()])
    cfg = CHAINS["base"]
    usdc, tok = cfg["tokens"]["USDC"][0], cfg["tokens"]["cbBTC"][0]
    w3 = build_w3(RPC, timeout_s=30)
    db = sqlite3.connect(DB, timeout=30)
    db.execute(SCHEMA)
    head = w3.eth.block_number - 5
    head_ts = w3.eth.get_block(head)["timestamp"]
    start_ms = int((head_ts - a.days * 86400) * 1000)
    log.info("fetching OKX BTC-USDC 1m candles...")
    candles = okx_candles("BTC-USDC", start_ms)
    log.info("%d candles", len(candles))
    step = int(a.step_min * 60 / 2)  # Base: 2 s blocks
    have = {r[0] for r in db.execute("SELECT block FROM xvenue_hist WHERE chain='base'")}
    blocks = [b for b in range(head, head - int(a.days * 86400 / 2), -step) if b not in have]
    for i, b in enumerate(blocks):
        try:
            tsv = head_ts - (head - b) * 2  # Base has exact 2 s blocks
            minute = (tsv // 60) * 60 * 1000
            px = candles.get(minute) or candles.get(minute - 60_000)
            if px is None:
                continue
            rows = []
            for s in (1_000, 10_000, 100_000):
                out_btc = q(w3, cfg["quoter_v2"], usdc, tok, s * 1e6, b)
                out_usdc = q(w3, cfg["quoter_v2"], tok, usdc, s / px * 1e8, b)
                if not out_btc or not out_usdc:
                    continue
                ask = s / (out_btc / 1e8)
                bid = (out_usdc / 1e6) / (s / px)
                rows.append((datetime.fromtimestamp(tsv, timezone.utc).isoformat(timespec="seconds"),
                             b, "base", "BTC", s, px, ask, bid,
                             (px / ask - 1) * 1e4,   # buy on DEX, sell at OKX px
                             (bid / px - 1) * 1e4))  # buy at OKX px, sell on DEX
            with db:
                db.executemany("INSERT OR REPLACE INTO xvenue_hist VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
            if i % 50 == 0 and rows:
                log.info("%d/%d %s buy %.1f sell %.1f ($1k)", i, len(blocks), rows[0][0], rows[0][8], rows[0][9])
        except Exception as e:  # noqa: BLE001
            log.warning("block %d: %s", b, str(e)[:200])
            time.sleep(3)
    log.info("done")


if __name__ == "__main__":
    main()
