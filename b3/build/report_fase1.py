"""
report_fase1.py — gera reports/REPORT_fase1.md (mapa do universo small caps). Chamado por
`python b3/build/universe.py --report`.
"""

import os

import numpy as np
import pandas as pd

import common


def fmt_brl(x):
    if x is None or pd.isna(x):
        return "—"
    for div, suf in ((1e9, " bi"), (1e6, " mi"), (1e3, " mil")):
        if abs(x) >= div:
            return f"R$ {x / div:,.1f}{suf}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {x:,.0f}"


def pct(x, d=1):
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.{d}f}%"


def md(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def series(con, t, col="close_tr"):
    s = pd.read_sql(f"SELECT date, {col} v FROM prices_adj WHERE ticker=? ORDER BY date", con, params=(t,))
    return s.set_index(pd.to_datetime(s["date"]))["v"]


def stats(s):
    s = s.dropna()
    end = s.index[-1]
    r = s.pct_change().dropna()

    def ret_since(days):
        base = s[s.index <= end - pd.Timedelta(days=days)]
        return s.iloc[-1] / base.iloc[-1] - 1 if len(base) else None

    def ann(days):
        x = ret_since(days)
        return None if x is None else (1 + x) ** (365 / days) - 1

    dd = s / s.cummax() - 1
    r1y = r[r.index > end - pd.Timedelta(days=365)]
    return {"1m": ret_since(30), "3m": ret_since(91), "12m": ret_since(365), "3a a.a.": ann(3 * 365),
            "5a a.a.": ann(5 * 365),
            "desde 2010 a.a.": (s.iloc[-1] / s.iloc[0]) ** (365 / max((end - s.index[0]).days, 1)) - 1,
            "vol 12m": r1y.std() * np.sqrt(252), "max DD": dd.min(), "DD atual": dd.iloc[-1]}


def write(con, asof):
    u = pd.read_sql("SELECT * FROM universe WHERE asof=? AND included=1", con, params=(asof,))
    allu = pd.read_sql("SELECT * FROM universe WHERE asof=?", con, params=(asof,))
    tks = pd.read_sql("SELECT * FROM universe_tickers WHERE asof=?", con, params=(asof,))
    L = [f"# Fase 1 — Mapa das small caps da B3 (dados até {asof})", "",
         "Gerado por `python b3/build/universe.py --report`. Fontes: COTAHIST (B3), carteiras teóricas "
         "B3 (indexProxy), cadastro/eventos B3 (listedCompaniesProxy), proventos Yahoo (.SA).", "",
         "## 1. Universo", "",
         "- Regra: carteira **SMLL** ∪ (market cap < R$ 10 bi **e** ADTV21 do ticker principal > R$ 1 mi).",
         f"- Emissoras com ação à vista negociada nos últimos 63 pregões: **{len(allu)}**.",
         f"- Incluídas: **{len(u)}** — na SMLL: {int(u.in_smll.sum())}; fora da SMLL (só pela regra): "
         f"{int(((u.by_rule == 1) & (u.in_smll == 0)).sum())}; na SMLL mas fora da regra (cap ≥ 10 bi ou "
         f"ADTV ≤ 1 mi): {int(((u.by_rule == 0) & (u.in_smll == 1)).sum())}.",
         f"- Excluídas por liquidez (cap < 10 bi, ADTV ≤ 1 mi, fora da SMLL): "
         f"{int(((allu.mcap < 10e9) & (allu.adtv21_main <= 1e6) & (allu.in_smll == 0)).sum())} "
         f"(micro caps ilíquidas — ficam fora do monitor).", ""]

    # --- distribuição
    bins = [0, 5e8, 1e9, 3e9, 5e9, 10e9, 1e13]
    labels = ["< 0,5 bi", "0,5–1 bi", "1–3 bi", "3–5 bi", "5–10 bi", "≥ 10 bi"]
    u["cap_b"] = pd.cut(u["mcap"], bins, labels=labels)
    d = u.groupby("cap_b", observed=False).agg(n=("issuer", "size"), adtv_med=("adtv21_main", "median"),
                                                smll=("in_smll", "sum")).reset_index()
    d["adtv_med"] = d["adtv_med"].map(fmt_brl)
    d.columns = ["Market cap", "Nº", "ADTV21 mediano", "na SMLL"]
    L += ["### Por market cap", "", md(d), ""]
    abins = [0, 1e6, 5e6, 20e6, 50e6, 1e12]
    alab = ["≤ 1 mi", "1–5 mi", "5–20 mi", "20–50 mi", "> 50 mi"]
    u["adtv_b"] = pd.cut(u["adtv21_main"], abins, labels=alab)
    d = u.groupby("adtv_b", observed=False).size().reset_index()
    d.columns = ["ADTV21 (ticker principal)", "Nº"]
    L += ["### Por liquidez", "", md(d), ""]
    s = u.groupby(u["sector"].fillna("—")).agg(n=("issuer", "size"), cap=("mcap", "sum"),
                                               adtv=("adtv21_main", "median")) \
        .sort_values("n", ascending=False).reset_index()
    s["cap"] = s["cap"].map(fmt_brl)
    s["adtv"] = s["adtv"].map(fmt_brl)
    s.columns = ["Setor", "Nº", "Market cap somado", "ADTV21 mediano"]
    L += ["### Por setor", "", md(s), ""]

    # --- benchmarks
    b = pd.DataFrame({k: stats(series(con, k)) for k in ("SMAL11", "BOVA11")}).T
    for c in b.columns:
        b[c] = b[c].map(pct)
    b.insert(0, "ETF", b.index)
    sm, bo = series(con, "SMAL11"), series(con, "BOVA11")
    j = pd.concat([sm.pct_change(), bo.pct_change()], axis=1).dropna()
    corr = j[j.index > j.index[-1] - pd.Timedelta(days=365)].corr().iloc[0, 1]
    rel = (sm / bo).dropna()
    L += ["## 2. SMLL vs IBOV (via ETFs SMAL11 / BOVA11)", "", md(b), "",
          f"- Correlação diária 12m SMAL11×BOVA11: **{corr:.2f}**.",
          f"- Razão SMAL11/BOVA11 hoje vs máxima desde 2010: **{pct(rel.iloc[-1] / rel.max() - 1)}**; "
          f"vs mínima: {pct(rel.iloc[-1] / rel.min() - 1)}.", ""]

    # --- tabela do universo
    rows = []
    for _, r in u.sort_values("mcap", ascending=False).iterrows():
        try:
            x = stats(series(con, r["main_ticker"]))
        except Exception:  # noqa: BLE001
            x = {}
        rows.append({"Emissora": r["name"] or r["issuer"], "Ticker": r["main_ticker"],
                     "Setor": (r["sector"] or "—")[:28], "Mkt cap": fmt_brl(r["mcap"]),
                     "ADTV21": fmt_brl(r["adtv21_main"]), "12m TR": pct(x.get("12m")),
                     "Vol 12m": pct(x.get("vol 12m"), 0).lstrip("+"), "DD atual": pct(x.get("DD atual")),
                     "SMLL": "✔" if r["in_smll"] else "",
                     "Situação": r["distress"] or ""})
    L += [f"## 3. Universo ({len(u)} emissoras, ordem de market cap)", "",
          "TR = retorno total (proventos reinvestidos). DD atual = distância do topo (desde 2010).", "",
          md(pd.DataFrame(rows)), ""]

    # --- pares de classes
    pr = []
    for _, r in u.iterrows():
        tt = tks[(tks.issuer == r["issuer"]) & (tks.cls.isin(["ON", "PN", "UNIT"])) & (tks.adtv21 > 0)]
        if len(tt) < 2:
            continue
        on = tt[tt.cls == "ON"].sort_values("adtv21").tail(1)
        pn = tt[tt.cls == "PN"].sort_values("adtv21").tail(1)
        un = tt[tt.cls == "UNIT"].sort_values("adtv21").tail(1)
        for a_, b_ in ((pn, on), (un, on), (un, pn)):
            if a_.empty or b_.empty:
                continue
            ta, tb = a_.ticker.iloc[0], b_.ticker.iloc[0]
            ratio = (series(con, ta, "close_split") / series(con, tb, "close_split")).dropna()
            ratio = ratio[ratio.index > ratio.index[-1] - pd.Timedelta(days=365)]
            if len(ratio) < 60:
                continue
            z = (ratio.iloc[-1] - ratio.mean()) / ratio.std()
            pr.append({"Par": f"{ta}/{tb}", "Razão": f"{ratio.iloc[-1]:.3f}", "Mín 12m": f"{ratio.min():.3f}",
                       "Máx 12m": f"{ratio.max():.3f}", "z 12m": f"{z:+.2f}",
                       "ADTV21 (a / b)": f"{fmt_brl(a_.adtv21.iloc[0])} / {fmt_brl(b_.adtv21.iloc[0])}",
                       "_z": abs(z)})
    if pr:
        p = pd.DataFrame(pr).sort_values("_z", ascending=False).drop(columns="_z")
        L += [f"## 4. Pares entre classes (ON/PN/UNIT) — insumo da fase 2 ({len(p)} pares)", "",
              "Razão de preços ajustada só por eventos em ações (proventos diferentes entre classes ficam "
              "no spread — tratar na fase 2). Ordenado por |z| em 12 meses.", "", md(p), ""]

    # --- qualidade
    q = pd.read_sql("SELECT issue, count(*) n FROM data_quality GROUP BY issue", con)
    L += ["## 5. Qualidade dos dados", "", md(q) if len(q) else "Sem ocorrências.", ""]
    val_path = os.path.join(common.DATA, "adjust_validation.csv")
    if os.path.exists(val_path):
        v = pd.read_csv(val_path)
        v = v[v.ticker.isin(u.main_ticker)]
        L += [f"- Validação vs Yahoo (tickers principais do universo, n={len(v)}): desvio |log| da série "
              f"retorno-total p50 = {v.tr_p50.median() * 100:.2f}%, p95 mediano = {v.tr_p95.median() * 100:.2f}%; "
              f"{int((v.tr_p95 > 0.02).sum())} tickers com p95 > 2% (lista em `data/adjust_validation.csv`; "
              f"concentrados no histórico antigo de ilíquidas).", ""]
    bad3 = []
    for t in u.main_ticker:
        d = pd.read_sql("SELECT a.close_tr c, y.adj_close ya FROM prices_adj a JOIN yf_daily y USING(date, ticker) "
                        "WHERE ticker=? AND date >= date(?, '-3 years') AND y.adj_close > 0 ORDER BY date",
                        con, params=(t, asof))
        if len(d) < 50:
            continue
        e = (np.log(d.c / d.c.iloc[-1]) - np.log(d.ya / d.ya.iloc[-1])).abs()
        if e.quantile(.95) > 0.01:
            bad3.append(f"{t} ({e.quantile(.95) * 100:.1f}%)")
    L += [f"- Janela de 3 anos (a que importa para o monitor): {len(u) - len(bad3)}/{len(u)} tickers principais "
          f"com desvio p95 ≤ 1% vs Yahoo. Fora: {', '.join(bad3) or 'nenhum'} — diferenças de proventos "
          f"especiais/redução de capital; conferir caso a caso antes de usar em backtest.", ""]
    L += ["## 6. Limitações conhecidas", "",
          "- Composição histórica da SMLL não é pública de graça: só snapshots a partir de 2026-10-12 "
          "(`index_members`). Backtests usarão a regra de cap/liquidez, não a carteira histórica.",
          "- Proventos em dinheiro vêm do Yahoo (a B3 expõe só ~12 meses). Ações sem histórico no Yahoo ficam "
          "ajustadas só por eventos em ações.",
          "- Market cap usa o nº de ações do cadastro B3 de hoje (inclui tesouraria).", ""]
    os.makedirs(common.REPORTS, exist_ok=True)
    path = os.path.join(common.REPORTS, "REPORT_fase1.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"relatório: {path}")
