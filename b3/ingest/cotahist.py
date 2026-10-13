#!/usr/bin/env python3
"""
cotahist.py — série histórica oficial da B3 (COTAHIST) → tabela prices_raw.

Fonte: https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP (anual; o do ano corrente
é atualizado pela B3) e COTAHIST_D{DDMMAAAA}.ZIP (diário). Layout fixo de 245 colunas, registro tipo 01.
Preços NÃO ajustados (ajuste fica em build/adjust.py).

Filtro: mercado à vista (TPMERC 010), CODBDI 02/05/06/07/08 (lote padrão + RJ/RE/sancionadas), espécies ON/PN/PNA/PNB/.../UNT,
mais os ETFs BOVA11/SMAL11 (CODBDI 14) como benchmarks.

Uso:
  python b3/ingest/cotahist.py --years 2010-2026
  python b3/ingest/cotahist.py --daily 10102026
"""

import argparse
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402

BASE = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/"
RAWDIR = os.path.join(common.RAW, "cotahist")
KEEP_ESPECI = ("ON", "PN", "UNT")  # prefixos: ON, ON NM, PN N1, PNA, PNB, UNT N2 ...
BENCH_ETFS = {"BOVA11", "SMAL11"}  # benchmarks (CODBDI 14): Ibovespa e Small Cap
# 02 lote padrão; 05 sancionadas; 06 concordatárias; 07 recuperação extrajudicial; 08 recuperação judicial.
# A B3 MOVE a ação de 02 para 07/08 quando a empresa entra em RE/RJ (ex.: BRKM, ONCO em 2026) — sem isso a
# empresa some da base.
SPOT_BDI = {"02", "05", "06", "07", "08"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices_raw (
  date TEXT, ticker TEXT, codbdi TEXT, especi TEXT, nomres TEXT, isin TEXT,
  open REAL, high REAL, low REAL, avg REAL, close REAL, bid REAL, ask REAL,
  trades INTEGER, qty INTEGER, volume REAL,
  PRIMARY KEY (date, ticker)
);
CREATE INDEX IF NOT EXISTS ix_prices_raw_ticker ON prices_raw(ticker, date);
"""


def parse_line(ln):
    if ln[0:2] != "01" or ln[24:27] != "010":
        return None
    especi = ln[39:49].strip()
    bdi = ln[10:12]
    if bdi in SPOT_BDI:
        if not especi.startswith(KEEP_ESPECI):
            return None
    elif not (bdi == "14" and ln[12:24].strip() in BENCH_ETFS):
        return None
    fat = int(ln[210:217] or 1) or 1

    def px(a, b):
        return int(ln[a:b]) / 100.0 / fat

    d = ln[2:10]
    return (
        f"{d[:4]}-{d[4:6]}-{d[6:]}", ln[12:24].strip(), bdi, especi, ln[27:39].strip(), ln[230:242],
        px(56, 69), px(69, 82), px(82, 95), px(95, 108), px(108, 121), px(121, 134), px(134, 147),
        int(ln[147:152]), int(ln[152:170]), int(ln[170:188]) / 100.0,
    )


def fetch(name, force=False):
    os.makedirs(RAWDIR, exist_ok=True)
    path = os.path.join(RAWDIR, name)
    if os.path.exists(path) and not force:
        return path
    r = common.http_get(BASE + name, timeout=600, stream=True, pause=2)
    if r.status_code != 200:
        print(f"  {name}: HTTP {r.status_code}")
        return None
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    os.replace(tmp, path)
    return path


def load_zip(path, con):
    rows = []
    with zipfile.ZipFile(path) as z:
        for nm in z.namelist():
            with z.open(nm) as fh:
                for ln in io.TextIOWrapper(fh, encoding="latin-1"):
                    rec = parse_line(ln)
                    if rec:
                        rows.append(rec)
    con.executemany("INSERT OR REPLACE INTO prices_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", help="ex.: 2010-2026")
    ap.add_argument("--daily", nargs="*", help="datas DDMMAAAA")
    ap.add_argument("--refresh-current", action="store_true", help="rebaixa o anual do ano corrente")
    a = ap.parse_args()
    con = common.db()
    con.executescript(SCHEMA)
    names = []
    if a.years:
        y0, y1 = (int(x) for x in a.years.split("-"))
        names += [(f"COTAHIST_A{y}.ZIP", a.refresh_current and y == y1) for y in range(y0, y1 + 1)]
    for d in a.daily or []:
        names.append((f"COTAHIST_D{d}.ZIP", False))
    for nm, force in names:
        p = fetch(nm, force)
        if p:
            n = load_zip(p, con)
            print(f"{nm}: {n} linhas", flush=True)
    tot, d0, d1 = con.execute("SELECT count(*), min(date), max(date) FROM prices_raw").fetchone()
    print(f"prices_raw: {tot} linhas, {d0} → {d1}")


if __name__ == "__main__":
    main()
