# Fase 1 — Mapa das small caps da B3 (dados até 2026-10-09)

Gerado por `python b3/build/universe.py --report`. Fontes: COTAHIST (B3), carteiras teóricas B3 (indexProxy), cadastro/eventos B3 (listedCompaniesProxy), proventos Yahoo (.SA).

## 1. Universo

- Regra: carteira **SMLL** ∪ (market cap < R$ 10 bi **e** ADTV21 do ticker principal > R$ 1 mi).
- Emissoras com ação à vista negociada nos últimos 63 pregões: **308**.
- Incluídas: **143** — na SMLL: 103; fora da SMLL (só pela regra): 40; na SMLL mas fora da regra (cap ≥ 10 bi ou ADTV ≤ 1 mi): 25.
- Excluídas por liquidez (cap < 10 bi, ADTV ≤ 1 mi, fora da SMLL): 114 (micro caps ilíquidas — ficam fora do monitor).

### Por market cap

| Market cap | Nº | ADTV21 mediano | na SMLL |
|---|---|---|---|
| < 0,5 bi | 11 | R$ 1,7 mi | 1 |
| 0,5–1 bi | 11 | R$ 4,0 mi | 5 |
| 1–3 bi | 37 | R$ 9,1 mi | 20 |
| 3–5 bi | 21 | R$ 23,3 mi | 18 |
| 5–10 bi | 38 | R$ 39,0 mi | 34 |
| ≥ 10 bi | 24 | R$ 116,0 mi | 24 |

### Por liquidez

| ADTV21 (ticker principal) | Nº |
|---|---|
| ≤ 1 mi | 0 |
| 1–5 mi | 27 |
| 5–20 mi | 48 |
| 20–50 mi | 23 |
| > 50 mi | 45 |

### Por setor

| Setor | Nº | Market cap somado | ADTV21 mediano |
|---|---|---|---|
| Consumo Cíclico | 46 | R$ 223,7 bi | R$ 25,1 mi |
| Bens Industriais | 21 | R$ 77,5 bi | R$ 11,1 mi |
| Financeiro | 15 | R$ 100,1 bi | R$ 19,4 mi |
| Consumo não Cíclico | 14 | R$ 84,0 bi | R$ 26,1 mi |
| Materiais Básicos | 12 | R$ 72,2 bi | R$ 24,5 mi |
| Saúde | 11 | R$ 59,9 bi | R$ 9,0 mi |
| Utilidade Pública | 9 | R$ 110,0 bi | R$ 66,9 mi |
| Tecnologia da Informação | 7 | R$ 40,2 bi | R$ 19,7 mi |
| Petróleo. Gás e Biocombustíveis | 6 | R$ 43,7 bi | R$ 20,6 mi |
| Comunicações | 2 | R$ 4,7 bi | R$ 11,3 mi |

## 2. SMLL vs IBOV (via ETFs SMAL11 / BOVA11)

| ETF | 1m | 3m | 12m | 3a a.a. | 5a a.a. | desde 2010 a.a. | vol 12m | max DD | DD atual |
|---|---|---|---|---|---|---|---|---|---|
| SMAL11 | +26.9% | +25.9% | +35.1% | +11.8% | +1.8% | +5.3% | +25.8% | -53.8% | -9.5% |
| BOVA11 | +12.4% | +17.5% | +48.1% | +22.0% | +13.7% | +6.7% | +19.9% | -49.7% | +0.0% |

- Correlação diária 12m SMAL11×BOVA11: **0.90**.
- Razão SMAL11/BOVA11 hoje vs máxima desde 2010: **-51.1%**; vs mínima: +13.7%.

## 3. Universo (143 emissoras, ordem de market cap)

TR = retorno total (proventos reinvestidos). DD atual = distância do topo (desde 2010).

