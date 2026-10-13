# Tópico 3: instâncias BRLA em Base e Gnosis (item C)

*Medido em 2026-10-11. Só leitura. Slug `t3_brla_l2`.*

## 1. Pergunta e hipótese
O `xend-arb` opera OKX `USDC-BRL` ↔ pool USDC/BRLA da Polygon e fecha o inventário pela Avenia. A pergunta
é se os pools de BRLA em Base e Gnosis (e em outras chains) desviam mais da OKX do que o da Polygon. Se sim,
cada pool pode virar mais uma instância igual, desde que a Avenia emita e resgate BRLA nessas chains.
O scanner antigo (último negócio) indicava Base +54 bps, Gnosis Oku −3, Gnosis Curve −20 e Polygon −7.
**Hipótese:** parte disso é preço velho. Este tópico mede com cotação executável, no tamanho.

## 2. Fontes e o que foi verificado
| Item | Status |
|---|---|
| Pools, tokens, fee e tickSpacing | **Verificado on-chain** (eth_call, bloco fixo) |
| Cotação no tamanho | **Verificado.** Usei um simulador local de swap CL (slot0, tickBitmap e ticks lidos on-chain). Ele bate **exatamente** com o QuoterV2 na Polygon (0,0000 bps a $1k e $10k) e com swaps reais da Base (6 swaps) e da Gnosis (5 de 6 exatos; 1 com 1 unidade de arredondamento). O Curve da Gnosis é **twocrypto-ng** (`get_dy(uint256,…)`, fee dinâmica) e foi cotado com `get_dy` on-chain. |
| Livros OKX | API pública ao vivo: livro de 400 níveis, taker de 2 bps (par BRL) |
| Histórico OKX | Candles de 1 min de `USDC-BRL`/`USDT-BRL` (14,5 d). Calibração contra 3.217 snapshots de livro do `xvenue_collector` (11/10, ~8,5 h): meio-spread `USDC-BRL` mediano de **0,6 bps**; erro candle−mid com p50 de −0,5 bps e \|erro\| p95 de **3,1 bps**. A profundidade por tamanho usa o livro atual (até $100k: ≤0,6 bps). |
| Avenia × chains | **Docs públicas** ([Available Combinations](https://integration-guide.avenia.io/docs/Operations/combinations/)): BRLA aceito como meio de pagamento em INTERNAL, **BASE, CELO, ETHEREUM, GNOSIS**, MOONBEAM e POLYGON, com `blockchainSendMethod` PERMIT ou TRANSFER. USDC também aparece com **BASE e GNOSIS**; USDT não aparece com Base nem Gnosis. A API é de quote + ticket, com quote válida por 15 s. **Não verificado:** taxa e prazo do resgate por chain. A página só menciona "Markup/Gas/In Fee", sem valores, e os exemplos de resgate usam INTERNAL. |
| OKX aceita USDC na Gnosis? | **Não** (confirmado pelo usuário em 11/10). Redes de USDC na conta: Unichain, Sui, Solana, Polygon USDC.e, Polygon, Monad, **Base**, Avalanche C-Chain, Arbitrum One, Aptos, X Layer e Ethereum. Celo também não está na lista. |
| Avenia resgata BRLA em Gnosis e Base? | **Sim, igual à Polygon** (sem taxa, ≤10 min; confirmado pelo usuário em 11/10). |
| Ponte USDC → USDC.e na Gnosis | **Cotado** (só quote, `near_quotes.py` e `bridge_quotes.py`). NEAR Intents 1Click: Base/Arbitrum/Ethereum USDC → Gnosis USDC.e por **~2,0 bps**, em ~30–50 s, até $50k, mesmo custo no sentido inverso. Pela LI.FI a mesma rota sai a 28 bps (25 bps são taxa da LI.FI). Relay: 61 bps, com teto de ~$32k. |

## 3. Venues e pools (bloco do probe, 11/10 ~23h UTC)
| Pool | Chain | Endereço | Saldos | Fee | Fluxo orgânico 14 d (bruto/dia, swaps/dia) |
|---|---|---|---|---|---|
| Aerodrome Slipstream BRLA/USDC (CL factory `0xade6…716a`, ts 10) | Base | `0x1c33aa5cc206ed3d9e29fb136796a8815e48af58` | 43,1k USDC / **10,3k BRLA** | 0,05% | $9,9k, 64 (85% via EntryPoint 4337: app de smart wallet) |
| Oku (Uniswap v3 oficial) USDC.e/BRLA | Gnosis | `0x576bf065cbc15cb2d61affb156118fcff01a8238` | 81,3k USDC.e / 116k BRLA | 0,05% | $14,3k, 45 (CoW solvers, Velora, contas 4337) |
| Curve twocrypto-ng BRLA/USDC.e | Gnosis | `0xfb8b95fb2296a0ad4b6b1419fdaa5aa5f13e4009` | 99,1k BRLA / 37,4k USDC.e | ~0,10% dinâmica | $2,5k, 36 |
| Uniswap v3 USD₮/BRLA | **Celo** (novo) | `0x14e577e42d45fd2200a9b0e31d87fe826467111a` | 22,9k USD₮ / 40,4k BRLA | 0,01% | $0,4k, 0,6 (**morto**) |
| Uniswap v3 USDC/BRLA (bot brla, referência) | Polygon | `0x0e7754127dedd4097be750825dbb4669bc32c956` | 112k USDC / 192k BRLA | 0,05% | $211k, 550 |

Tokens: BRLA na Base é `0xfcb3…1783`. Na Gnosis e na Celo é o **mesmo** endereço, `0xfecb…3760`. USDC.e na
Gnosis é `0x2a22…76f0`. Descartados: BRLA spot no Hyperliquid (`@298`: livro sem sentido, 0,001 USDC/BRLA e
spread de 60%, provavelmente token não oficial); HyperEVM BRLA/WHYPE com fee de 2%; Robinhood chain
BRLA/WETH sem volume; Gnosis BRZ/BRLA (BRZ congelado); restos de < $5k na Polygon. Detalhes em `discovery.json`.

**Profundidade.** Na Base, o lado BRLA do pool só tem ~R$10k. Comprar BRLA ali passa de **~$2k** e esgota o
range. Na Gnosis, Oku aguenta ~$5k com custo razoável e o Curve ~$1–2k. **$100k não cabe em nenhum pool**,
nem na Polygon.

## 4. Método
- **Probe one-shot** (`probe.py`): grade de $250 a $100k, nos dois sentidos, contra o livro da OKX
  (`USDC-BRL`; na Celo, `USDT-BRL`), com BRLA = R$1. Líquido de taker 2 bps, fee do pool (embutida na
  cotação) e gás. Gás por swap: Base $0,004 (com L1), Gnosis ~$0, Celo e Polygon $0,003.
  - **usd2brla:** compra BRLA no DEX com USD e recompra USD na OKX com BRL (asks).
  - **brla2usd:** vende BRLA no DEX e vende o USD na OKX (bids).
- **Backfill archive** (`backfill.py`): 14 dias, 1 amostra a cada 30 min, **RPC público archive**
  (mainnet.base.org, rpc.gnosischain.com, forno.celo.org, polygon.drpc.org), 673 amostras por chain. Em cada
  amostra, o simulador CL e o Curve `get_dy` rodaram no bloco exato. A referência OKX é o close do candle de
  1 min ± meio-spread medido, mais o slippage do livro atual (`analyze.py`).
- **"best"** = melhor dos dois sentidos na amostra (modelo com inventário dos dois lados).
- **Episódio** = sequência de amostras de 30 min com líquido > 0.
- **Fluxo** (`flow.py`): todos os eventos Swap/TokenExchange de 14 dias, para medir volume orgânico,
  direção e quem opera.
- **P&L/dia:** limite inferior = 1 captura por episódio (melhor tamanho da grade). Limite superior = 1 captura
  a cada amostra de 30 min. O **"teto por fluxo"** é volume orgânico bruto × edge médio positivo.

## 5. Resultados (14 d, 11/10 − 14 d → 11/10; líquido em bps sobre o notional)

**Desvio do mid DEX vs OKX** (+ = BRLA barato no DEX): Base p5/p50/p95 = −83 / **−6** / +97;
Gnosis Oku −57 / **+18** / +99; Gnosis Curve −51 / **+19** / +96; Celo −146 / −12 / +103; Polygon −16 / **+7** / +33.

| Pool | Tamanho | best p50 | best p95 | % > 0 | Episódios (mediana) | Sentido dominante |
|---|---|---|---|---|---|---|
| **Gnosis Oku** | $1k | **+20,7** | +87,6 | **87%** | 26 (4,2 h) | usd2brla (57% > 0, p50 +5) |
| | $2k | +15,5 | +82,3 | 75% | 30 (2,2 h) | |
| | $5k | −0,2 | +66,2 | 50% | 22 (3,5 h) | |
| | $10k | −27,3 | +39,5 | 18% | 19 (1,5 h) | |
| | $100k | não cabe | | 0% | | |
| **Base Aerodrome** | $1k | **+15,2** | +84,5 | 71% | 26 (4,2 h) | dois lados (usd2brla 34%, brla2usd 39%) |
| | $2k | +3,1 | +72,0 | 56% | 29 (2,5 h) | |
| | $5k | −45 | +32 | 13% | 12 | compra de BRLA esgota em 45% das amostras |
| | $10k / $100k | −106 / não cabe | | 1,5% / 0% | | |
| **Gnosis Curve** | $1k | +7,2 | +69,9 | 59% | 24 (2,8 h) | usd2brla |
| | $2k | −11,9 | +55,4 | 36% | 19 | |
| | $10k | −135 | −62 | 1% | | |
| Celo Uni 0,01% | $1k | −69 | +57 | 16% | 5 | lado BRLA esgota |
| *Polygon (ref.)* | $1k | +0,3 | +22,0 | 51% | 83 (1,5 h) | usd2brla |
| | $2k | −2,4 | +20,2 | 41% | 81 (1,0 h) | |
| | $10k | −25,3 | −2,8 | 4% | 15 | |

**Probe ao vivo (23h UTC de 11/10)** a $1k: Gnosis Oku **+32,6** (+11,6 a $5k), Gnosis Curve +7,1, Base −9,5,
Polygon −7,4. Celo sem liquidez útil.

**Lucro capturável estimado (USD/dia)**

| Pool | Inferior (1×/episódio) | Superior (a cada 30 min) | Teto por fluxo (bruto × edge médio) | Ticket típico |
|---|---|---|---|---|
| Gnosis Oku | 59 | 525 | ~48 ($14,3k/d × 34 bps) | $2k |
| Base | 27 | 233 | ~35 ($9,9k/d × 36 bps) | $2k |
| Gnosis Curve | 25 | 180 | ~8 | $1k |
| Celo | 4 | 63 | ~1 | $500 |
| *Polygon (ref.)* | 35 | 123 | | $2k |

**Calibração do método.** Na Polygon, o método dá $35–123/dia. O bot real fez **R$89,50 ≈ $17/dia**
(28/08), com concorrência. Ou seja, o método superestima em pelo menos 2×. Base e Gnosis parecem ter
menos concorrência: os gaps duram horas (mediana de episódio de 2–4 h, contra 1–1,5 h na Polygon) e não
encontrei um arbitrador dedicado entre os maiores endereços (CoW, Velora, contas 4337). Por isso o teto por
fluxo, de **~$50–100/dia somando Gnosis (Oku + Curve)** e **~$25–40/dia na Base**, é a estimativa central.
Isso dá algo como **$1,5–3k/mês na Gnosis e $0,8–1,2k/mês na Base**, antes do custo de rebalanceamento.
Volume capturável: ~**$5–15k/dia** na Gnosis e ~**$3–10k/dia** na Base, sempre em tickets de $1–5k.

### 5.1 Backtest com ticket fixo de $200 (formato do bot atual), 12/10
As tabelas acima usam uma grade de **$500 a $100k**, e os destaques estão em $1k. O bot CEX-DEX em produção
(instância brla, Polygon) opera **tickets fixos de $200** e ganha em média **R$1,20 por trade**. O
`backtest.py` refaz a análise nesse formato:
- Usa os mesmos dados (backfill de 30 min e coletor de 15 s), sem nenhuma chamada nova de RPC.
- A cada amostra, dispara tickets de $200 enquanto o ticket *marginal* líquido for maior que o mínimo. Cada
  ticket extra desce a curva do pool, ou seja, inclui o impacto do próprio bot.
- O ponto de $200 é extrapolado da taxa média a $500 e $1k. Conferido contra o mid × fee do pool CL, o erro
  é ≤0,05 bps (Celo: 0,5).
- Custos: taker de 2 bps na OKX e gás por tx.

Os resultados abaixo usam mínimo de 0 bps por trade; janelas de 60 d (Polygon: 45 d; Celo: 14 d).

| Pool | Amostras com trade | R$/trade (média / p50) | Tickets por amostra (p50 / p95) | R$/dia: inferior (trades) | R$/dia: teto por fluxo | R$/dia: superior |
|---|---|---|---|---|---|---|
| Gnosis Oku | 90% | **3,32** / 2,09 (32 bps) | 10 / 48 | **181** (28) | 238 (72) | 2.506 |
| Base | 83% | 3,24 / 2,51 (31 bps) | 9 / 10 | 70 (12) | 160 (49) | 941 |
| Gnosis Curve | 70% | 2,93 / 2,12 (28 bps) | 5 / 10 | 45 (8) | 36 (12) | 550 |
| Celo | 53% | 5,64 / 3,61 | 1 / 4 | 20 (2) | 11 (2) | 273 |
| *Polygon (bot real)* | 64% | **1,32** / 0,70 (13 bps) | 10 / 48 | **179** (87) | 702 | 702 |

**Calibração.** Na Polygon, o backtest dá **R$1,32 por trade** contra os **R$1,20 reais** do bot, e ~87
trades/dia no limite inferior contra os ~75 implícitos em R$89,50/dia (28/08). O lucro por trade bate. O
lucro por dia sai **~2× acima** do real, porque há concorrência e as amostras de 30 min não veem quem chega
primeiro. Aplicando o mesmo desconto de 2× ao limite inferior:

| Pool | Estimativa central em tickets de $200 |
|---|---|
| Gnosis (Oku + Curve) | **~R$110–140/dia** (~R$3,3k–4,2k/mês), a ~R$3 por trade (2,5× o lucro por trade da Polygon) |
| Base | **~R$35–80/dia** |
| Celo | Irrelevante |

**Ticket menor muda a leitura da Base.** No coletor ao vivo (9,9 h), a Base estava negativa a $1k (−9 bps),
mas **positiva a $200** (p50 +0,8, p95 +2,8 bps; 61% do tempo > 0). O pool é raso e o impacto domina acima
de $500. Gnosis Oku a $200: +33 bps o tempo todo. Polygon a $200: positiva em 19% do tempo, >5 bps em 4%.

**Limitações:**
- Amostragem de 30 min: não captura picos curtos nem a disputa por ordem de chegada.
- A OKX usa candle de 1 min ± meio-spread (|erro| p95 de 3,1 bps).
- O limite "superior" supõe que o gap volta inteiro a cada 30 min. Não é realista; serve só como teto.
- Mínimos de 5 e 10 bps por trade mudam pouco o R$/dia inferior (Gnosis 186–193, Base 76–79, Polygon
  188–194). Detalhe em `backtest_200.json`.

### 5.2 Tamanho ótimo do ticket ($20–$500) e swap ótimo, 12/10
Script `optimal_size.py` → `optimal_size.json`. Usa os mesmos dados e a mesma regra do §5.1: a cada amostra o bot
dispara tickets enquanto o ticket *marginal* líquido for maior que o mínimo, e o impacto do próprio bot se acumula.
O que muda em relação ao §5.1:
- **Curva abaixo de $500.** Nos pools CL uso um ramo exato de range único: taxa marginal em 0 = `dex_mid × (1−fee)`,
  ajustado ao ponto exato de $500. No Curve uso a extrapolação do `backtest.py`.
- **Validação.** `optimal_size_resim.py` re-simulou exatamente 100 blocos por chain em 20/50/100/150/200/300/500,
  só com RPC público archive (0 Alchemy; tabela `small_resim`). |Erro| p95 = **0,00 bps** em Oku e Base, **0,007**
  na Polygon e **0,39** no Curve a $20 (0,20 a $200). A extrapolação linear antiga também fica ≤0,04 bps nos CL.
  **Conclusão: abaixo de $500 a curva é praticamente linear e não precisa de mais re-simulação.**
- **Conferência.** A $200 e mínimo de 0 bps, o script reproduz o `backtest_200.json` (Polygon R$1,32 e 87 tr/dia;
  Oku R$3,32 e 181 R$/dia).

**Tabela ticket × pool (mínimo de 10 bps por trade; backfill de 30 min, 60 d; Polygon 45 d).**
Colunas: R$ por trade (bps), trades/dia e R$/dia em três regimes (inferior = 1× por episódio, teto por fluxo
orgânico, superior), mais o regime inferior calibrado contra o bot real.

| Pool | Ticket | R$/trade (bps) | Inferior: R$/dia (trades) | Teto fluxo: R$/dia (trades) | Superior: R$/dia (trades) | Calibrado: R$/dia (trades) |
|---|---|---|---|---|---|---|
| Gnosis Oku | $20 | 0,44 (42) | 188 (271) | 313 (717) | 2.393 (5.480) | 94 (233) |
| | $50 | 1,09 (42) | 189 (109) | 313 (287) | 2.402 (2.199) | 95 (94) |
| | $100 | 2,19 (42) | 189 (55) | 313 (143) | 2.404 (1.100) | 95 (47) |
| | $200 | 4,37 (42) | 193 (29) | 313 (72) | 2.404 (550) | 97 (25) |
| | **$500** | **10,92 (42)** | **196 (12)** | 313 (29) | 2.393 (219) | **98 (10)** |
| | ótimo/amostra | 73 por swap | 192 | 251 | 2.489 | 96 |
| Gnosis Curve | $20 | 0,40 (39) | 44 (59) | 50 (123) | 522 (1.294) | 22 (51) |
| | $200 | 4,01 (39) | 45 (6) | 49 (12) | 521 (130) | 22 (5) |
| | $500 | 9,96 (39) | 48 (3) | 49 (5) | 519 (52) | 24 (2) |
| Base | $20 | 0,41 (39) | 75 (113) | 201 (495) | 849 (2.091) | 37 (97) |
| | $100 | 2,04 (40) | 78 (25) | 202 (99) | 905 (444) | 39 (21) |
| | $200 | 4,07 (39) | 79 (13) | 201 (49) | 906 (223) | 39 (11) |
| | $500 | 10,21 (40) | 83 (6) | 202 (20) | 903 (88) | 42 (5) |
| *Polygon* | $20 | 0,34 (33) | 175 (496) | 470 (1.392) | = teto | 88 (426) |
| | $100 | 1,52 (30) | 183 (108) | 533 (351) | = teto | 92 (93) |
| | $200 | 3,00 (29) | 188 (56) | 543 (181) | = teto | 94 (48) |
| | $500 | 7,45 (29) | 196 (24) | 547 (74) | = teto | 98 (21) |

Com mínimo de 0 bps (o bot real), a Polygon a $200 dá R$1,32 e 87 trades/dia no regime inferior, contra R$1,20 e
~75 reais. Os fatores de calibração são: R$/trade × 0,91, trades/dia × 0,86 e **R$/dia × 0,50**, este último
aplicado na coluna "calibrado". Na Gnosis o fator de 0,5 é conservador, porque não há arbitrador dedicado (§5).
Tickets intermediários ($150, $300) e mínimos de 0 e 5 bps estão no JSON.

**Respostas às cinco perguntas:**
1. **Ticket que maximiza R$/dia:** na prática, nenhum. No modelo de rajada, o R$/dia é **quase plano no ticket**
   (Oku 188–196, Base 75–83, Polygon 175–196 com mínimo de 10 bps). Um ticket menor só divide o mesmo lucro em
   mais trades. O R$/trade cresce de forma linear com o ticket, e o bps por trade não muda. O mínimo de **10 bps**
   rende igual ou mais que o de 0 bps em todos os pools (a $500: Oku 196 contra 181; Polygon 196 contra 181), com
   metade dos trades. É também uma folga contra o erro da referência OKX (|erro| p95 de 3,1 bps).
2. **Tamanho ótimo por amostra (X\*), com mínimo de 10 bps:** Oku mediana de ~$2,0k (p25 $1,9k, p75 $4,9k, p95
   $9,8k); Curve ~$1k (p95 $2k); Base ~$1,9k (p25 $1k, p95 $4,7k; compras de BRLA acima de ~$2k costumam esgotar o
   range); Polygon ~$1,9k (p95 $9,8k). Com mínimo de 0 bps, a rajada de tickets fixos captura **98–100% do lucro
   ótimo na Gnosis** e 92–98% na Base. Na Polygon captura 86% a $20 e ≥97% a partir de $100. Com mínimo de 10 bps
   a captura cai para ~89–97% (77% na Polygon a $20), porque a regra para antes do ótimo, mas o R$/dia do regime
   inferior sobe.
3. **Um swap contra vários tickets no mesmo gap:** o swap CL exact-input é aditivo no caminho. Assim, N tickets de k
   rendem no DEX exatamente o mesmo que um swap de N·k, e a diferença é só (N−1) × gás. Na Gnosis isso vale ≤0,8% do
   lucro, mesmo a $20. Na Base vale 8% a $20 e 1,5% a $100. Na Polygon, 15% a $20, 3% a $100 e 1,4% a $200 (mínimo
   de 0 bps). O custo real de vários tickets não é o gás. É o **tempo**: são N transações em N blocos, e quem chega
   primeiro leva o gap. Os dados de 30 min não medem esse efeito, mas ele favorece tickets maiores ou um swap
   dimensionado pelo X\*.
4. **Quando o gás domina:** o gás é sempre minoria do lucro bruto. Com mínimo de 0 bps, a fatia do gás é:

   | Pool | $20 | $50 | $100 | $200 |
   |---|---|---|---|---|
   | Polygon | 13% | 6% | 3% | 1,5% |
   | Base | 7,5% | 3% | 1,6% | 0,8% |
   | Gnosis | 0,8% | 0,3% | 0,2% | 0,1% |

   O ponto em que o gás passa de 10% do lucro fica perto de **$25–30 na Polygon** e **$15 na Base**. Na Gnosis o gás
   não domina em nenhum tamanho da grade.
5. **Regimes e calibração:** ver a tabela. Na Gnosis Oku, o regime inferior calibrado dá **~R$95–98/dia** em
   qualquer ticket e o teto por fluxo ~R$313/dia. Com o Curve, chega a **~R$120/dia calibrado**. O §5.1 calculava
   R$110–140 somando Oku e Curve com 0 bps e desconto de 2×.

**Checagem no live de 15 s:** ver §5.3 (24 h completas). A checagem parcial de 10,5 h está em
`optimal_size_partial10h.json`.

### 5.3 Coletor ao vivo de 24 h (00:32 UTC 12/10 → 00:33 UTC 13/10), 13/10
5.763 ticks de 15 s, **0 erros**, só RPC público. Script `optimal_size.py` re-rodado (→ `optimal_size.json`,
stdout em `optimal_size_24h.stdout.log`). Líquido = best dos dois sentidos, taker 2 bps, gás, livro OKX ao vivo.

| Pool | $500 p5 / p50 / p95 | $1k p50 | $2k p50 | $5k p50 | % tempo > 10 bps ($500) | Sentido | Mudanças de preço do pool em 24 h |
|---|---|---|---|---|---|---|---|
| **Gnosis Oku** | +30 / **+34** / +55 | +31 | +26 | +10 | **100%** | só usd2brla | **8** |
| Gnosis Curve | +13 / +22 / +48 | +11 | −11 | −92 | 100% | só usd2brla | (sem mid) |
| Base Aerodrome | −13 / **−5** / −1 | −11 | −23 | −62 | **0%** | nenhum | 67 |
| *Polygon (ref.)* | −9 / −0,2 / +11 | −1,3 | −3,7 | −11 | 12% | dois lados | 300 |

Desvio de mid na Oku: p50 de **+44 bps** (BRLA barato na Gnosis), entre +40 e +65 bps na média de cada hora.

**Leitura nova, e mais importante que o bps: a Gnosis é um *estoque* de gap, não um *fluxo*.**
- A Oku ficou num **único episódio de 24 h**, e o preço do pool **mudou só 8 vezes no dia**: +14 e +8 bps às
  13h10 UTC (alguém vendeu BRLA), −23 bps às 15h27 (alguém comprou), e o resto ≤5 bps. Ninguém fecha o gap porque
  quase ninguém negocia ali.
- Assim, o "regime inferior" do `optimal_size.py` no live (**R$108**, 1 rajada por episódio) é uma **captura única**,
  não R$/dia. Com mínimo de 10 bps, o volume capturável é de **$2k no início e no máximo $5k no dia** (grade do live:
  500/1k/2k/5k). Depois que o bot leva o pool até ~10 bps, só sobra o que o fluxo orgânico **reabre**.
- **Reposição orgânica (14 d de swaps, `swaps`):** vendas de BRLA na Oku de **$4,1k/dia (p50)**, média de $6,1k.
  Compras de BRLA (concorrentes ou usuários) de $2,7k/dia (p50); um dia teve $38k de compra líquida. A venda
  líquida p50 é de só **$0,9k/dia**. No Curve, $0,6k/dia de vendas.
- **Nova estimativa central:** o bot captura ~$1–4k/dia de reposição a ~25–35 bps, ou seja, **~R$15–70/dia na Oku**
  mais ~R$5–10 no Curve. Isso dá **~R$40–80/dia, ~R$1,2–2,4k/mês**, mais uma captura inicial única de ~R$100. Fica
  **abaixo** dos ~R$120/dia calibrados no §5.2, porque a amostragem de 30 min tratava cada amostra positiva como
  gap novo, e no live se vê que é o mesmo gap parado. O número é comparável ao bot da Polygon (R$89,50/dia),
  com uma vantagem: **sem disputa de latência** (gap parado por horas, 8 mudanças/dia).
- **Base: morta nesta janela.** Negativa 100% do tempo em qualquer tamanho; a $500, o p95 é −1 bps. O +15 bps a
  $1k do backfill de 14 d era intermitente. **Base sai da fila.**
- **Polygon:** p50 ≈ 0 e >10 bps em 12% do tempo a $500, com 300 mudanças de preço/dia. É o mercado competitivo.
- Os dois maiores "senders" da Oku em 14 d (`0xb525…`, com $70k de compra líquida, e `0xc6d2…`) são **contratos
  roteadores**, então não dá para saber quem opera por trás. Um deles pode ser um arbitrador lento.

**Limitação:** a grade do live ($500/1k/2k/5k) é grossa demais para medir a reposição com precisão. Para isso,
o próprio piloto (§6) é a medida certa.

## 6. Conclusão
**Gnosis é oportunidade, mas depende do lado dólar. Base é uma oportunidade pequena. Celo não é. $100k não cabe em lugar nenhum.**

1. **Gnosis (Oku, mais Curve na mesma instância): é a melhor.** Executável p50 de +21 bps a $1k e +15 a $2k,
   com 87% e 75% das amostras positivas. Melhor que a Polygon em todos os tamanhos até $10k. O desvio é
   **persistente e de um lado só**: BRLA fica barato na Gnosis, e os CoW solvers vendem BRLA ali.
   A instância compraria BRLA com USDC.e e acumularia BRLA na Gnosis, que a Avenia resgataria (as docs
   listam GNOSIS para BRLA). O gargalo é **repor USDC.e na Gnosis**. A OKX não parece suportar USDC na
   Gnosis, então as opções são: (a) BRL → USDC na Gnosis direto pela Avenia (USDC aparece com GNOSIS nas
   docs; o markup é desconhecido); (b) sacar USDC da OKX em Ethereum ou Base e fazer bridge (custo de
   gás de L1 e prazo); (c) ciclo só Avenia: USDC.e → BRLA no pool → resgate em BRL → USDC na Gnosis pela
   Avenia. Com edge de ~20–35 bps, **qualquer custo de reposição abaixo de ~10 bps por ciclo deixa a
   instância positiva**.
2. **Base (Aerodrome): opção secundária.** p50 +15 a $1k, com edge nos **dois sentidos** (34% / 39% das
   amostras). Isso ajuda o inventário a se reequilibrar sozinho. Mas o pool tem só ~R$10k de BRLA, o que
   limita o ticket a ~$1–2k e o lucro a ~$25–40/dia. A OKX suporta USDC na Base (fonte de terceiros; falta
   confirmar), e a Avenia lista BASE para BRLA. O router é Slipstream (tickSpacing no lugar de fee), então
   o `xend-arb` precisaria de um adaptador.
3. **Celo:** pool parado (0,6 swaps/dia, um lado esgotado). Não abrir.
4. **Polygon:** confirma que o método funciona. Mostra p50 ≈ 0 porque o pool já é arbitrado pelo nosso
   bot e por outros.
5. Em todos os casos, o tamanho que cabe é **$1–5k por trade**. **$10k** só aparece em 2–18% das amostras
   e **$100k nunca**. Abrir instâncias só faz sentido se o custo operacional (RPC, monitoramento e
   rebalanceamento manual) for pequeno perto de ~$50–100/dia.

**Recomendação:** abrir **primeiro a Gnosis**, em teste com $2–5k de inventário, depois de responder aos
itens 7.1–7.3. ~~A Base fica como segunda~~ **Base descartada pelo live de 24 h (§5.3).** Atualização de 13/10: a
Gnosis é um gap *parado* (estoque, não fluxo), sem disputa de latência. O bot pode ser simples (polling de 15–60 s);
o que limita o lucro é a reposição orgânica (~$1–4k/dia), não a velocidade.

**Ticket da instância Gnosis (§5.2):** **$500 fixo com mínimo de 10 bps por trade**, ou, se o bot suportar, um swap
único dimensionado pelo ótimo da amostra (X\* de ~$2k na mediana). O motivo:
- O R$/dia é praticamente igual de $20 a $500, e o gás na Gnosis é desprezível.
- Com $500, o bot faz 2,5× menos transações que com $200, fica menos exposto a quem chega primeiro e ganha
  **R$10,9 por trade (42 bps)**. Na Polygon, com $200, são R$1,32 (13 bps) no modelo e R$1,20 no real.
- Estimativa calibrada (backfill 30 min): ~R$98/dia na Oku + ~R$24 no Curve ≈ R$120/dia (regime inferior × 0,5).
  **Revista no live de 24 h (§5.3): ~R$40–80/dia**, limitada pela reposição orgânica do gap. O teto por
  fluxo orgânico é ~R$313 + ~R$49/dia.

**Polygon e Base:** não vale baixar o ticket do bot da Polygon. Abaixo de ~$50 o gás come 6–15% do lucro e o R$/dia
não sobe. A Base com ticket pequeno ficou só +0,5 a +1,7 bps no live, o que reforça que ela é secundária.

## 7. Perguntas para o usuário e terceiros
**Respondidas em 11/10:** (1) a Avenia resgata BRLA em Gnosis e Base igual à Polygon; (3) a OKX não tem
USDC na Gnosis nem na Celo, mas tem na Base, Arbitrum, Ethereum e Polygon.

**Pendentes:**
1. **Avenia:** qual o markup de BRL → **USDC na GNOSIS** e na BASE? Com a NEAR Intents a 2 bps, essa rota
   deixa de ser necessária, mas a Avenia pode ser mais simples operacionalmente.
2. **OKX:** qual a taxa de saque de USDC na rede Base (e Arbitrum)? É o único custo da reposição ainda não
   medido. Fica no painel de saque.
3. **xend-arb:** já tem suporte a Uniswap v3 em outra chain? O Oku na Gnosis tem ABI idêntico ao da
   Polygon. Tem suporte a Slipstream (Base) e RPC confiável na Gnosis?
4. **Correção possível no ciclo B (RECAP §9):** na Gnosis, os EOAs `0x4337…` (`0x4337050608…`,
   `0x43370188…`, `0x43370384…`) são **bundlers ERC-4337**: as tx vão para o EntryPoint
   `0x5FF1…2789` com `handleOps`. Se os `0x4337…` da Polygon forem os mesmos, eles não são um searcher e
   sim contas inteligentes de algum app. Vale reconferir na sessão de consolidação.
5. **Backtest no formato do bot ($200 fixo) nas operações já descartadas** (pedido de 12/10). Este tópico já
   tem o backtest (§5.1). Ficam pendentes, para refazer com ticket de $200 e o critério R$/trade calibrado
   contra o bot (R$1,20):
   - t2 USDG: best −3,5 bps taker;
   - t5 SOL/XRP/meme: −4 a −15 bps p95;
   - ciclo B (Polygon atômico);
   - item 1 WBTC/BTC/ETH.

   Esses tópicos foram medidos com grade ≥$500–1k. Com $200 cai só o impacto no pool; as taxas fixas em bps
   não mudam. Por isso só operações negativas *por causa de impacto* podem virar. Cada tópico precisa do
   próprio `backtest.py` (o deste tópico serve de modelo; a lógica de curva por amostra é a mesma).

## 8. Requisições Alchemy usadas
**10** (só `eth_getLogs` do `flow.py` em Base e Polygon, porque os RPCs públicos negaram ranges grandes
de logs). Probe, backfill (4 × 673 amostras) e logs da Gnosis e da Celo usaram RPC público. Registro em
`data.db:rpc_usage`. O re-sim do §5.2 (`optimal_size_resim.py`, 100 blocos × 3 chains) e o coletor ao vivo
usaram **só RPC público**: **0** chamadas pagas a mais. O total continua em **10**.

## 9. Arquivos criados e o que ficou rodando
Tudo em `topics/t3_brla_l2/`:
- `l2common.py`: config local das chains e pools, simulador CL, cotador Curve e helpers de OKX.
- `gt_discover.py` → `gt_brla_pools.json`: descoberta via GeckoTerminal.
- `discovery.json`: pools validados e descartados.
- `probe.py` → `probe_20261011T225838.json`: foto executável.
- `backfill.py`: 14 d archive; logs `backfill_<chain>.log`.
- `okx_candles.py`: candles de 1 min.
- `flow.py`: swaps de 14 d.
- `hl_probe.py` → `hl_probe.json`: Hyperliquid, descartado.
- `analyze.py` → `analysis.json`: tabelas acima.
- `backtest.py` → `backtest_200.json`: backtest de ticket fixo (bot-style, padrão $200), offline.
- `collector.py` + `run_collector.ps1` (`-Stop`) → `data.db:live`: coletor ao vivo de 15 s, 24 h, RPC público.
- `optimal_size_resim.py` → `data.db:small_resim` (logs `resim_<chain>.log`): re-sim exato de $20–$500 em 100
  blocos por chain, para validar o modelo.
- `optimal_size.py` → `optimal_size.json`: estudo de ticket ($20–$500) × mínimo (0/5/10 bps) × pool, com swap
  ótimo, captura, gás, calibração e checagem no live (§5.2).
- `data.db`: tabelas `dex_hist`, `okx_candles`, `swaps`, `probe`, `rpc_usage`, `live`, `small_resim`.

**Status (13/10):** o coletor ao vivo (pid 33072) terminou sozinho às 00:33 UTC de 13/10, após 5.763 ticks e 0 erros.
Nada está rodando. O `optimal_size.py` foi re-rodado com as 24 h (§5.3).