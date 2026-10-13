#!/usr/bin/env python3
"""
corporate.py — cadastro das emissoras + eventos corporativos (B3 listedCompaniesProxy).

Para cada emissora (4 letras) com ação negociada nos últimos N dias em prices_raw:
  GetListedSupplementCompany → nº de ações ON/PN, segmento, codeCVM, proventos em dinheiro (só ~12m
                               recentes) e eventos em ações (desdobramento/grupamento/bonificação, histórico)
  GetDetail                  → setor/subsetor/segmento econômico, nome, CNPJ
Tabelas: companies, corp_actions. Cache JSON em data/raw/b3api/ (7 dias).

Uso: python b3/ingest/corporate.py [--days 120] [--issuers TTEN MGLU]
"""

import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402

P = "listedCompaniesProxy/CompanyCall/"

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
  issuer TEXT PRIMARY KEY, code_cvm TEXT, trading_name TEXT, company_name TEXT, cnpj TEXT,
  sector TEXT, subsector TEXT, segment TEXT, listing TEXT,
  n_on REAL, n_pn REAL, n_total REAL, quoted_since TEXT, updated TEXT
);
CREATE TABLE IF NOT EXISTS corp_actions (
  issuer TEXT, isin TEXT, kind TEXT, label TEXT, value REAL,
  approved_on TEXT, last_date_prior TEXT, payment_date TEXT, related_to TEXT,
  PRIMARY KEY (isin, kind, label, last_date_prior, value)
);
"""


def issuers_recent(con, days):
    d0 = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    rows = con.execute("SELECT DISTINCT substr(ticker,1,4) FROM prices_raw WHERE date >= ? "
                       "AND ticker NOT IN ('BOVA11','SMAL11')", (d0,)).fetchall()
    return sorted(r[0] for r in rows)


def ingest(con, issuer):
    sup = common.b3_json(P + "GetListedSupplementCompany", {"issuingCompany": issuer, "language": "pt-br"},
                         cache_name=f"supp_{issuer}")
    if not sup:
        return False
    s = sup[0] if isinstance(sup, list) else sup
    det = None
    if s.get("codeCVM"):
        det = common.b3_json(P + "GetDetail", {"codeCVM": s["codeCVM"], "language": "pt-br"},
                             cache_name=f"detail_{s['codeCVM']}")
    cls = ((det or {}).get("industryClassification") or "").split("/")
    cls = [c.strip() for c in cls] + [None] * 3
    con.execute("INSERT OR REPLACE INTO companies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        issuer, s.get("codeCVM"), (s.get("tradingName") or "").strip(), (det or {}).get("companyName"),
        (det or {}).get("cnpj"), cls[0], cls[1], cls[2], s.get("segment"),
        common.br_num(s.get("numberCommonShares")), common.br_num(s.get("numberPreferredShares")),
        common.br_num(s.get("totalNumberShares")), common.br_date(s.get("quotedPerSharSince")),
        dt.date.today().isoformat()))
    rows = []
    for c in s.get("cashDividends") or []:
        rows.append((issuer, c.get("isinCode"), "cash", c.get("label"), common.br_num(c.get("rate")),
                     common.br_date(c.get("approvedOn")), common.br_date(c.get("lastDatePrior")),
                     common.br_date(c.get("paymentDate")), c.get("relatedTo")))
    for c in s.get("stockDividends") or []:
        rows.append((issuer, c.get("isinCode"), "stock", c.get("label"), common.br_num(c.get("factor")),
                     common.br_date(c.get("approvedOn")), common.br_date(c.get("lastDatePrior")), None, None))
    con.executemany("INSERT OR REPLACE INTO corp_actions VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--issuers", nargs="*")
    a = ap.parse_args()
    con = common.db()
    con.executescript(SCHEMA)
    iss = a.issuers or issuers_recent(con, a.days)
    print(f"{len(iss)} emissoras", flush=True)
    ok = 0
    for i, e in enumerate(iss, 1):
        try:
            ok += ingest(con, e)
        except Exception as ex:  # noqa: BLE001
            print(f"  {e}: {ex}")
        if i % 25 == 0:
            con.commit()
            print(f"  {i}/{len(iss)}", flush=True)
    con.commit()
    n = con.execute("SELECT count(*) FROM corp_actions").fetchone()[0]
    print(f"companies ok: {ok}/{len(iss)}; corp_actions: {n}")


if __name__ == "__main__":
    main()
