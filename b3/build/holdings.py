#!/usr/bin/env python3
"""
holdings.py — desconto de holding (fase 2).

  NAV  = Σ (ações detidas × preço da investida) − dívida líquida da holding (controladora)
  desconto = 1 − market cap da holding / NAV
Participações e dívida vêm de config/holdings.json (fonte e data anotadas lá). O histórico usa as
quantidades ATUAIS sobre preços close_split (base de ações de hoje) e a dívida constante — aproximação,
válida enquanto a participação não mudou; o z-score é mais confiável que o nível antigo.

Saída: tabela `holding_discount` (série diária) + resumo impresso.
Uso: python b3/build/holdings.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402
from spreads import ar1  # noqa: E402

CFG = os.path.join(common.HERE, "config", "holdings.json")


def px(con, t, since):
    s = pd.read_sql("SELECT date, close_split FROM prices_adj WHERE ticker=? AND date >= ? ORDER BY date",
                    con, params=(t, since))
    return s.set_index(pd.to_datetime(s["date"]))["close_split"].rename(t)


def main():
    con = common.db()
    cfg = json.load(open(CFG, encoding="utf-8"))
    since = "2019-01-01"
    out, summ = [], []
    for name, h in cfg.items():
        if name.startswith("_"):
            continue
        own = pd.concat([px(con, t, since) for t in h["own_tickers"]], axis=1).ffill()
        mcap = sum(own[t] * n for t, n in h["own_shares"].items())
        legs = pd.concat([px(con, s["ticker"], since) for s in h["stakes"]], axis=1).ffill()
        gav = sum(legs[s["ticker"]] * s["shares"] for s in h["stakes"])
        nav = gav - h.get("net_debt", 0)
        d = pd.concat([mcap.rename("mcap"), gav.rename("gav"), nav.rename("nav")], axis=1).dropna()
        d["disc"] = 1 - d.mcap / d.nav
        for dt_, r in d.iterrows():
            out.append((name, dt_.date().isoformat(), r.mcap, r.gav, r.nav, r.disc))
        x = d.disc
        w = x.tail(252)
        summ.append({"holding": name, "desconto": x.iloc[-1], "média 12m": w.mean(), "mín 12m": w.min(),
                     "máx 12m": w.max(), "z 12m": (x.iloc[-1] - w.mean()) / w.std(),
                     "média 5a": x.tail(1260).mean(), "meia-vida": ar1(x.tail(756))[0], "DF t": ar1(x.tail(756))[1],
                     "mcap": d.mcap.iloc[-1], "NAV": d.nav.iloc[-1], "status": h.get("status")})
    con.execute("CREATE TABLE IF NOT EXISTS holding_discount (holding TEXT, date TEXT, mcap REAL, gav REAL, "
                "nav REAL, disc REAL, PRIMARY KEY (holding, date))")
    con.execute("DELETE FROM holding_discount")
    con.executemany("INSERT INTO holding_discount VALUES (?,?,?,?,?,?)", out)
    con.commit()
    pd.set_option("display.width", 200)
    print(pd.DataFrame(summ).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
