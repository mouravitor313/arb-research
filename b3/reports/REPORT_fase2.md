# Fase 2 — Spreads estruturais nas small caps (dados até 2026-10-09)

Gerado por `python b3/build/report_fase2.py`. Método e parâmetros nos docstrings de `build/spreads.py`, `spreads_robust.py`, `holdings.py`, `opas.py`.

## Resumo

- **Units vs cesta:** composição confirmada (B3) e espelhada no preço com erro < 1%; desvios revertem em < 1 pregão e são menores que o custo → **não é oportunidade** (a conversão de units arbitra).
- **Pares de classe (ON/PN):** a maioria não paga o custo. Robustos (grade ≥ 75% positiva e média > 0 dentro e fora da amostra): BMEB4/BMEB3 e CLSC4/CLSC3 (+2–3%/op., mas R$ 2–40 mil/dia de capacidade) e **SAPR4/SAPR3** (+0,6%/op., ~R$ 260 mil/dia) e **POMO4/POMO3** (+0,8%/op., ~R$ 1 mi/dia, mas só +0,2% fora da amostra). Uso realista: **regra de troca de classe para quem já carrega a ação**, não L/S.
- **Holdings:** descontos não são estacionários (DF t > −2,86) e têm meia-vida de 1–3 meses → monitorar extremos, não operar reversão mecânica.
- **OPAs:** fonte mais concreta de oportunidade (eventos com data e preço). Ver §4.
- **Correção de dados:** a fase 1 descartava ações em recuperação judicial/extrajudicial (a B3 as move do CODBDI 02 para 07/08). Corrigido: +71 mil linhas, 24 tickers recentes (Americanas, Braskem, Oncoclínicas, Ambipar, Oi…). O universo agora marca `distress` (RJ/RE).

## 1. Pares entre classes (ON/PN/UNIT)

Spread = log(retorno total A) − log(retorno total B). Backtest 2019→hoje: z com média/desvio de 126 pregões até t−1, entra |z| > 2 no fechamento de t+1, sai |z| < 0,5 (máx. 126 pregões). Custo = emolumentos B3 0,03%/lado + meio spread bid/ask mediano (63 pregões), 2 pernas × ida e volta. 'Troca' = sem aluguel (quem já tem a ação troca de classe). Grade = % de 9 combinações (janela 63/126/252 × z 1,5/2/2,5) com média positiva. Capacidade = 10% do ADTV21 da perna menos líquida.

