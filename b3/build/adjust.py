#!/usr/bin/env python3
"""
adjust.py — série ajustada por eventos e proventos → prices_adj (+ data_quality, + validação vs Yahoo).

  close_split = close / Π(multiplicadores de ações com data-com ≥ data)       (B3 corp_actions 'stock')
      DESDOBRAMENTO/BONIFICACAO valor v (%) → m = 1 + v/100 ; GRUPAMENTO valor v → m = v
  close_tr    = close_split × Π(1 − D/Close_ant) dos proventos com data-ex > data   (Yahoo; razão invariante)

Retorno total = close_tr. Base = preço atual (último dia não é alterado).
Eventos em ações = B3 ∪ Yahoo (o histórico da B3 é incompleto e tem erros); eventos > 30% só entram se o
salto de preço do COTAHIST no pregão ex confirmar. data_quality: saltos |ret| > 45% e eventos rejeitados.

Uso: python b3/build/adjust.py [--tickers ...] [--validate]
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402

MULT = {"DESDOBRAMENTO": lambda v: 1 + v / 100, "BONIFICACAO": lambda v: 1 + v / 100,
        "GRUPAMENTO": lambda v: v}

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices_adj (
  date TEXT, ticker TEXT, close REAL, close_split REAL, close_tr REAL, volume REAL,
  PRIMARY KEY (date, ticker)
);
CREATE INDEX IF NOT EXISTS ix_prices_adj_ticker ON prices_adj(ticker, date);
CREATE TABLE IF NOT EXISTS data_quality (ticker TEXT, date TEXT, issue TEXT, detail TEXT);
"""


def adjust_one(t, raw, acts, yf):
    raw = raw.sort_values("date").reset_index(drop=True)
    dates = raw["date"].to_numpy()
    issues = []
    # --- eventos em ações: candidatos B3 ∪ Yahoo, confirmados pelo salto de preço do COTAHIST
    closes = raw["close"].to_numpy()
    cands = []  # (data-com, multiplicador, fonte)
    for _, e in acts.iterrows():
        f = MULT.get(e["label"])
        if f and e["last_date_prior"] and e["value"]:
            cands.append((e["last_date_prior"], f(e["value"]), "b3"))
    if yf is not None and not yf.empty:
        for _, r in yf[yf["split"] > 0].iterrows():
            prior = dates[dates < r["date"]]
            if len(prior):
                cands.append((prior[-1], float(r["split"]), "yahoo"))
    accepted = []
    for L, m, src in sorted(cands, key=lambda c: c[2]):  # 'b3' antes de 'yahoo'
        if m <= 0 or abs(np.log(m)) < 1e-6:
            continue
        if any(abs((pd.Timestamp(L) - pd.Timestamp(a[0])).days) <= 7 and abs(np.log(m / a[1])) < 0.05
               for a in accepted):
            continue  # mesmo evento já aceito pela outra fonte
        i = np.searchsorted(dates, L, side="right")  # primeiro pregão ex
        if i == 0 or i >= len(dates):
            continue  # evento fora da janela de dados
        jump = np.log(closes[i] / closes[i - 1])
        gap = (pd.Timestamp(dates[i]) - pd.Timestamp(dates[i - 1])).days
        if gap <= 30 and abs(np.log(m)) > np.log(1.3) and not abs(jump + np.log(m)) < min(0.25, abs(jump)):
            issues.append((t, L, "event_rejected_no_price_jump", f"{src} m={m:g} jump={jump:+.2f}"))
            continue
        accepted.append((L, m, src))
    split_cum = np.ones(len(raw))
    for L, m, _ in accepted:
        split_cum[dates <= L] *= m
    # --- eventos inferidos: degrau persistente entre a nossa série e a do Yahoo (já ajustada por eventos)
    if yf is not None and not yf.empty:
        j = pd.DataFrame({"date": dates, "cs": closes / split_cum}).merge(
            yf[["date", "close"]].rename(columns={"close": "yc"}), on="date")
        j = j[(j.yc > 0) & (j.cs > 0)].reset_index(drop=True)
        q = np.log(j.cs / j.yc).to_numpy().copy()
        dq = np.diff(q)
        for k in np.where(np.abs(dq) > 0.06)[0]:
            pre, post = np.median(q[max(0, k - 4):k + 1]), np.median(q[k + 1:k + 6])
            if len(q[k + 1:k + 6]) < 3 or abs((post - pre) - dq[k]) > 0.03:
                continue  # glitch pontual (não persiste)
            m = float(np.exp(-dq[k]))  # multiplicador que alinha o trecho anterior
            L = j.date.iloc[k]
            split_cum[dates <= L] *= m
            q[:k + 1] += dq[k]
            issues.append((t, L, "event_inferred_from_yahoo", f"m={m:.4f}"))
    close_split = closes / split_cum
    # --- proventos em dinheiro (Yahoo, data-ex)
    div_cum = np.ones(len(raw))
    if yf is not None and not yf.empty:
        y = yf.sort_values("date").reset_index(drop=True)
        y["prev"] = y["close"].shift(1)
        for _, r in y[y["dividend"] > 0].iterrows():
            if not r["prev"] or r["prev"] <= 0:
                continue
            f = 1 - r["dividend"] / r["prev"]
            if not 0.75 < f < 1:
                issues.append((t, r["date"], "dividend_outlier", f"D/P={1 - f:.3f}"))
                continue
            div_cum[dates < r["date"]] *= f
    close_tr = close_split * div_cum
    ret = pd.Series(close_split).pct_change().abs()
    for i in np.where(ret > 0.45)[0]:
        issues.append((t, dates[i], "jump_gt_45pct", f"{dates[i - 1]}→{dates[i]} ret={ret[i]:.2f}"))
    out = pd.DataFrame({"date": dates, "ticker": t, "close": raw["close"], "close_split": close_split,
                        "close_tr": close_tr, "volume": raw["volume"]})
    return out, issues


