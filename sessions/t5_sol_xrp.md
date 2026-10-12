# Tópico 5 — SOL e XRP on-chain vs OKX `SOL-BRL` / `XRP-BRL`  ·  slug `t5_sol_xrp`

## Por que
A OKX tem `SOL-BRL` e `XRP-BRL`. No item 1 o SOL só entrou nos triângulos internos da OKX (fechados,
−25 a −28 bps). Falta comparar com as DEXes nativas. **Hipótese a priori fraca**: ativos nativos
tendem a estar alinhados (ETH e cbBTC deram −10 a −16 bps). Então este tópico é **time-boxed**:
probe rápido; só aprofundar se aparecer p95 > 0.

## Perguntas
1. **SOL:** Jupiter lite API (`https://lite-api.jup.ag/swap/v1/quote`, ≤0,5 req/s) SOL↔USDC/USDT a
   $1k/$10k/$100k vs OKX `SOL-BRL` (+ `USDC-BRL`/`USDT-BRL` para fechar). Líquido de taxa OKX VIP 9,
   fee de rota e taxa de prioridade da Solana. Rodar algumas horas a cada ~30–60 s antes de concluir.
2. **XRP:** DEX nativo do XRPL (order book + AMM; API pública ex. `https://xrplcluster.com` /
   `s1.ripple.com`, métodos `book_offers`, `amm_info`) para XRP/USD-stable (RLUSD, USDC no XRPL?)
   vs OKX `XRP-BRL`. Checar se existe profundidade real antes de medir.
3. Ver também os pares BRL "estranhos" da OKX (`PEPE-BRL`, `PI-BRL`, `TRUMP-BRL`): só checar
   profundidade/spread do livro; se o livro BRL for raso e largo, pode haver desalinhamento contra o
   par USDT da própria OKX + DEX. Probe de 1 hora no máximo.
4. Alchemy aqui só se precisar de Solana/EVM pago; o padrão é API pública.

## Saída esperada
`topics/t5_sol_xrp/REPORT.md` curto: tabela por ativo, conclusão, e se algum merece coletor.
