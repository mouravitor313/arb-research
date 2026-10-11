# RECAP — estado do repo + alinhamento de objetivo (v3)

> Data: 2026-10-10. Ponto de parada antes de retomar a pesquisa. Complementa o `PROJECT.md` (estado
> técnico) e substitui o *enquadramento* de `STRATEGY.md` / `research_v2.md` onde houver conflito.
> §7 registra as respostas de alinhamento dadas pelo usuário nesta mesma data.

---

## 1. Objetivo (alinhado)

**Arbitragem on-chain em DEXes com as pontas em:**
- **stablecoin de real** — **BRLA** (já operada) e **BRL1** (dá para abrir relação com o emissor); e/ou
- **CEX = só OKX** (VIP 9 — taxas na §4).

**Relação com o `xend-arb`:** o `xend-arb` é o **motor de execução** (já roda em produção). Este
repo (`arb`) é a **camada de pesquisa e varredura**: ele encontra e mede as oportunidades e entrega
para o `xend-arb` as que já foram validadas, como instância nova ou como melhoria.

| Antes (v1 / v2 neste repo) | Agora (v3) |
|---|---|
| Achar *paths* `TOKEN → DEX → USDC → CEX → BRL` para liquidar tokens diversos | Achar **arbitragens recorrentes** com pontas em BRLA/BRL1 e/ou OKX |
| Terminal BRL = Foxbit | Terminal BRL = **OKX** (já é o que o `xend-arb` usa) |
| Qualquer CEX onboardável | **Só OKX** — spreads entre CEXes deixam de ser oportunidade |
| LatAm + China + Europa, 4 classes de ativos | **Só BRL** — MXN/COP/EUR/RMB/USDY/sUSDe fora |
| Taxa OKX no config = 10 bps | **BRL: maker −1,5 / taker 2 bps · não-BRL: maker 2,5 / taker 11 bps** |

---

## 2. O que já existe

### 2.1 Este repo (`arb`) — pesquisa
| Entrega | Ainda útil no v3? |
|---|---|
| `research.md` (v1) | Só como histórico de exclusões |
| `research_v2.md` | **Parcial**: profundidade BRLA, modelo de scoring (§3), split multi-pool |
| `arb_tracker.py` + SQLite (612 polls, 18–22/set) | **Sim**, como scanner; precisa de OKX BRL, BRL1, Gnosis/Base e quotes executáveis |
| `dashboard.py` (não commitado) | Sim, depois de reconfigurar |
| `watchlist.json` / `tracking_config.json` | Precisam ser podados para o escopo BRL |

### 2.2 `xend-arb` — execução (números do `.specs/STATE.md` de lá)
- **Duas instâncias ao vivo** desde 27/08, com sub-contas OKX e wallets separadas:
  - **brz**: OKX `USDT-BRL` ↔ Uniswap v3 `BRZ/USDT0` 0,05% (Polygon `0x4af6…0817`)
  - **brla**: OKX `USDC-BRL` ↔ Uniswap v3 `USDC/BRLA` 0,05% (Polygon `0x0e77…c956`)
- **Modo:** semi-automático, com inventário pré-posicionado. O bot executa as duas pernas; o hedge
  e o rebalanceamento são manuais (resgate na Avenia, saques da OKX).
- **Medido em 28/08 (24 h):** brz 380 trades / R$160; brla 123 trades / R$89,50. Ciclo mediano
  de 2,9 s, gás ~US$0,01 por tx, taker OKX de 2 bps confirmado em fill.
- **Gargalo:** o **ciclo de inventário** (WP-23). Quase 100% das execuções saem em
  `buy_dex_sell_cex`, ou seja, a stable de real fica sistematicamente barata no DEX. Isso
  acumula BRL na OKX e consome BRLA/BRZ da wallet. Em 28/08 houve ~1.000 skips/dia por
  `insufficient_capacity`.
- A perna CEX é **sempre taker**: o `src/cex/okx.py` não tem post-only/maker.

---

## 3. Dados de BRLA (scanner, 18–22/set) e mapa de pools

