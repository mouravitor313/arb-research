# Pesquisa de mesa — renda fixa brasileira tokenizada · 2026-10-11

Fonte: subagente de pesquisa web + leituras on-chain próprias dele (Polygon bloco ~95.369.239, ~22:50 UTC).
V = verificado (fonte primária / leitura on-chain) · R = relatado.

## TESOURO (Etherfuse "Stablebond" Brasil)
- **Emissor: Etherfuse** (V: `api.etherfuse.com/lookup/stablebonds`; TOML Stellar). Transfero/DFB só fizeram a
  distribuição na Polygon e o pool Curve "DFB BRL Pool v1" (R, dez/2025).
- Lastro: "títulos públicos brasileiros (Tesouro)" (V, docs); LTN pré/indexados segundo DefiLlama/rwa.xyz (R). Não
  achei fonte primária dizendo LFT/Selic.
- Endereços (V, API Etherfuse + on-chain): Polygon `0xd574b191B5a00262Ff19953d3CE25543AB7C8098` (6 dec, 466k),
  Solana `BRNTNaZeTJANz9PeuD8drNbBHwGgg7ZTjiQYrFgWQ48p` (450k), Base `0x7ceE47e7B7CD04CF984e8Dd86C42595B5771A9B2` (95k),
  Stellar `TESOURO-GCRYUGD5…MYWC` (1,21M). **Total 2,22M tokens ≈ R$2,81M (~$564k).**
- Polygon: OFT LayerZero (`RateLimitedOFTUpgradeable`), sem blacklist/pausa → transferível livre. Solana: Token-2022
  sem freeze authority. Stellar: `auth_clawback_enabled`.
- **NAV** (V): `api.etherfuse.com/lookup/tokens/cost/TESOURO` → `token_cost_in_fiat` 1,265416 BRL ($0,25375),
  taxa 1128 bps (11,28% a.a.), USD/BRL 4,98687; API pública, cache ~5 min. Solana: PDA `BondPrice` ["bond_price", mint].
- **Mint/resgate**: app/SDK/ramp Etherfuse, KYC/KYB; **trilho BRL (Pix) "upcoming"** (V, docs/fees); Polygon tem
  on/offramp mas não swap (V). rwa.xyz: instantâneo, 0% taxa, sem mínimo, não-EUA, 1,5% adm (R).
- **Pool Curve `0xc89f31f74573cc19fffc06108601c1ac71ba9735`** (Polygon, stableswap-ng, A=2000, fee 0,03%):
  coins TESOURO(0, oráculo) / BRZ(1) / stBRZ(2, rebasing) / BRLA(3). Saldos: 30.859 TESOURO, 384k BRZ, 223k stBRZ,
  42,9k BRLA (~$137k).
  - **Oráculo de taxa `0xc1df935339989f398c59af034fdfc13b2a84c4f2`** (`getRate()`, proxy, implementação não verificada),
    `description()` = "DFB TESOURO/BRZ", 8 dec, atualiza ~10 min, **não monotônico**; 1,274334 em 2026-10-11 22:49 UTC,
    desde 2025-11-15. **≈70 bps acima do NAV Etherfuse** — consistente com o oráculo cotar TESOURO em BRZ e BRZ valer
    ~0,993 BRL (inferência, não verificada).
- Outros pools: Polygon Uni v4 TESOURO/USDC 0,15% ~$16k; Uni v3 ~$1k; Solana Orca TESOURO/USDC
  `3bYZCXv6rWpbT3zizsTArUdZ4SEmDRMCWtjzasz8nVpK` ~$83k (volume ~0); Base TESOURO/BRZ ~$74k.
- stBRZ (Kona Finance / Transfero): rebasing `rewardMultiplier` 1,2857; mint/burn só `STAKING_ROLE`, blacklist e pausa.

## Outros BR
| Produto | Situação |
|---|---|
| BRLY/BRLV (Crown, Base) | BRLY `0x57323db6d883811c17877d075e05ad9e2ed41519` (372M), BRLV `0xd2047ebdb205ee6862b69ae9fb3501652cc97d36` (ERC-4626 sobre BRLY). Lastro em títulos públicos/% CDI (R). DEX: BRLV/USDC Uni v4 ~$28,6k. Termos de resgate não encontrados. |
| BRL1 | Reserva ~99,9% Tesouro Selic (R), mas não paga yield ao holder → stablecoin, não título. |
| MB Renda Fixa Digital, Liqi, Vórtx QR | Custodiais/permissionados, sem saque para carteira externa e sem DEX. |
| Drex / TPFt | Piloto encerrado nov/2025, retomada 2027 (R). |
| CSD BR × Ripple (XRPL) | Só instituições KYC. |

## Outros LatAm (Etherfuse)
CETES (México) NAV 1,185417 MXN, AUM ~$4,6M; pools Orca CETES/MXNe ~$138k, CETES/USDC ~$100k, Aerodrome Base ~$98k,
volume ~0. Fora do escopo BRL.

## Fontes
api.etherfuse.com (stablebonds, tokens/cost/TESOURO) · docs.etherfuse.com (price-feeds, fees, glossary, chains/polygon) ·
Sourcify (impl. TESOURO `0x79a5c491…6e41`, stBRZ `0xb9dca56b…7db8`) · RPC Polygon/Solana · stellar.expert/Horizon ·
GeckoTerminal/DexScreener · rwa.xyz / DefiLlama (R) · mexc.com/news/215380 (R) · openzeppelin.com (auditoria Crown).