def validate(con, tickers):
    """Desvio |log| entre nossa série e a do Yahoo, ambas normalizadas no último dia comum."""
    res = []
    for t in tickers:
        q = ("SELECT a.date, a.close_split, a.close_tr, y.close yc, y.adj_close ya FROM prices_adj a "
             "JOIN yf_daily y ON y.ticker=a.ticker AND y.date=a.date WHERE a.ticker=? ORDER BY a.date")
        d = pd.read_sql(q, con, params=(t,))
        d = d[(d["yc"] > 0) & (d["ya"] > 0) & (d["close_split"] > 0)]
        if len(d) < 50:
            continue
        last = d.iloc[-1]
        es = np.log(d["close_split"] / last["close_split"]) - np.log(d["yc"] / last["yc"])
        et = np.log(d["close_tr"] / last["close_tr"]) - np.log(d["ya"] / last["ya"])
        res.append({"ticker": t, "n": len(d), "split_p50": es.abs().median(), "split_max": es.abs().max(),
                    "tr_p50": et.abs().median(), "tr_p95": et.abs().quantile(.95), "tr_first": et.iloc[0]})
    return pd.DataFrame(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()
    con = common.db()
    if a.tickers:
        tks = a.tickers
    else:
        tks = [r[0] for r in con.execute("SELECT DISTINCT ticker FROM yf_daily UNION "
                                         "SELECT DISTINCT ticker FROM prices_raw WHERE date >= date('now','-120 day')")]
    con.executescript(SCHEMA)
    acts_all = pd.read_sql("SELECT * FROM corp_actions WHERE kind='stock'", con)
    allq = []
    for t in sorted(set(tks)):
        raw = pd.read_sql("SELECT date, close, volume, isin FROM prices_raw WHERE ticker=? ORDER BY date",
                          con, params=(t,))
        if raw.empty:
            continue
        isin = raw["isin"].iloc[-1]
        acts = acts_all[acts_all["isin"] == isin]
        yf = pd.read_sql("SELECT date, close, dividend, split FROM yf_daily WHERE ticker=?", con, params=(t,))
        out, issues = adjust_one(t, raw, acts, yf)
        con.execute("DELETE FROM prices_adj WHERE ticker=?", (t,))
        out.to_sql("prices_adj", con, if_exists="append", index=False)
        con.execute("DELETE FROM data_quality WHERE ticker=?", (t,))
        con.executemany("INSERT INTO data_quality VALUES (?,?,?,?)", issues)
        allq += issues
    con.commit()
    print(f"prices_adj: {len(tks)} tickers; data_quality: {len(allq)} ocorrências")
    if a.validate:
        v = validate(con, sorted(set(tks)))
        pd.set_option("display.width", 200)
        print(v.describe(percentiles=[.5, .9, .95]).T.round(4))
        bad = v[(v["split_max"] > 0.05) | (v["tr_p95"] > 0.02)]
        print(f"\n{len(bad)}/{len(v)} tickers com divergência (split_max>5% ou tr_p95>2%):")
        print(bad.sort_values("tr_p95", ascending=False).head(30).round(4).to_string(index=False))
        v.to_csv(os.path.join(common.DATA, "adjust_validation.csv"), index=False)


if __name__ == "__main__":
    main()
