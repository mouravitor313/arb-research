# arb — stablecoin & tokenized-asset arbitrage tracker

Research + live price tracker for stablecoin / tokenized-asset arbitrage across LatAm, Europe,
and (excluded) China, for a **$10k–$100k** trader who must exit to **USD/USDC on a major CEX**.

## Files

| File | Purpose |
|---|---|
| `research.md` | Full research overview: findings by asset class, regulatory constraints, prioritized shortlist, verification queue, refuted claims. |
| `watchlist.json` | Machine-readable list of tracked/excluded assets with confidence + verification status. |
| `tracking_config.json` | Concrete venues/pairs the tracker polls. Edit this to add pairs/pools. |
| `arb_tracker.py` | Live tracker: CEX prices/spread/slippage (CCXT) + on-chain DEX prices (GeckoTerminal). |

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Runs with **no API keys** — uses public read-only market data.

## Run

```powershell
python arb_tracker.py --once                       # one poll
python arb_tracker.py --interval 30                # poll every 30s
python arb_tracker.py --once --depth-notional 50000 --threshold-bps 10
```

## What it does

1. **CEX cross-venue spread** — for each pair in `cexSpreads`, polls every listed exchange and
   reports the best `buy here / sell there` gross spread. Flags `<<< OPPORTUNITY` when the gross
   spread ≥ `--threshold-bps`.
2. **Peg deviation** — for USD stables (`pegRef: 1.0`), flags any venue deviating ≥ `pegDeviationAlertBps`.
3. **Executable depth** — when a headline spread fires, walks the order book on both venues to
   estimate VWAP slippage at your `depthNotionalUsd`, and prints a **net-of-slippage** spread.
   This directly answers "is $10k–$100k executable?".
4. **On-chain DEX price** — for each `dexPools` entry with a real address, fetches price/liquidity
   from GeckoTerminal (auto-selects the top pool from a `tokenAddress`). `TODO_` entries are skipped.

## Before trusting a signal

Gross spreads **exclude** taker fees, withdrawal fees, and bridge/settlement time. A ~8 bps gross
spread on a stable pair typically does **not** clear round-trip taker fees (~10–20 bps) unless you
maker-rebate or the spread is wider. Treat flags as *candidates to investigate*, not trades.

## Filling the DEX / verification gaps

The research could not verify pool addresses or regional-peg CEX exits. `watchlist.json →
verificationQueue` lists what to prove. To activate DEX tracking, replace the `TODO_...` addresses
in `tracking_config.json → dexPools` with real token/pool addresses (GeckoTerminal networks:
`eth`, `solana`, `base`, `arbitrum`, `celo`).

## Extending

- **Add a pair:** append to `cexSpreads` (`symbol` must be the CCXT unified symbol, e.g. `USDE/USDT`).
- **Add a DEX pool:** append to `dexPools` with `network` + `tokenAddress` (or `poolAddress`).
- **Private endpoints / withdrawals:** add API keys in `get_exchange()` and use CCXT auth calls.
- **Alerting/persistence:** `run_once()` is the hook point to write rows to CSV/DB or push alerts.
