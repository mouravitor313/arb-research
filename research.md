# Arbitragem de Stablecoins & Ativos Tokenizados — Visão Geral da Pesquisa

**Escopo:** LatAm, China, Europa. Trader operando **$10k–$100k**, precisa conseguir **sair para USD/USDC em uma CEX grande** com suporte real de saque.
**Classes de ativos:** (1) stablecoins regionais atreladas a moeda fiduciária, (2) stables USD entre venues, (3) títulos tokenizados/RWAs, (4) stables com rendimento.
**Data:** 17/09/2026 · **Método:** harness de deep-research (5 ângulos de busca → 25 fontes → 100 afirmações → 25 verificadas adversarialmente, 19 confirmadas / 6 descartadas).

> ⚠️ **Leia isso primeiro.** O resultado mais forte e mais relevante para decisão desta pesquisa é *negativo*: **nenhuma afirmação verificada confirma positivamente um caminho funcional de saque para USD/USDC em CEX grande, ou liquidez executável ao vivo, para qualquer uma das stablecoins regionais atreladas a moedas fiduciárias (MXNe, cCOP).** O caminho realista para dólares é um *swap FX on-chain para USDC*, depois sacar USDC em uma CEX — não uma listagem nativa do token atrelado em CEX. Tudo abaixo é classificado por confiança e carrega um **status de verificação** para sabermos o que provar antes de operar.

---

## 1. Resumo executivo

- **Stablecoins regionais atreladas a moedas fiduciárias são reais on-chain, mas fracamente conectadas a CEXes.** MXNe (MXN) e cCOP (COP) existem e fazem swap para USDC/USDT on-chain a taxas FX, mas nenhuma tem uma saída documentada para USD em CEX grande. Trate o token atrelado como um instrumento *on-chain*; a saída em USD é USDC após um swap FX. **[confiança alta]**
- **Arbitragem *primária* de stables USD (mint/redeem a $1) está efetivamente fechada para essa faixa de capital no Tether** (resgate mínimo de $100k, taxa = o maior entre $1.000 ou 0,1%, ~6 resgatadores ativos/mês) e muito mais aberta na Circle/USDC (~521 resgatadores). Então arb de stables USD aqui = **spreads secundários / entre venues**, não resgate primário. **[alta]**
- **Títulos do tesouro tokenizados institucionais são inacessíveis.** BUIDL: mínimo de $5M, somente para compradores qualificados, ATS com KYC e carteiras permissionadas — **não pode** ser liquidado em CEX/DEX aberta. **[alta]**
- **Títulos do tesouro tokenizados viáveis para varejo com saída real on-chain para USD existem:** OUSG (mint/redeem atômico 24/7 para USDC, mas restrito a QP), USDY (acumulativo, saída via AMMs secundários — Curve/Aerodrome/Solana), USYC (resgate T+0 para USDC). Fundos registrados com mínimo baixo (BENJI $20, WTGXX $1, Spiko USTBL $1) existem, mas têm liquidez secundária aberta escassa. **[alta]**
- **RMB/CNH é um beco sem saída.** A proibição da China de fev. 2026 pelo PBOC + 7 agências cobre CNY onshore *e* CNH offshore, emissores nacionais e estrangeiros; o único token CNH notável (CNHC) está extinto. **Nenhum instrumento de arb CNH viável/legal com saída em CEX existe.** **[alta]**
- **Stables EUR são reguladas pelo MiCA.** Desde o Título V do MiCA (30 dez 2024), CASPs do EEE só podem oferecer EMTs autorizados; moedas não autorizadas (ex: USDT) foram deslistadas para usuários do EEE. Para saída em CEX do EEE, prefira **EMTs autorizados (EURC, EURe/Monerium, etc.)**. **[alta]**

**Conclusão para alocação de capital:** os setups mais limpos e defensáveis para $10k–$100k são (a) **spreads de stables USD entre venues / entre chains** e (b) **desvio de NAV de stables com rendimento (sUSDe, USDY, USYC)** — *ambos liquidam nativamente para USDC em CEXes grandes.* As stablecoins regionais de FX são interessantes, mas exigem que primeiro provemos um caminho real de saída (ver Fila de Verificação).

---

## 2. Achados por classe de ativo