Desvio do BRLA vs USD/BRL de referência, em bps (último preço negociado, **não** cotação executável):

| Pool | TVL | p5 | **mediana** | p95 |
|---|---|---|---|---|
| Polygon Uni v3 0.05% (o do bot) | $126–152k | −24 | **−7** | +18 |
| Gnosis Oku 0.05% | $104k | −14 | **−3** | +34 |
| Gnosis Curve | $56k | −41 | **−20** | +8 |
| Base Aerodrome 0.05% | $45k | +3 | **+54** | +125 |

A mediana negativa na Polygon é o mesmo fenômeno que o `xend-arb` vê: BRLA barato no DEX, fluxo
numa direção só.

**Pools de real com mais de $2k (GeckoTerminal, hoje):**

| Chain | Pool | TVL | Vol 24h |
|---|---|---|---|
| Polygon | USDC/BRLA 0.05% (bot brla) | $152k | $144k |
| Polygon | BRZ/USDT0 0.05% (bot brz) | $73k | $53k |
| Polygon | **BRZ/BRLA 0.05%** | $8,6k | $4,5k |
| Polygon | **TESOURO/BRZ/stBRZ/BRLA** (stable pool) | $136k | $1,2k |
| Polygon | **BRL1/USDT 0.3%** | $103k | ~$2k |
| Gnosis | USDC.e/BRLA Oku 0.05% · BRLA/USDC.e Curve · BRZ/USDC.e · BRZ/BRLA | $104k · $57k · $41k · $11k | baixo |
| Base | BRLA/USDC 0.05% · BRZ/USDC (2 pools) · frxUSD/BRZ | $45k · $24k · $23k | baixo |

➡️ **Achado importante:** na Polygon existe um **ciclo fechado 100% on-chain**,
`USDC → BRLA → BRZ → USDT0 → USDC`, usando os dois pools do bot e as pontes BRZ/BRLA ou TESOURO.
Ele seria executável **atomicamente** e sem tocar na OKX (ver §6).

---

## 4. OKX como terminal (medido hoje) + taxas VIP 9

| Par | Bid / Ask (tarde) | Vol 24h | Livro (20 níveis, moeda de cotação) | Tabela de taxa |
|---|---|---|---|---|
| `USDT-BRL` | 5,0253 / 5,0260 | ~R$42,8M | R$4,9M / R$2,2M | **BRL** |
| `USDC-BRL` | 5,0298 / 5,0304 | ~R$1,1M | R$1,4M / R$1,3M | **BRL** |
| `BRL1-BRL` | 1,0000 / 1,0001 | ~R$474k | R$1,25M / R$3,0M | **BRL** |
| `BRL1-USDT` | 0,1981 / 0,1992 | ~$68k | **$5,8k** / $144k | não-BRL |

**Taxas (print do usuário):**
- **Pares BRL:** maker **−1,5 bps** (rebate), taker **2 bps**
- **Pares não-BRL:** maker 2,5 bps, taker **11 bps**

**Implicações:**
1. **Na OKX, sempre rotear por pares BRL.** Converter USDT↔USDC passando por BRL
   (`USDT-BRL` + `USDC-BRL`) custa 4 bps a taker ou −3 bps a maker, contra 11 bps no par direto.
   On-chain, o pool USDC/USDT da Polygon (~$8M) também é barato.
2. **Perna CEX como maker:** o bot hoje paga +2 bps. Ficar no book com post-only e fazer o hedge no
   DEX quando a ordem é executada mudaria para −1,5 bps, ou seja, **3,5 bps a mais por trade** sobre
   uma edge típica de ~14–15 bps. O preço é o risco de execução e de seleção adversa.
3. **Triângulo interno com BRL1** (BRL→USDT→BRL1→BRL): fechado a mercado (≈ −12 bps). O livro de
   `BRL1-USDT` é unilateral (só $5,8k no bid) e caro de taxa. Fica **baixa prioridade** e fora do
   escopo on-chain.
4. `USDC-BRL` paga ~9 bps a mais que `USDT-BRL`, então sair via USDC continua sendo melhor.

---

## 5. Mapa de oportunidades sob o v3 (priorizado)

