# Tópico 3 — Instâncias BRLA em Base e Gnosis (item C)  ·  slug `t3_brla_l2`

## Por que
O `xend-arb` já opera OKX ↔ pool USDC/BRLA na Polygon, com a Avenia (sem taxa, ≤10 min) fechando o
ciclo de inventário. Se o BRLA na Base/Gnosis desvia mais que na Polygon, cada pool vira **mais uma
instância** igual, sem bridge, desde que a Avenia emita/resgate nessas chains. O scanner antigo
(GeckoTerminal, último negócio) mostrou mediana de **Base +54 bps**, **Gnosis Oku −3**,
**Gnosis Curve −20**, contra **Polygon −7** (`RECAP.md §3`). Pode ser só preço velho em pool de pouco
volume — este tópico mede com cotação executável.

## Pools conhecidos (validar on-chain)
| Chain | Pool | Endereço | Obs. |
|---|---|---|---|
| Base | BRLA/USDC Aerodrome Slipstream 0,05% | `0x1c33aa5cc206ed3d9e29fb136796a8815e48af58` | ~$45k; BRLA `0xfcb34c47f850f452c15ea1b84d51231c38a61783` |
| Gnosis | USDC.e/BRLA Oku (Uni v3) 0,05% | `0x576bf065cbc15cb2d61affb156118fcff01a8238` | ~$104k; BRLA `0xfecb3f7c54e2caae9dc6ac9060a822d47e053760` |
| Gnosis | BRLA/USDC.e Curve | `0xfb8b95fb2296a0ad4b6b1419fdaa5aa5f13e4009` | ~$56k |
| Polygon (referência) | USDC/BRLA Uni v3 0,05% | ver `cycle_discovery.json` | pool do bot |

Procurar também outros pools de BRLA nessas chains (e em outras onde o BRLA exista) que não estavam
no mapa.

## Perguntas
1. Cotação executável a $1k/$10k/$100k, nos dois sentidos, contra a OKX `USDC-BRL`/`USDT-BRL`
   (BRLA = R$1). Líquido de taxa OKX VIP 9 + fee do pool + gás. Atenção: na Gnosis o lado dólar é
   **USDC.e (bridged)** — como ele chega/sai da OKX? (A OKX aceita USDC na Gnosis? Se não, custo de
   ponte entra na conclusão.)
2. Backfill archive de 14 dias com passo grosso (30–60 min) via Alchemy (`base-mainnet`,
   `gnosis-mainnet`) para ter distribuição, não só a foto. Livros OKX históricos não existem: usar
   candles OKX (`/api/v5/market/history-candles`) de `USDC-BRL` como referência e declarar o erro.
3. Comparar com a Polygon nas mesmas condições (mesmo método) para dizer se Base/Gnosis são
   **melhores** que a instância atual, e quanto volume por dia caberia.
4. Pesquisa de mesa: a Avenia emite/resgata BRLA em Base e Gnosis? Mesmo prazo e sem taxa? Tem API?
   (Docs públicas da Avenia/BRLA. Se não der para confirmar, deixar como pergunta para o usuário,
   que tem conta — pendência `PONTOS_DE_ATENCAO.md §3.1`.)

## Saída esperada
`topics/t3_brla_l2/REPORT.md` com ranking das chains/pools (p50/p95/% > 0, tamanho que cabe, volume
diário capturável) e a recomendação de abrir ou não instâncias no `xend-arb`.
