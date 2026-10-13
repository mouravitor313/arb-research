#!/usr/bin/env python3
"""
spreads.py — fase 2: spreads estruturais entre classes da mesma emissora (ON/PN/UNIT).

Para cada emissora do universo com 2+ classes negociadas:
  * pares de classes (ticker mais líquido de cada classe; PNA/PNB contam como PN)
  * UNIT vs cesta teórica a·ON + b·PN (composição inferida dos preços: inteiros 0..6 que minimizam o erro)
Spread  s = log(A_tr) − log(B_tr)  (retorno total → proventos diferentes entre classes já entram)
Métricas: z63/z252, meia-vida (AR(1)), t de Dickey-Fuller, % de pregões com negócio de cada perna.
Backtest (desde --since): z com média/desvio rolantes de --win pregões até t−1; sinal no fechamento de t,
execução no fechamento de t+1; entra |z| > --z-in, sai |z| < --z-out ou após --max-hold pregões.
Custo por perna por lado = emolumentos (--fee) + meio spread bid/ask mediano de 63 pregões.
Duas leituras: "troca" (quem já tem a ação troca de classe — sem aluguel) e "L/S" (com aluguel --rent a.a.
na perna vendida). Saída: tabela `spreads` (snapshot), `spread_trades`, e JSON para o relatório.

Uso: python b3/build/spreads.py [--since 2019-01-01] [--win 126] [--z-in 2] [--rent 0.03]
"""