| # | Oportunidade | Natureza | Por que | Próxima medição | Prioridade |
|---|---|---|---|---|---|
| **A** | **Melhorar o `xend-arb` atual**: perna OKX como maker + automatizar o ciclo Avenia (grátis, ≤10 min) | CEX↔DEX, semi-auto | É onde o dinheiro já está; o gargalo medido é o inventário, não a edge | Simular o ganho de maker com o histórico `arb_opportunities` (taxa de fill × 3,5 bps) | **1** |
| **B** | **Ciclo atômico na Polygon** `USDC→BRLA→BRZ→USDT0→USDC` | On-chain, atômico | ~~Ciclo fechado sem CEX nem inventário~~ **MEDIDO 2026-10-10: fechado (0% das amostras > 0) e já disputado por um searcher atômico (`0x4337…`)** — ver §9 | Só reabrir com um backrun no mesmo bloco (nível 3) ou se a profundidade da ponte BRLA↔BRZ crescer | ~~2~~ **baixa** |
| **C** | **Instâncias BRLA em Base / Gnosis** (OKX ↔ pool local; Avenia emite/resgata na chain) | CEX↔DEX, semi-auto | Base com **+54 bps de mediana** vs −7 na Polygon. Se a Avenia mintar/resgatar na Base, isso deixa de ser "cross-chain" e vira só mais uma instância | Quote executável a $1k/$10k; confirmar chains da Avenia e redes de saque da OKX | **3** |
| **D** | **Ciclos atômicos na Gnosis** (Oku ↔ Curve ↔ BRZ/BRLA ↔ BRZ/USDC.e) | On-chain, atômico | Oku vs Curve com ~17 bps de diferença mediana | Mesmo quoter do B | 4 |
| **E** | **BRL1**: instância `BRL1/USDT` (Polygon) ↔ OKX `USDT-BRL` + `BRL1-BRL`; e/ou BRL1 como **trilho de rebalanceamento** (BRL@OKX → BRL1 a 1:1 com rebate → saque on-chain) | CEX↔DEX | A OKX já tem BRL1-BRL líquido; o problema é que on-chain o BRL1 só tem um pool de 0,3% | Redes de depósito/saque de BRL1 na OKX; termos do emissor; o pool de 0,3% exige desvio > ~34 bps | 5 |
| F | Triângulo interno OKX com BRL1 | CEX-only | Fechado hoje | — | fora |

---

## 6. Complexidade: semi-automático → atômico

**A primeira coisa é entender que atomicidade só existe quando todas as pernas estão on-chain, na
mesma chain e na mesma transação.** Uma perna na OKX (A, C, E) **nunca** fica atômica. O que dá
para melhorar ali é a latência e o hedge. A edge estrutural do time é o acesso KYC ao emissor
(Avenia mint/redeem a 1:1, sem taxa) e à OKX BRL. Um bot atômico **não usa essa vantagem**: ele
compete com searchers genéricos. Então o atômico é um **complemento** (B, D), não um substituto.

| Nível | O que é | O que precisa | Risco / esforço relativo |
|---|---|---|---|
| **0 — hoje** | CEX↔DEX não-atômico com inventário (`xend-arb`) | — | Risco de perna (já mitigado com circuit breakers e exposição máxima) |
| **1 — multi-hop via router** | Uma tx no Uniswap SwapRouter / UniversalRouter com path `USDC→BRLA→BRZ→USDT0→USDC` e `amountOutMinimum ≥ amountIn × (1+edge)`. Se não houver lucro, a tx reverte e custa só o gás (~$0,01) | Os pools do ciclo precisam ser Uniswap v3 (os 3 principais são; confirmar o BRZ/BRLA). Reaproveita `chain/quoter.py` + `chain/swap.py`. Capital próprio em USDC | **Baixo.** Sem Solidity. Principal risco: front-run/sandwich no mempool público → usar RPC privado |
| **2 — contrato executor próprio** | Contrato que encadeia DEXes diferentes (Uniswap v3 + Curve/TESOURO + Aerodrome), checa `saldoFinal > saldoInicial + minLucro` e opcionalmente usa **flash swap/flash loan** (sem capital parado) | Solidity + testes em fork (Foundry), deploy por chain, gestão de chave/allowances, revisão de segurança | **Médio.** Abre o pool TESOURO e as rotas de Gnosis/Base |
| **3 — competitivo/MEV** | Backrun de swaps alheios no mesmo bloco, leilões de ordem de fluxo (ex.: FastLane na Polygon), latência de nó | Nó/RPC dedicado, mempool streaming, lógica de lances | **Alto.** Só vale se B/D mostrarem que a edge é disputada |

