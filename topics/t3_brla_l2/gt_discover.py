"""Find BRLA pools on every chain via GeckoTerminal (pool *discovery only*; prices come from quoters).

READ-ONLY, public API, <= ~20 req/min. Writes gt_brla_pools.json next to this file.

    python topics/t3_brla_l2/gt_discover.py
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
SLEEP = 3.5


def get(path, **params):
    for i in range(4):
        r = requests.get(GT + path, params=params, headers=H, timeout=20)
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
            "last_price_base_usd": a.get("base_token_price_usd"),
            "last_price_quote_usd": a.get("quote_token_price_usd"),
        }


def main():
    pools: dict[str, dict] = {}
    for page in range(1, 6):
        resp = get("/search/pools", query="BRLA", page=page, include="base_token,quote_token")
        got = list(rows(resp))
        for r in got:
            pools[f"{r['network']}:{r['address']}"] = r
        if len(got) < 20:
            break
    # every BRLA token address seen -> its full pool list on that network
    brla = {(r["network"], r[k]) for r in pools.values() for k in ("base", "quote")
            if (r[f"{k}_sym"] or "").upper() == "BRLA"}
    for net, addr in sorted(brla):
        for page in (1, 2):
            resp = get(f"/networks/{net}/tokens/{addr}/pools", page=page, include="base_token,quote_token")
            got = list(rows(resp))
            for r in got:
                pools[f"{r['network']}:{r['address']}"] = r
            if len(got) < 20:
                break
    out = sorted(pools.values(), key=lambda r: -r["tvl_usd"])
    json.dump({"brla_tokens": sorted(brla), "pools": out}, open(os.path.join(HERE, "gt_brla_pools.json"), "w"),
              indent=1)
    print("BRLA tokens:", sorted(brla))
    for r in out:
        print(f"{r['network']:12s} {r['dex']:28s} {r['name'][:34]:34s} {r['address']} "
              f"tvl ${r['tvl_usd']:>10,.0f} vol24 ${r['vol24_usd']:>9,.0f} tx {r['tx24']}")


if __name__ == "__main__":
    main()
