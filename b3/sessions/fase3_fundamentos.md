# Fase 3 — Valor / fundamentos das small caps · pasta `b3/`

> Abrir: `cd C:\Users\Pedro\Projetos\arb; claude` → **"Leia b3/PROJECT.md e b3/sessions/fase3_fundamentos.md e execute."**

## Por que
Fases 1–2 deram preço, universo e spreads estruturais. Falta saber o que está **barato/caro** em relação ao
próprio histórico e aos pares — base para o screening e para os alertas do monitor (fase 5).

## Perguntas
1. **Ingestão CVM** (`ingest/cvm.py`): `dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{DFP,ITR}/DADOS/*_{ano}.zip`
   (2012→hoje) → DRE, BP, DFC consolidados, por `code_cvm` (já em `companies`). Mapear contas-padrão: receita,
   EBIT, EBITDA (EBIT + D&A da DFC), lucro líquido controlador, PL, caixa, dívida bruta, dividendos pagos.
   Cuidado: versões reapresentadas (`VERSAO`), escala (`ESCALA_MOEDA`), bancos/seguradoras com plano de contas próprio.
2. **Múltiplos diários** (LTM, data de divulgação = disponibilidade, sem look-ahead): P/L, EV/EBITDA, P/VPA, DY,
   ROE, ROIC, dívida líquida/EBITDA, margem. Market cap diário = preço × ações (histórico de ações via FRE/FCA ou
   `companies` atual como aproximação — documentar).
3. **Percentis**: cada múltiplo vs o próprio histórico de 5 anos e vs o setor (`companies.sector`/`subsector`).
4. **Screening** inicial (valor + qualidade, ex.: EV/EBITDA no 20º percentil próprio com ROE > mediana e dívida
   controlada) e checagem simples se o fator funcionou nas small caps (retorno 3/6/12m dos quintis, 2015→hoje,
   universo pela regra de cap/liquidez — não há histórico da SMLL).
5. Validar 5 empresas contra o release de RI (lucro, PL, dívida) — erro < 1%.

## Saída
`b3/reports/REPORT_fase3.md`, tabelas `fundamentals` (trimestral) e `multiples` (diário), atualização do
`b3/PROJECT.md` e inclusão no `update.py`.