**Recomendação:** antes de qualquer código, **medir B** com o quoter (frequência × lucro líquido
por $1k/$10k). Se fechar, o nível 1 é um incremento pequeno no `xend-arb` (nova instância/modo
"cycle"). O nível 2 só se justifica se o TESOURO ou a Gnosis/Base mostrarem edge relevante.

---

## 7. Respostas de alinhamento (2026-10-10)

1. **CEX atual:** OKX (já é a do `xend-arb`).
2. **Taxas VIP 9:** BRL maker −1,5 / taker 2 bps; não-BRL maker 2,5 / taker 11 bps.
3. **Avenia:** conta ativa, **sem taxas, prazo ≤ ~10 min**. **BRL1:** sem conta, mas há contatos para abrir.
4. **Execução:** semi-automática como o `xend-arb`; quer entender a evolução para atômico (§6).
5. **Chains:** hoje Polygon; outras onde for viável.
6. **Tamanhos:** mantém as faixas de $10k / $100k.

### Ainda em aberto → movido para `PONTOS_DE_ATENCAO.md §3`
- Respondidas depois: USDC tem as principais redes na OKX; **BRL1 só Polygon**; este repo = **só
  pesquisa e indexing** (execução no `xend-arb`).
- Pendentes: Avenia em Base/Gnosis + API; termos do emissor de BRL1.

---

## 8. Próximos passos propostos

1. ✅ **Medir B (ciclo atômico na Polygon)** — feito em 2026-10-10, resultado negativo (§9). O coletor
   ao vivo segue rodando para cobrir alguns dias; reanalisar com `python cycle_analyze.py`.
2. **Medir A-maker:** com o histórico do `xend-arb` (`arb_opportunities`), estimar quanto rende a
   perna OKX como post-only (−1,5 bps) vs taker, e com que taxa de fill.
3. **Reconfigurar o scanner (`arb_tracker.py`)** para o v3: OKX BRL/BRL1 (books), pools de real na
   Polygon/Gnosis/Base da §3, taxas VIP 9, quotes executáveis; podar o resto.
4. **Pesquisa dirigida** (itens em aberto da §7): Avenia multichain, redes OKX, BRL1.

---

## 9. Resultado do item B — ciclo atômico na Polygon (MEDIDO 2026-10-10)

> Medição só-leitura (eth_call): QuoterV2 / V4Quoter / Curve `get_dy` via Multicall3, travada num
> bloco. As fees dos pools já estão dentro das cotações; o gás é somado à parte. Scripts `cycle_*.py`,
> tabelas `cycle_*` em `arb_tracker.db`.

### 9.1 Pools verificados on-chain (bloco 95.303.440, `cycle_discovery.json`)
| Perna | Pool | Tipo / fee | Reservas na data |
|---|---|---|---|
| USDC↔BRLA | `0x0e77…c956` | Uni v3 0,05% (factory oficial, `getPool` confere). **USDC nativo** `0x3c49…` | 114k USDC / 186k BRLA |
| BRZ↔USDT0 | `0x4af6…0817` | Uni v3 0,05% | 146k BRZ / 44k USDT0 |
| BRZ↔BRLA | `0x6e05…fb86` | **Uni v3 0,05% (confirmado)**, mas raso e torto | 39,5k BRZ / **3,9k BRLA** (~$780) |
| BRZ↔BRLA | `0xc89f…9735` "DFB BRL Pool v1" | **Curve stableswap-ng v7**, 4 moedas (TESOURO/BRZ/stBRZ/BRLA), fee 0,03%, A=2000, `get_dy(int128…)` | 387k BRZ / 223k stBRZ / 52k BRLA / 32k TESOURO |
| USDT0↔USDC | `0x3108…81B7` | Uni v3 0,01% | **só 46k USDC** / 935k USDT0 |
| USDT0↔USDC | v4 id `0xa37d…a399` | **Uni v4, fee 8 (0,0008%)**, tickSpacing 1, sem hook | **~$477k** (não os ~$8M de 18/set); vol 24h ~$6M |

