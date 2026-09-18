# Research v2 — DEX-First Multi-Leg Paths to a BRL Terminal

**Supersedes the framing of `research.md` (v1).** v1 tested *"can token X exit to USD/USDC on a
major CEX with withdrawal support?"* and concluded negatively for regional pegs. Under the
architecture in `STRATEGY.md`, **that is the wrong test.** The terminal is **BRL**, routing is
**DEX-first**, and the last mile (`USDC/USDT → BRL`) is already running. A source token no longer
needs a major-CEX USD listing — it only needs a **real DEX path to USDC/USDT at size**. The binding
constraint is therefore **executable DEX depth/slippage**, not CEX listings.

- **Date:** 2026-09-18
- **Trader profile:** Brazil-based, $10k (Test) and $100k (Scale) tiers.
- **Method:** deep-research harness (5 angles → 23 sources → 99 claims → 25 adversarially verified,
  **21 confirmed / 4 killed**) **reconciled against live measurement** (this project's tracker +
  Foxbit v3 public API + GeckoTerminal, 2026-09-18). Every depth/economics number from the harness
  was flagged *CLAIMED / measure-live*; the reconciliation below marks each **MEASURED** where we
  pulled it live.

> **Headline:** the reframe re-opens the question but the data mostly re-confirms the shape of v1
> for a *different reason*. USD-stable core paths are deep and production-ready at both tiers; the
> BRL terminal (Foxbit) is deep and cheap at both tiers; but regional pegs (MXNe, cCOP) and most
> RWAs (USYC, BENJI-class) still fail — now demonstrably on **DEX depth**, not on CEX access. BRLA
> and USDY are the two names that materially improve under the new lens.

---

## 1. The terminal is solved and cheap (MEASURED)

Foxbit exposes a **public, no-auth REST v3 quote endpoint** (`GET /rest/v3/markets/quotes`,
params `base_currency`, `quote_currency`, `side`, `amount`) that simulates size-aware fills. Live
pull 2026-09-18 (BRL per unit):

| Pair | Sell $10k | Sell $100k | Buy $10k | Buy $100k | Round-trip spread | $10k→$100k impact |
|---|---|---|---|---|---|---|
| **USDC/BRL** | 5.16795 | 5.16826 | 5.16972 | 5.17003 | ~3.4 bps | ≈ 0 bp |
| **USDT/BRL** | 5.16541 | 5.16495 | 5.16580 | 5.16616 | ~2.3 bps | ≈ 0 bp |

**Takeaways for path scoring:**
1. The terminal absorbs **$100k with no measurable size penalty** — it is not the bottleneck.
2. **Exit via USDC, not USDT, when possible:** USDC/BRL fetches ~R$5.168 vs USDT/BRL ~R$5.165 —
   **~5 bps more BRL per unit.** Every upstream path should target USDC as the pre-terminal token
   unless the USDT leg is >5 bps cheaper upstream.
3. Foxbit lists **128 BRL markets** including `usdcbrl`, `usdtbrl`, `rlusdbrl`, `usdgbrl`, `ondobrl`,
   `xautbrl` — but **no `brlabrl` / `brzbrl`.** BRLA/BRZ are **DEX-side** instruments, not Foxbit CEX
   pairs. (This refines the harness: its "only USDTBRL is quotable" claim was correctly refuted —
   both USDC and USDT BRL markets are live.)

The active CEX↔DEX last mile (CEX `USDC/BRL` ↔ DEX `USDC/BRLA`) therefore has a **hard terminal
reference of ≈ R$5.168/USDC**; treat that as the anchor every path is scored against.

---

## 2. DEX-routable source universe — CLAIMED vs MEASURED depth

Ranked by **executable depth to USDC/USDT**. "$10k / $100k" = can the deepest venue absorb that
notional at low bps. MEASURED = pulled live 2026-09-18; CLAIMED = harness/secondary, not yet live.

