#!/usr/bin/env python3
"""
update.py — atualização incremental (rodar após o fechamento, ~20h, em dia útil).

  1. COTAHIST do ano corrente (rebaixa o anual, que a B3 atualiza)
  2. snapshot das carteiras SMLL/IBOV/IBRA/MLCX
  3. cadastro/eventos B3 (cache de 7 dias → só busca o que expirou)
  4. Yahoo dos últimos 60 dias (proventos/splits novos)
  5. ajuste + universo + REPORT_fase1.md
  6. fase 2: spreads de classe/units, robustez, holdings, OPAs + REPORT_fase2.md

Uso: python b3/update.py [--skip-corporate]
"""

import argparse
import datetime as dt
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(*args):
    print(">>", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], cwd=HERE, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-corporate", action="store_true")
    a = ap.parse_args()
    y = dt.date.today().year
    run("ingest/cotahist.py", "--years", f"{y}-{y}", "--refresh-current")
    run("ingest/index_portfolio.py")
    if not a.skip_corporate:
        run("ingest/corporate.py")
    run("ingest/yahoo.py", "--start", (dt.date.today() - dt.timedelta(days=60)).isoformat())
    run("build/adjust.py")
    run("build/universe.py", "--report")
    for script in ("spreads.py", "spreads_robust.py", "holdings.py", "opas.py", "report_fase2.py"):
        run(f"build/{script}")


if __name__ == "__main__":
    main()