| Par | z 252d | Meia-vida (pregões) | Custo ida+volta | Ops | Média líq./op. (troca) | Dentro (≤2022) | Fora (2023+) | Acerto fora | Grade + | Capacidade/dia | Robusto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BMEB4/BMEB3 | +0.79 | 21 | 2.0% | 19 | +3.3% | +3.2% | +3.4% | 67% | 100% | R$ 37,3 mil | ✔ |
| CLSC4/CLSC3 | +0.79 | 5 | 2.4% | 12 | +2.6% | +3.3% | +2.3% | 89% | 100% | R$ 2,5 mil | ✔ |
| SAPR4/SAPR3 | -0.76 | 65 | 1.2% | 22 | +0.6% | +0.7% | +0.6% | 60% | 78% | R$ 260,9 mil | ✔ |
| POMO4/POMO3 | -0.08 | 139 | 0.6% | 31 | +0.8% | +1.2% | +0.2% | 83% | 100% | R$ 1,0 mi | ✔ |
| RAPT4/RAPT3 | -0.92 | 103 | 1.6% | 20 | -0.5% | -2.9% | +1.9% | 50% | 22% | R$ 27,0 mil |  |
| PINE4/PINE3 | +1.94 | 7 | 2.4% | 12 | +1.3% | — | +1.3% | 58% | 100% | R$ 8,8 mil |  |
| CYRE4/CYRE3 | +0.76 | 4 | 0.9% | 3 | +0.9% | — | +0.9% | 100% | 67% | R$ 1,0 mi |  |
| USIM5/USIM3 | -0.10 | 16 | 0.9% | 19 | +0.2% | -0.0% | +0.4% | 64% | 56% | R$ 622,6 mil |  |
| TASA4/TASA3 | -2.85 | 11 | 1.7% | 23 | +0.8% | +1.6% | +0.3% | 50% | 56% | R$ 85,4 mil |  |
| SAPR11/SAPR4 | +0.79 | 10 | 0.6% | 40 | +0.0% | +0.3% | -0.2% | 33% | 33% | R$ 1,7 mi |  |
| UNIP6/UNIP3 | -0.25 | 13 | 1.6% | 33 | -0.1% | +0.1% | -0.3% | 57% | 33% | R$ 30,0 mil |  |
| SAPR11/SAPR3 | -0.72 | 57 | 1.1% | 25 | -0.4% | -0.5% | -0.3% | 36% | 11% | R$ 260,9 mil |  |
| IGTI11/IGTI3 | -0.49 | 14 | 1.5% | 18 | +0.9% | +4.1% | -0.3% | 62% | 78% | R$ 25,7 mil |  |
| GOAU4/GOAU3 | +1.20 | 24 | 1.1% | 28 | -0.2% | -0.0% | -0.3% | 35% | 44% | R$ 41,0 mil |  |
| TAEE11/TAEE4 | +1.04 | 1 | 0.7% | 80 | -0.5% | -0.6% | -0.4% | 23% | 0% | R$ 312,0 mil |  |
| ALPA4/ALPA3 | +1.44 | 42 | 3.3% | 34 | -0.3% | -0.1% | -0.5% | 47% | 33% | R$ 13,8 mil |  |
| BRKM5/BRKM3 | -0.85 | 26 | 1.8% | 37 | +0.9% | +1.9% | -0.5% | 47% | 89% | R$ 26,1 mil |  |
| BRAP4/BRAP3 | -1.39 | 32 | 1.0% | 30 | -0.2% | +0.1% | -0.6% | 57% | 44% | R$ 135,7 mil |  |
| TAEE11/TAEE3 | +0.19 | 1 | 0.7% | 63 | -0.6% | -0.3% | -0.8% | 11% | 0% | R$ 139,6 mil |  |
| TAEE4/TAEE3 | -0.69 | 1 | 0.9% | 53 | -0.6% | -0.2% | -0.9% | 12% | 0% | R$ 139,6 mil |  |
| ALUP11/ALUP4 | +0.18 | 5 | 1.4% | 58 | -0.9% | -0.6% | -1.2% | 22% | 0% | R$ 19,1 mil |  |
| BRSR6/BRSR3 | +1.48 | 25 | 1.7% | 27 | +1.0% | +2.5% | -1.2% | 45% | 67% | R$ 10,0 mil |  |
| ALUP11/ALUP3 | +0.47 | 10 | 2.3% | 50 | -1.5% | -1.8% | -1.3% | 23% | 0% | R$ 11,2 mil |  |
| ALUP4/ALUP3 | +0.24 | 15 | 2.7% | 40 | -1.6% | -1.8% | -1.5% | 26% | 11% | R$ 11,2 mil |  |
| FESA4/FESA3 | +1.38 | 27 | 5.1% | 16 | +2.7% | +13.2% | -2.1% | 18% | 67% | R$ 437 |  |
| EUCA4/EUCA3 | +1.71 | 18 | 4.5% | 18 | -1.1% | +0.1% | -2.3% | 56% | 11% | R$ 955 |  |
| IGTI4/IGTI3 | -0.46 | 4 | 8.7% | 11 | -4.2% | — | -4.2% | 18% | 0% | R$ 881 |  |
| IGTI11/IGTI4 | +0.75 | 0 | 8.1% | 21 | -7.1% | — | -7.1% | 5% | 0% | R$ 881 |  |
| RCSL4/RCSL3 | -2.66 | 149 | 4.5% | 20 | -1.9% | +1.6% | -10.0% | 67% | 22% | R$ 50,1 mil |  |
| AZEV4/AZEV3 | -2.72 | inf | 1.2% | 20 | +6.2% | +22.5% | -10.1% | 70% | 100% | R$ 355,4 mil |  |

