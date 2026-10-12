"""OKX 1m history candles for the BRL books (reference for the backfill; no historical order books exist).

READ-ONLY public API, ~1 req/s. Stores data.db:okx_candles (inst, ts_ms, o, h, l, c, vol_base).

    python okx_candles.py --days 14.5
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://www.okx.com/api/v5/market/history-candles"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=14.5)
    ap.add_argument("--insts", default="USDC-BRL,USDT-BRL")
    a = ap.parse_args()
    db = sqlite3.connect(os.path.join(HERE, "data.db"), timeout=60)
    db.execute("CREATE TABLE IF NOT EXISTS okx_candles (inst TEXT, ts_ms INTEGER, o REAL, h REAL, l REAL, c REAL,"
               " vol REAL, PRIMARY KEY (inst, ts_ms))")
    stop = int((time.time() - a.days * 86400) * 1000)
    for inst in a.insts.split(","):
        after, n = None, 0
        while True:
            p = {"instId": inst, "bar": "1m", "limit": 100}
            if after:
                p["after"] = after
            d = requests.get(URL, params=p, timeout=15).json().get("data", [])
            if not d:
                break
            with db:
                db.executemany("INSERT OR REPLACE INTO okx_candles VALUES (?,?,?,?,?,?,?)",
                               [(inst, int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]))
                                for r in d])
            n += len(d)
            after = d[-1][0]
            if int(after) < stop:
                break
            time.sleep(1.0)
        print(inst, n, "candles")


if __name__ == "__main__":
    main()