import argparse
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS spreads (
  asof TEXT, pair TEXT, kind TEXT, leg_a TEXT, leg_b TEXT, basket TEXT,
  spread REAL, z63 REAL, z252 REAL, mean252 REAL, half_life REAL, df_t REAL,
  traded_a REAL, traded_b REAL, adtv_a REAL, adtv_b REAL, cost_rt REAL,
  bt_trades INTEGER, bt_win REAL, bt_mean_swap REAL, bt_mean_ls REAL, bt_hold REAL, bt_total_swap REAL,
  PRIMARY KEY (asof, pair)
);
CREATE TABLE IF NOT EXISTS spread_trades (
  pair TEXT, entry TEXT, exit TEXT, side INTEGER, z_entry REAL, days INTEGER,
  gross REAL, net_swap REAL, net_ls REAL
);
"""


def load(con, t, since):
    s = pd.read_sql("SELECT date, close_split, close_tr FROM prices_adj WHERE ticker=? AND date >= ? ORDER BY date",
                    con, params=(t, since))
    return s.set_index(pd.to_datetime(s["date"]))


def half_spread(con, t, asof):
    d = pd.read_sql("SELECT bid, ask FROM prices_raw WHERE ticker=? AND date <= ? AND bid > 0 AND ask > 0 "
                    "ORDER BY date DESC LIMIT 63", con, params=(t, asof))
    if d.empty:
        return 0.005
    rel = (d["ask"] - d["bid"]) / ((d["ask"] + d["bid"]) / 2)
    return float(np.clip(rel[rel >= 0].median() / 2, 0.0001, 0.05))


def ar1(s):
    """Meia-vida e t de Dickey-Fuller (constante, sem defasagens) de uma série de spread."""
    x = s.dropna().to_numpy()
    if len(x) < 60:
        return None, None
    y, xl = np.diff(x), x[:-1]
    X = np.column_stack([np.ones_like(xl), xl])
    beta, res, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    se = np.sqrt(resid.var(ddof=2) / ((xl - xl.mean()) ** 2).sum())
    b = beta[1]
    hl = -np.log(2) / np.log(1 + b) if -1 < b < 0 else np.inf
    return float(hl), float(b / se)


def backtest(s, cost_rt, rent, win, z_in, z_out, max_hold):
    """s: série de spread (log A − log B). side=+1 → compra A/vende B (spread barato)."""
    mu = s.rolling(win, min_periods=win // 2).mean().shift(1)
    sd = s.rolling(win, min_periods=win // 2).std().shift(1)
    z = (s - mu) / sd
    idx, zs, sv = s.index, z.to_numpy(), s.to_numpy()
    trades, i = [], 0
    while i < len(idx) - 2:
        if np.isfinite(zs[i]) and abs(zs[i]) > z_in:
            side = -1 if zs[i] > 0 else 1
            e = i + 1  # executa no pregão seguinte
            j = e + 1
            while j < len(idx) - 1 and j - e < max_hold and not (np.isfinite(zs[j]) and abs(zs[j]) < z_out):
                j += 1
            x = j + 1 if j + 1 < len(idx) else j  # sai no pregão seguinte ao sinal
            gross = side * (sv[x] - sv[e])
            days = (idx[x] - idx[e]).days
            trades.append({"entry": idx[e].date().isoformat(), "exit": idx[x].date().isoformat(), "side": side,
                           "z_entry": float(zs[i]), "days": int(x - e), "gross": float(gross),
                           "net_swap": float(gross - cost_rt),
                           "net_ls": float(gross - cost_rt - rent * days / 365)})
            i = x
        i += 1
    return trades


def infer_basket(unit, on, pn):
    """Composição a·ON + b·PN (inteiros) que melhor explica o preço da unit (close_split, 252 pregões)."""
    j = pd.concat([unit, on, pn], axis=1, keys=["u", "on", "pn"]).dropna().tail(252)
    if len(j) < 60:
        return None
    best = None
    for a, b in itertools.product(range(0, 7), range(0, 7)):
        if a + b == 0:
            continue
        err = np.log(j.u / (a * j.on + b * j.pn)).abs().median()
        if best is None or err < best[2]:
            best = (a, b, err)
    return best if best[2] < 0.05 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2019-01-01")
    ap.add_argument("--win", type=int, default=126)
    ap.add_argument("--z-in", type=float, default=2.0)
    ap.add_argument("--z-out", type=float, default=0.5)
    ap.add_argument("--max-hold", type=int, default=126)
    ap.add_argument("--fee", type=float, default=0.0003, help="emolumentos+liquidação por lado")
    ap.add_argument("--rent", type=float, default=0.03, help="aluguel a.a. na perna vendida (L/S)")
    a = ap.parse_args()
    con = common.db()
    con.executescript(SCHEMA)
    asof = con.execute("SELECT max(asof) FROM universe").fetchone()[0]
    u = pd.read_sql("SELECT issuer FROM universe WHERE asof=? AND included=1", con, params=(asof,))
    tk = pd.read_sql("SELECT ticker, issuer, cls, adtv21 FROM universe_tickers WHERE asof=? AND adtv21 > 0 "
                     "AND cls IN ('ON','PN','UNIT')", con, params=(asof,))
    tk = tk[tk.issuer.isin(u.issuer)]
    adtv = tk.set_index("ticker")["adtv21"].to_dict()
    pairs = []  # (kind, A, B, basket)
    for iss, d in tk.groupby("issuer"):
        top = {c: g.sort_values("adtv21").ticker.iloc[-1] for c, g in d.groupby("cls")}
        for ca, cb in (("PN", "ON"), ("UNIT", "ON"), ("UNIT", "PN")):
            if ca in top and cb in top:
                pairs.append(("classes", top[ca], top[cb], None))
        if {"UNIT", "ON", "PN"} <= set(top):
            pairs.append(("unit_cesta", top["UNIT"], top["ON"], top["PN"]))

    snap, all_trades, out = [], [], {}
    con.execute("DELETE FROM spread_trades")
    for kind, A, B, C in pairs:
        la, lb = load(con, A, a.since), load(con, B, a.since)
        hs = {t: half_spread(con, t, asof) for t in (A, B) + ((C,) if C else ())}
        if kind == "classes":
            j = pd.concat([la.close_tr, lb.close_tr], axis=1, keys=["a", "b"]).dropna()
            s = np.log(j.a) - np.log(j.b)
            name, basket = f"{A}/{B}", None
            cost_rt = 2 * 2 * (a.fee + (hs[A] + hs[B]) / 2)  # 2 pernas × entrada+saída
        else:
            lc = load(con, C, a.since)
            bk = infer_basket(la.close_split, lb.close_split, lc.close_split)
            if not bk:
                continue
            ka, kb, err = bk
            j = pd.concat([la.close_split, lb.close_split, lc.close_split], axis=1, keys=["u", "on", "pn"]).dropna()
            s = np.log(j.u) - np.log(ka * j.on + kb * j.pn)  # prêmio da unit sobre a cesta (base split)
            name, basket = f"{A}/cesta", f"{ka} {B} + {kb} {C} (erro med. {err * 100:.2f}%)"
            cost_rt = 2 * 2 * (a.fee + (hs[A] + (hs[B] + hs[C]) / 2) / 2)
        if len(s) < 150:
            continue
        last = s.iloc[-1]
        w252, w63 = s.tail(252), s.tail(63)
        z252 = (last - w252.mean()) / w252.std()
        z63 = (last - w63.mean()) / w63.std()
        hl, dft = ar1(s.tail(756))
        sessions = con.execute("SELECT count(DISTINCT date) FROM prices_raw WHERE date >= date(?, '-1 year')",
                               (asof,)).fetchone()[0]
        tr = {t: con.execute("SELECT count(*) FROM prices_raw WHERE ticker=? AND date >= date(?, '-1 year')",
                             (t, asof)).fetchone()[0] / sessions for t in (A, B)}
        trades = backtest(s, cost_rt, a.rent, a.win, a.z_in, a.z_out, a.max_hold)
        tdf = pd.DataFrame(trades)
        for t in trades:
            all_trades.append((name, t["entry"], t["exit"], t["side"], t["z_entry"], t["days"], t["gross"],
                               t["net_swap"], t["net_ls"]))
        row = dict(asof=asof, pair=name, kind=kind, leg_a=A, leg_b=B, basket=basket, spread=float(last),
                   z63=float(z63), z252=float(z252), mean252=float(w252.mean()), half_life=hl, df_t=dft,
                   traded_a=tr[A], traded_b=tr[B], adtv_a=adtv.get(A), adtv_b=adtv.get(B), cost_rt=cost_rt,
                   bt_trades=len(tdf), bt_win=float((tdf.net_swap > 0).mean()) if len(tdf) else None,
                   bt_mean_swap=float(tdf.net_swap.mean()) if len(tdf) else None,
                   bt_mean_ls=float(tdf.net_ls.mean()) if len(tdf) else None,
                   bt_hold=float(tdf.days.mean()) if len(tdf) else None,
                   bt_total_swap=float(np.exp(np.log1p(tdf.net_swap.clip(lower=-0.99)).sum()) - 1) if len(tdf) else None)
        snap.append(row)
        out[name] = {"series": {d.date().isoformat(): round(float(v), 5) for d, v in s.tail(756).items()}}
    con.execute("DELETE FROM spreads WHERE asof=?", (asof,))
    pd.DataFrame(snap).to_sql("spreads", con, if_exists="append", index=False)
    con.executemany("INSERT INTO spread_trades VALUES (?,?,?,?,?,?,?,?,?)", all_trades)
    con.commit()
    with open(os.path.join(common.DATA, "spread_series.json"), "w") as f:
        json.dump(out, f)
    df = pd.DataFrame(snap)
    pd.set_option("display.width", 250)
    cols = ["pair", "spread", "z63", "z252", "half_life", "df_t", "traded_b", "cost_rt", "bt_trades", "bt_win",
            "bt_mean_swap", "bt_mean_ls", "bt_hold"]
    print(df.sort_values("z252", key=abs, ascending=False)[cols].round(3).to_string(index=False))
    print(df[df.kind == "unit_cesta"][["pair", "basket"]].to_string(index=False))


if __name__ == "__main__":
    main()
