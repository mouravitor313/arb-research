# Tópico 5 — SOL e XRP on-chain vs OKX `SOL-BRL` / `XRP-BRL` (MEDIDO 2026-10-11)

## 1. Pergunta e hipótese
Há desalinhamento explorável entre o SOL nas DEXes da Solana (Jupiter) ou o XRP no DEX nativo do XRPL
(CLOB + AMM) e os pares `SOL-BRL` / `XRP-BRL` da OKX, fechando por `USDT-BRL`/`USDC-BRL`? E os pares
BRL "estranhos" (`PEPE-BRL`, `PI-BRL`, `TRUMP-BRL`) estão desalinhados do par USDT da própria OKX?
Hipótese a priori fraca (ativos nativos tendem a estar alinhados, como ETH/cbBTC no item 1).
**Confirmada: não há oportunidade.**

## 2. Fontes e o que foi verificado
| Item | Status | Fonte |
|---|---|---|
| Livros OKX (400 níveis), volume 24 h, lista de pares (`SOL/XRP-BRL`, `RLUSD-USDT`) | verificado | API pública OKX |
| Cotação Solana executável no tamanho | verificado | Jupiter `api.jup.ag/swap/v1/quote` (keyless; **`lite-api.jup.ag/swap/v1` deu 503** em 11/10). Sem platform fee (a Ultra cobra +2 bps). |
| Cotação XRPL executável no tamanho (CLOB + AMM, regras do rippled) | verificado | `ripple_path_find` exact-out em s1/s2.ripple.com, usando como *source* contas com saldo (só leitura) |
| AMM XRP/RLUSD e XRP/USDC (reservas, fee) | verificado | `amm_info` |
| Emissores RLUSD `rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De` (domain ripple.com) e USDC `rGm7WCVp9gb4jZHWTEtGUr4dd74z2XuWhE` (domain circle.com), **sem TransferRate** | verificado | `account_info` |
| Emissão: RLUSD no XRPL ~1,14 bi; USDC no XRPL ~5,75 mi | verificado | `gateway_balances` |
| Custo de tx Solana | **estimado**: 5.000 lamports + ~300k CU × 1 µlamport/CU ≈ 0,0003 SOL ≈ $0,034/swap (0,3 bps a $1k) | — |
| Mint/resgate 1:1 do RLUSD na Ripple (só institucional) | só relatado, não verificado | — |

## 3. Venues / profundidade (`discovery.json`)
| Venue | Par | Profundidade | Obs. |
|---|---|---|---|
| OKX | `SOL-BRL` | ~R$110k ask / R$119k bid dentro de ±1% (**~$22–24k por lado**); spread ~7 bps; volume ~R$168k/dia | $100k **não cabe** |
| OKX | `XRP-BRL` | ~R$107k ask / R$119k bid dentro de ±1% (**~$21–24k**); spread ~4 bps; volume ~R$65k/dia | $100k não cabe; abaixo de −5% há ordens-isca enormes (o livro foi cortado em ±5%) |
| OKX | `USDT-BRL` / `USDC-BRL` | R$6–7M / R$2–3M dentro de ±1% | não é o gargalo |
| OKX | `RLUSD-USDT` | ~$10M por lado; mid **1,00085** fixo durante a coleta | RLUSD ~8,5 bps acima do USDT |
| OKX | `PEPE/PI/TRUMP-BRL` | R$38–113k dentro de ±1%; spread 22–31 bps; **volume R$0,5k / R$2,2k / R$8,8k por dia** | praticamente sem negócios |
| Solana | SOL/USDC, SOL/USDT via Jupiter | rotas BisonFi/HumidiFi/etc.; $100k com impacto de poucos bps | profundo |
| XRPL | AMM XRP/RLUSD `rhWTXC2m2gGGA9WozUaoMm6kLAVPb1tcS3` | 1,78M XRP + 2,51M RLUSD (**~$5,0M**), fee 0,196% + CLOB ~$59k ask / $98k bid | profundo, mas fee alto |
| XRPL | AMM XRP/USDC `rM7cHVPfhe9yxQNk2kDNBEQqoQmMcQGPWE` | 99,7k XRP + 140k USDC (**~$280k**), fee 0,097% + CLOB ~$53k / $44k | raso: $100k custa ~17% |

## 4. Método
`t5_collector.py`, tick a cada 60 s, **88 ticks em 11/10 de 19:55 a 21:23 BRT** (~1,5 h; parado cedo
pela regra "matar cedo", já que nada chegou perto de zero). Modelo de inventário pré-posicionado,
todas as pernas OKX taker (VIP 9: BRL 2 bps, não-BRL 11 bps), fee do DEX embutido na cotação e custo de tx incluído.
- **DtoO:** S stable → compra A no DEX → vende A em `A-BRL` → recompra a stable em `<stable>-BRL`.
- **OtoD:** vende stable em `<stable>-BRL` → compra A em `A-BRL` → vende A no DEX.
- `@nb` = mesmo ciclo fechando direto em `A-USDT`/`A-USDC` (11 bps), como referência.
- RLUSD fecha via `USDT-BRL`. Duas leituras: **par** (RLUSD = 1 USDT) e **@mkt** (RLUSD ao mid
  `RLUSD-USDT` 1,00085, ou seja, o custo real de recompor o inventário de RLUSD).
- Memes: triângulo interno `USDT → A-USDT → A-BRL → USDT-BRL` e o inverso.
- Livro OKX contado só até ±5% do topo; fora disso = "não cabe".