| Emissora | Ticker | Setor | Mkt cap | ADTV21 | 12m TR | Vol 12m | DD atual | SMLL | Situação |
|---|---|---|---|---|---|---|---|---|---|
| COPASA | CSMG3 | Utilidade Pública | R$ 24,5 bi | R$ 282,0 mi | +101.4% | 33% | -3.9% | ✔ | nan |
| TOTVS | TOTS3 | Tecnologia da Informação | R$ 24,5 bi | R$ 216,0 mi | +1.0% | 40% | -10.6% | ✔ | nan |
| COSAN | CSAN3 | Petróleo. Gás e Biocombustív | R$ 21,4 bi | R$ 182,6 mi | -8.3% | 52% | -78.0% | ✔ | nan |
| MULTIPLAN | MULT3 | Financeiro | R$ 20,0 bi | R$ 254,5 mi | +47.9% | 30% | +0.0% | ✔ | nan |
| HYPERA | HYPE3 | Saúde | R$ 19,0 bi | R$ 113,2 mi | +35.2% | 32% | -37.3% | ✔ | nan |
| ALLOS | ALOS3 | Financeiro | R$ 18,1 bi | R$ 230,2 mi | +66.2% | 28% | +0.0% | ✔ | nan |
| ASSAI | ASAI3 | Consumo não Cíclico | R$ 18,0 bi | R$ 217,3 mi | +60.7% | 51% | -34.9% | ✔ | nan |
| AUREN | AURE3 | Utilidade Pública | R$ 16,4 bi | R$ 66,9 mi | +45.3% | 35% | -2.9% | ✔ | nan |
| TAESA | TAEE11 | Utilidade Pública | R$ 15,9 bi | R$ 96,7 mi | +39.2% | 23% | +0.0% | ✔ | nan |
| CYRELA REALT | CYRE3 | Consumo Cíclico | R$ 15,9 bi | R$ 296,7 mi | +30.9% | 50% | -0.2% | ✔ | nan |
| SMART FIT | SMFT3 | Consumo Cíclico | R$ 15,6 bi | R$ 217,6 mi | +8.2% | 42% | -12.8% | ✔ | nan |
| FLEURY | FLRY3 | Saúde | R$ 15,2 bi | R$ 115,5 mi | +93.9% | 30% | +0.0% | ✔ | nan |
| LOJAS RENNER | LREN3 | Consumo Cíclico | R$ 15,2 bi | R$ 316,1 mi | +16.4% | 42% | -61.8% | ✔ | nan |
| GERDAU MET | GOAU4 | Materiais Básicos | R$ 14,8 bi | R$ 116,5 mi | +59.4% | 30% | -18.2% | ✔ | nan |
| TRACK FIELD | TFCO4 | Consumo Cíclico | R$ 14,6 bi | R$ 18,3 mi | -5.2% | 34% | -13.8% | ✔ | nan |
| SANEPAR | SAPR11 | Utilidade Pública | R$ 13,9 bi | R$ 81,5 mi | +31.4% | 34% | -5.9% | ✔ | nan |
| ALUPAR | ALUP11 | Utilidade Pública | R$ 13,5 bi | R$ 52,2 mi | +33.6% | 23% | +0.0% | ✔ | nan |
| GPS | GGPS3 | Bens Industriais | R$ 13,4 bi | R$ 85,6 mi | +9.5% | 38% | -9.0% | ✔ | nan |
| GRUPO MATEUS | GMAT3 | Consumo não Cíclico | R$ 13,1 bi | R$ 35,2 mi | -9.8% | 43% | -32.6% | ✔ | nan |
| ORIZON | ORVR3 | Utilidade Pública | R$ 12,1 bi | R$ 72,7 mi | +65.8% | 32% | +0.0% | ✔ | nan |
| CURY S/A | CURY3 | Consumo Cíclico | R$ 10,6 bi | R$ 161,6 mi | +26.8% | 43% | -14.0% | ✔ | nan |
| ECORODOVIAS | ECOR3 | Bens Industriais | R$ 10,3 bi | R$ 141,6 mi | +103.8% | 52% | -12.8% | ✔ | nan |
| NATURA | NATU3 | Consumo não Cíclico | R$ 10,2 bi | R$ 89,9 mi | -11.6% | 47% | -89.2% | ✔ | nan |
| SIMPAR | SIMH3 | Financeiro | R$ 10,1 bi | R$ 79,4 mi | +96.9% | 64% | -44.8% | ✔ | nan |
| JHSF PART | JHSF3 | Consumo Cíclico | R$ 10,0 bi | R$ 56,5 mi | +158.4% | 40% | +0.0% | ✔ | nan |
| ALPARGATAS | ALPA4 | Consumo Cíclico | R$ 9,7 bi | R$ 33,5 mi | +107.8% | 44% | -67.4% | ✔ | nan |
| BRAVA | BRAV3 | Petróleo. Gás e Biocombustív | R$ 9,6 bi | R$ 69,8 mi | +29.1% | 38% | -19.1% | ✔ | nan |
| MAGAZ LUIZA | MGLU3 | Consumo Cíclico | R$ 9,5 bi | R$ 299,3 mi | +44.4% | 69% | -94.8% | ✔ | nan |
| IGUATEMI S.A | IGTI11 | Financeiro | R$ 9,3 bi | R$ 120,8 mi | +45.6% | 31% | +0.0% | ✔ | nan |
| USIMINAS | USIM5 | Materiais Básicos | R$ 9,0 bi | R$ 80,9 mi | +66.3% | 46% | -69.5% | ✔ | nan |
| SLC AGRICOLA | SLCE3 | Consumo não Cíclico | R$ 8,8 bi | R$ 48,9 mi | +33.1% | 26% | -8.9% | ✔ | nan |
| SID NACIONAL | CSNA3 | Materiais Básicos | R$ 8,8 bi | R$ 156,0 mi | -21.5% | 58% | -80.5% | ✔ | nan |
| VAMOS | VAMO3 | Consumo Cíclico | R$ 8,4 bi | R$ 134,3 mi | +138.0% | 61% | -56.2% | ✔ | nan |
| MOVIDA | MOVI3 | Consumo Cíclico | R$ 8,1 bi | R$ 172,2 mi | +155.2% | 70% | +0.0% | ✔ | nan |
| MERCANTIL | BMEB4 | Financeiro | R$ 7,9 bi | R$ 2,1 mi | +61.5% | 52% | -9.9% |  | nan |
| FRAS-LE | FRAS3 | Bens Industriais | R$ 7,8 bi | R$ 6,9 mi | +29.9% | 29% | -1.6% | ✔ | nan |
| BRADESPAR | BRAP4 | Materiais Básicos | R$ 7,8 bi | R$ 70,1 mi | +35.9% | 27% | -19.1% | ✔ | nan |
| BANRISUL | BRSR6 | Financeiro | R$ 7,8 bi | R$ 42,9 mi | +75.7% | 31% | +0.0% | ✔ | nan |
| ABC BRASIL | ABCB4 | Financeiro | R$ 7,7 bi | R$ 19,4 mi | +51.5% | 25% | +0.0% | ✔ | nan |
| CBA | CBAV3 | Materiais Básicos | R$ 7,3 bi | R$ 42,0 mi | +145.4% | 28% | -47.2% | ✔ | nan |
| CELESC | CLSC4 | Utilidade Pública | R$ 7,0 bi | R$ 1,2 mi | +108.3% | 20% | +0.0% |  | nan |
| DEXCO | DXCO3 | Materiais Básicos | R$ 7,0 bi | R$ 25,4 mi | +66.3% | 35% | -42.4% | ✔ | nan |
| M.DIASBRANCO | MDIA3 | Consumo não Cíclico | R$ 7,0 bi | R$ 18,2 mi | -18.7% | 33% | -58.1% | ✔ | nan |
| VIVARA S.A. | VIVA3 | Consumo Cíclico | R$ 7,0 bi | R$ 93,1 mi | +10.8% | 40% | -16.7% | ✔ | nan |
| SAO MARTINHO | SMTO3 | Consumo não Cíclico | R$ 6,9 bi | R$ 36,0 mi | +34.6% | 45% | -53.6% | ✔ | nan |
| UNIPAR | UNIP6 | Materiais Básicos | R$ 6,8 bi | R$ 15,7 mi | -13.1% | 30% | -14.6% | ✔ | nan |
| 3TENTOS | TTEN3 | Consumo não Cíclico | R$ 6,8 bi | R$ 27,2 mi | +2.8% | 41% | -23.6% | ✔ | nan |
| AZUL | AZUL3 | Bens Industriais | R$ 6,7 bi | R$ 2,9 mi | — | 83% | -63.4% |  | nan |
| COGNA ON | COGN3 | Consumo Cíclico | R$ 6,6 bi | R$ 128,1 mi | +19.4% | 47% | -70.8% | ✔ | nan |
| DASA | DASA3 | Saúde | R$ 6,6 bi | R$ 5,9 mi | +292.5% | 90% | -97.4% | ✔ | nan |
| INTELBRAS | INTB3 | Tecnologia da Informação | R$ 6,5 bi | R$ 22,0 mi | +96.3% | 40% | -34.9% | ✔ | nan |
| DIRECIONAL | DIRR3 | Consumo Cíclico | R$ 6,4 bi | R$ 143,0 mi | -9.1% | 42% | -27.4% | ✔ | nan |
| LIGHT S/A | LIGT3 | Utilidade Pública | R$ 6,3 bi | R$ 10,8 mi | -22.3% | 61% | -83.5% |  | nan |
| MARCOPOLO | POMO4 | Bens Industriais | R$ 6,0 bi | R$ 85,7 mi | -25.5% | 36% | -35.8% | ✔ | nan |
| IRBBRASIL RE | IRBR3 | Financeiro | R$ 5,7 bi | R$ 67,8 mi | +52.5% | 33% | -93.0% | ✔ | nan |
| HIDROVIAS | HBSA3 | Bens Industriais | R$ 5,6 bi | R$ 7,4 mi | +11.8% | 37% | -46.0% | ✔ | nan |
| EZTEC | EZTC3 | Consumo Cíclico | R$ 5,5 bi | R$ 53,9 mi | +71.3% | 43% | -46.2% | ✔ | nan |
| RIACHUELO | RIAA3 | Consumo Cíclico | R$ 5,4 bi | R$ 18,0 mi | — | 48% | +0.0% | ✔ | nan |
| AZZAS 2154 | AZZA3 | Consumo Cíclico | R$ 5,4 bi | R$ 98,7 mi | +14.8% | 52% | -46.8% | ✔ | nan |
| VULCABRAS | VULC3 | Consumo Cíclico | R$ 5,3 bi | R$ 35,9 mi | +0.5% | 28% | -17.7% | ✔ | nan |
| OCEANPACT | OPCT3 | Petróleo. Gás e Biocombustív | R$ 5,2 bi | R$ 17,8 mi | +47.1% | 37% | -4.5% | ✔ | nan |
| METAL LEVE | LEVE3 | Consumo Cíclico | R$ 5,1 bi | R$ 11,1 mi | +51.4% | 25% | -1.0% | ✔ | nan |
| BANCO BMG | BMGB4 | Financeiro | R$ 4,5 bi | R$ 10,0 mi | +101.9% | 34% | +0.0% |  | nan |
| MINERVA | BEEF3 | Consumo não Cíclico | R$ 4,5 bi | R$ 106,7 mi | -27.8% | 45% | -69.4% | ✔ | nan |
| HAPVIDA | HAPV3 | Saúde | R$ 4,5 bi | R$ 76,2 mi | -75.2% | 82% | -96.7% | ✔ | nan |
| MRV | MRVE3 | Consumo Cíclico | R$ 4,4 bi | R$ 89,1 mi | +25.1% | 53% | -61.4% | ✔ | nan |
| PETZCOBASI | AUAU3 | Consumo Cíclico | R$ 4,3 bi | R$ 20,4 mi | — | 41% | +0.0% | ✔ | nan |
| GRENDENE | GRND3 | Consumo Cíclico | R$ 4,2 bi | R$ 11,3 mi | +27.2% | 29% | -24.3% | ✔ | nan |
| CEA MODAS | CEAB3 | Consumo Cíclico | R$ 4,2 bi | R$ 117,6 mi | -7.0% | 57% | -31.5% | ✔ | nan |
| YDUQS PART | YDUQ3 | Consumo Cíclico | R$ 4,0 bi | R$ 76,3 mi | +30.6% | 50% | -69.9% | ✔ | nan |
| PAGUE MENOS | PGMN3 | Saúde | R$ 4,0 bi | R$ 44,8 mi | +60.0% | 54% | -48.1% | ✔ | nan |
| RAIZEN | RAIZ4 | Petróleo. Gás e Biocombustív | R$ 3,9 bi | R$ 5,7 mi | -56.8% | 75% | -94.2% |  | nan |
| MILLS | MILS3 | Bens Industriais | R$ 3,8 bi | R$ 15,7 mi | +53.4% | 26% | -38.4% | ✔ | nan |
| TENDA | TEND3 | Consumo Cíclico | R$ 3,8 bi | R$ 158,7 mi | +39.7% | 51% | -15.8% | ✔ | nan |
| PINE | PINE4 | Financeiro | R$ 3,7 bi | R$ 13,1 mi | +91.6% | 48% | -1.1% | ✔ | nan |
| JSL | JSLG3 | Bens Industriais | R$ 3,7 bi | R$ 20,6 mi | +135.6% | 66% | -56.2% | ✔ | nan |
| PETRORECSA | RECV3 | Petróleo. Gás e Biocombustív | R$ 3,6 bi | R$ 23,3 mi | +17.4% | 33% | -47.6% | ✔ | nan |
| BRASKEM | BRKM5 | Materiais Básicos | R$ 3,5 bi | R$ 23,7 mi | -33.0% | 81% | -92.7% |  | RE |
| MOURA DUBEUX | MDNE3 | Consumo Cíclico | R$ 3,4 bi | R$ 50,2 mi | +49.4% | 48% | -4.3% | ✔ | nan |
| LWSA | LWSA3 | Tecnologia da Informação | R$ 3,2 bi | R$ 19,7 mi | +48.6% | 47% | -81.8% | ✔ | nan |
| LAVVI | LAVV3 | Consumo Cíclico | R$ 3,1 bi | R$ 13,4 mi | +38.0% | 41% | -15.0% | ✔ | nan |
| RANDON PART | RAPT4 | Bens Industriais | R$ 3,1 bi | R$ 28,4 mi | +44.2% | 45% | -39.3% | ✔ | nan |
| VITRUEDUCA | VTRU3 | Consumo Cíclico | R$ 3,0 bi | R$ 15,3 mi | +90.0% | 40% | +0.0% | ✔ | nan |
| TEGMA | TGMA3 | Bens Industriais | R$ 3,0 bi | R$ 14,9 mi | +45.6% | 33% | -0.1% | ✔ | nan |
| BEMOBI TECH | BMOB3 | Tecnologia da Informação | R$ 3,0 bi | R$ 31,2 mi | +76.2% | 35% | +0.0% | ✔ | nan |
| BLAU | BLAU3 | Saúde | R$ 2,9 bi | R$ 3,1 mi | +36.5% | 40% | -63.3% |  | nan |
| LOG COM PROP | LOGG3 | Financeiro | R$ 2,8 bi | R$ 20,1 mi | +88.2% | 33% | +0.0% | ✔ | nan |
| FERBASA | FESA4 | Materiais Básicos | R$ 2,7 bi | R$ 7,4 mi | +12.7% | 38% | -46.4% | ✔ | nan |
| TUPY | TUPY3 | Bens Industriais | R$ 2,7 bi | R$ 14,6 mi | +64.9% | 41% | -26.1% | ✔ | nan |
| GRUPO SBF | SBFG3 | Consumo Cíclico | R$ 2,6 bi | R$ 46,7 mi | +1.5% | 50% | -67.0% | ✔ | nan |
| CRUZEIRO EDU | CSED3 | Consumo Cíclico | R$ 2,6 bi | R$ 2,5 mi | +51.5% | 50% | -41.8% |  | nan |
| CAMIL | CAML3 | Consumo não Cíclico | R$ 2,5 bi | R$ 7,3 mi | +53.6% | 45% | -33.5% | ✔ | nan |
| UNIFIQUE | FIQE3 | Comunicações | R$ 2,5 bi | R$ 9,1 mi | +79.5% | 38% | -18.2% |  | nan |
| DIMED | PNVL3 | Saúde | R$ 2,4 bi | R$ 14,5 mi | +79.8% | 38% | -42.1% | ✔ | nan |
| EUCATEX | EUCA4 | Materiais Básicos | R$ 2,4 bi | R$ 1,8 mi | +69.3% | 39% | -5.0% |  | nan |
| MATER DEI | MATD3 | Saúde | R$ 2,3 bi | R$ 1,6 mi | +71.3% | 38% | -65.7% |  | nan |
| DESKTOP | DESK3 | Comunicações | R$ 2,3 bi | R$ 13,4 mi | +54.7% | 56% | -24.9% | ✔ | nan |
| SER EDUCA | SEER3 | Consumo Cíclico | R$ 2,2 bi | R$ 14,6 mi | +77.0% | 54% | -40.3% | ✔ | nan |
| ARMAC | ARML3 | Bens Industriais | R$ 2,2 bi | R$ 7,4 mi | +130.4% | 63% | -69.7% | ✔ | nan |
| ANIMA | ANIM3 | Consumo Cíclico | R$ 2,1 bi | R$ 25,4 mi | +76.2% | 72% | -56.3% | ✔ | nan |
| ORANJEBTC | OBTC3 | Consumo Cíclico | R$ 2,0 bi | R$ 13,9 mi | -68.2% | 60% | -72.0% |  | nan |
| MULTILASER | MLAS3 | Tecnologia da Informação | R$ 2,0 bi | R$ 5,1 mi | +150.3% | 57% | -80.4% |  | nan |
| BRASILAGRO | AGRO3 | Consumo não Cíclico | R$ 2,0 bi | R$ 5,3 mi | -1.7% | 23% | -25.0% |  | nan |
| IRANI | RANI3 | Materiais Básicos | R$ 1,9 bi | R$ 5,8 mi | -1.4% | 23% | -20.9% | ✔ | nan |
| SCHULZ | SHUL4 | Bens Industriais | R$ 1,9 bi | R$ 3,3 mi | +33.4% | 25% | -15.1% |  | nan |
| PLANOEPLANO | PLPL3 | Consumo Cíclico | R$ 1,8 bi | R$ 26,3 mi | -37.1% | 54% | -48.3% | ✔ | nan |
| P.ACUCAR-CBD | PCAR3 | Consumo não Cíclico | R$ 1,8 bi | R$ 25,1 mi | -9.8% | 69% | -91.3% |  | nan |
| IOCHP-MAXION | MYPK3 | Consumo Cíclico | R$ 1,7 bi | R$ 9,1 mi | -1.5% | 29% | -54.7% | ✔ | nan |
| VALID | VLID3 | Bens Industriais | R$ 1,6 bi | R$ 4,5 mi | +9.6% | 33% | -27.0% | ✔ | nan |
| CASAS BAHIA | BHIA3 | Consumo Cíclico | R$ 1,6 bi | R$ 18,7 mi | -49.7% | 114% | -91.5% |  | RJ |
| TRISUL | TRIS3 | Consumo Cíclico | R$ 1,6 bi | R$ 2,3 mi | +44.8% | 42% | -24.3% |  | nan |
| WIZ CO | WIZC3 | Financeiro | R$ 1,5 bi | R$ 3,3 mi | +20.5% | 27% | -8.1% |  | nan |
| TAURUS ARMAS | TASA4 | Bens Industriais | R$ 1,4 bi | R$ 15,5 mi | +101.8% | 45% | -56.1% |  | nan |
| KEPLER WEBER | KEPL3 | Bens Industriais | R$ 1,4 bi | R$ 11,1 mi | +11.0% | 36% | -26.4% | ✔ | nan |
| AMERICANAS | AMER3 | Consumo Cíclico | R$ 1,3 bi | R$ 9,9 mi | +14.0% | 60% | -99.9% |  | RJ |
| ONCOCLINICAS | ONCO3 | Saúde | R$ 1,3 bi | R$ 9,0 mi | -52.3% | 151% | -94.1% |  | RE |
| PRINER | PRNR3 | Bens Industriais | R$ 1,3 bi | R$ 14,5 mi | +45.4% | 34% | +0.0% | ✔ | nan |
| EVEN | EVEN3 | Consumo Cíclico | R$ 1,2 bi | R$ 7,9 mi | -1.7% | 43% | -49.7% | ✔ | nan |
| BOA SAFRA | SOJA3 | Consumo não Cíclico | R$ 1,2 bi | R$ 6,1 mi | -6.1% | 46% | -48.9% | ✔ | nan |
| PROFARMA | PFRM3 | Saúde | R$ 1,1 bi | R$ 1,4 mi | +33.4% | 43% | -45.8% |  | nan |
| JALLESMACHAD | JALL3 | Consumo não Cíclico | R$ 916,7 mi | R$ 2,9 mi | +14.8% | 47% | -70.9% |  | nan |
| CVC BRASIL | CVCB3 | Consumo Cíclico | R$ 904,0 mi | R$ 24,8 mi | -1.1% | 72% | -96.9% | ✔ | nan |
| MELNICK | MELK3 | Consumo Cíclico | R$ 748,8 mi | R$ 1,6 mi | +5.4% | 27% | -8.3% |  | nan |
| ROMI | ROMI3 | Bens Industriais | R$ 732,3 mi | R$ 2,7 mi | +9.2% | 27% | -61.7% |  | nan |
| POSITIVO TEC | POSI3 | Tecnologia da Informação | R$ 714,7 mi | R$ 4,0 mi | +28.9% | 41% | -64.4% | ✔ | nan |
| QUALICORP | QUAL3 | Saúde | R$ 690,2 mi | R$ 7,4 mi | +7.6% | 62% | -93.9% | ✔ | nan |
| AUTOMOB | AMOB3 | Consumo Cíclico | R$ 646,0 mi | R$ 2,0 mi | +40.2% | 49% | -31.8% |  | nan |
| SYN PROP TEC | SYNE3 | Financeiro | R$ 624,3 mi | R$ 2,0 mi | -9.2% | 38% | -68.8% |  | nan |
| QUERO-QUERO | LJQQ3 | Consumo Cíclico | R$ 606,3 mi | R$ 7,4 mi | +38.9% | 74% | -87.1% | ✔ | nan |
| ALLIED | ALLD3 | Consumo Cíclico | R$ 596,9 mi | R$ 11,4 mi | +6.3% | 39% | -55.4% |  | nan |
| MELIUZ | CASH3 | Tecnologia da Informação | R$ 526,3 mi | R$ 9,0 mi | +15.6% | 51% | -95.9% | ✔ | nan |
| AZEVEDO | AZEV3 | Bens Industriais | R$ 491,2 mi | R$ 7,9 mi | +31.7% | 153% | -98.9% |  | nan |
| PORTOBELLO | PTBL3 | Bens Industriais | R$ 462,4 mi | R$ 1,3 mi | -14.6% | 54% | -80.3% |  | nan |
| MITRE REALTY | MTRE3 | Consumo Cíclico | R$ 432,6 mi | R$ 2,8 mi | +24.8% | 32% | -65.7% |  | nan |
| HELBOR | HBOR3 | Consumo Cíclico | R$ 362,7 mi | R$ 2,5 mi | -10.4% | 69% | -92.0% | ✔ | nan |
| HBR REALTY | HBRE3 | Financeiro | R$ 348,8 mi | R$ 1,5 mi | -15.1% | 53% | -80.0% |  | nan |
| ESPACOLASER | ESPA3 | Consumo não Cíclico | R$ 287,0 mi | R$ 1,7 mi | -23.7% | 55% | -96.2% |  | nan |
| AMBIPAR | AMBP3 | Utilidade Pública | R$ 250,6 mi | R$ 1,1 mi | -79.2% | 137% | -99.4% |  | RJ |
| PARANAPANEMA | PMAM3 | Materiais Básicos | R$ 152,8 mi | R$ 10,6 mi | -65.0% | 186% | -99.7% |  | RJ |
| GAFISA | GFSA3 | Consumo Cíclico | R$ 69,2 mi | R$ 3,2 mi | -93.6% | 103% | -100.0% |  | nan |
| AZT ENERGIA | AZTE3 | Petróleo. Gás e Biocombustív | R$ 58,8 mi | R$ 1,3 mi | -63.3% | 102% | -90.5% |  | nan |
| RECRUSUL | RCSL4 | Bens Industriais | R$ 40,8 mi | R$ 1,0 mi | -23.1% | 149% | -100.0% |  | nan |
| BR PARTNERS | BRBI11 | Financeiro | — | R$ 8,5 mi | +18.1% | 37% | -6.8% | ✔ | nan |