O ciclo fecha em USDC nativo (nenhum USDC.e envolvido). Só a rota 100% Uniswap cabe num router
(v3 + v4 → UniversalRouter). A rota pelo Curve exige contrato executor (nível 2).

### 9.2 Lucro líquido (melhor sentido × rota por amostra)
| Janela | Tamanho | p50 | p95 | **máx** | % > 0 | % > 5 bps |
|---|---|---|---|---|---|---|
| Backfill archive, 30/09 → 10/10, 2.016 amostras (~10 min) | $1k | −21,5 | −13,6 | **−3,2** | **0%** | 0% |
| idem | $10k | −120 | −71 | −46 | 0% | 0% |
| idem | $100k | −7.623 | −6.272 | −5.861 | 0% | 0% (só profundidade) |
| Ao vivo, 10/10 16:48–18:42 BRT, 566 ticks (12 s) | $1k | −28,9 | −25,3 | −22,3 | 0% | 0% |
| idem | $10k | −129 | −120 | −120 | 0% | 0% |

Por rota ($1k, backfill): fwd/curve p50 −28 · fwd/uni p50 −38 · rev/curve p50 −26 · rev/uni p50 −26,
mas a pool v3 BRZ/BRLA **se esgota em 56% das amostras já a $1k** no sentido rev (e em 51% a $10k
no fwd). Gás: 275 gwei × POL $0,102 → **$0,017–0,03 por ciclo** (~0,2–0,3 bps a $1k; irrelevante).

### 9.3 Por que não fecha
- **O desvio no mid (spot, sem fees) é pequeno:** rota v3 p50 −0,9 bps, p5/p95 −11,5/+9,2, extremos
  −37/+35. Já as fees somam ~15 bps (3×5 + 0,08) na rota uni e ~13 bps na Curve, mais o impacto.
- **A ponte BRLA↔BRZ é o gargalo.** A v3 só tem ~$780 de BRLA. O Curve (A=2000) segura BRZ≈BRLA perto
  de 1:1, enquanto o mercado (v3) precifica **BRZ ~0,96% abaixo do BRLA**. O Curve cobra caro
  justamente no sentido que o ciclo precisaria.
- **Já existe um searcher atômico.** EOAs com prefixo vanity `0x4337…` (22 EOAs distintas, 25 txs
  em ~2 h) fazem **38 de 58 swaps (66%)** nos pools BRL. Há txs tocando USDC/BRLA + BRZ/USDT0 + TESOURO
  + BRZ/BRLA na mesma transação, ou seja, exatamente este ciclo, no mesmo bloco do desequilíbrio.
  Quoter a cada 12 s ou 10 min só vê o ciclo **depois** de fechado. Nos ticks ≤3 blocos após um swap
  em pool BRL, o melhor $1k ficou em mediana −32,5 bps vs −28,9 nos demais: não há janela visível.
- Correlação com os bots do `xend-arb`: não dá para separar sem os endereços das wallets (estão no
  `.env` de lá, que não foi lido). Os swaps ficam registrados em `cycle_pool_swaps` (bloco, tx,
  tx.from) para cruzar quando os endereços forem informados.

### 9.4 Conclusão
B **não é oportunidade** no formato "quote periódico + router multi-hop" (nível 1/2). A única forma
de capturar algo seria **backrun no mesmo bloco** (nível 3) contra um searcher já estabelecido, e com
a ponte BRLA↔BRZ rasa o tamanho por evento é pequeno (centenas de dólares). Prioridade rebaixada;
foco volta para **A** (maker na OKX + ciclo Avenia) e **C** (instâncias Base/Gnosis).