### 2.1 Stablecoins regionais atreladas a moeda fiduciária

| Token | Paridade | Emissor | Chains | Venue on-chain | Saída USD em CEX? | Verificado? |
|---|---|---|---|---|---|---|
| **MXNe** | MXN | Brale / Etherfuse ("Real MXN", lastreado por CETES Stablebonds) | Stellar, Solana, Base (desde mar. 2025) | Brale, **Stabull DEX** | ❌ Nenhuma documentada → swap FX on-chain para USDC | ✅ alta |
| **cCOP** (antigo COPm) | COP | Mento Labs / Celo Colombia DAO | Celo | **Mento Asset Exchange** (swap para USDT/USDC a taxa FX) | ❌ Nenhuma documentada → swap FX on-chain para USDC | ✅ alta |
| BRLA, BRZ, cREAL (BRL) | BRL | Diversos | Multi | — | ⚠️ **Não verificado** — precisa de checagem ao vivo | ❓ não verificado |
| MMXN, MXNT (MXN) | MXN | Diversos | Multi | — | ⚠️ **Não verificado** | ❓ não verificado |
| ARS/COP outros | — | — | — | — | ⚠️ **Não verificado** | ❓ não verificado |

**Padrão de arb:** FX vs preço on-chain (token atrelado negocia fora de sua taxa FX real em fiat) e deslocamento de paridade. **Realidade da saída:** token atrelado → USDC on-chain (Stabull / Mento) → sacar USDC na CEX. O token atrelado em si *não* é considerado sacável via CEX.

> BRL é o mercado de stablecoins fiduciárias LatAm mais líquido na prática (BRLA, BRZ), mas a pesquisa **não** verificou listagens atuais em CEXes ou profundidade — isso é um item de verificação prioritário, não um setup confirmado.

### 2.2 Stables USD — entre venues

- **Resgate primário não é a jogada** para este tamanho (barreira do Tether acima). USDC primário é aberto, mas a arb primária é competitiva/institucional.
- **A jogada são spreads secundários entre venues / entre chains** de USDC, USDT, USDe, DAI/USDS, FDUSD entre DEXes e CEXes.
- ⚠️ A estatística principal de que stablecoins desviam de $1 uma grande fração do tempo (o número de "27–41% desconto / 57–72% prêmio") foi **REFUTADA (0-3)**. Precisamos **medir frequência e magnitude do deslocamento nós mesmos** antes de dimensionar — não assuma janelas frequentes.
- **Liquidação:** todos estes liquidam nativamente para USD/USDC em CEXes grandes (Binance, Coinbase, Kraken, OKX, Bybit). CCTP v2 permite USDC nativo entre chains, reduzindo fricção de bridge.

### 2.3 Títulos tokenizados / RWAs

| Token | Emissor | Mín | Acesso | Saída USD | Liquidável em CEX? | Verificado |
|---|---|---|---|---|---|---|
| **BUIDL** | BlackRock/Securitize | $5M | Somente QP, ATS permissionado, carteiras KYC | T+0 USDC / T+1 transferência bancária **somente para whitelisted** | ❌ **NÃO** — não negociável para nós | ✅ alta |
| **OUSG** | Ondo | $5k tx instantânea | Restrito a acreditados/QP | Mint/redeem atômico 24/7 para USDC (Ethereum) | ⚠️ On-chain USDC sim; restrito | ✅ alta |
| **USDY** | Ondo | ~$500 app (mint/redeem direto $100k) | **Pessoas não-EUA**, lockup de 40 dias | AMMs secundários: Curve, Aerodrome, DEXs Solana (~$12–15M de profundidade em pool USDC) | ⚠️ Via DEX→USDC→CEX | ✅ alta |
| **USYC** | Circle | — | Perfil institucional | Resgate T+0 para USDC (~$3B AUM) | ⚠️ On-chain USDC | ✅ alta |
| **BENJI** | Franklin Templeton | $20 | Varejo EUA (limitado por estado) | App Benji | ❌ liquidez secundária escassa | ✅ (2-1) |
| **WTGXX** | WisdomTree | $1 | MMF registrado | — | ❌ liquidez secundária escassa | ✅ (2-1) |
| **Spiko USTBL** | Spiko (EU UCITS) | $1 | Varejo EU | — | ❌ liquidez secundária escassa | ✅ (2-1) |

