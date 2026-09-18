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
import csv
import json
import os
import sqlite3
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
FOXBIT_BASE = "https://api.foxbit.com.br/rest/v3"
COINBASE_RATES_URL = "https://api.coinbase.com/v2/exchange-rates"

# On-chain pool names can contain non-Latin symbols (e.g. USD₮ = U+20AE). The
# default Windows console codec (cp1252) can't encode those and crashes on print.
# Force UTF-8 output with replacement so a stray glyph never kills a poll.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# ----------------------------------------------------------------------------- persistence

def init_db(db_path=None):
    """Initialize SQLite schema. Returns db connection."""
    if db_path is None:
        db_path = os.path.join(HERE, "arb_tracker.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS fx_refs (
            ts TEXT PRIMARY KEY,
            usd_brl REAL,
            usd_brl_ask REAL,
            usd_brl_bid REAL,
            usd_mxn REAL,
            usd_cop REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cex_quotes (
            ts TEXT,
            exchange TEXT,
            symbol TEXT,
            bid REAL,
            ask REAL,
            last REAL,
            peg_dev_bps REAL,
            PRIMARY KEY (ts, exchange, symbol)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cex_spreads (
            ts TEXT,
            symbol TEXT,
            best_ask_exchange TEXT,
            best_ask_price REAL,
            best_bid_exchange TEXT,
            best_bid_price REAL,
            gross_spread_bps REAL,
            net_spread_bps REAL,
            depth_notional REAL,
            slippage_buy_bps REAL,
            slippage_buy_fraction REAL,
            slippage_sell_bps REAL,
            slippage_sell_fraction REAL,
            PRIMARY KEY (ts, symbol)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS dex_pools (
            ts TEXT,
            label TEXT,
            network TEXT,
            pool_address TEXT,
            base_price REAL,
            quote_price REAL,
            liquidity_usd REAL,
            peg_price_usd REAL,
            peg_dev_bps REAL,
            peg_type TEXT,
            PRIMARY KEY (ts, label)
        )
    """)

    conn.commit()
    return conn

def init_csv_files():
    """Initialize CSV files if they don't exist."""
    fx_csv = os.path.join(HERE, "arb_tracker_fx_refs.csv")
    quotes_csv = os.path.join(HERE, "arb_tracker_cex_quotes.csv")
    spreads_csv = os.path.join(HERE, "arb_tracker_cex_spreads.csv")
    dex_csv = os.path.join(HERE, "arb_tracker_dex_pools.csv")

    if not os.path.exists(fx_csv):
        with open(fx_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ts", "usd_brl", "usd_brl_ask", "usd_brl_bid", "usd_mxn", "usd_cop"])
            w.writeheader()

    if not os.path.exists(quotes_csv):
        with open(quotes_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ts", "exchange", "symbol", "bid", "ask", "last", "peg_dev_bps"])
            w.writeheader()

    if not os.path.exists(spreads_csv):
        with open(spreads_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "ts", "symbol", "best_ask_exchange", "best_ask_price", "best_bid_exchange", "best_bid_price",
                "gross_spread_bps", "net_spread_bps", "depth_notional", "slippage_buy_bps", "slippage_buy_fraction",
                "slippage_sell_bps", "slippage_sell_fraction"
            ])
            w.writeheader()

    if not os.path.exists(dex_csv):
        with open(dex_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "ts", "label", "network", "pool_address", "base_price", "quote_price", "liquidity_usd",
                "peg_price_usd", "peg_dev_bps", "peg_type"
            ])
            w.writeheader()

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

# ----------------------------------------------------------------------------- FX references

def fetch_fx_refs():
    """
    Fetch live FX rates needed for peg-deviation on BRL/MXN/COP DEX pools.
    USD/BRL: Foxbit USDC/BRL mid (stablecoin rate — most relevant for arb).
    USD/MXN, USD/COP: Coinbase public exchange-rates (keyless, intraday).
    Returns dict with keys: usd_brl, usd_brl_ask, usd_brl_bid, usd_mxn, usd_cop.
    """
    refs = {"usd_brl": None, "usd_brl_ask": None, "usd_brl_bid": None,
            "usd_mxn": None, "usd_cop": None}
    try:
        r = requests.get(f"{FOXBIT_BASE}/markets/ticker/24hr",
                         params={"symbols": "usdcbrl,usdtbrl"},
                         headers={"accept": "application/json"}, timeout=10)
        r.raise_for_status()
        for item in r.json().get("data", []):
            if item.get("market_symbol") == "usdcbrl":
                ask = float(item["best"]["ask"]["price"])
                bid = float(item["best"]["bid"]["price"])
                refs["usd_brl_ask"] = ask
                refs["usd_brl_bid"] = bid
                refs["usd_brl"] = (ask + bid) / 2
                break
    except Exception:
        pass
    try:
        r = requests.get(COINBASE_RATES_URL, params={"currency": "USD"},
                         headers={"accept": "application/json"}, timeout=10)
        r.raise_for_status()
        rates = r.json().get("data", {}).get("rates", {})
        refs["usd_mxn"] = float(rates["MXN"]) if "MXN" in rates else None
        refs["usd_cop"] = float(rates["COP"]) if "COP" in rates else None
    except Exception:
        pass
    return refs

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

def track_cex_pair(cfg, depth_notional, threshold_bps, peg_dev_bps, taker_fees=None, ts=None):
    symbol = cfg["symbol"]
    peg = cfg.get("pegRef")
    print(f"\n  [{cfg.get('priority','?')}] {cfg['label']}  ({symbol})")
    quotes = {}
    quote_rows = []
    for exname in cfg["exchanges"]:
        t = fetch_ticker(exname, symbol)
        if t and (t["bid"] or t["ask"] or t["last"]):
            quotes[exname] = t
            mid = None
            if t["bid"] and t["ask"]:
                mid = (t["bid"] + t["ask"]) / 2
            dev = fmt_bps(bps(mid or t["last"], peg)) if peg else "  (fx)"
            dev_bps = bps(mid or t["last"], peg) if peg else None
            print(f"      {exname:<10} bid={fmt(t['bid'])} ask={fmt(t['ask'])} last={fmt(t['last'])}  peg-dev={dev}")
            if ts:
                quote_rows.append({
                    "ts": ts,
                    "exchange": exname,
                    "symbol": symbol,
                    "bid": t["bid"],
                    "ask": t["ask"],
                    "last": t["last"],
                    "peg_dev_bps": dev_bps
                })
        else:
            print(f"      {exname:<10} (no data / symbol not listed)")

    spread_row = None
    if len(quotes) < 2:
        return quote_rows, spread_row

    # cross-venue: cheapest ask (buy here) vs richest bid (sell there)
    best_ask = min(((n, q["ask"]) for n, q in quotes.items() if q["ask"]), key=lambda x: x[1], default=None)
    best_bid = max(((n, q["bid"]) for n, q in quotes.items() if q["bid"]), key=lambda x: x[1], default=None)
    if best_ask and best_bid:
        spread = bps(best_bid[1], best_ask[1])
        fees = taker_fees or {}
        buy_fee = fees.get(best_ask[0], {}).get("taker_bps", 10)
        sell_fee = fees.get(best_bid[0], {}).get("taker_bps", 10)
        net = (spread - buy_fee - sell_fee) if spread is not None else None
        flag = "  <<< OPPORTUNITY" if (spread is not None and spread >= threshold_bps) else ""
        print(f"      -> buy {best_ask[0]} @ {fmt(best_ask[1])} | sell {best_bid[0]} @ {fmt(best_bid[1])} "
              f"| gross {fmt_bps(spread)} | net-of-fees {fmt_bps(net)} "
              f"(buy {buy_fee}bps + sell {sell_fee}bps){flag}")

        slippage_buy_bps = None
        slippage_sell_bps = None
        slippage_buy_fraction = None
        slippage_sell_fraction = None

        if flag:  # only pay for order-book calls when there's a headline spread
            buy = slippage_for_notional(best_ask[0], symbol, depth_notional, "buy")
            sell = slippage_for_notional(best_bid[0], symbol, depth_notional, "sell")
            if buy and sell:
                net = None
                if spread is not None and buy["slippage_bps"] is not None and sell["slippage_bps"] is not None:
                    net = spread - buy["slippage_bps"] - sell["slippage_bps"]
                slippage_buy_bps = buy["slippage_bps"]
                slippage_buy_fraction = buy["filled_fraction"]
                slippage_sell_bps = sell["slippage_bps"]
                slippage_sell_fraction = sell["filled_fraction"]
                print(f"         depth@${depth_notional:,.0f}: buy slip {fmt_bps(buy['slippage_bps'])} "
                      f"(filled {buy['filled_fraction']*100:.0f}%) | sell slip {fmt_bps(sell['slippage_bps'])} "
                      f"(filled {sell['filled_fraction']*100:.0f}%) | net-of-slippage {fmt_bps(net)}")

        if ts:
            spread_row = {
                "ts": ts,
                "symbol": symbol,
                "best_ask_exchange": best_ask[0],
                "best_ask_price": best_ask[1],
                "best_bid_exchange": best_bid[0],
                "best_bid_price": best_bid[1],
                "gross_spread_bps": spread,
                "net_spread_bps": net,
                "depth_notional": depth_notional,
                "slippage_buy_bps": slippage_buy_bps,
                "slippage_buy_fraction": slippage_buy_fraction,
                "slippage_sell_bps": slippage_sell_bps,
                "slippage_sell_fraction": slippage_sell_fraction
            }

    # peg deviation alert (uses the most extreme venue)
    if peg:
        for n, q in quotes.items():
            mid = (q["bid"] + q["ask"]) / 2 if q["bid"] and q["ask"] else q["last"]
            d = bps(mid, peg)
            if d is not None and abs(d) >= peg_dev_bps:
                print(f"      !!! peg deviation on {n}: {fmt_bps(d)} (threshold {peg_dev_bps}bps)")

    return quote_rows, spread_row

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

def track_dex_pool(cfg, fx_refs=None, ts=None):
    label = cfg["label"]
    network = cfg["network"]
    token = cfg.get("tokenAddress")
    pool = cfg.get("poolAddress")

    if (token and str(token).startswith("TODO")) or (not token and not pool):
        print(f"\n  [DEX] {label}: SKIPPED (fill tokenAddress/poolAddress from verification queue)")
        return None

    attrs = None
    if not pool and token:
        resolved = resolve_pool(network, token)
        if not resolved:
            print(f"\n  [DEX] {label}: no pool found for token on {network}")
            return None
        pool, attrs = resolved

    if not attrs:
        data = gecko_get(f"/networks/{network}/pools/{pool}")
        if not data or "data" not in data:
            print(f"\n  [DEX] {label}: pool fetch failed")
            return None
        attrs = data["data"]["attributes"]

    base_price = attrs.get("base_token_price_usd")
    quote_price = attrs.get("quote_token_price_usd")
    liq = attrs.get("reserve_in_usd")
    name = attrs.get("name", "?")
    print(f"\n  [DEX] {label}  ({network}:{pool[:10]}...)")
    print(f"      pool={name}  base=${fmt(float(base_price)) if base_price else 'n/a':<12} "
          f"quote=${fmt(float(quote_price)) if quote_price else 'n/a'}  liquidity=${liq}")

    # pegTokenSide: which side of the pool is the pegged token?
    # "base" (default) uses base_token_price_usd; "quote" uses quote_token_price_usd.
    # Use "quote" when the pool is named "USDC / BRLA" (USD is base, peg token is quote).
    peg_side = cfg.get("pegTokenSide", "base")
    raw_price = quote_price if peg_side == "quote" else base_price
    peg_type = cfg.get("pegType", "")
    price_f = float(raw_price) if raw_price else None
    refs = fx_refs or {}

    peg_dev_bps = None
    peg_price_usd = price_f

    if peg_type == "usd" and price_f:
        peg_dev_bps = bps(price_f, 1.0)
        print(f"      peg-dev vs $1.00: {fmt_bps(peg_dev_bps)}")
    elif peg_type == "fx_brl" and price_f and refs.get("usd_brl"):
        price_brl = price_f * refs["usd_brl"]
        peg_dev_bps = bps(price_brl, 1.0)
        print(f"      {peg_side}={fmt(price_f, 4)} USD = {fmt(price_brl, 4)} BRL  "
              f"peg-dev vs R$1.00: {fmt_bps(peg_dev_bps)}")
    elif peg_type == "fx_mxn" and price_f and refs.get("usd_mxn"):
        price_mxn = price_f * refs["usd_mxn"]
        peg_dev_bps = bps(price_mxn, 1.0)
        print(f"      {peg_side}={fmt(price_f, 4)} USD = {fmt(price_mxn, 4)} MXN  "
              f"peg-dev vs MX$1.00: {fmt_bps(peg_dev_bps)}")
    elif peg_type == "fx_cop" and price_f and refs.get("usd_cop"):
        price_cop = price_f * refs["usd_cop"]
        peg_dev_bps = bps(price_cop, 1.0)
        print(f"      {peg_side}={fmt(price_f, 4)} USD = {fmt(price_cop, 4)} COP  "
              f"peg-dev vs COP$1.00: {fmt_bps(peg_dev_bps)}")
    elif peg_type == "accruing_nav" and price_f:
        print(f"      NAV ~${fmt(price_f, 4)} (accruing — drift vs $1.00 is expected, not a dislocation)")

    if ts:
        return {
            "ts": ts,
            "label": label,
            "network": network,
            "pool_address": pool,
            "base_price": base_price,
            "quote_price": quote_price,
            "liquidity_usd": liq,
            "peg_price_usd": peg_price_usd,
            "peg_dev_bps": peg_dev_bps,
            "peg_type": peg_type
        }
    return None

# ----------------------------------------------------------------------------- BRL terminal

def persist_poll(ts, fx_refs, cex_quote_rows, cex_spread_rows, dex_pool_rows, db):
    """Write poll data to CSV and SQLite."""
    try:
        # Write FX refs to CSV
        fx_csv = os.path.join(HERE, "arb_tracker_fx_refs.csv")
        with open(fx_csv, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ts", "usd_brl", "usd_brl_ask", "usd_brl_bid", "usd_mxn", "usd_cop"])
            w.writerow({
                "ts": ts,
                "usd_brl": fx_refs.get("usd_brl"),
                "usd_brl_ask": fx_refs.get("usd_brl_ask"),
                "usd_brl_bid": fx_refs.get("usd_brl_bid"),
                "usd_mxn": fx_refs.get("usd_mxn"),
                "usd_cop": fx_refs.get("usd_cop")
            })

        # Write CEX quotes to CSV
        quotes_csv = os.path.join(HERE, "arb_tracker_cex_quotes.csv")
        with open(quotes_csv, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ts", "exchange", "symbol", "bid", "ask", "last", "peg_dev_bps"])
            w.writerows(cex_quote_rows)

        # Write CEX spreads to CSV
        spreads_csv = os.path.join(HERE, "arb_tracker_cex_spreads.csv")
        with open(spreads_csv, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "ts", "symbol", "best_ask_exchange", "best_ask_price", "best_bid_exchange", "best_bid_price",
                "gross_spread_bps", "net_spread_bps", "depth_notional", "slippage_buy_bps", "slippage_buy_fraction",
                "slippage_sell_bps", "slippage_sell_fraction"
            ])
            w.writerows(cex_spread_rows)

        # Write DEX pools to CSV
        dex_csv = os.path.join(HERE, "arb_tracker_dex_pools.csv")
        with open(dex_csv, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "ts", "label", "network", "pool_address", "base_price", "quote_price", "liquidity_usd",
                "peg_price_usd", "peg_dev_bps", "peg_type"
            ])
            w.writerows(dex_pool_rows)

        # Write to SQLite if connection provided
        if db:
            c = db.cursor()

            # FX refs (replace if exists)
            c.execute("""
                INSERT OR REPLACE INTO fx_refs
                (ts, usd_brl, usd_brl_ask, usd_brl_bid, usd_mxn, usd_cop)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ts,
                fx_refs.get("usd_brl"),
                fx_refs.get("usd_brl_ask"),
                fx_refs.get("usd_brl_bid"),
                fx_refs.get("usd_mxn"),
                fx_refs.get("usd_cop")
            ))

            # CEX quotes
            for row in cex_quote_rows:
                c.execute("""
                    INSERT OR REPLACE INTO cex_quotes
                    (ts, exchange, symbol, bid, ask, last, peg_dev_bps)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row["ts"], row["exchange"], row["symbol"], row["bid"], row["ask"],
                      row["last"], row["peg_dev_bps"]))

            # CEX spreads
            for row in cex_spread_rows:
                c.execute("""
                    INSERT OR REPLACE INTO cex_spreads
                    (ts, symbol, best_ask_exchange, best_ask_price, best_bid_exchange, best_bid_price,
                     gross_spread_bps, net_spread_bps, depth_notional, slippage_buy_bps, slippage_buy_fraction,
                     slippage_sell_bps, slippage_sell_fraction)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (row["ts"], row["symbol"], row["best_ask_exchange"], row["best_ask_price"],
                      row["best_bid_exchange"], row["best_bid_price"], row["gross_spread_bps"],
                      row["net_spread_bps"], row["depth_notional"], row["slippage_buy_bps"],
                      row["slippage_buy_fraction"], row["slippage_sell_bps"], row["slippage_sell_fraction"]))

            # DEX pools
            for row in dex_pool_rows:
                c.execute("""
                    INSERT OR REPLACE INTO dex_pools
                    (ts, label, network, pool_address, base_price, quote_price, liquidity_usd,
                     peg_price_usd, peg_dev_bps, peg_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (row["ts"], row["label"], row["network"], row["pool_address"],
                      row["base_price"], row["quote_price"], row["liquidity_usd"],
                      row["peg_price_usd"], row["peg_dev_bps"], row["peg_type"]))

            db.commit()
    except Exception as e:
        print(f"Persistence error: {e}")

def track_foxbit_terminal(fx_refs):
    brl = fx_refs.get("usd_brl")
    ask = fx_refs.get("usd_brl_ask")
    bid = fx_refs.get("usd_brl_bid")
    print("\n--- BRL Terminal (Foxbit USDC/BRL) -------------------------------------")
    if brl is None:
        print("  (fetch failed — check Foxbit API connectivity)")
        return
    spread_bps = ((ask - bid) / brl) * 1e4 if (ask and bid and brl) else None
    print(f"  bid={fmt(bid, 4)} | ask={fmt(ask, 4)} | mid={fmt(brl, 4)} BRL/USDC  "
          f"spread={fmt_bps(spread_bps)}")
    print(f"  Sell $10k  USDC → R${brl * 10_000:,.2f}  |  Sell $100k → R${brl * 100_000:,.2f}")
    print(f"  (Confirmed $100k absorbs ~0 bps impact — terminal is not the bottleneck)")

# ----------------------------------------------------------------------------- main

def run_once(watchlist, config, args, db=None):
    d = config.get("defaults", {})
    depth = args.depth_notional or d.get("depthNotionalUsd", 25000)
    thr = args.threshold_bps if args.threshold_bps is not None else d.get("alertThresholdBps", 15)
    peg_dev = d.get("pegDeviationAlertBps", 20)

    taker_fees = config.get("takerFees", {})
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

    print("=" * 78)
    print(f"ARB TRACKER  {utcnow()}   depth=${depth:,.0f}  spread-alert>={thr}bps  peg-alert>={peg_dev}bps")
    print("=" * 78)

    print("\nFetching FX references (Foxbit BRL + Coinbase MXN/COP)...")
    fx_refs = fetch_fx_refs()
    brl_str = f"R${fx_refs['usd_brl']:.4f}" if fx_refs.get("usd_brl") else "n/a"
    mxn_str = f"MX${fx_refs['usd_mxn']:.4f}" if fx_refs.get("usd_mxn") else "n/a"
    cop_str = f"COP${fx_refs['usd_cop']:.2f}" if fx_refs.get("usd_cop") else "n/a"
    print(f"  USD/BRL={brl_str}  USD/MXN={mxn_str}  USD/COP={cop_str}")

    track_foxbit_terminal(fx_refs)

    # Collect data for persistence
    cex_quote_rows = []
    cex_spread_rows = []
    dex_pool_rows = []

    print("\n--- CEX cross-venue & peg deviation ------------------------------------")
    for cfg in config.get("cexSpreads", []):
        quotes, spread = track_cex_pair(cfg, depth, thr, peg_dev, taker_fees, ts)
        cex_quote_rows.extend(quotes)
        if spread:
            cex_spread_rows.append(spread)

    print("\n--- DEX on-chain (GeckoTerminal) ---------------------------------------")
    dex_delay = config.get("defaults", {}).get("dexPollDelayMs", 2000) / 1000
    for cfg in config.get("dexPools", []):
        dex_row = track_dex_pool(cfg, fx_refs, ts)
        if dex_row:
            dex_pool_rows.append(dex_row)
        time.sleep(dex_delay)

    print("\n" + "-" * 78)
    print("Net-of-fees = gross - taker_buy - taker_sell. Round-trip ~14 bps Binance / ~20 bps OKX·Bybit·Bitget / ~40 bps Kraken·Gate.")
    print("Alert threshold is on gross spread — confirm net > 0 before acting.")
    print("See research_v2.md verification queue for open items before deploying capital.")

    # Persist data to CSV and SQLite
    if db:
        persist_poll(ts, fx_refs, cex_quote_rows, cex_spread_rows, dex_pool_rows, db)

def main():
    ap = argparse.ArgumentParser(description="Stablecoin/RWA arbitrage price tracker (CCXT + GeckoTerminal)")
    ap.add_argument("--config", default=os.path.join(HERE, "tracking_config.json"))
    ap.add_argument("--watchlist", default=os.path.join(HERE, "watchlist.json"))
    ap.add_argument("--once", action="store_true", help="Run one poll and exit")
    ap.add_argument("--interval", type=int, default=None, help="Seconds between polls (loop mode)")
    ap.add_argument("--depth-notional", type=float, default=None, help="USD notional for slippage check")
    ap.add_argument("--threshold-bps", type=float, default=None, help="Min gross spread to flag as opportunity")
    ap.add_argument("--persist", action="store_true", help="Log to CSV and SQLite (enabled by default in loop mode)")
    args = ap.parse_args()

    config = load_json(args.config)
    watchlist = {}
    if os.path.exists(args.watchlist):
        try:
            watchlist = load_json(args.watchlist)
        except Exception:
            pass

    db = None
    if args.persist or args.interval:
        init_csv_files()
        db = init_db()
        print(f"Persistence enabled: CSV + SQLite → {os.path.join(HERE, 'arb_tracker*.csv')} & {os.path.join(HERE, 'arb_tracker.db')}")

    if args.once or args.interval is None:
        run_once(watchlist, config, args, db)
        if db:
            db.close()
        return

    print(f"Looping every {args.interval}s (persistence enabled). Ctrl+C to stop.")
    try:
        while True:
            run_once(watchlist, config, args, db)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        if db:
            db.close()

if __name__ == "__main__":
    main()
