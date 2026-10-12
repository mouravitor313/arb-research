# Tópico 4 — Ciclos atômicos na Gnosis (e Base) (item D)  ·  slug `t4_gnosis_atomic`

## Por que
Na Polygon o ciclo atômico de BRL fechou (`RECAP.md §9`) e já é explorado por um searcher
(EOAs vanity **`0x4337…`**, ~66% dos swaps nos pools BRL). Na Gnosis há vários pools de real com
preços diferentes: Oku BRLA/USDC.e (mediana −3 bps) vs Curve BRLA/USDC.e (−20 bps), mais BRZ/USDC.e
e BRZ/BRLA (`RECAP.md §3`). Um ciclo 100% on-chain não usa OKX nem inventário e não depende de
resgatar BRZ (ele entra e sai do ciclo no mesmo bloco).

## Pools de partida (Gnosis)
- USDC.e/BRLA Oku (Uni v3) 0,05% `0x576bf065cbc15cb2d61affb156118fcff01a8238` (~$104k)
- BRLA/USDC.e Curve `0xfb8b95fb2296a0ad4b6b1419fdaa5aa5f13e4009` (~$56k)
- BRZ/USDC.e (~$41k) e BRZ/BRLA (~$11k) — descobrir endereços
- Base: BRLA/USDC Aerodrome 0,05%, BRZ/USDC (2 pools), frxUSD/BRZ — ver se forma ciclo

## Perguntas
1. **Primeiro (barato):** o searcher `0x4337…` opera na Gnosis/Base? Descobrir os endereços dele a
   partir do `cycle_pool_swaps.tx_from` do `arb_tracker.db` (**só leitura**, abrir com
   `sqlite3` em modo `?mode=ro`) e checar atividade nos pools da Gnosis/Base com
   `alchemy_getAssetTransfers` (poucas chamadas, filtradas por contrato). Mapear também quem mais
   faz swaps multi-pool nesses pools nos últimos 14 dias.
2. Ciclos candidatos: `USDC.e→BRLA(Oku)→USDC.e(Curve)` (2 pernas), e os de 3–4 pernas com BRZ.
   Quote no bloco fixo via multicall (QuoterV2 do Oku + Curve `get_dy` — reaproveitar
   `cycle_common.py`/`cycle_quote.py`). $1k/$10k/$100k, os dois sentidos, líquido de gás (xDAI ≈ $1).
3. Backfill archive 14 dias com passo grosso via Alchemy (`gnosis-mainnet`), depois refinar só se
   houver p95 > 0.
4. Se houver lucro: qual nível de execução seria preciso (`RECAP.md §6`: nível 1 router multi-hop só
   se todos forem Uni v3; Curve exige nível 2 = contrato executor) e quanto por evento/dia.

## Saída esperada
`topics/t4_gnosis_atomic/REPORT.md`: tabela de ciclos (p50/p95/% > 0/lucro por evento), quem já
compete e a recomendação (vale/não vale subir para nível 2 por causa da Gnosis/Base).
