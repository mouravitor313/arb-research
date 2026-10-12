"""t2_usdg — fast OKX-only poller (READ-ONLY public REST): USDG-BRL vs USDC-BRL / USDT-BRL every ~10 s.

The DEX side is ~static (USDG ≈ USDC on-chain, measured by usdg_probe.py every ~2.5 min), so short episodes
live in the OKX USDG-BRL book. Per tick and size S we store the OKX-leg rates (taker, VIP 9, fees included):
  sell_g_x[S]  = X received per USDG selling S USDG on USDG-BRL bids and buying X on X-BRL asks
  buy_g_x[S]   = USDG received per X selling S X on X-BRL bids and buying USDG on USDG-BRL asks
Net of a cross-venue trade = sell_g_x × (USDG per X on DEX) − 1  (dex_buy)  or  buy_g_x × (X per USDG on DEX) − 1.

    python okx_fast.py --interval 10 --hours 24        (pid: okx_fast.pid ; stop: create okx_fast.stop)
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import requests  # noqa: E402

from xvenue_collector import buy_with_quote, sell_base  # noqa: E402

FEE = 2e-4
SIZES = (1_000, 10_000, 100_000)
S = requests.Session()
SCHEMA = """CREATE TABLE IF NOT EXISTS fast (ts TEXT, x TEXT, size_usd INTEGER, sell_g_x REAL, buy_g_x REAL,
  g_bid REAL, g_ask REAL, x_bid REAL, x_ask REAL, PRIMARY KEY (ts, x, size_usd));"""


def book(inst):
    d = S.get("https://www.okx.com/api/v5/market/books", params={"instId": inst, "sz": 400}, timeout=8).json()["data"][0]
    return {k: [(float(p), float(q)) for p, q, *_ in d[k]] for k in ("asks", "bids")}


def rows(ts):
    bk = {i: book(i) for i in ("USDG-BRL", "USDC-BRL", "USDT-BRL")}
    g = bk["USDG-BRL"]
    out = []
    for x in ("USDC", "USDT"):
        xb = bk[f"{x}-BRL"]
        for s in SIZES:
            brl = sell_base(g["bids"], s)
            xs = buy_with_quote(xb["asks"], brl * (1 - FEE)) if brl else None
            brl2 = sell_base(xb["bids"], s)
            gs = buy_with_quote(g["asks"], brl2 * (1 - FEE)) if brl2 else None
            out.append((ts, x, s, None if xs is None else xs * (1 - FEE) / s, None if gs is None else gs * (1 - FEE) / s,
                        g["bids"][0][0], g["asks"][0][0], xb["bids"][0][0], xb["asks"][0][0]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=10)
    ap.add_argument("--hours", type=float, default=24)
    a = ap.parse_args()
    os.chdir(HERE)
    db = sqlite3.connect("data.db", timeout=30)
    db.execute(SCHEMA)
    open("okx_fast.pid", "w").write(str(os.getpid()))
    end = time.time() + a.hours * 3600
    try:
        while time.time() < end and not os.path.exists("okx_fast.stop"):
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            try:
                db.executemany("INSERT OR REPLACE INTO fast VALUES (?,?,?,?,?,?,?,?,?)", rows(ts))
                db.commit()
            except Exception as e:  # noqa: BLE001
                print(ts, "error", repr(e), flush=True)
            time.sleep(a.interval)
    finally:
        os.remove("okx_fast.pid")


if __name__ == "__main__":
    main()
