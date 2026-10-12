# T6 — Títulos tokenizados / RWA × NAV · REPORT (2026-10-11)

**Resumo:**
- **Não há oportunidade em títulos tokenizados no tamanho que nos interessa.**
- Os tokens dos EUA que se transferem livremente (syrupUSDC/USDT, USDY, sfrxUSD, sUSDS/sDAI, scrvUSD, cUSDO) negociam em DEX **ancorados no NAV**:
  - Na compra, o preço fica ≈ NAV: ganho de 0 a +2 bps nas venues fundas.
  - Na venda, sai de −0,5 a −35 bps abaixo do NAV. Esse é o custo de sair sem resgatar.
- Os fundos de T-bill de verdade (USTB, USYC, OUSG, TBILL, BUIDL, BENJI, Spiko…) não têm DEX, porque o token é permissionado.
- **TESOURO (Etherfuse) é o único caso com desvio real**:
  - O pool Curve da DFB na Polygon paga **+22 bps (p50) / +64 bps (p95) acima do NAV em BRL** para quem vende TESOURO→BRLA.
  - Mas só cabe **~R$10–15k por vez** (o pool tem ~43k BRLA).
  - Para capturar, é preciso emitir TESOURO na Etherfuse em BRL, e o trilho BRL deles ainda está como "upcoming".
  - Pelo caminho via USDC/OKX, o ganho desaparece: **−18 bps hoje, já com o melhor preço**.
- **Veredito:** não é oportunidade para os EUA. Para o TESOURO, **depende de X** (trilho BRL da Etherfuse + conta KYC), e mesmo assim o teto é de ~R$50–100 por episódio.

---

## 1. Pergunta e hipótese
Um token com NAV conhecido (T-bills, títulos BR, "savings" crescentes) negociando em DEX abaixo/acima do NAV,
com saída em USDC/USDT → OKX `USDC-BRL`/`USDT-BRL`. Variantes: (a) atômica (comprar abaixo do NAV e resgatar/
vender), (b) **carregar**: comprar com desconto e manter até o resgate, ganhando o yield.

## 2. Fontes e o que foi verificado
Detalhes completos em `desk_research_us.md` e `desk_research_br.md`.

**Verificado (fonte primária ou leitura on-chain própria):**
- **NAVs on-chain** (`nav.py`, Ethereum):
  - syrupUSDC `convertToExitAssets` = 1,18756
  - syrupUSDT = 1,14755
  - USDY `RWADynamicOracle.getPrice()` = 1,14924
  - sfrxUSD 1,21496 · sUSDS 1,11249 · sDAI 1,18162 · scrvUSD 1,10956 · cUSDO 1,06338 · USTB oráculo 11,2423
- **Permissionamento:**
  - USTB/USCC exigem allowlist dos dois lados (docs Superstate).
  - USYC usa contrato de Entitlements; OUSG é só para QP; TBILL usa whitelist.
  - BUIDL/BENJI/WTGXX/Spiko são permissionados.
- **TESOURO:**
  - O emissor é a **Etherfuse**, não a Transfero nem a DFB.
  - Endereços por chain e supply total de 2,22M tokens (≈R$2,81M) vêm da API pública da Etherfuse.
  - O NAV vem de `api.etherfuse.com/lookup/tokens/cost/TESOURO`: **R$1,265419**, taxa 11,28% a.a., FX deles 4,9858.
  - O pool Curve usa o oráculo `0xc1df…c4f2` ("DFB TESOURO/BRZ", ~13 min por round, não monotônico), que lia **1,274327 = +70 bps sobre o NAV**.
  - No contrato da Polygon (OFT), não há blacklist.
  - Na Etherfuse, o trilho Pix/BRL aparece como "Upcoming" (docs/fees).

**Relatado (não verificado):**
- Mínimos e lockup de 40 dias do USDY.
- Prazo da fila de saque da Maple: normalmente < 24 h, até 30 d; o pior caso observado foi 7,1 d.
- Lastro do TESOURO em LTN.
- Termos de emissão/resgate da Etherfuse: 0% de taxa, sem mínimo.
- Piso atual do bUSD0.