**Leitura:** pares líquidos (TAEE, ALUP, GOAU, BRAP, USIM, SAPR11) não pagam o custo. Os robustos são ilíquidos; aluguel de ON ilíquida costuma passar de 20% a.a. (B3/InfoMoney), então o L/S não fecha — só a troca de classe.

## 2. Units vs cesta teórica

Composições inferidas dos preços batem com a tabela oficial da B3 (TAEE11/ALUP11/IGTI11 = 1 ON + 2 PN; SAPR11 = 1 ON + 4 PN).

| Unit | Cesta inferida | Prêmio atual | z 252d | Meia-vida | Custo ida+volta | Média líq./op. |
|---|---|---|---|---|---|---|
| ALUP11 | 1 ALUP3 + 2 ALUP4 (erro med. 0.44%) | +0.8% | +0.96 | 0.2 | 1.9% | -1.8% |
| IGTI11 | 1 IGTI3 + 2 IGTI4 (erro med. 0.76%) | +1.0% | +0.70 | 0.4 | 4.8% | -5.4% |
| SAPR11 | 1 SAPR3 + 4 SAPR4 (erro med. 0.36%) | +0.3% | +0.30 | 0.6 | 0.9% | -0.6% |
| TAEE11 | 1 TAEE3 + 2 TAEE4 (erro med. 0.36%) | +0.3% | +0.91 | 0.6 | 0.7% | -0.6% |

## 3. Desconto de holding

Desconto = 1 − market cap / (Σ ações detidas × preço − dívida líquida da holding). Participações em `config/holdings.json` (com fonte e data). O histórico aplica as quantidades atuais sobre preços ajustados — confiável para z-score recente, aproximado para níveis antigos. DF t < −2,86 = estacionário a 5%.