**Padrão de arb:** Desvio de NAV/rendimento vs preço no mercado secundário (tokens acumulativos como USDY sobem previsivelmente; descontos em AMMs secundários = oportunidade de comprar e resgatar/manter). **Ressalva:** a afirmação de que "spreads uniformemente <35 bps" foi **REFUTADA** — trate os limites de spread como desconhecidos, meça ao vivo.

### 2.4 Stables com rendimento

- **USDe / sUSDe (Ethena):** USDe mantém ~$1 (hedge delta-neutro + mint/redeem permissionless); **todo o rendimento acumula no sUSDe via taxa de câmbio crescente** (modelo de taxa de resgate, não rebase). Desvio previsível da taxa de câmbio = sinal de arb.
  - ⚠️ A afirmação de um **cooldown de 7 dias para sUSDe→USDe foi REFUTADA (0-3)** — não assuma essa restrição; verifique as mecânicas atuais de resgate ao vivo.
- **USDY, USYC:** cobertos acima (desvio de NAV acumulativo).
- **sDAI / sUSDS (Sky/Maker):** acúmulo via taxa de poupança — padrão de desvio de NAV padrão (não verificado separadamente aqui; adicionar à fila de verificação).
- **Liquidação:** USDe, sUSDe estão listados em CEXes grandes e liquidam para USDC — saídas limpas.

---

## 3. Restrições regionais / regulatórias

- **China / RMB — NÃO VIÁVEL.** Notificação Nº 42 [2026], 06/02/2026: PBOC + NDRC, MIIT, MPS, SAMR, NFRA, CSRC, SAFE proíbem stablecoins atreladas ao RMB não aprovadas e RWAs tokenizados por emissores nacionais *e* estrangeiros; cobre CNY onshore e CNH offshore. CNHC extinto; Hong Kong não aprovou nenhum; Ant/JD arquivaram planos. **Excluir inteiramente.**
- **Europa / MiCA.** Título V totalmente aplicável em 30 dez 2024. CASPs do EEE só podem oferecer EMTs autorizados ao público. Pares spot de USDT deslistados para usuários do EEE na Coinbase, Binance, Kraken, Crypto.com (dez 2024–mar 2025). Para saída em CEX do EEE, **use EMTs autorizados (EURC, EURe/Monerium e outros emissores autorizados)**; confirme a autorização de cada emissor + listagem atual em CEX do EEE (item de verificação).
- **LatAm.** Nenhum regime único bloqueante; fricção de KYC e off-ramp por país. A restrição vinculante é *liquidez do venue + saída em CEX*, não legalidade.

---

## 4. Stack de rastreamento de preços & monitoramento

- **Preços/livros de ordens de CEXes:** API unificada **CCXT** (REST + WebSocket: `watchOrderBook`, `watchTicker`, `watchTrades`, `watchOHLCV`, autenticado `watchBalance/watchOrders/watchMyTrades`). Uma toolchain para todas as CEXes grandes — isso é a espinha dorsal para detecção de spreads entre venues.
- **Cotações de DEXes:** 1inch, Jupiter (Solana), cotações do agregador CoW Swap para preço realista executável incl. slippage.
- **Dados on-chain / pools:** DefiLlama (TVL, dashboards de stablecoins), GeckoTerminal DEX API (preços/profundidade de pool por par).
- **USDC cross-chain:** Circle **CCTP v2** (USDC nativo em 13+ chains) para minimizar fricção de bridge nas saídas.

---

## 5. Lista priorizada (mais → menos negociável para $10k–$100k)

1. **Spreads de stables USD entre venues / entre chains** (USDC/USDT/USDe/DAI-USDS/FDUSD). Liquidação limpa em CEX. *Precisa primeiro medir frequência real de deslocamento* — a afirmação de "janelas frequentes" foi refutada. **Começar rastreamento imediatamente.**
2. **Desvio de NAV/taxa de câmbio do sUSDe** (Ethena). Previsível, listado em CEX, liquidável em USDC. Verificar mecânicas atuais de resgate.
3. **Resgate T+0 USYC para USDC** e **captura de desconto do USDY em AMMs secundários** (Curve/Aerodrome/Solana). Saída on-chain em USDC; verificar profundidade de pool ao vivo & slippage no nosso tamanho.
4. **Stablecoins regionais FX — MXNe (Stabull), cCOP (Mento)** como jogadas *on-chain* de FX vs preço, saída em USDC. **Somente após** provarmos liquidez executável + um round-trip real USDC→CEX. Prioridade menor.
5. **Stablecoins BRL (BRLA/BRZ)** — potencialmente o mercado LatAm mais líquido, mas **não verificado**; promover somente após checagem ao vivo de listagem/profundidade em CEX.

