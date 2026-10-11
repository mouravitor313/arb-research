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
| `dashboard.py` | **PoC realtime dashboard (Streamlit, PT-BR)** — reads `arb_tracker.db` and tells the story + shows live data. |
| `run_dashboard.ps1` | Helper: launches the tracker loop + the dashboard together. |

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

## Dashboard (PoC)

A realtime **Streamlit** dashboard (PT-BR) for presenting the idea to the team. It reads
`arb_tracker.db` **read-only** — the tracker stays the sole writer. Run the tracker in loop mode
so the DB keeps filling, then open the dashboard:

```powershell
# one command — starts tracker loop (new window) + dashboard (this window):
.\run_dashboard.ps1                 # default 60s poll
.\run_dashboard.ps1 -Interval 30

# or manually, in two terminals:
python arb_tracker.py --interval 60     # terminal A (writes arb_tracker.db)
streamlit run dashboard.py              # terminal B → http://localhost:8501
```

It shows: KPIs (terminal USD/BRL, best net spread, executable-pool counts), the thesis (v1→v2
reframe), the BRL terminal card, a **DEX depth** bar chart (log-scale, colored by executability),
a **gross-vs-net spreads** table, and live time-series. Panels auto-refresh every 10s. If the DB is
empty it falls back to the saved CSVs, then to static research figures, so the demo always renders.

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

## v3 measurement scripts (read-only, 2026-10-10/11)

All of them only do `eth_call`s and public OKX REST calls (no keys, no tx). Results are in `RECAP.md §9–10`.

```powershell
# Polygon atomic cycle USDC→BRLA→BRZ→USDT0→USDC (item B)
python cycle_discover.py          # validate pools on-chain -> cycle_discovery.json
python cycle_probe.py             # one-shot quotes, both directions, $1k/$10k/$100k
.un_cycle_collector.ps1         # live loop (12 s) -> cycle_quotes/cycle_ticks/cycle_pool_swaps
python cycle_backfill.py --days 14 --step 300   # archive backfill -> cycle_*_hist
python cycle_analyze.py [--hist]

# Item 1: OKX BRL pairs vs OKX USD pairs vs DEX (Ethereum/Arbitrum/Base), USDC/USDT basis
python xvenue_discover.py         # BTC/ETH pools per chain -> xvenue_discovery.json
.un_xvenue_collector.ps1        # live loop (10 s) -> xvenue_opps/xvenue_ticks
python xvenue_backfill.py --days 14             # cbBTC (Base) vs OKX BTC basis -> xvenue_hist
python xvenue_analyze.py [--size 10000]
```
RPC overrides: `POLYGON_RPC_URL`, `ETHEREUM_RPC_URL`, `ARBITRUM_RPC_URL`, `BASE_RPC_URL`.

## Extending

- **Add a pair:** append to `cexSpreads` (`symbol` must be the CCXT unified symbol, e.g. `USDE/USDT`).
- **Add a DEX pool:** append to `dexPools` with `network` + `tokenAddress` (or `poolAddress`).
- **Private endpoints / withdrawals:** add API keys in `get_exchange()` and use CCXT auth calls.
- **Alerting/persistence:** `run_once()` is the hook point to write rows to CSV/DB or push alerts.
