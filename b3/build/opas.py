#!/usr/bin/env python3
"""
opas.py — spread de OPAs em curso (fase 2): valor da oferta vs preço de tela.

  cash:     valor = preço ofertado
  exchange: valor = ratio × preço do ativo entregue (hedge: comprar alvo, vender ratio × pay_ticker)
  spread bruto = valor / preço do alvo − 1 ; anualizado até o leilão quando houver data.
Usa o último fechamento e o bid/ask do COTAHIST. Saída: tabela `opa_spreads` + impressão.

Uso: python b3/build/opas.py
"""

import datetime as dt
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402

CFG = os.path.join(common.HERE, "config", "opas.json")


def last(con, t):
    r = con.execute("SELECT date, close, bid, ask FROM prices_raw WHERE ticker=? ORDER BY date DESC LIMIT 1",
                    (t,)).fetchone()
    adtv = con.execute("SELECT sum(volume)/21.0 FROM (SELECT volume FROM prices_raw WHERE ticker=? "
                       "ORDER BY date DESC LIMIT 21)", (t,)).fetchone()[0]
    return (r, adtv) if r else (None, None)


def main():
    con = common.db()
    cfg = json.load(open(CFG, encoding="utf-8"))
    rows = []
    for name, o in cfg.items():
        if name.startswith("_"):
            continue
        (d, close, bid, ask), adtv = last(con, o["target"])
        value = None
        if o["consideration"] == "cash":
            value = o["price"]
        elif o["consideration"] == "exchange":
            (_, pclose, pbid, _), _ = last(con, o["pay_ticker"])
            value = o["ratio"] * (pbid or pclose)  # vende o ativo entregue no bid
        spread = value / (ask or close) - 1 if value else None  # compra o alvo no ask
        days = ann = None
        if o.get("auction") and spread is not None:
            days = (dt.date.fromisoformat(o["auction"]) - dt.date.fromisoformat(d)).days
            ann = (1 + spread) ** (365 / max(days, 1)) - 1 if days > 0 else None
        rows.append({"OPA": name, "alvo": o["target"], "último": d, "preço": close, "valor oferta": value,
                     "spread": spread, "leilão": o.get("auction"), "dias": days, "anualizado": ann,
                     "ADTV21": adtv, "verificado": o.get("verified"), "status": o.get("status")})
    df = pd.DataFrame(rows)
    con.execute("DROP TABLE IF EXISTS opa_spreads")
    df.assign(asof=dt.date.today().isoformat()).to_sql("opa_spreads", con, index=False)
    con.commit()
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 60)
    print(df.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