**Explicitamente excluídos:** BUIDL (não liquidável para nós), todos os tokens RMB/CNH (banidos/extintos), fundos registrados de mínimo baixo (BENJI/WTGXX/Spiko — liquidez secundária aberta escassa).

---

## 6. Fila de verificação (provar antes de operar)

Estas são questões em aberto que a pesquisa **não** conseguiu fechar — resolver cada uma antes de alocar capital:

1. **Stablecoins regionais:** $10k–$100k conseguem de fato fazer round-trip MXNe/cCOP → USDC → *saque nomeado em CEX*? Medir profundidade e slippage no Stabull / Mento; confirmar a perna USDC→CEX.
2. **Profundidade de DEX ao vivo:** Pool exato (par, chain, TVL, slippage no nosso tamanho) para USDY (Curve/Aerodrome/Solana), sUSDe, USYC — na data da operação.
3. **Stables EUR:** Quais dentre EURC, EURe/Monerium, EURt, agEUR/EURA, stEUR atualmente possuem autorização MiCA *e* permanecem em CEXes acessíveis no EEE com saída real para USD/USDC? Onde ocorrem spreads recorrentes de stables EUR?
4. **Realidade do deslocamento:** Medir empiricamente frequência + magnitude de deslocamentos de paridade secundários para USDC/USDT/USDe/DAI-USDS/FDUSD entre DEXes/CEXes (estatística principal foi refutada) — supera as taxas no nosso tamanho?
5. **Mercado BRL:** Confirmar listagens atuais em CEXes + profundidade para BRLA, BRZ.

---

## 7. Afirmações refutadas (NÃO confiar)

- Stablecoins desviam de $1 "27–41% / 57–72%" do tempo — **refutada 0-3**.
- **Cooldown de 7 dias** sUSDe→USDe — **refutada 0-3**.
- OUSG oferece um caminho limpo primário de USDC por $5.000 sem restrições para pequenos traders — **refutada 0-3**.
- OUSG mín $100k / NAV constante de $1 em 5 chains nomeadas — **refutada 0-3**.
- Spreads de títulos tokenizados uniformemente "<35 bps" — **refutada 0-3**.
- Dicotomia limpa de saída BUIDL-transferência bancária vs OUSG-USDC — **refutada 1-2**.

---

## 8. Confiança & ressalvas

Fatos regulatórios e de emissores primários são **fortes** (paper BFI/NBER, docs Tether/Circle/Ondo/BlackRock, Bloomberg, Biblioteca do Congresso dos EUA, ESMA/MiCA). **Números de profundidade de liquidez e rendimento vêm de fontes agregadoras/blogs secundárias** (eco.com, on-chain-finance.com, financefeeds.com) e um achado se baseia em voto 2-1 — trate todos os números de profundidade/rendimento como *indicativos, verificar ao vivo*. Este é um cenário 2025–2026 em rápida evolução (proibição da China fev. 2026; aplicação do MiCA 2024–2025); profundidades de pool, rendimentos, deploys em chains e listagens mudam mensalmente. **Re-verificar antes de cada alocação.**

### Fontes principais
- BFI/UChicago WP 2025-76 (NBER w33882) — *Stablecoin Runs and the Centralization of Arbitrage*
- Página do emissor Brale MXNe · Post de lançamento do Mento cCOP
- Docs Ondo (OUSG/USDY), Circle (USYC, CCTP v2), BlackRock/Securitize (BUIDL)
- Mecanismo Ethena sUSDe/USDe · Docs WebSocket CCXT · GeckoTerminal DEX API
- Notificação da China Nº 42 [2026] (via Cointelegraph/Bloomberg/LoC) · Análise Scorechain MiCA
