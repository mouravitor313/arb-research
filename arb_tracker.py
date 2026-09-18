#!/usr/bin/env python3
"""
arb_tracker.py — Stablecoin / tokenized-asset arbitrage price tracker.

Ingests watchlist.json (context) + tracking_config.json (concrete venues) and:
  1. Polls CEX prices for each configured pair across multiple exchanges (CCXT, public data).
  2. Computes cross-venue spread (best bid vs best ask across venues) and deviation from peg.
  3. Estimates executable slippage at your capital notional via order books ("is $10k-$100k executable?").
  4. Polls on-chain DEX prices via GeckoTerminal (free API, no key). TODO-address entries are skipped.

Runs with NO API keys (read-only public market data). Add keys later for private endpoints.

Usage:
  python arb_tracker.py --once
  python arb_tracker.py --interval 30
  python arb_tracker.py --once --depth-notional 50000 --threshold-bps 10
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    import ccxt
except ImportError:
    sys.exit("Missing dependency: pip install -r requirements.txt  (ccxt)")

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install -r requirements.txt  (requests)")

HERE = os.path.dirname(os.path.abspath(__file__))
GECKO_BASE = "https://api.geckoterminal.com/api/v2"

# ----------------------------------------------------------------------------- utils

def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def bps(a, b):
    """Basis points difference of a relative to b."""
    if b in (None, 0):
        return None
    return (a / b - 1.0) * 1e4

def fmt(x, nd=6):
    return "n/a" if x is None else f"{x:.{nd}f}"

def fmt_bps(x):
    return "n/a" if x is None else f"{x:+.1f}bps"

# ----------------------------------------------------------------------------- CEX

_EXCHANGE_CACHE = {}

def get_exchange(name):
    if name not in _EXCHANGE_CACHE:
        try:
            klass = getattr(ccxt, name)
        except AttributeError:
            _EXCHANGE_CACHE[name] = None
            return None
        ex = klass({"enableRateLimit": True, "timeout": 15000})
        _EXCHANGE_CACHE[name] = ex
    return _EXCHANGE_CACHE[name]

def fetch_ticker(exchange_name, symbol):
    """Return dict with bid/ask/last or None on failure."""
    ex = get_exchange(exchange_name)
    if ex is None:
        return None
    try:
        t = ex.fetch_ticker(symbol)
        return {
            "bid": t.get("bid"),
            "ask": t.get("ask"),
            "last": t.get("last") or t.get("close"),
        }
    except ccxt.BadSymbol:
        return None
    except ccxt.BaseError:
        return None
    except Exception:
        return None

def slippage_for_notional(exchange_name, symbol, notional_usd, side):
    """
    VWAP slippage (bps) to fill `notional_usd` on `side` ('buy' walks asks, 'sell' walks bids).
    Returns (vwap, slippage_bps, filled_fraction) or None.
    """
    ex = get_exchange(exchange_name)
    if ex is None:
        return None
    try:
        ob = ex.fetch_order_book(symbol, limit=100)
    except Exception:
        return None
    levels = ob.get("asks") if side == "buy" else ob.get("bids")
    if not levels:
        return None
    best = levels[0][0]
    remaining = notional_usd
    cost = 0.0
    base_filled = 0.0
    for price, amount in levels:
        level_notional = price * amount
        take = min(level_notional, remaining)
        base = take / price
        cost += base * price
        base_filled += base
        remaining -= take
        if remaining <= 0:
            break
    filled_fraction = (notional_usd - max(remaining, 0)) / notional_usd
    if base_filled == 0:
        return None
    vwap = cost / base_filled
    slip = bps(vwap, best) if side == "buy" else bps(best, vwap)
    return {"vwap": vwap, "slippage_bps": slip, "filled_fraction": filled_fraction}

def track_cex_pair(cfg, depth_notional, threshold_bps, peg_dev_bps):
    symbol = cfg["symbol"]
    peg = cfg.get("pegRef")
    print(f"\n  [{cfg.get('priority','?')}] {cfg['label']}  ({symbol})")
    quotes = {}
    for exname in cfg["exchanges"]:
        t = fetch_ticker(exname, symbol)
        if t and (t["bid"] or t["ask"] or t["last"]):
            quotes[exname] = t
            mid = None
            if t["bid"] and t["ask"]:
                mid = (t["bid"] + t["ask"]) / 2
            dev = fmt_bps(bps(mid or t["last"], peg)) if peg else "  (fx)"
            print(f"      {exname:<10} bid={fmt(t['bid'])} ask={fmt(t['ask'])} last={fmt(t['last'])}  peg-dev={dev}")
        else:
            print(f"      {exname:<10} (no data / symbol not listed)")

    if len(quotes) < 2:
        return

    # cross-venue: cheapest ask (buy here) vs richest bid (sell there)
    best_ask = min(((n, q["ask"]) for n, q in quotes.items() if q["ask"]), key=lambda x: x[1], default=None)
    best_bid = max(((n, q["bid"]) for n, q in quotes.items() if q["bid"]), key=lambda x: x[1], default=None)
    if best_ask and best_bid:
        spread = bps(best_bid[1], best_ask[1])
        flag = "  <<< OPPORTUNITY" if (spread is not None and spread >= threshold_bps) else ""
        print(f"      -> buy {best_ask[0]} @ {fmt(best_ask[1])} | sell {best_bid[0]} @ {fmt(best_bid[1])} "
              f"| gross spread {fmt_bps(spread)}{flag}")
        if flag:  # only pay for order-book calls when there's a headline spread
            buy = slippage_for_notional(best_ask[0], symbol, depth_notional, "buy")
            sell = slippage_for_notional(best_bid[0], symbol, depth_notional, "sell")
            if buy and sell:
                net = None
                if spread is not None and buy["slippage_bps"] is not None and sell["slippage_bps"] is not None:
                    net = spread - buy["slippage_bps"] - sell["slippage_bps"]
                print(f"         depth@${depth_notional:,.0f}: buy slip {fmt_bps(buy['slippage_bps'])} "
                      f"(filled {buy['filled_fraction']*100:.0f}%) | sell slip {fmt_bps(sell['slippage_bps'])} "
                      f"(filled {sell['filled_fraction']*100:.0f}%) | net-of-slippage {fmt_bps(net)}")

    # peg deviation alert (uses the most extreme venue)
    if peg:
        for n, q in quotes.items():
            mid = (q["bid"] + q["ask"]) / 2 if q["bid"] and q["ask"] else q["last"]
            d = bps(mid, peg)
            if d is not None and abs(d) >= peg_dev_bps:
                print(f"      !!! peg deviation on {n}: {fmt_bps(d)} (threshold {peg_dev_bps}bps)")

# ----------------------------------------------------------------------------- DEX (GeckoTerminal)

def gecko_get(path, params=None):
    try:
        r = requests.get(f"{GECKO_BASE}{path}", params=params,
                         headers={"accept": "application/json"}, timeout=15)
        if r.status_code == 429:
            print("      (GeckoTerminal rate-limited; slow down --interval)")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"      (GeckoTerminal error: {e})")
        return None

def resolve_pool(network, token_address):
    """Return highest-liquidity pool address for a token, or None."""
    data = gecko_get(f"/networks/{network}/tokens/{token_address}/pools",
                     params={"page": 1})
    if not data or "data" not in data or not data["data"]:
        return None
    # GeckoTerminal returns pools sorted; take the first (top by reserve/volume)
    pool = data["data"][0]
    return pool["attributes"].get("address"), pool["attributes"]

def track_dex_pool(cfg):
    label = cfg["label"]
    network = cfg["network"]
    token = cfg.get("tokenAddress")
    pool = cfg.get("poolAddress")

    if (token and str(token).startswith("TODO")) or (not token and not pool):
        print(f"\n  [DEX] {label}: SKIPPED (fill tokenAddress/poolAddress from verification queue)")
        return

    attrs = None
    if not pool and token:
        resolved = resolve_pool(network, token)
        if not resolved:
            print(f"\n  [DEX] {label}: no pool found for token on {network}")
            return
        pool, attrs = resolved

    if not attrs:
        data = gecko_get(f"/networks/{network}/pools/{pool}")
        if not data or "data" not in data:
            print(f"\n  [DEX] {label}: pool fetch failed")
            return
        attrs = data["data"]["attributes"]

    price = attrs.get("base_token_price_usd")
    quote_price = attrs.get("quote_token_price_usd")
    liq = attrs.get("reserve_in_usd")
    name = attrs.get("name", "?")
    print(f"\n  [DEX] {label}  ({network}:{pool[:10]}...)")
    print(f"      pool={name}  base=${fmt(float(price)) if price else 'n/a':<12} "
          f"quote=${fmt(float(quote_price)) if quote_price else 'n/a'}  liquidity=${liq}")
    if cfg.get("pegType") == "usd" and price:
        print(f"      peg-dev vs $1: {fmt_bps(bps(float(price), 1.0))}")

# ----------------------------------------------------------------------------- main

def run_once(watchlist, config, args):
    d = config.get("defaults", {})
    depth = args.depth_notional or d.get("depthNotionalUsd", 25000)
    thr = args.threshold_bps if args.threshold_bps is not None else d.get("alertThresholdBps", 15)
    peg_dev = d.get("pegDeviationAlertBps", 20)

    print("=" * 78)
    print(f"ARB TRACKER  {utcnow()}   depth=${depth:,.0f}  spread-alert>={thr}bps  peg-alert>={peg_dev}bps")
    print("=" * 78)

    print("\n--- CEX cross-venue & peg deviation ------------------------------------")
    for cfg in config.get("cexSpreads", []):
        track_cex_pair(cfg, depth, thr, peg_dev)

    print("\n--- DEX on-chain (GeckoTerminal) ---------------------------------------")
    for cfg in config.get("dexPools", []):
        track_dex_pool(cfg)

    print("\n" + "-" * 78)
    print("Reminder: gross spreads exclude taker fees, withdrawal fees, and bridge/settlement time.")
    print("See watchlist.json -> verificationQueue for what to prove before deploying capital.")

def main():
    ap = argparse.ArgumentParser(description="Stablecoin/RWA arbitrage price tracker (CCXT + GeckoTerminal)")
    ap.add_argument("--config", default=os.path.join(HERE, "tracking_config.json"))
    ap.add_argument("--watchlist", default=os.path.join(HERE, "watchlist.json"))
    ap.add_argument("--once", action="store_true", help="Run one poll and exit")
    ap.add_argument("--interval", type=int, default=None, help="Seconds between polls (loop mode)")
    ap.add_argument("--depth-notional", type=float, default=None, help="USD notional for slippage check")
    ap.add_argument("--threshold-bps", type=float, default=None, help="Min gross spread to flag as opportunity")
    args = ap.parse_args()

    config = load_json(args.config)
    watchlist = {}
    if os.path.exists(args.watchlist):
        try:
            watchlist = load_json(args.watchlist)
        except Exception:
            pass

    if args.once or args.interval is None:
        run_once(watchlist, config, args)
        return

    print(f"Looping every {args.interval}s. Ctrl+C to stop.")
    try:
        while True:
            run_once(watchlist, config, args)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
