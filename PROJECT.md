# PROJECT.md — arb (stablecoin arbitrage research + tracker)

> Context-persistence file for cross-session continuity. Read this first when resuming.
> Last updated: 2026-09-18 (v2 pass complete)

## v2 reframe (2026-09-18) — DEX-first, BRL terminal — READ THIS

`STRATEGY.md` changed the terminal from USD/USDC-on-a-major-CEX to **BRL**, routing to **DEX-first**,
with the last mile (`USDC/USDT → BRL`) already running (CEX `USDC/BRL` ↔ DEX `USDC/BRLA`). This
**inverts v1's test:** a source token no longer needs a CEX USD listing — only a real **DEX path to
USDC/USDT at size**. Binding constraint = **executable DEX depth**, not CEX access.

- ✅ New deep-research pass done (harness: 5 angles → 23 sources → 25 verified, **21 confirmed / 4
  killed**) **reconciled against live measurement**. Written to **`research_v2.md`** (supersedes v1's
  framing; v1 `research.md` kept).
- ✅ **Terminal anchor MEASURED (Foxbit public v3 API, no auth):** `USDC/BRL` ≈ R$5.168, `USDT/BRL`
  ≈ R$5.165 — both absorb **$100k with ~0 size penalty**. Exit via **USDC (+~5 bps vs USDT)**.
  Foxbit has 128 BRL markets incl. usdcbrl/usdtbrl but **no brlabrl/brzbrl** (those are DEX-only).
- ✅ **Reconciled depth (live 2026-09-18):** Polygon USDC/USDT ~$8.32M (matches harness) ✅;
  **BRLA/USDC (Polygon) ~$139k, vol $124k — best regional peg, promoted** ✅ $10k / ⚠️ $100k-split;
  **USDY real venue is Solana ~$2.92M** (not ETH ~$19k, not Aerodrome) — upgraded; BRZ ~$170k thin;
  **MXNe ~$558 / cCOP ~$444 still dead; USYC ~$4-9k dead** (now on depth grounds, not CEX access).
- ✅ Tracker updated: 4 new `dexPools` wired + verified resolving (usdc-usdt-polygon, brla-usdc-polygon,
  usdy-solana, brz-tesouro-polygon). NOTE: 8 DEX lookups now exceed GeckoTerminal free ~30/min in a
  single `--once` burst — use `--interval` spacing.
