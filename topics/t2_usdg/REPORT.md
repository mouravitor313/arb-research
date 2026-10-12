# Tópico 2 — USDG (Paxos Global Dollar) · relatório

> Sessão de 2026-10-11 (22:40–23:56 UTC). Somente leitura. Números líquidos com VIP 9 (pares BRL:
> taker 2 / maker −1,5 bps; não-BRL: taker 11 bps), gás incluído, modelo de inventário pré-posicionado.

## 1. Pergunta e hipótese
A OKX lista `USDG-BRL`, mais um dólar com saída barata em BRL. A hipótese era: se o USDG negociar fora
do par contra USDC/USDT em algum venue, comprar barato num lado e vender no outro, fechando pelos pares
BRL, pode dar uma instância nova do formato `xend-arb`.

**Resposta curta: não é oportunidade com taker.** O USDG negocia colado no USDC em todo lugar: on-chain
e no livro USDG-BRL, que um market maker mantém ~1,4 bps acima do USDC-BRL com spread de 0,4 bps.
A margem bruta entre venues é de ~0–1,5 bps, e as duas pernas BRL custam 4 bps.

## 2. Fontes e o que foi verificado
| Item | Status | Fonte |
|---|---|---|
| Redes: Ethereum, Solana, Ink, X Layer, Robinhood Chain, Mantle, Arbitrum (desde 06/10/2026). Não existe em Base nem em Polygon | **Verificado** | docs.paxos.com/guides/stablecoin/usdg/mainnet |
| Endereços: ETH/Ink `0xe343…491D` · X Layer `0x4ae4…2dc8` · Arbitrum `0x004B…9bbC` · Solana `2u1t…GWH` · Mantle `0x063C…C086` · Robinhood `0x5fc5…d168`. Ponte oficial LayerZero OFT | **Verificado** | idem |
| Supply ~US$3,04B: X Layer 1,39B · Robinhood 0,69B · Solana 0,63B · Ethereum 0,26B · Ink 0,06B | Verificado (DefiLlama) | stablecoins.llama.fi |
| Pares OKX: `USDG-USDT` (desde 06/2025), `USDG-EUR`, `USDG-SGD`, `USDG-BRL` (desde 22/07/2026). **Não existe `USDG-USDC`** | **Verificado** (API pública) | /api/v5/public/instruments |
| Redes de depósito/saque da OKX para USDG (relatado: ERC-20, Solana, X Layer), taxa e mínimo | **Não verificado** (o endpoint `/asset/currencies` exige auth) | okx.com/learn/earn-apy-usdg |
| Mint e resgate Paxos 1:1 com **taxa zero**. Só para institucional com KYB no Paxos Dashboard. Funciona 24/7 nas 7 redes. O Dashboard tem swap stablecoin→stablecoin (USDC aceito em ETH/Base/Polygon/Solana/Avalanche) | Verificado (página Paxos) | paxos.com/mint-and-redeem, docs.paxos.com/…/convert |
| Mínimo e prazo de mint/resgate; USDT→USDG | Não encontrado | — |
| GDN: o parceiro recebe até 100% do rendimento das reservas proporcional ao USDG mantido na plataforma. A OKX é parceira e repassa até ~3,5% APY no Exchange, **com o Brasil excluído** (no OKX Pay o Brasil entra) | Verificado (páginas GDN/OKX) | globaldollar.com/network, okx.com/learn |
| OKX "zero-fee conversion" USD↔USDT↔USDC↔USDG | Relatado (não testado; o livro paga ~8 bps no USDG-USDT, então provavelmente sai a preço de mercado) | okx.com/learn/usdg |
| Depeg do USDG | Nenhum encontrado | — |

## 3. Venues e pools
**OKX** (snapshot das 22:45 UTC, 400 níveis):