**Inferência:** o oráculo da DFB ≈ NAV em USD da Etherfuse × USD/BRL "cripto". O FX implícito hoje é 5,021, contra 5,029 na OKX e 4,986 na Etherfuse. Isso explica por que o prêmio sobre o NAV em BRL acompanha o prêmio do BRL cripto.

## 3. Venues / pools

| Token | Chain · venue | Endereço / id | TVL | Profundidade útil (≤ 10 bps de custo) |
|---|---|---|---|---|
| syrupUSDC | ETH Uni v4 0,08% + Fluid | v4 `0xcdb422a8…0228`, Fluid `0x79eea4a1…ae29` | $3,8M | ≥ $100k (compra a +0,1 bps) |
| syrupUSDC | Solana Orca/AlphaQ/Manifest | `6fteKNvM…S613J` | $10,0M | ≥ $100k (−0,5 a −2 bps) |
| syrupUSDC | Base Uni v4 | token `0x6609…00f5` | $0,46M | ~$10k |
| syrupUSDT | ETH Uni v4 0,08% | `0xd861038a…8e1d` | $4,7M | ≥ $100k na compra |
| USDY | Solana Orca Whirlpool | mint `A1KLoBrK…Eto6` | $2,9M | $100k com spread de ~32 bps |
| USDY | ETH / Arbitrum | — | < $20k | nenhuma (cotações −170 a −9.900 bps) |
| sfrxUSD | ETH Curve sfrxUSD/frxUSD | — | $11,9M | ≥ $100k |
| scrvUSD | ETH Curve (vs reUSD/sDOLA) | — | $15,5M | ≥ $100k |
| cUSDO | ETH Curve cUSDO/USDC | — | $104k | ~$10k |
| bUSD0 | ETH Uni bUSD0/USD0 + Curve | `0xABfCA967…EcDa`, `0x1d08E7ad…Eec52` | $5,1M | ≥ $100k |
| **TESOURO** | **Polygon Curve "DFB BRL Pool v1"** | `0xc89f31f74573cc19fffc06108601c1ac71ba9735` | $137k (só 30,9k TESOURO / 42,9k BRLA) | **~R$10–15k** |
| TESOURO | Polygon Uni v4 TESOURO/USDC | — | $16k | ~$1k |
| TESOURO | Solana Orca TESOURO/USDC | `3bYZCXv6…nVpK` | $83k | inutilizável (venda −644 bps; compra sem rota) |

Os pools achados via GeckoTerminal (36 símbolos) estão em `gt_rwa_pools.json`.

## 4. Método
1. **Pesquisa de mesa:** 2 subagentes, cobrindo EUA/DeFi e Brasil.
2. **Descoberta de pools:** GeckoTerminal e DexScreener.
3. **Probe one-shot** (`probe.py`):
   - Cotação executável via **KyberSwap /routes** nas EVM (já inclui gás) e **Jupiter /quote** na Solana.
   - Comparada com o NAV on-chain do mesmo minuto, a $1k/$10k/$100k, nos dois sentidos.
   - Fórmulas: `buy = tokens·NAV/USD − 1`, `sell = USD/(tokens·NAV) − 1`, ambos líquidos de gás.
   - Duas rodadas com 11 min de intervalo; os resultados ficaram idênticos (±0,1 bps).
4. **TESOURO** (`tesouro_probe.py`):
   - Curve `get_dy` TESOURO↔BRLA contra o NAV da Etherfuse.
   - Kyber na Polygon e Jupiter na Solana.
   - Loop USDC→TESOURO→BRLA→BRL→USDC, saindo pela OKX `USDC-BRL` ask com taker de 2 bps.
   - Varredura de capacidade de R$1k a R$45k.
