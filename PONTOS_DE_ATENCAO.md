# Pontos de atenção e pendências

> Lista viva de pontos a lembrar no futuro e de questões ainda sem resposta. Criada em 2026-10-10
> a partir do alinhamento v3 (ver `RECAP.md`). Quando um item for resolvido, marque `[x]`, coloque
> a data e diga onde a resposta foi registrada.

---

## 1. Escopo deste repo (confirmado 2026-10-10)

- **`arb` = só pesquisa + indexing.** Ele mede, indexa e encontra oportunidades. **Execução fica no
  `xend-arb`** (`C:\Users\Pedro\Projetos\xend-arb`). Nada de envio de ordem, assinatura de tx ou
  chave privada neste repo.

---

## 2. Pontos de atenção futuros

### BRZ congelado (informado pelo usuário em 2026-10-11)
- [ ] **A operação com BRZ (instância brz do `xend-arb`) está congelada** por problemas de saque com
  o emissor (**Transfero**). Sem resgate de BRZ→BRL, não dá para levar BRL para a OKX e fechar o ciclo
  de inventário. Até isso mudar, **qualquer rota que dependa de BRZ fica em segundo plano** (inclui o
  item B e a ponte BRLA↔BRZ). O pool Curve TESOURO/BRZ/stBRZ/BRLA também é do ecossistema BRZ: tratar
  stBRZ/TESOURO com o mesmo risco de emissor.

### Execução / `xend-arb` (propor lá, medir aqui)
- [ ] **Perna OKX como maker (post-only).** Pares BRL: maker −1,5 bps vs taker +2 bps → **+3,5 bps
  por trade** sobre uma edge típica de ~14–15 bps. Hoje o `src/cex/okx.py` só faz taker. Antes,
  medir taxa de fill e seleção adversa com o histórico `arb_opportunities`.
- [ ] **Nunca usar pares não-BRL na OKX** (taker 11 bps). Para trocar USDT↔USDC, passar por BRL
  (`USDT-BRL` + `USDC-BRL`: 4 bps taker / −3 bps maker) ou usar o pool USDC/USDT da Polygon (~$8M).
- [ ] **Ciclo de inventário (WP-23 do `xend-arb`) é o gargalo real**, não a edge. O fluxo sai quase
  todo em `buy_dex_sell_cex`, então BRL acumula na OKX. A Avenia (sem taxa, ≤10 min) fecha o ciclo;
  automatizar essa perna depende de existir API (ver §3).

### Atômico
- [ ] **Atomicidade só existe com todas as pernas on-chain, na mesma chain e na mesma tx.** Qualquer
  rota com perna na OKX nunca vira atômica.
- [ ] **O atômico complementa, não substitui.** A vantagem do time (Avenia 1:1 + BRL na OKX) não é
  usada por um bot atômico, que compete com searchers genéricos.
- [ ] **Escada de complexidade:** nível 1 = multi-hop no router Uniswap com `amountOutMinimum` (sem
  Solidity); nível 2 = contrato executor + flash loan (Foundry, revisão de segurança); nível 3 =
  MEV/backrun. Só subir de nível se a medição justificar.
- [ ] **Nível 1 em mempool público é sanduichável** → exigir RPC privado/protegido.
- [x] 2026-10-10 — **BRZ/BRLA 0.05% (`0x6e05…fb86`) é Uniswap v3** (factory oficial, `getPool` confere).
  Mas é raso (~$780 de BRLA) e se esgota a $1k. O pool TESOURO (`0xc89f…`) é **Curve stableswap-ng**
  (nível 2). Ver `RECAP.md §9.1`.
- [x] 2026-10-10 — **Ciclo B medido: fechado.** 0% das amostras com lucro líquido > 0 (14 dias de
  archive + ao vivo a 12 s). O melhor a $1k foi −3,2 bps. Ver `RECAP.md §9`.
- [ ] **Há um searcher atômico no ciclo BRL da Polygon** (EOAs vanity `0x4337…`, ~66% dos swaps
  nos pools BRL, txs multi-pool). Qualquer ideia atômica nesses pools compete com ele no mesmo bloco
  (nível 3). Vale checar se ele também opera Gnosis/Base antes de medir o item D.
- [x] 2026-10-11 — Coletor `cycle_collector.py` **parado** a pedido do usuário (ciclo B fechado). Antes rodava (pid em `cycle_collector.pid`; parar com
  `.\run_cycle_collector.ps1 -Stop`). Reanalisar após alguns dias com `python cycle_analyze.py`.

### Item 1 (BTC/ETH/SOL, USDC/USDT) — medido 2026-10-11
- [ ] **Na OKX, fechar sempre pelos pares BRL:** `BTC-BRL ÷ USDC-BRL` bate com o `BTC-USDC` (~0,5 bps),
  mas a taxa é 2+2 contra 11 bps. Isso vale 5–7 bps por operação em qualquer instância nova.
- [ ] **WBTC negocia 10–15 bps abaixo do BTC** (e o cbBTC fica no par). O desconto pode abrir mais
  em crise (FTX/2022: −150 a −200 bps) e há risco de custódia (BiT Global / Justin Sun). Se virar
  instância, limitar a exposição em WBTC não resgatado.