| Par | Spread | Profundidade (bid/ask) | Slippage a $100k (compra/venda) | Volume |
|---|---|---|---|---|
| USDG-BRL | 0,4 bps | $195k / $132k | 4,3 / 1,0 bps | mediana ~R$40k/dia (≈$8k), picos de R$960k; 76% dos negócios recentes são compras |
| USDG-USDT | 1 bp | $11M / $23M | 0,5 / 0,5 | ~$13M/dia |
| USDC-BRL | 1,4 bps | $570k / $395k | 1,3 / 1,7 | — |
| USDT-BRL | 0,2 bps | $1,6M / $1,3M | 1,9 / 1,2 | — |

**DEX** (GeckoTerminal só para achar as pools; as cotações vêm de quoter/agregador no tamanho, em `gt_search_usdg.json`):

| Rede | Pool | Endereço | TVL | Usada como |
|---|---|---|---|---|
| Ethereum | Curve USDG/USDC | `0xc061caa073f3d95f80f8e5428d32d2d76f5e1622` | $20M | `get_dy` de referência + rota Kyber |
| Ethereum | Uni v4 USDG/USDC, USDG/USDT 0,01%, Ekubo, Maverick | vários | $0,2–3M | via Kyber |
| Solana | Orca USDG/USDC | `9RqDTfwCx2SgxsvKpspQHc38HUo3B6hRd3oR9JR966Ps` | $18M | via Jupiter |
| X Layer | Uni v3 USDG/USD₮0 0,01% | `0x0cbe0dbe1400e57f371a38bd3b9bc80f7c3676da` | $6,9M | QuoterV2 `0xd1b797d9…4343` |
| Arbitrum | Fluid USDG/USDC, Uni v4 | `0xd0810e5c…`, `0x52b42d…` | $5M / $0,5M | via Kyber |
| Ink | Velodrome USDG/USD₮0, Uni v4 USDG/USDC | `0x31826a86…`, `0xf58608…` | $1,4M / $1,1M | não cotado (Kyber não cobre Ink; pools pequenas) |

**Preço do USDG on-chain, em USDC ou USDT por USDG, a $1k:**

| Venue | Compra USDG com USDC | Venda USDG por USDC | Compra USDG com USDT | Venda USDG por USDT |
|---|---|---|---|---|
| Ethereum (Kyber) | 1,00008 | 1,00006 | 1,00109 | 1,00102 |
| Arbitrum (Kyber) | 1,00030 | 1,00020 | 1,00124 | 1,00113 |
| X Layer (Uni v3) | — | — | 1,00093 | 1,00073 |
| Solana (Jupiter) | 1,00000 | 1,00000 | 1,00095 | 1,00095 |

O `get_dy` da Curve a $100k dá 0,99994 USDC por USDG e 0,99985 USDG por USDC. **O USDG fica no par
com o USDC** (±1 bp) e carrega o mesmo prêmio de ~9–10 bps sobre o USDT. Na OKX vale o mesmo: o
USDG-USDT está em 1,00085 e o USDC-USDT em 1,00096, ou seja USDG ≈ USDC −1 bp. **Resposta à pista
do brief: o USDG fica perto do USDC.**

## 4. Método
1. `okx_books.py`: snapshot de profundidade dos 5 livros OKX.
2. `usdg_probe.py`: probe one-shot, depois coletor a cada ~2,5 min. Cota $1k/$10k/$100k nos dois sentidos:
   - `dex_buy`: compra USDG no DEX com X, vende no USDG-BRL e recompra X no X-BRL.
   - `dex_sell`: o caminho inverso.
   - X ∈ {USDC, USDT}.
   - Venues: Kyber (Ethereum/Arbitrum), QuoterV2 (X Layer), Jupiter (Solana; consultado a cada 3 ticks).
   - Gás: estimativa do Kyber; X Layer $0,01; Solana $0,002.
   - Também mede o triângulo interno OKX `BRL→USDT→USDG→BRL`.
   - `net_bps_maker` = as duas pernas BRL como maker no topo do livro (limite superior).
3. `okx_fast.py`: livros OKX BRL a cada 10 s. `analyze.py` combina cada tick rápido com a cotação DEX
   mais recente, o que vale porque o lado DEX é praticamente estático.