## 5. Resultados (bps líquidos, 88 ticks; `summary.json`)
| Estratégia | $1k p50 / p95 | $10k p50 / p95 | $100k | % > 0 |
|---|---|---|---|---|
| SOL Jupiter USDC → `SOL-BRL` (DtoO) | −10,6 / −9,5 | −15,0 / −13,0 | não cabe (via `SOL-USDC` −20) | 0% |
| SOL `SOL-BRL` → Jupiter USDC (OtoD) | −9,5 / −7,2 | −14,8 / −12,5 | não cabe (−22 nb) | 0% |
| SOL Jupiter USDT (DtoO) | −10,9 / −8,0 | −15,0 / −12,8 | não cabe (−15 nb) | 0% |
| SOL `SOL-BRL` → Jupiter USDT (OtoD) | **−8,1 / −3,7** (máx −2,1) | −13,3 / −9,4 | não cabe (−16 nb) | 0% |
| XRP XRPL RLUSD → `XRP-BRL` (DtoO), RLUSD **ao par** | **−3,8 / −0,2** (máx +0,6) | −9,2 / −5,9 | não cabe | 3% (3 ticks isolados) |
| idem, RLUSD **@mkt** | −12,3 / −8,7 | −17,7 / −14,4 | — | 0% |
| XRP `XRP-BRL` → XRPL RLUSD (OtoD), ao par / @mkt | −24,1 / −20,8 · −15,6 / −12,3 | −29,4 · −20,9 | não cabe | 0% |
| XRP XRPL USDC ↔ `XRP-BRL` (os dois sentidos) | −17 a −21 / −12 a −15 | −28 a −29 | não cabe (−1.700 a −1.800 nb) | 0% |
| PEPE triângulo OKX (2 sentidos) | −30 a −32 / −25 a −29 | −62 a −64 | — | 0% |
| PI triângulo OKX | −31 a −33 / −29 | −78 a −82 (só 80% cabe) | — | 0% |
| TRUMP triângulo OKX | −37 a −38 / −32 | −71 a −80 | — | 0% |

Gap entre mids (A-BRL ÷ USDT-BRL vs A-USDT): PEPE p50 −0,9 bps (−3,3 a +2,7), PI −0,5 (−5,6 a +17),
TRUMP −0,6 (−7,2 a +0,6). **Os pares BRL "estranhos" são cotados por market maker colado no par USDT**;
o que se paga é só spread + taxa. Nenhum episódio > 0 nas estratégias a preço de mercado.

## 6. Conclusão: **não é oportunidade**
1. **SOL:** alinhado. O custo é o spread do `SOL-BRL` (~7 bps) mais 4 bps de taxa. O melhor caso
   (comprar na OKX, vender USDT na Jupiter, $1k) dá p95 −3,7. Além disso, o `SOL-BRL` só tem
   ~$22k por lado, então o tamanho útil é ≤ $10k.
2. **XRP:** o único número perto de zero (RLUSD → `XRP-BRL`, $1k, p95 −0,2) é **ilusão de
   avaliação**: depende de o RLUSD valer 1 USDT, mas a OKX cotou o RLUSD 8,5 bps acima durante toda
   a coleta. A mercado, dá −12 p50. O AMM XRP/RLUSD é profundo, porém cobra 0,196%. O XRP/USDC no XRPL é raso.
3. **PEPE/PI/TRUMP-BRL:** mids alinhados ao par USDT, spread de 22–31 bps e volume de R$0,5–9k/dia. Nada a fazer.
4. **Nenhum ativo merece coletor.** O tópico fica fechado como resultado negativo bem medido.

Única ressalva ("depende de X"): se a equipe conseguir **mintar RLUSD a $1,0000 com a Ripple** e o
**resgate/venda** sair pelos ~8,5 bps de prêmio, o ciclo XRPL→`XRP-BRL` fica em ~−4 p50 / ~0 p95 a $1k.
Mesmo assim não paga a operação, e o tamanho é limitado pelo livro BRL (~$20k).

## 7. Perguntas para o usuário / terceiros
- OKX: há market maker com programa para os pares BRL de SOL/XRP? Os livros têm só ~$20k por lado; um
  rebate maker (−1,5 bps) postando liquidez seria outro negócio (market making, não arbitragem).
- Ripple: a equipe tem acesso a mint/resgate institucional do RLUSD? Com qual fee e mínimo? Isso só
  importa se outro tópico usar RLUSD como ponte; aqui não muda a conclusão.

## 8. Requisições Alchemy usadas
**0.** Tudo por APIs públicas: OKX, Jupiter (~12 req/tick, ≤ 0,5 req/s), XRPL s1/s2.ripple.com e
xrplcluster. A Jupiter deu 14 erros transitórios ("Oracle is stale" / 5xx), com retry.

## 9. Arquivos criados / processos
Tudo em `topics/t5_sol_xrp/`:
- `t5_collector.py`: probe/coletor (`--once` ou `--interval/--hours`; pára com arquivo `STOP`)
- `discovery.py` → `discovery.json`: AMMs/CLOB do XRPL e profundidade dos livros OKX
- `analyze.py` → `summary.json`: tabela p50/p95/% > 0/episódios
- `data.db`: tabelas `opps` (60 linhas/tick) e `ticks` (JSON bruto: mids, RLUSD-USDT, cotações DEX)
- `collector.log`

**Nada ficou rodando** (coletor parado às 21:23 BRT via `STOP`; o `.pid` foi removido).