- [ ] Triângulos internos da OKX e a diferença USDC/USDT estão **fechados** (custo ≈ taxa). Monitorar
  só como secundário. O coletor `xvenue_collector.py` segue rodando (`.\run_xvenue_collector.ps1 -Stop`).
- [ ] `ETH-BRL` é raso (não absorve $100k); `BTC-BRL` aguenta $10k bem e $100k com impacto.

### Dados / medição
- [ ] **GeckoTerminal = último negócio, não cotação executável.** Desvios "persistentes" em pools de
  pouco volume (Base +54 bps, Gnosis Curve −20 bps) podem ser só preço velho. Validar sempre com
  quoter on-chain antes de tirar conclusão.
- [ ] **BRLA em Base/Gnosis:** se a Avenia emitir/resgatar nessas chains, cada pool vira só mais uma
  instância OKX↔DEX, sem precisar de bridge. Depende da pendência §3.1.
- [ ] **Pool USDC/USDT da Polygon é Uni v4** (fee 0,0008%, id `0xa37d…a399`) e hoje tem **~$477k**,
  não os ~$8M de 18/set (o volume de ~$6M/dia continua). O v3 0,01% só tem ~46k USDC. Para USDT0→USDC
  acima de ~$40k, rotear pelo v4 ou dividir. (Medido 2026-10-10.)
- [ ] **RPCs públicos:** publicnode não serve estado histórico e dá 403 sob carga; drpc serve archive
  (usado no backfill). Para rodar dias, preferir uma `POLYGON_RPC_URL` própria.
- [ ] Rate limit do GeckoTerminal (~30 req/min): espaçar polls com `--interval` / `dexPollDelayMs`.
- [ ] O config do scanner ainda usa **OKX 10 bps**. Trocar para a tabela VIP 9 (§4 do `RECAP.md`).

### BRL1
- [ ] **BRL1 na OKX só tem rede Polygon** (confirmado 2026-10-10). Como trilho de rebalanceamento
  (BRL@OKX → `BRL1-BRL` a 1:1 com rebate → saque na Polygon), ele chega na wallet como BRL1. **Mas
  on-chain o BRL1 não converte bem em BRLA/BRZ**: o pool BRL1/BRLA tem ~$167, e o único pool real
  é BRL1/USDT 0,3% (~$103k, volume baixo). Esse pool só compensa com desvio acima de ~34 bps.
- [ ] O triângulo interno OKX (BRL→USDT→BRL1→BRL) está **fechado** (≈ −12 bps a mercado, livro
  `BRL1-USDT` unilateral e com taxa não-BRL). Fora de escopo, salvo mudança no livro.

---

## 3. Pendências a clarificar (usuário vai confirmar)

- [ ] **3.1 Avenia multichain:** emite/resgata BRLA também em **Base e Gnosis**, com o mesmo prazo
  (≤10 min) e sem taxa? **Tem API** para automatizar mint/redeem?
- [ ] **3.2 BRL1:** quem é o emissor operacional, quais são os termos de mint/redeem (taxa, prazo,
  limites) e se há como abrir conta (há contatos).

- [ ] **3.4 DFB (contato interno):** a DFB gerencia os pools de BRZ, BRLA e TESOURO em alguns
  protocolos (inclui o Curve "DFB BRL Pool v1" `0xc89f…` na Polygon). Perguntar: (a) existe rota para
  **liquidar BRZ** enquanto o resgate na Transfero está travado (OTC, pool, recompra)? (b) quem emite o
  **TESOURO**, como funciona mint/resgate (prazo, taxa, mínimo, NAV; o pool usa rate ~1,2728) e se
  dá para arbitrar NAV × preço no Curve? (c) eles operam/rebalanceiam o pool Curve (A=2000 segura
  BRZ≈BRLA perto de 1:1, enquanto o mercado dá BRZ ~0,96% abaixo)? (d) planos de pools em Base/Gnosis.
- [ ] **3.5 BitGo / WBTC (item 1, `RECAP.md §10.3`):** a conta BitGo **não** dá direito a queimar
  WBTC; só merchants aprovados pela DAO podem. Pedir à **BitGo Prime** (que é merchant): fee de
  resgate em bps (custodiante + merchant), mínimo, prazo, e se aceitam WBTC vindo de Arbitrum ou
  só do Ethereum. **Ponto de equilíbrio medido: all-in ≤ ~4 bps.** Também confirmar com uma chamada
  autenticada se a OKX aceita depósito de WBTC (`GET /api/v5/asset/currencies?ccy=WBTC`); a OKX não
  tem mercado de WBTC.
- [ ] **3.3 Endereços das wallets dos bots do `xend-arb`** (brz e brla) para correlacionar com
  `cycle_pool_swaps.tx_from`. Ficam no `.env` de lá, que não deve ser lido.

### Respondidas
- [x] 2026-10-10 — **Redes OKX:** USDC tem as principais redes; **BRL1 só Polygon**.
- [x] 2026-10-10 — **Escopo:** este repo é só pesquisa e indexing; a execução fica no `xend-arb`.
- [x] 2026-10-10 — CEX atual = OKX; taxas VIP 9; Avenia sem taxa, ≤10 min; execução semi-automática;
  Polygon hoje, outras chains onde for viável; faixas de $10k/$100k mantidas. (Ver `RECAP.md §7`.)
