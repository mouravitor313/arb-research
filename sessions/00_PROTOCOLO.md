# Protocolo das sessões por tópico

> Cada tópico roda numa sessão própria e longa do Claude Code, em paralelo com as outras.
> Para abrir uma: num terminal novo, `cd C:\Users\Pedro\Projetos\arb; claude` e digite
> **"Leia sessions/00_PROTOCOLO.md e sessions/<arquivo-do-tópico>.md e execute."**

## Contexto mínimo (não precisa reler o repo inteiro)
- Objetivo v3: arbitragem DEX on-chain com entrada/saída em **BRLA/BRL1** e/ou **OKX** (VIP 9).
  Taxas OKX: pares BRL maker −1,5 / taker 2 bps; não-BRL maker 2,5 / taker 11 bps. **Sempre fechar
  pelos pares BRL na OKX** (vale 5–7 bps por operação).
- Faixas de tamanho: $1k / $10k / $100k. Modelo de inventário pré-posicionado (como o `xend-arb`):
  sem custo de transferência no trade, mas o custo/prazo de rebalanceamento entra na conclusão.
- Já medido e fechado (não refazer): ciclo atômico Polygon USDC→BRLA→BRZ→USDT0→USDC (`RECAP.md §9`);
  triângulos OKX, cbBTC, ETH, USDC/USDT (`RECAP.md §10`). BRZ está **congelado** (resgate Transfero
  travado): rota que dependa de resgatar BRZ fica em segundo plano.
- Reutilizar código existente: `chains.py` (configs EVM + `rpc_list`/`alchemy_url`), `xvenue_collector.py`
  (livros OKX + QuoterV2/V4Quoter via multicall), `cycle_common.py` (Curve `get_dy`, multicall, bloco fixo),
  `xvenue_backfill.py`/`cycle_backfill.py` (backfill archive). Dados medidos: `RECAP.md §3–4, §9–10`.

## Regras
1. **Só leitura.** Nada de assinar/enviar tx, chave privada ou ordem. **Nunca abrir/imprimir `.env`**
   (nem `cat`, nem `Read`). A chave da Alchemy está no `.env` da raiz e é carregada sozinha ao importar
   `chains.py` (`import chains` → `chains.alchemy_url("gnosis")`). O `.env` do `xend-arb` não se lê nunca.
2. **Isolamento entre sessões paralelas:** escrever só dentro de `topics/<slug>/` (scripts, `data.db`
   próprio, JSONs, logs, `REPORT.md`). **Não editar** `PROJECT.md`, `RECAP.md`, `PONTOS_DE_ATENCAO.md`,
   `chains.py`, nem o `arb_tracker.db`. Config de chain/token nova fica local no tópico (importe
   `chains.py` só para ler). A consolidação nos arquivos centrais é feita depois, numa sessão à parte.
3. **Não commitar** (o usuário commita quando quiser).
4. **Orçamento de RPC pago (Alchemy, `RPC_API_KEY` no `.env`):**
   - Padrão = RPC público (`rpc_list(chain)`). Alchemy só com opt-in explícito (`rpc_list(chain, paid=True)`
     ou flag `--paid`) para o que o público não serve: archive/backfill, Arbitrum archive, Transfers API
     (`alchemy_getAssetTransfers`), Token/Prices API quando poupar muito trabalho.
   - Agrupar em multicall, fixar bloco, cachear em disco, backfill com passo grosso (ex.: 30–60 min)
     antes de refinar. Nunca fazer polling ao vivo pela Alchemy.
   - **Teto por sessão: ~5.000 requisições pagas** sem perguntar. Contar e registrar no `REPORT.md`.
     Passar disso = perguntar ao usuário antes.
   - Nunca imprimir, logar ou gravar a URL da Alchemy (ela contém a chave).
5. **Rate limits compartilhados** (várias sessões + 2 coletores rodando): OKX público ≥ 5 s entre polls
   do mesmo livro; GeckoTerminal ≤ ~20 req/min; Jupiter lite ≤ 0,5 req/s.
6. **Coletores longos:** rodar destacado, com `.pid` e `-Stop`, no máximo ~24 h sem perguntar, e
   parar ao terminar. Anotar no relatório se ficou algum rodando.
7. **Cotação executável > último negócio.** GeckoTerminal/DexScreener servem só para achar pools;
   conclusão sempre com quoter on-chain (ou API de quote) no tamanho.

## Método padrão
1. **Pesquisa de mesa curta** (fontes primárias: docs do emissor/protocolo, APIs públicas). Separar
   o que foi verificado do que é só relatado.
2. **Descoberta** de pools/venues com profundidade real → `topics/<slug>/discovery.json`.
3. **Probe** one-shot a $1k/$10k/$100k nos dois sentidos, líquido de taxas e gás.
4. Se o probe mostrar algo perto de zero ou positivo: **backfill** (archive) e/ou **coletor ao vivo**
   para medir frequência, mediana, p95, duração dos episódios.
5. **Matar cedo:** se o probe e um backfill grosso derem tudo claramente negativo (ex.: p95 < −5 bps),
   registrar e encerrar. Resultado negativo bem medido também é resultado.

## Entregável: `topics/<slug>/REPORT.md` (PT-BR)
1. Pergunta e hipótese · 2. Fontes e o que foi verificado · 3. Venues/pools (endereço, chain, TVL,
profundidade no tamanho) · 4. Método · 5. Tabela de resultados (estratégia, tamanho, p50, p95, % > 0,
episódios) · 6. Conclusão: **oportunidade / não é / depende de X** · 7. Perguntas para o usuário ou
terceiros (emissor, OKX, DFB) · 8. Requisições Alchemy usadas · 9. Arquivos criados e o que ficou rodando.