## 4. Pares entre classes (ON/PN/UNIT) — insumo da fase 2 (30 pares)

Razão de preços ajustada só por eventos em ações (proventos diferentes entre classes ficam no spread — tratar na fase 2). Ordenado por |z| em 12 meses.

| Par | Razão | Mín 12m | Máx 12m | z 12m | ADTV21 (a / b) |
|---|---|---|---|---|---|
| TASA4/TASA3 | 0.851 | 0.851 | 1.021 | -2.79 | R$ 15,5 mi / R$ 854,4 mil |
| AZEV4/AZEV3 | 0.135 | 0.122 | 1.037 | -2.11 | R$ 3,6 mi / R$ 7,9 mi |
| PINE4/PINE3 | 1.119 | 0.941 | 1.185 | +1.97 | R$ 13,1 mi / R$ 88,4 mil |
| EUCA4/EUCA3 | 1.070 | 0.801 | 1.072 | +1.75 | R$ 1,8 mi / R$ 9,6 mil |
| ALPA4/ALPA3 | 1.410 | 0.961 | 1.470 | +1.73 | R$ 33,5 mi / R$ 137,6 mil |
| RCSL4/RCSL3 | 0.470 | 0.468 | 3.398 | -1.69 | R$ 1,0 mi / R$ 501,2 mil |
| BRAP4/BRAP3 | 1.112 | 1.090 | 1.199 | -1.41 | R$ 70,1 mi / R$ 1,4 mi |
| BRSR6/BRSR3 | 0.977 | 0.743 | 0.993 | +1.39 | R$ 42,9 mi / R$ 99,8 mil |
| GOAU4/GOAU3 | 1.110 | 0.994 | 1.145 | +1.22 | R$ 116,5 mi / R$ 409,6 mil |
| FESA4/FESA3 | 0.653 | 0.476 | 0.718 | +1.07 | R$ 7,4 mi / R$ 4,4 mil |
| RAPT4/RAPT3 | 0.767 | 0.560 | 1.077 | -1.06 | R$ 28,4 mi / R$ 270,3 mil |
| TAEE11/TAEE4 | 2.999 | 2.935 | 3.027 | +1.01 | R$ 96,7 mi / R$ 3,1 mi |
| BRKM5/BRKM3 | 0.995 | 0.864 | 1.435 | -0.89 | R$ 23,7 mi / R$ 260,7 mil |
| IGTI11/IGTI4 | 2.308 | 2.038 | 2.406 | +0.82 | R$ 120,8 mi / R$ 8,8 mil |
| SAPR11/SAPR4 | 5.210 | 5.008 | 5.380 | +0.77 | R$ 81,5 mi / R$ 16,9 mi |
| CYRE4/CYRE3 | 0.952 | 0.899 | 1.014 | +0.76 | R$ 10,3 mi / R$ 296,7 mi |
| SAPR4/SAPR3 | 0.836 | 0.763 | 0.982 | -0.76 | R$ 16,9 mi / R$ 2,6 mi |
| BMEB4/BMEB3 | 1.292 | 1.032 | 1.545 | +0.73 | R$ 2,1 mi / R$ 372,9 mil |
| SAPR11/SAPR3 | 4.355 | 4.068 | 4.969 | -0.72 | R$ 81,5 mi / R$ 2,6 mi |
| TAEE4/TAEE3 | 1.012 | 0.982 | 1.033 | -0.61 | R$ 3,1 mi / R$ 1,4 mi |
| IGTI11/IGTI3 | 7.919 | 7.011 | 9.055 | -0.49 | R$ 120,8 mi / R$ 257,3 mil |
| ALUP11/ALUP3 | 2.799 | 2.601 | 3.015 | +0.41 | R$ 52,2 mi / R$ 112,3 mil |
| IGTI4/IGTI3 | 3.507 | 2.983 | 3.973 | -0.27 | R$ 8,8 mil / R$ 257,3 mil |
| TAEE11/TAEE3 | 3.034 | 2.931 | 3.070 | +0.26 | R$ 96,7 mi / R$ 1,4 mi |
| UNIP6/UNIP3 | 1.044 | 0.988 | 1.224 | -0.25 | R$ 15,7 mi / R$ 299,8 mil |
| ALUP11/ALUP4 | 3.152 | 2.982 | 3.284 | +0.22 | R$ 52,2 mi / R$ 190,9 mil |
| CLSC4/CLSC3 | 1.125 | 0.977 | 1.243 | +0.19 | R$ 1,2 mi / R$ 25,3 mil |
| ALUP4/ALUP3 | 0.888 | 0.800 | 1.011 | +0.17 | R$ 190,9 mil / R$ 112,3 mil |
| USIM5/USIM3 | 1.040 | 0.957 | 1.154 | -0.13 | R$ 80,9 mi / R$ 6,2 mi |
| POMO4/POMO3 | 1.069 | 0.998 | 1.195 | +0.04 | R$ 85,7 mi / R$ 10,2 mi |

