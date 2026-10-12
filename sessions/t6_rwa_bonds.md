# Tópico 6 — Títulos tokenizados / RWA  ·  slug `t6_rwa`

## Por que
O usuário ampliou o escopo para "outros stables, BTC e títulos" com saída pela OKX (pares BRL). Ainda
não há nada medido em títulos. A tese: um token com NAV conhecido (T-bills, títulos públicos,
renda fixa BR) negociando em DEX abaixo/acima do NAV, com saída em USDC/USDT → OKX `USDC-BRL`/`USDT-BRL`.

## Restrições já conhecidas (v1/v2, `research.md`/`research_v2.md`)
- BUIDL e fundos registrados de mínimo baixo (BENJI, WTGXX, Spiko) foram excluídos: sem saída para
  nós / mercado secundário raso. USYC raso (~$4–9k). **USDY** acumula (~$1,14, sem par em $1); o
  mercado real dele é a Solana (~$2,9M em 18/set); resgate nativo em USDC foi refutado.
- OUSG: caminho sem gate de $5k foi refutado. Spreads de treasuries tokenizados "<35 bps" foi refutado.
- **TESOURO** (pool Curve "DFB BRL Pool v1" na Polygon, rate ~1,2728) é do ecossistema BRZ (congelado)
  → tratar com risco de emissor; perguntas à DFB em `PONTOS_DE_ATENCAO.md §3.4`.

## Perguntas
1. **Mapa 2026** (pesquisa de mesa, fontes primárias + rwa.xyz/DefiLlama): quais tokens de títulos
   têm (a) NAV publicado com frequência (on-chain via oráculo ou site do emissor), (b) pool DEX com
   profundidade ≥ ~$500k, (c) mint/resgate acessível ou ao menos secundário fundo. Candidatos:
   USDY, OUSG, USTB (Superstate), USYC, BUIDL-derivados, sDAI/sUSDS e outros "savings" (não são títulos
   mas são NAV-crescente), syrupUSDC, e **títulos brasileiros tokenizados** (Liqi, Vórtx, Tesouro
   tokenizado/Drex, etc.).
2. Para os 2–4 melhores: cotação executável no tamanho vs NAV do mesmo bloco. Medir a diferença
   (prêmio/desconto) em bps, histórico de 14 dias com passo grosso (Alchemy só para o archive).
3. O desconto é capturável? Precisa de resgate (prazo, mínimo, KYC) ou dá para sair pelo próprio
   pool depois? Comparar com o custo de carregar o título (yield ganho enquanto espera) —
   em títulos, "comprar com desconto e carregar até o resgate" pode ser o trade, não o atômico.
4. Algum desses tem par direto ou caminho curto até a OKX `USDC-BRL`/`USDT-BRL`?

## Saída esperada
`topics/t6_rwa/REPORT.md`: tabela de candidatos (NAV, venue, profundidade, prêmio/desconto p50/p95,
caminho de saída, prazo), os excluídos com motivo, e 1–2 recomendações para medir com coletor.
