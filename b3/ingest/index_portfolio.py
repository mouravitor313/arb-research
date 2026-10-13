#!/usr/bin/env python3
"""
index_portfolio.py — composição do dia dos índices B3 (SMLL, IBOV, IBRA, MLCX) → index_members.

Fonte: indexProxy/indexCall/GetPortfolioDay (público, base64). A B3 não expõe histórico de composição
de graça; por isso gravamos um snapshot datado a cada execução (rodar diariamente/quadrimestralmente).
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402

INDICES = ["SMLL", "IBOV", "IBRA", "MLCX"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS index_members (
  snap_date TEXT, ref_date TEXT, idx TEXT, ticker TEXT, asset TEXT, type TEXT,
  part REAL, theor_qty REAL,
  PRIMARY KEY (snap_date, idx, ticker)
);
"""


def fetch(idx):
    d = common.b3_json("indexProxy/indexCall/GetPortfolioDay",
                       {"language": "pt-br", "pageNumber": 1, "pageSize": 500, "index": idx, "segment": "1"})
    ref = d["header"]["date"]  # dd/mm/aa
    dd, mm, yy = ref.split("/")
    return f"20{yy}-{mm}-{dd}", d["results"]


def main():
    con = common.db()
    con.executescript(SCHEMA)
    snap = dt.date.today().isoformat()
    for idx in INDICES:
        ref, res = fetch(idx)
        rows = [(snap, ref, idx, r["cod"].strip(), r["asset"].strip(), " ".join(r["type"].split()),
                 common.br_num(r["part"]), common.br_num(r["theoricalQty"])) for r in res]
        con.executemany("INSERT OR REPLACE INTO index_members VALUES (?,?,?,?,?,?,?,?)", rows)
        print(f"{idx}: {len(rows)} ativos (carteira ref. {ref}), soma part = {sum(r[6] for r in rows):.2f}%")
    con.commit()


if __name__ == "__main__":
    main()
