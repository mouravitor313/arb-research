"""Find DEX pools for tokenized-treasury / NAV-accruing tokens via GeckoTerminal (discovery only;
prices for conclusions come from on-chain quoters).

READ-ONLY, public API, <= ~17 req/min. Writes gt_rwa_pools.json next to this file.

    python topics/t6_rwa/gt_discover.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
GT = "https://api.geckoterminal.com/api/v2"
H = {"accept": "application/json"}
SLEEP = 3.6
MIN_TVL = 50_000

QUERIES = [
    "USDY", "rUSDY", "OUSG", "USTB", "USCC", "USYC", "mTBILL", "TBILL", "USDO", "cUSDO",
    "USD0++", "bIB01", "sUSDS", "sDAI", "syrupUSDC", "syrupUSDT", "sfrxUSD", "scrvUSD",
    "USDtb", "TESOURO", "CETES", "stBRZ", "wUSDM", "BENJI", "JTRSY", "USDz", "sUSDC",
    "stUSDS", "sUSDa", "USTBL", "EUTBL", "wYLDS", "PRIME", "srUSD", "sUSDf", "reUSD",
]


def get(path, **params):
    for i in range(4):
        try:
            r = requests.get(GT + path, params=params, headers=H, timeout=20)
        except requests.RequestException:
            time.sleep(5)
            continue
        if r.status_code == 429:
            time.sleep(20 * (i + 1))
            continue
        time.sleep(SLEEP)
        return r.json() if r.ok else {}
    return {}


def rows(resp):
    toks = {t["id"]: t["attributes"] for t in resp.get("included", []) if t["type"] == "token"}
    for p in resp.get("data", []):
        a, rel = p["attributes"], p["relationships"]
        b, q = rel["base_token"]["data"]["id"], rel["quote_token"]["data"]["id"]
        yield {
            "network": p["id"].rsplit("_", 1)[0], "name": a["name"], "address": a["address"],
            "tvl_usd": float(a.get("reserve_in_usd") or 0),
            "vol24_usd": float((a.get("volume_usd") or {}).get("h24") or 0),
            "tx24": (a.get("transactions") or {}).get("h24"),
            "dex": rel["dex"]["data"]["id"],
            "base": b.split("_", 1)[1], "base_sym": toks.get(b, {}).get("symbol"),
            "quote": q.split("_", 1)[1], "quote_sym": toks.get(q, {}).get("symbol"),
            "base_price_usd": a.get("base_token_price_usd"),
            "quote_price_usd": a.get("quote_token_price_usd"),
        }


def main():
    out: dict[str, list] = {}
    for q in QUERIES:
        seen = {}
        for page in (1, 2):
            got = list(rows(get("/search/pools", query=q, page=page, include="base_token,quote_token")))
            for r in got:
                syms = {(r["base_sym"] or "").upper(), (r["quote_sym"] or "").upper()}
                if q.upper() in syms and r["tvl_usd"] >= MIN_TVL:
                    seen[(r["network"], r["address"])] = r
            if len(got) < 20:
                break
        out[q] = sorted(seen.values(), key=lambda r: -r["tvl_usd"])
        top = out[q][:4]
        print(f"{q:10s} {len(out[q]):3d} pools >= ${MIN_TVL/1e3:.0f}k | " + " ; ".join(
            f"{r['network']}:{r['name']} ${r['tvl_usd']/1e3:.0f}k v{r['vol24_usd']/1e3:.0f}k" for r in top))
    with open(os.path.join(HERE, "gt_rwa_pools.json"), "w", encoding="utf-8") as f:
        json.dump({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "min_tvl": MIN_TVL, "pools": out}, f, indent=1)


if __name__ == "__main__":
    main()
