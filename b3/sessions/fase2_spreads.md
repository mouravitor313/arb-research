# Fase 2 — Spreads estruturais nas small caps · pasta `b3/`

> Abrir: `cd C:\Users\Pedro\Projetos\arb; claude` → **"Leia b3/PROJECT.md e b3/sessions/fase2_spreads.md e execute."**

## Por que
É o tipo de oportunidade mais próximo da experiência do time (arb/relativo) e já temos o insumo:
29 pares ON/PN/UNIT no universo (`reports/REPORT_fase1.md §4`).

## Perguntas
1. **Classes (ON/PN/UNIT):** para cada par, razão com proventos por classe (usar `close_tr` de cada
   ticker, não `close_split`), z-score em janelas 63/252, meia-vida (OU), teste de cointegração.
   UNIT vs cesta teórica (ex.: TAEE11 = 1 ON + 2 PN; SAPR11 = 1 ON + 4 PN; ALUP11, IGTI11, KLBN11):
   desconto/prêmio vs composição, quanto custa montar/desmontar a unit na B3.
2. **Custo real:** emolumentos B3 + corretagem, spread bid/ask (`bid`/`ask` em `prices_raw`), impacto
   no ADTV do lado ilíquido, aluguel (BTC) para o lado vendido — achar fonte gratuita de taxa de aluguel.
3. **Holdings:** BRAP4 (Vale), GOAU4 (Gerdau), SIMH3 (JSL/Vamos/Movida/Automob), outras do universo:
   desconto de holding = mkt cap vs Σ(participação × valor de mercado das investidas) — histórico e z-score.
4. **OPAs / fechamento de capital:** listar OPAs em curso (CVM/B3) com preço ofertado vs preço de tela.
5. Backtest simples das regras de reversão (entrada |z| > 2, saída z ~ 0) líquido de custos, por par.

## Saída
`b3/reports/REPORT_fase2.md` (estratégia, par, p50/p95 do spread, meia-vida, nº de episódios, retorno
líquido, capacidade em R$), tabela `spreads` no `b3.db` para o monitor da fase 5, e atualização do
`b3/PROJECT.md` (estado + próximos passos).
