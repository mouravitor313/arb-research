# Crypto Arbitrage Strategy — Multi-Leg Path Optimization

## Context & Problem Statement

The initial verification followed a simplified path:

```
[TOKEN] → CEX → USDC
```

This approach focuses on direct liquidation of a given token into USD stablecoins on a centralized exchange. While functional, it leaves significant value on the table by ignoring DEX pricing, cross-venue spreads, and local-currency exit advantages.

## Target Architecture

The intended flow introduces a DEX-first routing layer before CEX settlement:

```
[TOKEN] → DEX → USDC/USDT → CEX → BRL (fiat or stablecoin)
```

### Core Principles

1. **Do NOT default to direct token → USD stable liquidation on a CEX.** The primary goal is to find the optimal multi-leg path that maximizes net value at the BRL exit.
2. **BRL is the terminal currency.** Since operations are based in Brazil, the final settlement target is BRL — either fiat BRL or a BRL-pegged stablecoin (BRZ, BRLA), whichever yields the best rate.
3. **CEX liquidation remains opportunistic.** If a CEX offers a materially better rate for a specific token pair, that path is valid — unless onboarding a Brazilian entity on that CEX is impractical or blocked (which is a likely constraint for several venues).
4. **BRL stablecoin exits are preferred when advantageous.** If exiting through BRZ or BRLA provides a better net rate than fiat BRL, use the stablecoin path.

---

## Active Arbitrage — The "Last Mile"

The USDT/USDC → BRL conversion is **already being executed** via an active CEX ↔ DEX arbitrage:

| Leg | Venue Type | Pair |
|-----|-----------|------|
| CEX | Centralized | USDC/BRL |
| DEX | Decentralized | USDC/BRLA |

This is the **terminal segment** of every path. All upstream optimization feeds into this exit.

Onboarding with BRZ and BRLA issuers/maintainers is available and can be activated if the path economics justify it.

---

## Venue Universe

### DEXes (Operational)

| Priority | Venue | Notes |
|----------|-------|-------|
| 🥇 Primary | **OKX DEX** | Best liquidity & routing |
| 🥈 Secondary | **Foxbit** | Local Brazilian venue |
| 🥉 Tertiary | **Bitgo** | Institutional-grade custody |

### CEXes

Any CEX where onboarding is feasible for a Brazilian entity. Factor in:
- KYC/AML friction for BR-domiciled accounts
- Withdrawal limits and fiat off-ramp availability
- Fee structures (maker/taker, withdrawal, conversion)

---

## Monitoring & Execution Framework

### Phase 1 — Price Surveillance

- **Continuously monitor spot prices** for target tokens across all CEXes and DEXes in the venue universe.
- Track bid/ask spreads, depth, and slippage at relevant size tiers.

### Phase 2 — Path Discovery

- For each token, enumerate all viable multi-leg paths from `[TOKEN]` to `USD stable` (USDC/USDT).
- Score each path by **net output per unit input** after fees, slippage, and gas costs.
- Include hybrid paths (e.g., TOKEN → intermediate token → USDC on DEX → USDT on CEX).

### Phase 3 — Last-Mile Optimization

- Route the resulting USDC/USDT through the active CEX ↔ DEX BRL arbitrage.
- Evaluate direct DEX-based BRL stablecoin exits as an alternative.

---

## Scalability Validation

Every path and venue combination **must be validated for scalability** across the following size tiers:

| Tier | Size (USD) | Purpose |
|------|-----------|---------|
| Test | $10,000 | Path validation, slippage measurement |
| Scale | $100,000 | Production viability, depth stress test |

A path that works at $10K but breaks at $100K due to thin order books or high slippage is **not production-ready**.

---

## Geographic Expansion — China / RMB Hypothesis

**Validation requested:** Can this same multi-leg architecture be replicated for a China/RMB exit?

```
[TOKEN] → DEX → USDC/USDT → CEX → RMB (fiat or CNY stable)
```

Key questions to validate:
- Are there RMB-pegged stablecoins with sufficient liquidity (e.g., CNHT, CNYx)?
- Which CEXes support RMB fiat off-ramps with manageable onboarding for non-Chinese entities?
- Are there CEX ↔ DEX arbitrage opportunities analogous to the USDC/BRL ↔ USDC/BRLA spread?
- What are the regulatory and capital-control constraints for RMB conversion and repatriation?
