#!/usr/bin/env python3
"""
report_fase2.py — gera reports/REPORT_fase2.md (spreads estruturais) a partir das tabelas
spreads, data/spreads_robust.csv, holding_discount, opa_spreads e config/*.json.
Rodar depois de: build/spreads.py, build/spreads_robust.py, build/holdings.py, build/opas.py.
"""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402
from report_fase1 import fmt_brl, md, pct  # noqa: E402
from spreads import ar1  # noqa: E402


def f(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x:+.{d}f}"


def main():
    con = common.db()
    asof = con.execute("SELECT max(asof) FROM spreads").fetchone()[0]
    sp = pd.read_sql("SELECT * FROM spreads WHERE asof=?", con, params=(asof,))
    rb = pd.read_csv(os.path.join(common.DATA, "spreads_robust.csv"))
    L = [f"# Fase 2 — Spreads estruturais nas small caps (dados até {asof})", "",
         "Gerado por `python b3/build/report_fase2.py`. Método e parâmetros nos docstrings de "
         "`build/spreads.py`, `spreads_robust.py`, `holdings.py`, `opas.py`.", "",
         "## Resumo", "",
         "- **Units vs cesta:** composição confirmada (B3) e espelhada no preço com erro < 1%; desvios revertem em "
         "< 1 pregão e são menores que o custo → **não é oportunidade** (a conversão de units arbitra).",
         "- **Pares de classe (ON/PN):** a maioria não paga o custo. Robustos (grade ≥ 75% positiva e média > 0 "
         "dentro e fora da amostra): BMEB4/BMEB3 e CLSC4/CLSC3 (+2–3%/op., mas R$ 2–40 mil/dia de capacidade) e "
         "**SAPR4/SAPR3** (+0,6%/op., ~R$ 260 mil/dia) e **POMO4/POMO3** (+0,8%/op., ~R$ 1 mi/dia, mas só +0,2% "
         "fora da amostra). Uso realista: **regra de troca de classe para quem já carrega a ação**, não L/S.",
         "- **Holdings:** descontos não são estacionários (DF t > −2,86) e têm meia-vida de 1–3 meses → "
         "monitorar extremos, não operar reversão mecânica.",
         "- **OPAs:** fonte mais concreta de oportunidade (eventos com data e preço). Ver §4.",
         "- **Correção de dados:** a fase 1 descartava ações em recuperação judicial/extrajudicial (a B3 as move do "
         "CODBDI 02 para 07/08). Corrigido: +71 mil linhas, 24 tickers recentes (Americanas, Braskem, Oncoclínicas, "
         "Ambipar, Oi…). O universo agora marca `distress` (RJ/RE).", ""]

    # --- 1. pares de classe
    cl = sp[sp.kind == "classes"].merge(rb[["pair", "grid_pos", "t", "mean_in", "mean_oos", "n_oos", "win_oos",
                                            "cap_brl"]], on="pair", how="left")
    cl["robusto"] = (cl.grid_pos >= 0.75) & (cl.mean_in > 0) & (cl.mean_oos > 0)
    cl = cl.sort_values(["robusto", "mean_oos"], ascending=False)
    t = pd.DataFrame({
        "Par": cl.pair, "z 252d": cl.z252.map(f), "Meia-vida (pregões)": cl.half_life.map(lambda x: f"{x:.0f}"),
        "Custo ida+volta": cl.cost_rt.map(lambda x: pct(x).lstrip("+")), "Ops": cl.bt_trades,
        "Média líq./op. (troca)": cl.bt_mean_swap.map(pct), "Dentro (≤2022)": cl.mean_in.map(pct),
        "Fora (2023+)": cl.mean_oos.map(pct), "Acerto fora": cl.win_oos.map(lambda x: pct(x, 0).lstrip("+")),
        "Grade +": cl.grid_pos.map(lambda x: pct(x, 0).lstrip("+")), "Capacidade/dia": cl.cap_brl.map(fmt_brl),
        "Robusto": cl.robusto.map(lambda x: "✔" if x else "")})
    L += ["## 1. Pares entre classes (ON/PN/UNIT)", "",
          "Spread = log(retorno total A) − log(retorno total B). Backtest 2019→hoje: z com média/desvio de 126 "
          "pregões até t−1, entra |z| > 2 no fechamento de t+1, sai |z| < 0,5 (máx. 126 pregões). Custo = "
          "emolumentos B3 0,03%/lado + meio spread bid/ask mediano (63 pregões), 2 pernas × ida e volta. "
          "'Troca' = sem aluguel (quem já tem a ação troca de classe). Grade = % de 9 combinações "
          "(janela 63/126/252 × z 1,5/2/2,5) com média positiva. Capacidade = 10% do ADTV21 da perna menos líquida.",
          "", md(t), "",
          "**Leitura:** pares líquidos (TAEE, ALUP, GOAU, BRAP, USIM, SAPR11) não pagam o custo. Os robustos são "
          "ilíquidos; aluguel de ON ilíquida costuma passar de 20% a.a. (B3/InfoMoney), então o L/S não fecha — "
          "só a troca de classe.", ""]

    # --- 2. units
    un = sp[sp.kind == "unit_cesta"]
    t = pd.DataFrame({"Unit": un.leg_a, "Cesta inferida": un.basket, "Prêmio atual": un.spread.map(pct),
                      "z 252d": un.z252.map(f), "Meia-vida": un.half_life.map(lambda x: f"{x:.1f}"),
                      "Custo ida+volta": un.cost_rt.map(lambda x: pct(x).lstrip("+")),
                      "Média líq./op.": un.bt_mean_swap.map(pct)})
    L += ["## 2. Units vs cesta teórica", "",
          "Composições inferidas dos preços batem com a tabela oficial da B3 (TAEE11/ALUP11/IGTI11 = 1 ON + 2 PN; "
          "SAPR11 = 1 ON + 4 PN).", "", md(t), ""]

    # --- 3. holdings
    cfg = json.load(open(os.path.join(common.HERE, "config", "holdings.json"), encoding="utf-8"))
    hd = pd.read_sql("SELECT * FROM holding_discount", con)
    rows = []
    for h, d in hd.groupby("holding"):
        x = d.sort_values("date").set_index("date").disc
        w = x.tail(252)
        hl, dft = ar1(x.tail(756))
        rows.append({"Holding": h, "Desconto": pct(x.iloc[-1]), "Média 12m": pct(w.mean()),
                     "Faixa 12m": f"{pct(w.min())} a {pct(w.max())}", "z 12m": f((x.iloc[-1] - w.mean()) / w.std()),
                     "Média 5a": pct(x.tail(1260).mean()), "Meia-vida": f"{hl:.0f}", "DF t": f"{dft:.2f}",
                     "Market cap": fmt_brl(d.mcap.iloc[-1]), "NAV": fmt_brl(d.nav.iloc[-1]),
                     "Dados": cfg[h]["status"].split(";")[0][:40]})
    L += ["## 3. Desconto de holding", "",
          "Desconto = 1 − market cap / (Σ ações detidas × preço − dívida líquida da holding). Participações em "
          "`config/holdings.json` (com fonte e data). O histórico aplica as quantidades atuais sobre preços "
          "ajustados — confiável para z-score recente, aproximado para níveis antigos. DF t < −2,86 = estacionário a 5%.",
          "", md(pd.DataFrame(rows)), "",
          "- **Bradespar:** desconto de 32,6% é o menor dos últimos 12 meses (z −3,4); a média de 5 anos é 29%. "
          "O RI publicou 36,6% em 15/09 com VALE3 a R$ 74,60.",
          "- **Simpar:** passou de prêmio (média 12m −10%) para desconto de 9% (z +1,9). Participações só "
          "relatadas e alteradas por swaps em out/26 — conferir antes de agir.",
          "- **Cosan:** nível não interpretável (Moove, Radar e Raízen fora do NAV); usar só a variação.",
          "- **Metalúrgica Gerdau:** desconto de 4,5% vs média de 5 anos de 10,7%.", ""]

    # --- 4. OPAs
    op = pd.read_sql("SELECT * FROM opa_spreads", con)
    ocfg = json.load(open(os.path.join(common.HERE, "config", "opas.json"), encoding="utf-8"))
    t = pd.DataFrame({"OPA": op.OPA, "Alvo": op.alvo, "Tela": op["preço"].map(lambda x: f"R$ {x:.2f}"),
                      "Valor da oferta": op["valor oferta"].map(lambda x: "—" if pd.isna(x) else f"R$ {x:.2f}"),
                      "Spread exec.": op.spread.map(pct), "Leilão": op["leilão"].fillna("—"),
                      "Anualizado": op.anualizado.map(pct), "ADTV21": op.ADTV21.map(fmt_brl),
                      "Fonte primária": op.verificado.map(lambda x: "✔" if x else "relatado"),
                      "Observação": [ocfg[n]["notes"][:90] for n in op.OPA]})
    L += ["## 4. OPAs em curso", "",
          "Fontes: base IPE da CVM (fatos relevantes/editais de 2026) e página de OPAs da B3 (12/10/2026). "
          "Spread executável: compra do alvo no ask; na permuta, venda do ativo entregue no bid. Sem custos/aluguel.",
          "", md(t), "",
          "- **Desktop (DESK3):** tela R$ 19,44 vs R$ 19,13 pagos no fechamento + R$ 1,51 diferido → o mercado "
          "precifica ~20% da parcela diferida e o prazo da OPA unificada (ainda a registrar). Melhor relação "
          "risco/retorno da lista para estudo: +6% se a OPA sair no preço cheio.",
          "- **Helbor (HBOR3):** +0,5% executável até 28/10 (~10% a.a.) antes do aluguel de HBRE3; condicionado ao "
          "quórum de 2/3.",
          "- **Unifique (FIQE3) e Fras-le (FRAS3):** tela acima da oferta → aposta em revisão de preço; sem arb.",
          "- **Arandu (ARND3):** +6% no papel, mas ADTV de R$ 3 mil/dia.",
          "- **Braskem:** pagamento em debêntures da NSP (relatado R$ 52/ação) — não comparável com a tela; leilão "
          "16/10.",
          "- **Taurus (TASA3):** prêmio da ON sobre a PN no maior nível de 12 meses (z −2,9) sem fato relevante "
          "na CVM até 09/10 → monitorar (possível disputa de controle/assembleia).", ""]

    L += ["## 5. Custos (verificado — tarifas B3, 2026)", "",
          "- Ações à vista: **0,0300% por lado** (negociação 0,005% + CCP 0,0224% + TTA 0,0026%) até R$ 3 mi de "
          "ADTV mensal do investidor; 0,0225% acima. Corretagem/custódia à parte.",
          "- Aluguel (BTC): tarifa B3 = 20% da taxa (piso 2,5 / teto 70 bps a.a.). Taxa de mercado: líquidas "
          "0,04–0,5% a.a.; ilíquidas > 20% a.a.; extremos 2025: AMBP3 ~117%, AMER3 ~100%.",
          "- Taxa média de aluguel por ativo é pública no Boletim Diário da B3 (Clearing → Empréstimo de Ativos), "
          "mas o endpoint ainda não foi identificado → pendente para a fase 5.", "",
          "## 6. Próximos passos", "",
          "1. Monitor diário (fase 5) com alertas: |z| > 2 nos pares robustos, desconto de holding fora da faixa "
          "de 12 meses, spread de OPA > 3% com data definida.",
          "2. Obter taxa de aluguel por ativo (Boletim Diário B3) para fechar o L/S.",
          "3. Atualizar `config/holdings.json` e `config/opas.json` a cada release/edital (CVM IPE diário).",
          "4. Fase 3 — valor/fundamentos (CVM DFP/ITR).", ""]
    path = os.path.join(common.REPORTS, "REPORT_fase2.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"relatório: {path}")


if __name__ == "__main__":
    main()
