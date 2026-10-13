#!/usr/bin/env python3
"""
universe.py — universo de small caps (datado) → tabelas universe (emissora) e universe_tickers.

Regra (acordada com o usuário em 2026-10-12):
  incluir emissora se  (algum ticker na carteira SMLL do snapshot mais recente)
                   OU  (market cap < R$ 10 bi  E  ADTV21 do ticker principal > R$ 1 mi)
Market cap = n_on × preço ON + n_pn × preço PN (classe sem negócio usa o preço da outra classe).
ADTV = volume financeiro médio por pregão (pregões sem negócio contam como 0).

Uso: python b3/build/universe.py [--mcap-max 10e9] [--adtv-min 1e6] [--report]
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS universe (
  asof TEXT, issuer TEXT, name TEXT, sector TEXT, subsector TEXT, segment TEXT, listing TEXT,
  main_ticker TEXT, tickers TEXT, mcap REAL, adtv21_main REAL, adtv63_main REAL, adtv21_issuer REAL,
  in_smll INTEGER, in_ibov INTEGER, by_rule INTEGER, included INTEGER, distress TEXT,
  PRIMARY KEY (asof, issuer)
);
CREATE TABLE IF NOT EXISTS universe_tickers (
  asof TEXT, ticker TEXT, issuer TEXT, cls TEXT, close REAL, adtv21 REAL, adtv63 REAL,
  last_trade TEXT, in_smll INTEGER, codbdi TEXT,
  PRIMARY KEY (asof, ticker)
);
"""


def ticker_class(t):
    suf = t[4:]
    if suf == "3":
        return "ON"
    if suf in ("4", "5", "6", "7", "8"):
        return "PN"
    if suf == "11":
        return "UNIT"
    return "OTHER"


def build(con, mcap_max, adtv_min):
    sessions = [r[0] for r in con.execute("SELECT DISTINCT date FROM prices_raw ORDER BY date DESC LIMIT 63")]
    asof, d21, d63 = sessions[0], sessions[20], sessions[62]
    px = pd.read_sql("SELECT ticker, date, close, volume, codbdi FROM prices_raw WHERE date >= ? "
                     "AND ticker NOT IN ('BOVA11','SMAL11')", con, params=(d63,))
    g = px.groupby("ticker")
    tk = pd.DataFrame({
        "close": g.apply(lambda d: d.sort_values("date")["close"].iloc[-1], include_groups=False),
        "last_trade": g["date"].max(),
        "codbdi": g.apply(lambda d: d.sort_values("date")["codbdi"].iloc[-1], include_groups=False),
        "adtv63": g["volume"].sum() / 63,
        "adtv21": px[px["date"] >= d21].groupby("ticker")["volume"].sum() / 21,
    }).fillna({"adtv21": 0}).reset_index()
    tk["issuer"] = tk["ticker"].str[:4]
    tk["cls"] = tk["ticker"].map(ticker_class)
    snap = con.execute("SELECT max(snap_date) FROM index_members").fetchone()[0]
    idx = pd.read_sql("SELECT idx, ticker FROM index_members WHERE snap_date=?", con, params=(snap,))
    smll, ibov = set(idx[idx.idx == "SMLL"].ticker), set(idx[idx.idx == "IBOV"].ticker)
    tk["in_smll"] = tk["ticker"].isin(smll).astype(int)
    comp = pd.read_sql("SELECT * FROM companies", con).set_index("issuer")

    rows = []
    for iss, d in tk.groupby("issuer"):
        d = d.sort_values("adtv21", ascending=False)
        main = d.iloc[0]
        c = comp.loc[iss] if iss in comp.index else None
        p_on = d[d.cls == "ON"]["close"].iloc[0] if (d.cls == "ON").any() else None
        p_pn = d[d.cls == "PN"]["close"].iloc[0] if (d.cls == "PN").any() else None
        mcap = None
        if c is not None and (p_on or p_pn):
            n_on, n_pn = c["n_on"] or 0, c["n_pn"] or 0
            mcap = n_on * (p_on or p_pn) + n_pn * (p_pn or p_on)
        in_s = int(d["in_smll"].any())
        rule = int(mcap is not None and mcap < mcap_max and main["adtv21"] > adtv_min)
        distress = {"07": "RE", "08": "RJ", "06": "concordata", "05": "sancionada"}.get(main["codbdi"])
        rows.append((asof, iss, None if c is None else c["trading_name"], None if c is None else c["sector"],
                     None if c is None else c["subsector"], None if c is None else c["segment"],
                     None if c is None else c["listing"], main["ticker"], " ".join(d["ticker"]), mcap,
                     main["adtv21"], main["adtv63"], d["adtv21"].sum(), in_s,
                     int(d["ticker"].isin(ibov).any()), rule, int(in_s or rule), distress))
    con.executescript(SCHEMA)
    con.execute("DELETE FROM universe WHERE asof=?", (asof,))
    con.executemany("INSERT INTO universe VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute("DELETE FROM universe_tickers WHERE asof=?", (asof,))
    tk.insert(0, "asof", asof)
    tk[["asof", "ticker", "issuer", "cls", "close", "adtv21", "adtv63", "last_trade", "in_smll", "codbdi"]].to_sql(
        "universe_tickers", con, if_exists="append", index=False)
    con.commit()
    u = pd.read_sql("SELECT * FROM universe WHERE asof=?", con, params=(asof,))
    inc = u[u.included == 1]
    print(f"asof {asof}: {len(u)} emissoras negociadas; incluídas {len(inc)} "
          f"(SMLL {int(inc.in_smll.sum())}, só pela regra {int(((inc.by_rule == 1) & (inc.in_smll == 0)).sum())}); "
          f"sem market cap: {int(u.mcap.isna().sum())}; em RJ/RE: {int(inc.distress.notna().sum())}")
    return asof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mcap-max", type=float, default=10e9)
    ap.add_argument("--adtv-min", type=float, default=1e6)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    con = common.db()
    asof = build(con, a.mcap_max, a.adtv_min)
    if a.report:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import report_fase1
        report_fase1.write(con, asof)


if __name__ == "__main__":
    main()