| Token | Class | Deepest live pool (MEASURED) | $10k | $100k | Verdict |
|---|---|---|---|---|---|
| **USDC/USDT** (Polygon) | USD stable | USDC/USDT ~**$8.30M**, vol $24.5M/24h | ✅ | ✅ | **Core. Production-ready.** Matches harness $8.3M claim. |
| **USDe** (eth) | USD stable | top pool ~**$0.87M**–$34M (USDe/FRAX) | ✅ | ✅ | Deep; peg −5.4 bps live. Cross-venue CEX spread also live (+6 bps Gate→Bitget). |
| **USDY** (Solana) | Yield RWA | USDY/USDC ~**$2.9M**, vol $85k | ✅ | ⚠️ split | **Upgraded vs v1.** Solana is the real venue, not ETH (~$19k). NAV-drift, not peg. |
| **BRLA** (EVM/Polygon) | BRL peg | USDC/BRLA 0.05% ~**$139k**, vol $121k | ✅ | ⚠️ marginal | Best regional peg by far. $100k needs multi-pool split; still thin. |
| **BRZ** (EVM) | BRL peg | TESOURO/BRZ ~$74k; BRZ/USDC.e ~$41k | ⚠️ | ❌ | Thinner than BRLA. $10k only, with slippage. |
| **MXNe** (base) | MXN peg | MXNe/SBC ~**$558** | ❌ | ❌ | Non-executable. Confirms v1 (now on depth grounds). |
| **cCOP** (celo) | COP peg | USD₮/cCOP ~**$444** | ❌ | ❌ | Non-executable. Confirms v1. |
| **USYC** | Yield RWA | USYC/USDC ~**$4–9k**, ~0 vol | ❌ | ❌ | No DEX depth; institutional off-DEX redemption only. |
| **sUSDe** | Yield stable | (on-hand addr; measure-live) | — | — | Redemption now **dynamic 1–7d cooldown** (see §4). |
| **DAI/USDS, FDUSD** | USD stable | CEX-side live (Kraken/Binance) | ✅ | ⚠️ | DAI/USDT +5 bps peg-dev live; FDUSD −1.5 bps. Measure DEX depth. |

**Excluded (unchanged from v1, re-confirmed):** MXNe, cCOP, USYC (all fail on DEX depth), all
RMB/CNH (§5), BUIDL (permissioned).

**Regional-peg conclusion under the new lens:** dropping the CEX-listing filter did **not** rescue
MXNe/cCOP — their on-chain pools are 3–4 orders of magnitude too thin. It **did** promote **BRLA**
(a ~$139k USDC pool with real $121k/day volume) to the most viable regional peg, and **USDY** (real
$2.9M Solana depth) from "thin" to "$10k-clean, $100k-splittable."

---

## 3. Path-scoring model (net, fee/slippage/gas-aware)

**Gate:** a path executes only when the **cyclic net product > 1.0** after *all* taker fees (one set
per leg — three for a triangular path), slippage, gas, and bridge cost (verified 3-0; CCXT +
arXiv:2105.02784 + ScienceDirect). Gross spreads are candidates, not signals.

For a path `TOKEN → [intermediate] → USDC → BRL(Foxbit)`:

```
net_BRL_per_unit =  Π_legs (1 - fee_i) · (1 - slip_i)  ·  P_terminal_BRL
                    - gas_total_BRL - bridge_total_BRL
edge_bps = 1e4 · (net_BRL_per_unit / (P_ref_BRL · qty) - 1)
```

- `P_terminal_BRL` = live Foxbit sell quote at the *actual* size (§1), **not** mid — the terminal is
  deep so this ≈ 5.168 (USDC) / 5.165 (USDT) with ~0 size penalty.
- `slip_i` at size comes from **live pool reserves** (GeckoTerminal) or the venue's own size-aware
  quote (Foxbit v3; OKX DEX quote) — never a static band. *(The harness's "0.1–2% mid-tier slippage
  band" and "Curve 3pool >$500M / negligible slippage" claims were both refuted 0-3 — do not assume
  slippage; measure it.)*
- **Trade-splitting across pools/venues:** use the marginal-price optimization framework
  (Loesch & Richardson, arXiv:2502.08258, verified 3-0) — reduces AMM convex routing to a
  root-find with one variable per token regardless of curve count. Relevant for splitting a $100k
  BRLA or USDY leg across its several sub-$150k pools.

