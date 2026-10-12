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
itens 7.1–7.3. A Base fica como segunda, condicionada ao adaptador Slipstream.

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
`data.db:rpc_usage`.

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
- `data.db`: tabelas `dex_hist`, `okx_candles`, `swaps`, `probe`, `rpc_usage`.

**Nada ficou rodando.** Os quatro backfills terminaram (`done`). Nenhum arquivo central foi editado. O
`arb_tracker.db` foi aberto só em modo leitura (`xvenue_ticks`, para calibrar o spread).