5. **Histórico TESOURO** (`tesouro_hist.py`):
   - 500 rounds do oráculo DFB (1 a cada 4), cobrindo **16,3 dias**, lidos via `getRoundData` em RPC público (sem archive).
   - O NAV em BRL foi reconstruído compondo para trás a 11,28% a.a. **Aproximação:** ignora a marcação a mercado do LTN.
   - FX oficial = ECB diário (frankfurter); FX da OKX = candles de 1 h.
6. **Backfill de syrup** (`syrup_backfill.py`, Alchemy archive):
   - 14 dias, passo de 1 h (336 blocos).
   - Mid dos pools Uni v4 syrupUSDC/USDC e syrupUSDT/USDT via `StateView.getSlot0`, contra `convertToExitAssets`. Também o oráculo do USDY.

## 5. Resultados

### 5.1 Probe one-shot, tokens EUA/DeFi (bps vs NAV, líquido de gás; + = a nosso favor)

| Token · chain | $1k compra / venda | $10k compra / venda | $100k compra / venda | Leitura |
|---|---|---|---|---|
| syrupUSDC · ETH | −0,3 / −10,7 | **+0,35** / −10,0 | +0,1 / −13,5 | compra = NAV; venda paga ~10 bps |
| syrupUSDC · Solana | +0,2 / −0,5 | +0,2 / −0,6 | +0,1 / −2,0 | livro mais justo de todos |
| syrupUSDC · Base | **+9,3** / −24,8 | **+5,1** / −25,7 | −5,2 / −35,4 | desconto pequeno, pool raso |
| syrupUSDT · ETH | −0,3 / −20,7 | +0,4 / −20,0 | +0,2 / −20,3 | idem |
| USDY · Solana | −21,4 / −10,7 | −21,7 / −11,0 | −24,9 / −14,3 | mid ≈ NAV +5 bps, spread ~32 bps |
| USDY · ETH / Arbitrum | — | — | — | sem liquidez |
| sfrxUSD · ETH | +1,2 / −5,4 | +1,8 / −6,1 | +0,05 / −6,6 | ancorado |
| sUSDS · ETH | −1,0 / −1,0 | −0,1 / −0,1 | 0,0 / 0,0 | controle: resgate instantâneo (o método fecha em 0) |
| sDAI · ETH | −1,0 / −0,2 | −0,1 / −0,05 | 0,0 / 0,0 | controle |
| scrvUSD · ETH | +4,6 / −8,8 | +5,6 / −7,9 | +5,5 / −7,7 | o "desconto" é crvUSD < $1; ida e volta −2 bps |
| cUSDO · ETH | +16,2 / −23,7 | +11,5 / −35,1 | −598 / −6.984 | saída só por resgate KYC ($100k, 10 bps) |
| bUSD0 · ETH (vs $1 nominal) | +289 / −286 | +289 / −285 | +280 / −293 | ver abaixo |

- **bUSD0:** o preço de 0,971 até o vencimento em 2028-06-11 rende ~1,7% a.a. Isso é desconto estrutural (lock), não erro de preço, e fica abaixo do T-bill: o NAV do USDY subiu 3,72% a.a. nos últimos 14 dias.

### 5.2 Backfill de 14 dias (passo de 1 h): mid do Uni v4 vs NAV

| Pool | n | p05 | p50 | p95 | máx | % com edge de compra (mid < −8 bps = taxa LP) | edge de compra máximo |
|---|---|---|---|---|---|---|---|
| syrupUSDC/USDC | 336 | −10,4 | −9,1 | −1,0 | +0,1 | 55% | **~+2,7 bps** |
| syrupUSDT/USDT | 336 | −10,7 | −10,2 | −9,7 | −9,5 | 100% | **~+3,3 bps** |

**Leitura:**
- O pool fica estacionado em "NAV − taxa − ~2 bps": quem compra paga ≈ NAV, quem vende paga a taxa.
- O ganho máximo de compra (~2–3 bps) só se realiza esperando a fila de saque da Maple (< 24 h típico, até 30 d) ou carregando a posição.
- Em nenhum ponto houve edge de venda.