**Where DEX-first beats direct CEX liquidation:** only when the DEX route's net edge exceeds the
CEX route's after *its* taker + withdrawal fees. Given the terminal's ~3 bps spread and typical
CEX round-trip taker of ~10–20 bps, the DEX-first advantage is real **only** for tokens with (a)
deep DEX pools and (b) no clean CEX/BRL pair — i.e. BRLA and USDY, not the USD-stable core (which is
already cheapest via the existing last mile).

---

## 4. Entry signals — dislocation vs NAV drift (two distinct classes)

**(a) Mean-reverting peg dislocation (USD stables).** The old headline "27–41%/57–72%" stat stays
**refuted** — do not use. Verified replacement (Eichengreen, Nguyen, Viswanath-Natraj, *Eur. J.
Finance* 2025): USDT **full-default** risk is low/stress-driven (~60 bps *physical* annualized,
>200 bps during Terra-Luna). **Partial** dislocations are the arbitrage-relevant tail — but the
~12 pp (5% threshold) / 31.1% (2%) / 14–18% (Polymarket) figures are **risk-neutral/market-implied**
and **overstate physical frequency**. Use them only for *relative ordering* (partial ≈ 20× more
frequent than full default), never as literal entry rates. **Action:** measure USDC/USDT/USDe/
DAI-USDS/FDUSD dislocation frequency empirically via the tracker — this is still an open question
(harness covered only USDT).

**(b) Predictable, monotonic NAV drift (yield-bearing).** A *different signal class* — not
mean-reverting. Verified 3-0:
- **sUSDe** (Ethena): non-rebasing ERC-4626; USDe value "can only increase or stay flat"; rewards
  vest linearly every 8h. Redemption is now a **dynamic 1/3/5/7-day cooldown** (governance #759,
  effective ~2026-03-13) tied to Tier-1 liquid-asset coverage — **the flat "7-day" claim is
  superseded; 7 days is the ceiling.** A redemption-dependent leg cannot assume a fixed lock.
- **USDY** (Ondo): accumulating, **no $1.00 peg** — tracks daily Treasury NAV (~$1.14 live, NAV
  ~$1.15). "Peg deviation vs $1" is *expected accrual*, not a dislocation. The native "mint/redeem
  to USDC anytime" issuer path was **refuted (1-2)** — do not assume it; treat USDY as DEX-exit only
  (Solana pool, §2).

---

## 5. Venue routing (layered) & RMB verdict

**Routing layer (verified):**
- **OKX DEX aggregator — primary.** Public API aggregates **400+ DEXs across 25 chains** (Polygon
  137, Base 8453, Arbitrum 42161, X Layer 196, Solana 501, TON 607, TRON 195) + **18+ bridges**
  (Stargate, Across, cBridge, SWFT). Endpoints for quote, supported-chain/token discovery,
  liquidity-source visibility, bridge routing. **Caveat:** the API proves *routability*, not
  *depth* — still measure-live per token. **Open:** confirm OKX can actually quote BRLA/USDY at size
  vs 1inch/Jupiter/Curve/Aerodrome/CoW for the same legs.
- **Foxbit — last-mile pricing.** Public v3 quote endpoint (§1) gives size-aware BRL fills; ~2
  req/2 s. This is the terminal oracle.
- **BitGo — custody/settlement only, NOT a router.** Custodial Base/Quote order model
  (Market/Limit/TWAP/VWAP), no AMM/DEX aggregation; reaches *external* DEX liquidity for slippage
  sims. Role = custody, not liquidity sourcing. Requires Enterprise + funded accounts.

**China / RMB — confirmed dead end (verified 3-0).** PBOC **Notice No. 42 [2026]** (Yinfa [2026]
No. 42, issued 2026-02-06 by PBOC + 7 agencies; repeals the 2021 notice) extends the crypto ban to
RMB stablecoins and RWA tokenization and bars **both domestic and foreign** entities from issuing
yuan-pegged stablecoins abroad without approval. Hong Kong approved only HKD tokens and disowned CNH
stablecoins. **No compliant RMB off-ramp exists for a non-Chinese trader.** Exclude entirely;
revisit only if the ban lifts.