| Holding | Desconto | Média 12m | Faixa 12m | z 12m | Média 5a | Meia-vida | DF t | Market cap | NAV | Dados |
|---|---|---|---|---|---|---|---|---|---|---|
| BRADESPAR | +32.6% | +37.2% | +31.0% a +39.7% | -3.39 | +29.0% | 62 | -2.23 | R$ 7,8 bi | R$ 11,6 bi | verificado |
| COSAN | -51.0% | -68.0% | -95.8% a -46.4% | +1.64 | -68.0% | 6 | -2.25 | R$ 21,4 bi | R$ 14,2 bi | misto: dívida e Compass verificados (rel |
| METALURGICA GERDAU | +4.5% | +6.0% | +1.6% a +11.2% | -0.81 | +10.7% | 32 | -2.83 | R$ 14,8 bi | R$ 15,4 bi | verificado (participação) |
| SIMPAR | +9.3% | -10.1% | -28.4% a +11.0% | +1.88 | -11.7% | 24 | -2.66 | R$ 10,1 bi | R$ 11,1 bi | relatado |

- **Bradespar:** desconto de 32,6% é o menor dos últimos 12 meses (z −3,4); a média de 5 anos é 29%. O RI publicou 36,6% em 15/09 com VALE3 a R$ 74,60.
- **Simpar:** passou de prêmio (média 12m −10%) para desconto de 9% (z +1,9). Participações só relatadas e alteradas por swaps em out/26 — conferir antes de agir.
- **Cosan:** nível não interpretável (Moove, Radar e Raízen fora do NAV); usar só a variação.
- **Metalúrgica Gerdau:** desconto de 4,5% vs média de 5 anos de 10,7%.

## 4. OPAs em curso

Fontes: base IPE da CVM (fatos relevantes/editais de 2026) e página de OPAs da B3 (12/10/2026). Spread executável: compra do alvo no ask; na permuta, venda do ativo entregue no bid. Sem custos/aluguel.

| OPA | Alvo | Tela | Valor da oferta | Spread exec. | Leilão | Anualizado | ADTV21 | Fonte primária | Observação |
|---|---|---|---|---|---|---|---|---|---|
| HELBOR | HBOR3 | R$ 2.71 | R$ 2.72 | +0.5% | 2026-10-28 | +10.3% | R$ 2,5 mi | ✔ | Controlador comprometido a vender 67,1 mi ações; quórum de 2/3 das ações em circulação par |
| UNIFIQUE | FIQE3 | R$ 6.20 | R$ 6.00 | -3.4% | — | — | R$ 9,1 mi | ✔ | Preço R$ 6,00 (+ Selic, relatado); laudo Apsis R$ 5,42. Tela acima do preço → mercado espe |
| DESKTOP | DESK3 | R$ 19.44 | R$ 20.63 | +6.1% | — | — | R$ 13,4 mi | ✔ | R$ 20,63 = R$ 19,1261 no fechamento + R$ 1,5051 diferido (garantia de indenizações, libera |
| FRAS-LE | FRAS3 | R$ 27.92 | R$ 27.35 | -2.3% | — | — | R$ 6,9 mi | relatado | 2,7 RAPT3 (ON) por FRAS3; prêmio anunciado ~45%. |
| BRASKEM | BRKM5 | R$ 4.37 | — | — | 2026-10-16 | — | R$ 23,7 mi | relatado | Relatado: R$ 52/ação pago em debêntures da NSP (não é caixa) → não comparável com a tela. |
| ARANDU | ARND3 | R$ 0.62 | R$ 0.67 | +6.3% | — | — | R$ 3,4 mil | relatado | R$ 0,67 + Selic (relatado); laudo R$ 0,66. |

- **Desktop (DESK3):** tela R$ 19,44 vs R$ 19,13 pagos no fechamento + R$ 1,51 diferido → o mercado precifica ~20% da parcela diferida e o prazo da OPA unificada (ainda a registrar). Melhor relação risco/retorno da lista para estudo: +6% se a OPA sair no preço cheio.
- **Helbor (HBOR3):** +0,5% executável até 28/10 (~10% a.a.) antes do aluguel de HBRE3; condicionado ao quórum de 2/3.
- **Unifique (FIQE3) e Fras-le (FRAS3):** tela acima da oferta → aposta em revisão de preço; sem arb.
- **Arandu (ARND3):** +6% no papel, mas ADTV de R$ 3 mil/dia.
- **Braskem:** pagamento em debêntures da NSP (relatado R$ 52/ação) — não comparável com a tela; leilão 16/10.
- **Taurus (TASA3):** prêmio da ON sobre a PN no maior nível de 12 meses (z −2,9) sem fato relevante na CVM até 09/10 → monitorar (possível disputa de controle/assembleia).

## 5. Custos (verificado — tarifas B3, 2026)

- Ações à vista: **0,0300% por lado** (negociação 0,005% + CCP 0,0224% + TTA 0,0026%) até R$ 3 mi de ADTV mensal do investidor; 0,0225% acima. Corretagem/custódia à parte.
- Aluguel (BTC): tarifa B3 = 20% da taxa (piso 2,5 / teto 70 bps a.a.). Taxa de mercado: líquidas 0,04–0,5% a.a.; ilíquidas > 20% a.a.; extremos 2025: AMBP3 ~117%, AMER3 ~100%.
- Taxa média de aluguel por ativo é pública no Boletim Diário da B3 (Clearing → Empréstimo de Ativos), mas o endpoint ainda não foi identificado → pendente para a fase 5.

## 6. Próximos passos

1. Monitor diário (fase 5) com alertas: |z| > 2 nos pares robustos, desconto de holding fora da faixa de 12 meses, spread de OPA > 3% com data definida.
2. Obter taxa de aluguel por ativo (Boletim Diário B3) para fechar o L/S.
3. Atualizar `config/holdings.json` e `config/opas.json` a cada release/edital (CVM IPE diário).
4. Fase 3 — valor/fundamentos (CVM DFP/ITR).