### 5.3 TESOURO (Polygon Curve), probe 2026-10-11 ~23:00 UTC (NAV R$1,265419, oráculo DFB +70,4 bps)

**Venda TESOURO→BRLA no Curve, por tamanho (bps vs NAV em BRL):**

| R$1k | R$5k | R$10k | R$15k | R$20k | R$25k | R$30k | R$40k |
|---|---|---|---|---|---|---|---|
| +75 | +63 | +47 | +28 | +4,5 | −28 | −81 | −412 |

- **Compra BRLA→TESOURO no Curve:** −100 bps a R$5k; −2.331 bps a R$50k.
- **TESOURO→BRZ:** +170 bps a R$5k, mas o BRZ está **congelado** e no mercado vale ~1% abaixo. Fica em segundo plano, como manda o protocolo.
- **Polygon via Kyber (USDC↔TESOURO):** compra −19,5 / venda −21 bps a $1k; −178 / −78 bps a $10k; $100k inviável.
- **Solana Orca:** venda −644 bps; sem rota de compra.
- **Loop USDC→TESOURO (Kyber Polygon)→BRLA (Curve)→BRL→USDC (OKX ask, 2 bps):** **−45 bps a $1k**, −1.714 bps a $10k.

**Histórico de 16,3 dias (500 rounds do oráculo DFB):**

| Série | p05 | p50 | p95 | % > 0 |
|---|---|---|---|---|
| Prêmio DFB vs NAV em BRL (= edge de venda no Curve antes do slippage, ~8 bps a R$5k) | +2 | **+22** | **+64** | 97% |
| OKX USDC-BRL vs ECB | −12 | +37 | +94 | 90% |
| Loop via USDC (emissão na Etherfuse a NAV → Curve → OKX) | −69 | −16 | +39 | 36% |

- O loop via USDC usa o FX oficial **diário** do ECB contra a OKX **horária**. É ruído, não edge. Com o FX ao vivo da própria Etherfuse, o loop de hoje dá **−18 bps** antes do slippage.
- As medianas diárias do prêmio subiram de +12 (25/set) para +62 (11/out), acompanhando o BRL cripto mais fraco.

## 6. Conclusão
- **EUA/DeFi: não é oportunidade.**
  - Onde o token é livre e o pool é fundo, o lado comprador já está em NAV (0 a +3 bps). Quem fixa isso é o próprio mint/depósito a NAV.
  - O "desconto" que aparece é só o custo de quem vende sem querer esperar o resgate. Capturá-lo exige ficar na fila de saque (syrup) ou no resgate KYC (cUSDO), por +2 a +15 bps em ≤ $10k.
  - Para inventário "carregado", o syrupUSDC é no máximo um **lugar para estacionar USDC ocioso** (yield + ~2 bps de entrada). Isso não é arbitragem, e tem risco de crédito da Maple e risco de fila.
  - **USDY:** o mercado real é a Solana, mas com spread de ~32 bps em torno de NAV +5. Não há desvio a capturar.
- **TESOURO: depende de X.** O pool Curve paga sistematicamente acima do NAV em BRL (p50 +22, p95 +64 bps). O trade (emitir TESOURO a NAV em BRL → vender no Curve por BRLA → BRLA→BRL na Avenia) depende de:
  1. **Conta KYC na Etherfuse com trilho Pix/BRL ativo** (hoje "upcoming").
  2. Capacidade de **~R$10–15k por episódio** (BRLA no pool = 42,9k), ou seja, **~R$30–70 de lucro por vez**, até alguém reabastecer o BRLA.
  3. Risco de emissor/DFB: oráculo não verificado e controlado pela DFB; pool do ecossistema BRZ.

  Pelo caminho que existe hoje (USDC), o ganho se anula pelo FX da OKX: −18 a −45 bps. **Não justifica capital agora.**
- **Caminho até a OKX BRL:**
  - Todos os tokens EUA saem em USDC/USDT, depois `USDC-BRL`/`USDT-BRL` (genérico, sem ganho específico).
  - O TESOURO sai em BRLA (Curve). Para chegar à OKX, BRLA→USDC (Uni v3 Polygon) ou BRL via Avenia.
