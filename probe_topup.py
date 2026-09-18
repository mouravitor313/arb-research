"""One-shot top-up probe: reconcile harness 'CLAIMED' figures against live data.
- Foxbit public v3: which BRL pairs exist + size-aware quotes (terminal anchor).
- GeckoTerminal: depth for new candidates surfaced by the harness.
No API keys. Read-only.
"""
import json
import sys
import time
import requests

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "arb-probe/1.0", "Accept": "application/json"}
GT = "https://api.geckoterminal.com/api/v2"


def jget(url, params=None):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=25)
        if r.status_code != 200:
            return {"_status": r.status_code, "_body": r.text[:300]}
        return r.json()
    except Exception as e:  # noqa
        return {"_error": str(e)}


def hr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


# ---------------- Foxbit ----------------
hr("FOXBIT public REST v3 — markets & size-aware quotes (terminal anchor)")
markets = jget("https://api.foxbit.com.br/rest/v3/markets")
syms = []
if isinstance(markets, dict) and "data" in markets:
    for m in markets["data"]:
        sym = m.get("symbol", "")
        base = (m.get("base") or {}).get("symbol", "")
        quote = (m.get("quote") or {}).get("symbol", "")
        if quote.lower() == "brl" or base.lower() in ("brla", "brz"):
            syms.append(sym)
    print(f"BRL-quoted / BRL-stable markets found ({len(syms)}): {sorted(syms)}")
else:
    print("markets endpoint response:", json.dumps(markets)[:400])

# size-aware quotes at $10k and $100k equiv (in BRL ~ 5.4/USD -> 54k / 540k BRL)
targets = ["usdcbrl", "usdtbrl", "brlabrl", "brzbrl"]
for sym in targets:
    for amount_brl in (54000, 540000):
        q = jget(
            "https://api.foxbit.com.br/rest/v3/markets/quotes",
            {"market_symbol": sym, "side": "buy", "amount": amount_brl, "amount_type": "quote"},
        )
        print(f"  {sym:9s} buy amount_brl={amount_brl:>7} -> {json.dumps(q)[:280]}")
        time.sleep(1.2)

# ---------------- GeckoTerminal ----------------
candidates = [
    ("BRLA", "search", "BRLA"),
    ("BRZ", "search", "BRZ"),
    ("USYC", "search", "USYC"),
    ("USDY", "search", "USDY"),
]
for name, mode, query in candidates:
    hr(f"GeckoTerminal — top pools for {name}")
    res = jget(f"{GT}/search/pools", {"query": query, "page": 1})
    pools = (res or {}).get("data", []) if isinstance(res, dict) else []
    rows = []
    for p in pools[:12]:
        a = p.get("attributes", {})
        rel = p.get("relationships", {})
        net = (rel.get("network", {}).get("data", {}) or {}).get("id", "?")
        rows.append(
            (
                float(a.get("reserve_in_usd") or 0),
                a.get("name", "?"),
                net,
                a.get("base_token_price_usd"),
                (a.get("volume_usd", {}) or {}).get("h24"),
            )
        )
    rows.sort(reverse=True)
    for liq, pname, net, price, vol in rows[:8]:
        print(f"  liq=${liq:>14,.0f}  {net:14s} {pname:28s} px={price} vol24h={vol}")
    if not rows:
        print("  (no pools / ", json.dumps(res)[:200], ")")
    time.sleep(2.2)

# Validate the harness's headline: Polygon USDC/USDT ~$8.3M
hr("GeckoTerminal — Polygon top pools (validate ~$8.3M USDC/USDT claim)")
res = jget(f"{GT}/networks/polygon_pos/pools", {"page": 1})
pools = (res or {}).get("data", []) if isinstance(res, dict) else []
for p in pools[:10]:
    a = p.get("attributes", {})
    print(f"  liq=${float(a.get('reserve_in_usd') or 0):>14,.0f}  {a.get('name','?'):30s} vol24h={(a.get('volume_usd',{}) or {}).get('h24')}")
