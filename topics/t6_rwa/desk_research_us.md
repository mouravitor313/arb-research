# Pesquisa de mesa — tokens de T-bills / NAV (EUA e DeFi) · 2026-10-11

Fonte: subagente de pesquisa web (docs dos emissores, Etherscan, rwa.xyz, DefiLlama, DexScreener).
V = verificado em fonte primária · DS = snapshot DexScreener (agregador, preço arredondado) · R = relatado/secundário.

## Tabela (ordem de aderência ao trade DEX × NAV)

| Token | Transferível livre? | NAV on-chain (eth_call) | Melhor profundidade DEX (DS) | AUM | Aderência |
|---|---|---|---|---|---|
| syrupUSDC (Maple) | Sim (R) | ETH `0x80ac24aA929eaF5013f6436cdA2a7ba190f5Cc0b` `convertToExitAssets`/`convertToAssets` (V) | Solana Orca/USDC $10,1M; ETH Uni v4/USDC $3,97M; Base Uni/USDC $0,46M | Maple TVL $2,85B (V) | **Alta** |
| USDY (Ondo) | Sim após lockup 40 d, não-EUA, blocklist (R) | ETH `RWADynamicOracle` `0xA0219AA5B31e65Bc920B5b6DFb8EdF0988121De0` `getPrice()` (V) | Solana Orca/USDC $2,9M; Sui Cetus $2,05M; Sei $1,01M; ETH Uni v4 só $19k | $2,32B (V) | **Alta** (fora da ETH) |
| sfrxUSD (Frax) | Sim | ERC-4626 ETH `0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6` (DS/R) | Curve/frxUSD $11,9M; quase nada direto vs USDC | — | Média (perna frxUSD→USDC) |
| sUSDe (Ethena) | Sim | ERC-4626 `0x9D39A5DE30e57443BfF2A8307A4256c8797A3497` (R); cooldown 7 d | ETH Uni/USDT $880k e $597k | USDe $4,76B | Média (fora do escopo v3, só referência) |
| bUSD0 / USD0++ (Usual) | Sim | Não é NAV: USD0 travado até 2028-06-11 + piso DAO de saída antecipada (R) | Uni bUSD0/USD0 $3,37M a 0,9717; Curve $1,75M a 0,9712 | Usual TVL $86,6M | Desconto estrutural, não mispricing |
| scrvUSD | Sim | ERC-4626 `0x0655977FEb2f289A4aB78af67BAB0d17aAb84367` | Curve/reUSD $15,4M; resto < $55k | — | Baixa |
| sUSDS (Sky) | Sim | ERC-4626 `0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD` | Uni/OHM $11,6M; Curve frxUSD $1,75M | USDS $7,10B | Baixa: resgate instantâneo + PSM 1:1 |
| sDAI | Sim | ERC-4626 `0x83F20F44975D03b1b09e64809B757c47f942BEeA` | Curve/FRAX $204k | — | Baixa |
| cUSDO (OpenEden) | Sim (V) | ERC-4626 `0xaD55aebc9b8c03FC43cd9f62260391c13c23e7c0` | Curve/USDC $102k; Base $27k | — | < $500k |
| USDtb / AUSD | Sim | stable $1 (não NAV) | Curve USDtb/USDC $20M a 0,9999; AUSD $34M | — | Só peg |
| USTB / USCC (Superstate) | **Não** — remetente e destinatário na allowlist (V) | Oráculo contínuo `0xe4fa682f94610ccd170680cc3b045d77d9e528a8` (V) | nenhum | USTB $598M | Não negociável em DEX |
| USYC (Circle) | Permissionado (Entitlements) (V) | Oráculo `0x74f2199AEb743f68f05943e5715A33EaF2b61f53` (V) | nenhum | $2,38B | Não |
| OUSG (Ondo) | Não (QP + KYC) | `OndoOracle` `0x9Cad45a8BF0Ed41Ff33074449B357C7a1fAb4094` | nenhum | $319M | Não |
| TBILL (OpenEden) | Não (whitelist) (V) | `0xCe9a6626Eb99eaeA829D7fA613d5D0A2eaE45F40` | só XRPL poeira | $294M | Não |
| mTBILL (Midas) | Provável (blacklist) (R) | feed não encontrado | XRPL $189 | $74M | Sem profundidade |
| bIB01 (Backed) | Sim (R) | não on-chain | nenhum | ~$5M | Sem profundidade |
| deJTRSY / deJAAA (Centrifuge) | Sim, wrappers (R) | não encontrado | Aerodrome/Raydium/Kamino, poucos holders | JTRSY $345M | Raso |
| Spiko, BENJI, WTGXX, BUIDL, JLTXX, VBILL… | Permissionados | — | nenhum | BUIDL $2,2B etc. | Não |
| Mortos/avariados: USDM (encerrado 2025), deUSD (sunset nov/2025), USR (exploit 2026-03-22), USDz (~0,98) | — | — | — | — | Evitar |

## Notas
- **USDY:** ETH `0x96F6eF951840721AdBF46Ac996b59E0235CB985C`; Solana mint `A1KLoBrKBde8Ty9qtNQUtq3C2ortoC3u7twggz7sEto6`;
  Arbitrum `0x35e050d3C0eC2d29D269a8EcEa763a183bDF9A9D`; Mantle `0x5bE26527e817998A7206475496fDE1E68957c5A6` (oráculo Mantle `0xA96abbe61AfEdEB0D14a20440Ae7100D9aB4882f`).
  Preço "atualizado a cada dia útil" (V); o oráculo dinâmico interpola diariamente (R). Mínimos conflitantes ($500 / $5k / $100k); não-EUA (V).
  Resgate nativo em USDC já refutado em v2 → saída só pelo secundário.
- **USTB:** RedemptionIdle `0x4c21b7577c8fe8b0b0669165ee7c8f67fa1454cf` paga USDC atômico (fee 0), mínimo $100k, mas
  transferência exige allowlist dos dois lados → sem DEX.
- **USYC:** token `0x136471a34f6ef19fE571EFFC1CA711fdb8E49f2b`, Teller `0xeE35F963BFC71b51eC95147f26c030D674ea30e6`. T+0, não-EUA, ~$100k mín.
- **OpenEden USDO/cUSDO:** mint 3 bps, redeem 10 bps, $100k mín., KYC, não-EUA.
- **bUSD0:** token `0x35D8949372D46B7a3D5A56006AE77B215fc69bC0`; pool Uni `0xABfCA96716cf2911bBB50A4CDBcBAffA2ef8EcDa`; Curve `0x1d08E7adC263CfC70b1BaBe6dC5Bb339c16Eec52`.
  Jan/2025: piso de saída antecipada $0,87 → USD0++ caiu a ~$0,915.
- **syrupUSDC:** saque em fila FIFO, normalmente < 24 h, até 30 dias (docs); pior observado 7,1 d (Cork). Comprar desconto = risco de fila.
  Pools: Solana Orca `6fteKNvMdv7tYmBoJHhj1jx6rHcEwC6RdSEmVpyS613J`; ETH Uni v4 `0xcdb422a8…0228`.

## Fontes
docs.ondo.finance/addresses · docs.superstate.com (smart-contracts) · developers.circle.com/tokenized/usyc ·
docs.openeden.com · docs.maple.finance (asset-integration, risk) · app.rwa.xyz/treasuries · api.llama.fi ·
api.dexscreener.com · theblock.co (Usual, Elixir, Mountain) · cork.tech (tempo de saque Maple).