4. Backfill grosso: candles OKX de 1 h dos últimos 82 dias (`okx_1h_backfill.json`) e volumes diários
   (`okx_usdg_brl_activity.json`).

## 5. Resultados
Coletor ao vivo de **1 h** (23:00–23:56 UTC, 324 ticks rápidos, 27 ticks completos). Líquido em bps,
taker; a coluna "maker" é o p50 do limite superior. Nenhum episódio positivo no taker em nenhuma combinação.

| Estratégia | Venue / X | Tamanho | p50 | p95 | % > 0 | maker p50 |
|---|---|---|---|---|---|---|
| dex_buy | X Layer / USDT | $1k · $10k · $100k | −3,5 · −3,6 · −6,0 | −3,5 · −3,6 · −5,9 | 0 | +4,1 · +4,2 · +4,2 |
| dex_buy | Solana / USDT | $1k · $10k · $100k | −3,6 · −3,7 · −6,4 | −3,4 · −3,6 · −6,2 | 0 | +4,0 · +4,0 · +3,9 |
| dex_buy | Solana / USDC | $1k · $10k · $100k | −3,7 · −4,1 · −5,2 | −3,5 · −3,9 · −5,0 | 0 | +5,3 · +5,3 · +5,2 |
| dex_buy | Ethereum / USDC | $1k · $10k · $100k | −5,1 · −4,9 · −6,0 | −4,7 · −4,3 · −5,9 | 0 | +3,8 · +4,4 · +4,3 |
| dex_buy | Arbitrum / USDC·USDT | $10k | −7,1 · −6,8 | −5,5 · −5,9 | 0 | +2,3 · +1,0 |
| dex_sell | Arbitrum / USDT | $1k · $10k · $100k | −4,1 · −3,7 · −8,8 | −3,9 · −3,7 · −8,1 | 0 | +3,5 · +4,0 · +3,1 |
| dex_sell | Ethereum, Solana, X Layer | $10k | −5,0 a −7,4 | −4,6 a −7,0 | 0 | +0,3 a +2,8 |
| Triângulo OKX BRL→USDT→USDG→BRL (e o inverso) | — | $10k | −14,2 / −17,7 | −14,2 / −17,4 | 0 | — |

**Livro USDG-BRL na última hora:**
- Spread de 0,40 bps (p50 = p95). Mid USDG-BRL ÷ USDC-BRL = +1,4 bps (p5–p95 de +1,3 a +1,6).
- O livro é cotado por algoritmo, preso ao USDC-BRL, e não houve nenhum desvio na janela.

**Backfill de candles de 1 h (82 dias, USDG-BRL ÷ USDC-BRL pelo close):**
- Só 39 horas tiveram mais de $5k negociados. Nessas horas o close ficou entre −23 e +38 bps (p5–p95), com extremos de +119 (08/09) e +193 bps (05/10).
- Esses closes são negócios reais de alguém cruzando um livro raso. Não medem um livro cotável, mas mostram que um taker ocasional anda o livro.
- O USDG-USDT contra o USDC-USDT direto ficou entre −2 e +4 bps (p5–p95): sem dislocação estrutural.

## 6. Conclusão: **não é oportunidade com taker; com maker é marginal e limitado pelo fluxo**
- **Taker:** a margem bruta entre DEX e OKX-via-BRL é de ~0–1,5 bps. As duas pernas BRL custam 4 bps, então o melhor caso (X Layer ou Solana, $1–10k) fica em **−3,5 bps** com variância quase zero. O triângulo interno da OKX está fechado (−14 a −18 bps) pela taxa não-BRL de 11 bps. USDG vs USDC on-chain sem OKX também está fechado: as pools estão no par, ±1 bp.
- **Maker:** o limite superior de +4 a +5 bps é otimista. O realista é ficar maker só na perna ilíquida, o USDG-BRL, e taker no USDC-BRL/USDT-BRL. Isso dá ≈ taker + 3,5 (diferença de taxa) + 0,4 (spread) ≈ **0 a +0,5 bps**.
- Além disso, o fluxo que bate no USDG-BRL é de ~$8k/dia em mediana. Mesmo capturando os desvios ocasionais de 10–30 bps do backfill, o valor esperado fica na ordem de **dólares por dia**.
- **Por que o preço está colado:**
  - O USDG é resgatável 1:1 sem taxa na Paxos e tem conversão "zero-fee" relatada na própria OKX.
  - O livro USDG-BRL é claramente cotado por um MM a partir do USDC-BRL.
  - O prêmio de ~9 bps sobre o USDT é o mesmo do USDC, ou seja, é a base USDC/USDT (`RECAP.md §10.2`), não algo próprio do USDG.
  - A recompensa GDN (~3,5% APY na OKX) explicaria demanda para manter USDG lá, mas o Brasil está excluído dessa promoção. E na prática ela não aparece como prêmio sobre o USDC.
