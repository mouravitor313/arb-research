# Tópico 2 — USDG (Paxos Global Dollar)  ·  slug `t2_usdg`

## Por que
A OKX lista **`USDG-BRL`**: é mais um dólar com saída barata em BRL (taker 2 / maker −1,5 bps), e
ninguém do time estudou o USDG ainda. Se o USDG negociar fora do par contra USDC/USDT em algum
venue (on-chain ou na própria OKX) e houver mint/resgate 1:1 acessível, pode existir uma instância
nova no formato do `xend-arb`.

## Perguntas
1. Em quais redes o USDG existe (Ethereum, Solana, Ink, X Layer, outras)? Quais redes a OKX aceita
   para depósito/saque de USDG? (API pública de moedas/redes, se existir sem auth; senão, docs.)
2. Quais pares de USDG a OKX tem (`USDG-BRL`, `USDG-USDT`, `USDG-USDC`?) e qual a profundidade no
   tamanho ($1k/$10k/$100k)? `USDG-BRL ÷ USDT-BRL` e `÷ USDC-BRL` — onde fica o USDG contra USDT/USDC?
3. Pools on-chain de USDG com profundidade real (Uniswap v3/v4, Curve, Aerodrome, Orca/Raydium/Jupiter
   na Solana). Cotação executável USDG↔USDC/USDT no tamanho.
4. Mint/resgate na Paxos: quem acessa, taxa, mínimo, prazo, redes. (O USDG paga recompensa a parceiros
   do Global Dollar Network — isso cria fluxo/incentivo que distorce o preço?)
5. Estratégias a medir (líquido, VIP 9):
   - DEX compra USDG barato → OKX vende `USDG-BRL` → recompõe com `USDC-BRL`/`USDT-BRL` (e o inverso).
   - Triângulo interno OKX `BRL→USDG→USDT→BRL` (provavelmente fechado pela taxa não-BRL; confirmar rápido).
   - Diferença USDG vs USDC on-chain, sem OKX (só se houver pool fundo dos dois lados).

## Pistas
- Reaproveitar a parte de livros OKX do `xvenue_collector.py` (VWAP em 400 níveis) e os quoters do
  `chains.py`. Para Solana, Jupiter lite API (`https://lite-api.jup.ag/swap/v1/quote`, ≤0,5 req/s).
- Comparação útil: o USDC tem ~9 bps de prêmio sobre o USDT em todo lugar (`RECAP.md §10.2`).
  O USDG fica perto do USDC, do USDT ou de nenhum?

## Saída esperada
`topics/t2_usdg/REPORT.md` com a conclusão e, se houver sinal, um coletor ao vivo de ≤24 h para
medir frequência e duração dos episódios.