## 5. Qualidade dos dados

| issue | n |
|---|---|
| dividend_outlier | 34 |
| event_inferred_from_yahoo | 241 |
| event_rejected_no_price_jump | 53 |
| jump_gt_45pct | 603 |

- Validação vs Yahoo (tickers principais do universo, n=143): desvio |log| da série retorno-total p50 = 0.00%, p95 mediano = 0.00%; 20 tickers com p95 > 2% (lista em `data/adjust_validation.csv`; concentrados no histórico antigo de ilíquidas).

- Janela de 3 anos (a que importa para o monitor): 137/143 tickers principais com desvio p95 ≤ 1% vs Yahoo. Fora: CASH3 (1.4%), JSLG3 (29.3%), LJQQ3 (1.4%), PGMN3 (1.7%), SYNE3 (68.5%), VULC3 (1.3%) — diferenças de proventos especiais/redução de capital; conferir caso a caso antes de usar em backtest.

## 6. Limitações conhecidas

- Composição histórica da SMLL não é pública de graça: só snapshots a partir de 2026-10-12 (`index_members`). Backtests usarão a regra de cap/liquidez, não a carteira histórica.
- Proventos em dinheiro vêm do Yahoo (a B3 expõe só ~12 meses). Ações sem histórico no Yahoo ficam ajustadas só por eventos em ações.
- Market cap usa o nº de ações do cadastro B3 de hoje (inclui tesouraria).
