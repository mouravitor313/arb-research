#!/usr/bin/env python3
"""
yahoo.py — yfinance (.SA) como fonte secundária: proventos em dinheiro com histórico longo
(a B3 só expõe ~12 meses) e Adj Close para validar o nosso ajuste. → tabela yf_daily.

Close/Dividends do Yahoo vêm ajustados por desdobramento, mas a razão D/Close_anterior é invariante
a isso — é ela que build/adjust.py usa como fator de provento.

Uso: python b3/ingest/yahoo.py [--tickers TTEN3 MGLU3] [--days 120] [--start 2010-01-01]
"""

import argparse
import datetime as dt
import os
import sys
import time

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS yf_daily (
  date TEXT, ticker TEXT, close REAL, adj_close REAL, dividend REAL, split REAL, volume REAL,
  PRIMARY KEY (date, ticker)
);
"""


def recent_tickers(con, days):
    d0 = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    return [r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM prices_raw WHERE date >= ? ORDER BY ticker", (d0,))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--batch", type=int, default=40)
    a = ap.parse_args()
    con = common.db()
    con.executescript(SCHEMA)
    tks = a.tickers or recent_tickers(con, a.days)
    print(f"{len(tks)} tickers", flush=True)
    missing = []
    for i in range(0, len(tks), a.batch):
        chunk = tks[i:i + a.batch]
        df = yf.download([t + ".SA" for t in chunk], start=a.start, auto_adjust=False, actions=True,
                         group_by="ticker", progress=False, threads=True)
        rows = []
        for t in chunk:
            try:
                d = df[t + ".SA"].dropna(subset=["Close"])
            except KeyError:
                d = pd.DataFrame()
            if d.empty:
                missing.append(t)
                continue
            for idx, r in d.iterrows():
                rows.append((idx.strftime("%Y-%m-%d"), t, float(r["Close"]), float(r["Adj Close"]),
                             float(r.get("Dividends", 0) or 0), float(r.get("Stock Splits", 0) or 0),
                             float(r.get("Volume", 0) or 0)))
        con.executemany("INSERT OR REPLACE INTO yf_daily VALUES (?,?,?,?,?,?,?)", rows)
        con.commit()
        print(f"  {min(i + a.batch, len(tks))}/{len(tks)} ({len(rows)} linhas)", flush=True)
        time.sleep(3)
    print(f"sem dados no Yahoo ({len(missing)}): {' '.join(missing)}")
    # Carga incremental: um split novo reescreve todo o histórico ajustado do Yahoo → rebaixar completo.
    if a.start > "2010-01-01":
        resplit = [r[0] for r in con.execute(
            "SELECT DISTINCT ticker FROM yf_daily WHERE split > 0 AND date >= ?", (a.start,))]
        for t in resplit:
            df = yf.download(t + ".SA", start="2010-01-01", auto_adjust=False, actions=True,
                             progress=False, multi_level_index=False).dropna(subset=["Close"])
            con.execute("DELETE FROM yf_daily WHERE ticker=?", (t,))
            con.executemany("INSERT INTO yf_daily VALUES (?,?,?,?,?,?,?)", [
                (i.strftime("%Y-%m-%d"), t, float(r["Close"]), float(r["Adj Close"]),
                 float(r.get("Dividends", 0) or 0), float(r.get("Stock Splits", 0) or 0),
                 float(r.get("Volume", 0) or 0)) for i, r in df.iterrows()])
            con.commit()
            time.sleep(2)
        if resplit:
            print(f"histórico completo rebaixado (split recente): {' '.join(resplit)}")


if __name__ == "__main__":
    main()