- **Excluídos e motivo:**
  - Sem DEX por serem permissionados: USTB, USCC, USYC, OUSG, TBILL, BUIDL, BENJI/iBENJI, WTGXX, Spiko.
  - Sem profundidade: mTBILL (só pool Etherlink sem volume), bIB01, deJTRSY/deJAAA.
  - Sem liquidez na chain: USDY na ETH/Arbitrum.
  - Desconto de lock, não NAV: bUSD0.
  - Controles (resgate instantâneo zera o desvio): sUSDS/sDAI.
  - Mortos ou avariados: USDM, deUSD, USR, USDz.
  - Raso (~$29k): BRLY/BRLV (Crown, Base).
  - Custodiais: MB RFD, Liqi, Vórtx QR. Drex parado.
  - Fora de BRL: CETES.

**Recomendações de coletor** (só se a resposta da pergunta 1 abaixo for positiva):
1. **Coletor TESOURO** (só público, sem Alchemy), a cada 10 min:
   - NAV/FX da Etherfuse (API)
   - oráculo DFB
   - Curve `get_dy` TESOURO→BRLA a R$5k/10k/15k e saldos do pool
   - OKX `USDC-BRL`

   Mede o prêmio executável real, quanto dura e quão rápido o BRLA é reposto.
2. Nenhum coletor para os tokens EUA. Se quiserem estacionar USDC em syrupUSDC, basta um alerta simples para quando o mid do v4 ficar < NAV −12 bps (nunca aconteceu nos 14 dias).

## 7. Perguntas para o usuário / terceiros
1. **Etherfuse:**
   - Vocês conseguem conta KYB?
   - Quando o trilho BRL/Pix entra no ar? Quais são taxa e prazo de emissão/resgate de TESOURO em BRL e em USDC?
   - Dá para resgatar a NAV na Polygon? Qual o mínimo?
   - O lastro é LTN ou LFT?
2. **DFB (complementa `PONTOS_DE_ATENCAO §3.4`):**
   - Qual é a fórmula do oráculo `0xc1df…c4f2` (usa USD/BRL cripto?) e quem o atualiza?
   - Eles reabastecem BRLA no pool?
   - Existe pool TESOURO/BRLA ou TESOURO/USDC maior em Base/Gnosis?
3. **Avenia:** BRLA→BRL continua 1:1 sem taxa para os volumes de R$10–15k? Isso fecha o loop BRL.
4. Interesse em **syrupUSDC como caixa remunerado** do inventário (não é arb)? Se sim, avaliar risco de crédito da Maple e o prazo de fila à parte.

## 8. Requisições Alchemy usadas
**338** (`syrup_backfill.py`: 3 no teste + 335 no backfill; 1 multicall por bloco). Todo o resto foi público:
- RPC público (Ethereum/Polygon)
- KyberSwap, Jupiter lite (≤ 0,45 req/s)
- GeckoTerminal (≤ 17 req/min)
- DexScreener, Etherfuse, OKX

## 9. Arquivos criados e o que ficou rodando
`topics/t6_rwa/`:
- `REPORT.md` (este arquivo)
- **Pesquisa de mesa:** `desk_research_us.md`, `desk_research_br.md`
- **Descoberta:** `gt_discover.py` → `gt_rwa_pools.json`
- **Probes:**
  - `nav.py`: leitores de NAV on-chain
  - `probe.py` → `probe_2026-10-11T200137.json`, `probe_2026-10-11T201231.json`
  - `tesouro_probe.py` → `tesouro_probe_2026-10-11T200530.json`
- **Históricos e backfill:**
  - `tesouro_hist.py` → `tesouro_hist.json`
  - `syrup_backfill.py` → `syrup_backfill_cache.json`, `syrup_backfill_summary.json`

**Nada ficou rodando.** Nenhum coletor foi iniciado. Os processos python ativos na máquina são de outras sessões.