- Verified mechanics: **sUSDe cooldown is now dynamic 1-7d** (gov #759, ~2026-03-13), not flat 7d;
  **USDY accrues (~$1.14, no $1 peg)**, native USDC redemption path refuted. **China RMB = confirmed
  dead end** (PBOC Notice No. 42 [2026]).
- Open (v2 verification queue): OKX DEX can-it-actually-quote BRLA/USDY at size vs 1inch/Jupiter/etc.;
  BRLA $100k multi-pool split slippage; empirical dislocation freq for USDC/USDe/DAI-USDS/FDUSD.

---

## Goal

Find and track **arbitrage opportunities in stablecoins / tokenized assets** across **LatAm, China,
and Europe**, for a trader running **$10k–$100k** who must be able to **exit to USD/USDC on a major
CEX** with real withdrawal support. Cover four asset classes: regional fiat-pegged stables, USD
stables cross-venue, tokenized bonds/RWAs, and yield-bearing stables. Deliver a research overview
plus a live price tracker to monitor tokens/DEXes/CEXes and detect spreads.

## Current state

- ✅ Deep research completed (5 angles → 25 sources → 25 claims verified, 19 confirmed / 6 refuted).
- ✅ Research written to `research.md` (translated to PT-BR by the user).
- ✅ Machine-readable `watchlist.json` produced (10 tracked assets + 3 excluded + verification queue).
- ✅ Live tracker `arb_tracker.py` built and **verified running** (CCXT + GeckoTerminal, no API keys).
  - Pulls CEX prices/spread/peg-deviation/order-book-slippage; DEX prices via GeckoTerminal.
  - Live test already flagged a **USDe +8.0 bps** cross-venue spread (buy Gate / sell Bitget).
- ✅ DEX pool tracking is **active** — all four `dexPools` token addresses filled + verified against
  GeckoTerminal (2026-09-18); tracker resolves live pools for USDe, USDY, MXNe, cCOP.
  - Addresses: USDe `0x4c9edd58…1E68B3` (eth), USDY `0x96F6eF95…CB985C` (eth),
    MXNe `0x269caE7D…30E0aF` (base), cCOP `0x8A567e2a…4041eA` (celo). sUSDe on-hand:
    `0x9d39a5de…7a3497`.
  - **Finding (advances verif-queue #1):** on-chain depth for the regional pegs is *negligible* —
    MXNe top pools ~$140–550, cCOP ~$450–16k reserve. **Not executable at $10k–$100k.** Corroborates
    the negative research result. USDe deep (~$34M USDe/FRAX); USDY ETH pools thin (~$15–20k; deeper
    on Aerodrome/Solana).
  - Fixed a Windows crash: pool names with non-Latin glyphs (e.g. `USD₮`) broke cp1252 console output;
    tracker now forces UTF-8 stdout/stderr.

## What's in the project now

| File | Purpose |
|---|---|
| `research_v2.md` | **CURRENT.** DEX-first / BRL-terminal research: reconciled (claimed vs measured) depth table, path-scoring model, venue routing, signals, RMB verdict, v2 verification queue. (EN) |
| `research.md` | v1 overview (superseded framing; kept for reference). Findings by asset class, regulatory constraints, refuted claims. (PT-BR) |
| `probe_topup.py`, `probe_topup2.py`, `probe_ids.py` | One-shot live reconciliation probes (Foxbit v3 quotes + GeckoTerminal depth/ids). Re-run to refresh MEASURED figures. |
| `watchlist.json` | Machine-readable list of tracked/excluded assets with confidence + verification status. |
| `tracking_config.json` | Concrete venues/pairs the tracker polls. Edit to add pairs/pools. |
| `arb_tracker.py` | Live tracker: CEX prices/spread/slippage (CCXT) + on-chain DEX prices (GeckoTerminal). |
| `requirements.txt` | Python deps: `ccxt`, `requests` (installed & verified). |
| `README.md` | Setup, usage, and how to extend. |
| `PROJECT.md` | This file — cross-session context/state. |

## Key findings (condensed — see research.md for full)

- **Most decision-relevant result is negative:** no verified major-CEX USD withdrawal path or live
  executable liquidity for any regional fiat peg (MXNe, cCOP). Their USD path = on-chain FX swap to
  USDC, then withdraw USDC on a CEX.
- **USD-stable primary arb (mint/redeem to $1) is closed** for this size at Tether ($100k min, fee
  max($1,000, 0.1%)); the play is **secondary/cross-venue spreads**.
- **Best defensible setups:** (1) cross-venue USD-stable spreads, (2) yield-bearing NAV drift
  (sUSDe, USDY, USYC) — both settle natively to USDC on major CEXes.
- **Excluded:** BUIDL (not exitable for us), all RMB/CNH (China Feb-2026 ban; CNHC defunct),
  low-min registered funds (BENJI/WTGXX/Spiko — thin secondary).
- **EU EUR stables gated by MiCA** — only authorized EMTs (EURC, EURe/Monerium) offerable on EEA CEXes.
- **Refuted (do NOT rely on):** frequent-peg-dislocation stat; sUSDe 7-day cooldown; OUSG no-gate
  $5k path; tokenized-treasury spreads "<35 bps".

## Verification queue (prove before deploying capital)

1. Regional pegs: can $10k–$100k round-trip MXNe/cCOP → USDC → named CEX withdrawal? Measure
   Stabull/Mento depth + slippage; confirm the USDC→CEX leg.
2. Live DEX depth: exact pool (pair, chain, TVL, slippage at size) for USDY (Curve/Aerodrome/Solana),
   sUSDe, USYC.
3. EUR stables: which of EURC/EURe/EURt/agEUR-EURA/stEUR hold MiCA authorization AND remain on EEA
   CEXes with USD/USDC exit? Where do recurring spreads occur?
4. Dislocation reality: empirically measure frequency + magnitude of secondary peg dislocations for
   USDC/USDT/USDe/DAI-USDS/FDUSD across DEXes/CEXes (headline stat was refuted).
5. BRL market: confirm current CEX listings + depth for BRLA, BRZ.

## Next steps (options, not yet started)

1. ✅ ~~Fill DEX addresses (USDe, USDY, MXNe, cCOP)~~ — done 2026-09-18. Next on-chain step:
   **track deeper venues** — set `poolAddress` directly for USDY on Aerodrome/Solana (ETH pools are
   thin), and implement FX refs so `fx_mxn`/`fx_cop` pegs actually compute a dislocation (currently
   price is shown as raw USD, not vs live USD/MXN & USD/COP).
2. **Fee-aware net spreads:** add per-exchange taker fees to config so the tracker reports net
   (not gross) spread. Current gross flags don't clear ~10–20 bps round-trip taker fees.
3. **Persist + alert:** log poll rows to CSV/SQLite and push alerts (hook point: `run_once()`).
4. **Verification research pass** on the queue above (BRL CEX listings, MiCA-authorized EUR issuers,
   live pool depths).

## How to run

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
python arb_tracker.py --once
python arb_tracker.py --interval 30
```

## Notes / gotchas

- Environment: Windows 11, Python 3.14, PowerShell. Not a git repo.
- CCXT unified symbols are case-sensitive (e.g. USDe → `USDE/USDT`). Exchanges silently skip pairs
  they don't list.
- GeckoTerminal is free/no-key but rate-limited (~30 req/min) — keep `--interval` reasonable.
- Gross spreads exclude taker/withdrawal fees and settlement time — treat flags as candidates.
- Fast-moving 2025–2026 regulatory/product landscape; re-verify listings/depths before trading.