- **O que mudaria a conclusão** (depende de X):
  - (a) A conversão zero-fee da OKX entre USDT e USDG sair 1:1 de verdade. Aí vender USDG/USDC a ~1,0009 USDT no livro e recompor pelo Convert valeria ~9 bps. Precisa testar com conta e confirmar limites.
  - (b) Acesso ao mint/resgate Paxos combinado com o swap USDC→USDG do Dashboard, se ele for gratuito. Isso viraria uma ponte USDC↔USDG a 0 bps, mas o preço de mercado já está no par, então só ajuda no rebalanceamento.
  - (c) O MM do USDG-BRL sair ou alargar o livro. O histórico mostra que antes o livro era mais raso.

## 7. Perguntas para o usuário e terceiros
1. **OKX (com a conta):** o Convert USDT→USDG e USDG→USDT sai 1:1 ou a preço de mercado? Qual o limite? Quais redes, mínimo e taxa de saque do USDG (X Layer deve ser a mais barata)? É o único ponto que poderia abrir algo: ~9 bps.
2. **OKX:** a conta do time (VIP 9, Brasil) é elegível à recompensa USDG no Exchange ou só no OKX Pay? Vale como carry de inventário, não como arbitragem.
3. **Paxos:** o time tem ou quer conta institucional? Mínimo e prazo de mint/resgate; se o swap USDC↔USDG no Dashboard é sem taxa (há relato de 5 bps); se USDT é aceito.
4. Faz sentido um bot maker de baixa prioridade no USDG-BRL, cotando largo (±10–20 bps) para pegar os takers ocasionais, dado o fluxo de ~$8k/dia?

## 8. Requisições Alchemy usadas
**0.** Tudo saiu de RPC público (publicnode Ethereum, rpc.xlayer.tech), da API pública da OKX, do Kyber aggregator, do Jupiter lite e do GeckoTerminal.

## 9. Arquivos criados e o que ficou rodando
Tudo em `topics/t2_usdg/`:
- `okx_books.py`: snapshot de livros (+ `okx_books_*.json`).
- `usdg_probe.py`: probe one-shot (`probe_*.json`) e coletor `--loop`.
- `okx_fast.py`: poller OKX de 10 s.
- `analyze.py`: gera `analysis.json`. Rodar de novo a qualquer momento para atualizar os números.
- `run_usdg_collector.ps1` e `run_okx_fast.ps1`: start e `-Stop`.
- `data.db`: tabelas `opps`, `ticks`, `fast`.
- `gt_search_usdg.json` (descoberta de pools), `okx_1h_backfill.json`, `okx_usdg_brl_activity.json`.

**Rodando (iniciados às 22:48 e 22:55 UTC de 11/10, param sozinhos após 24 h, ~22:50 UTC de 12/10):**
- `usdg_probe.py --loop 90` (pid em `usdg_probe.pid`).
- `okx_fast.py --interval 10` (pid em `okx_fast.pid`).

Para parar antes: `.\run_usdg_collector.ps1 -Stop` e `.\run_okx_fast.ps1 -Stop`. Mantidos para cobrir o
horário comercial brasileiro, quando o backfill mostra os desvios. Depois, `python analyze.py` e atualizar a §5.