---

## 6. Prioritized shortlist (most → least actionable for BRL terminal)

1. **USD-stable core → USDC → Foxbit BRL.** Deepest, cheapest, already the running last mile.
   Polygon USDC/USDT ($8.3M) + terminal ($100k, ~0 impact). Route the exit through **USDC** for the
   ~5 bps edge over USDT.
2. **USDe cross-venue + peg-dev → USDC → BRL.** Live +6 bps Gate→Bitget (gross) already flagged;
   deep pools. Measure net after fees.
3. **BRLA (DEX) as an alternative BRL exit.** Real ~$139k USDC pool, $121k/day vol. $10k clean;
   $100k requires multi-pool split (arXiv:2502.08258). Compare net BRL vs Foxbit fiat exit — this is
   the "BRL stablecoin exit preferred when advantageous" branch of STRATEGY.md.
4. **USDY NAV-drift on Solana → USDC → BRL.** ~$2.9M depth, monotonic accrual. $10k clean,
   $100k splittable. DEX-exit only (no native USDC redemption).
5. **sUSDe NAV drift.** Predictable, but redemption is a dynamic 1–7d lock — only for
   non-time-critical capital.

**Explicitly excluded:** MXNe, cCOP, BRZ-at-$100k (all too thin), USYC/BENJI-class (no DEX depth),
all RMB/CNH (banned), BUIDL (permissioned).

---

## 7. Verification queue (open — prove before deploying capital)

Carried from the harness's open questions + reconciliation gaps:

1. **OKX DEX quote reality:** can it actually route+quote BRLA and USDY at $10k/$100k, and how do
   its quotes compare to 1inch/Jupiter/Curve/Aerodrome/CoW for the same legs? (Routability ≠ depth.)
2. **BRLA $100k split:** live multi-pool slippage for a $100k BRLA→USDC fill across its sub-$150k
   pools; net vs the Foxbit fiat exit.
3. **USDY Solana leg:** confirm the ~$2.9M pool network/venue and live slippage at both tiers; the
   $1.14B "pool" (vol ~$4k) is almost certainly a mispriced/lending artifact — do **not** treat as
   tradable.
4. **Dislocation reality (still open):** empirically measure secondary-dislocation frequency +
   magnitude for USDC/USDe/DAI-USDS/FDUSD (harness covered only USDT) via the tracker.
5. **BRLA/BRZ pool networks:** confirm chain (Polygon vs Base/Gnosis) for the deep BRLA pools and
   wire `poolAddress` directly into the tracker.

---

## 8. Confidence & caveats

- **Strong (primary + live-measured):** the Foxbit terminal anchor (§1, our own live pull), Polygon
  USDC/USDT depth (harness + our live pull agree at ~$8.3M), the OKX/BitGo/Foxbit capability map,
  the sUSDe dynamic-cooldown and USDY-NAV mechanics, and the China ban.
- **Measure-live (do not size on these yet):** all pool depths shift; regional-peg and RWA depths
  are point-in-time. USDT dislocation probabilities are **risk-neutral** and overstate physical
  frequency.
- **Refuted — do not repeat:** "27–41%/57–72%" dislocation stat; flat/permanent 7-day sUSDe
  cooldown; Curve 3pool >$500M/negligible-slippage; 0.1–2% mid-tier slippage band; native USDY→USDC
  issuer path; "only USDTBRL quotable on Foxbit."
- Fast-moving 2025–2026 landscape (China ban Feb-2026; sUSDe cooldown Mar-2026; MiCA Title V
  2024–2025). **Re-verify before each allocation.**

### Primary sources
OKX DEX API docs + `github.com/okx/dex-api-library` · Foxbit REST v3 docs (live-tested) ·
BitGo developer portal · GeckoTerminal (live) · Ethena docs + governance #759 · Ondo USDY docs ·
Eichengreen/Nguyen/Viswanath-Natraj (*Eur. J. Finance* 2025) · Loesch & Richardson arXiv:2502.08258 ·
cyclic-arb arXiv:2105.02784 · US Library of Congress on PBOC Notice No. 42 [2026].
