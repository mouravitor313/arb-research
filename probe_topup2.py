"""Probe 2: corrected Foxbit quote schema + resolve networks for deep pools."""
import json, sys, time, requests
sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "arb-probe/1.0", "Accept": "application/json"}
GT = "https://api.geckoterminal.com/api/v2"

def jget(url, params=None):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=25)
        return r.json() if r.status_code == 200 else {"_status": r.status_code, "_body": r.text[:400]}
    except Exception as e:
        return {"_error": str(e)}

def hr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# ---- Foxbit corrected quote schema: base_currency / quote_currency / side / amount ----
hr("FOXBIT v3 quotes — corrected schema, size-aware terminal (USDC/BRL, USDT/BRL)")
for base in ("usdc", "usdt"):
    for side in ("buy", "sell"):
        # try amount in base units ~ $10k and $100k (1 unit ~= 1 USD)
        for amt in (10000, 100000):
            q = jget("https://api.foxbit.com.br/rest/v3/markets/quotes",
                     {"base_currency": base, "quote_currency": "brl", "side": side, "amount": amt})
            print(f"  {base}/brl {side:4s} amount(base)={amt:>7} -> {json.dumps(q)[:260]}")
            time.sleep(1.1)

# ---- Resolve networks + reserves for the deep candidate pools ----
def top_pools(query, label):
    hr(f"GeckoTerminal — {label} pools with NETWORK resolved")
    res = jget(f"{GT}/search/pools", {"query": query})
    data = res.get("data", []) if isinstance(res, dict) else []
    rows = []
    for p in data:
        a = p.get("attributes", {}) or {}
        rel = p.get("relationships", {}) or {}
        netobj = (rel.get("network") or {}).get("data") or {}
        net = netobj.get("id", "?")
        rows.append((float(a.get("reserve_in_usd") or 0), net, a.get("name", "?"),
                     a.get("address", "")[:12], (a.get("volume_usd", {}) or {}).get("h24")))
    rows.sort(reverse=True)
    for liq, net, name, addr, vol in rows[:10]:
        print(f"  liq=${liq:>14,.0f}  net={net:14s} {name:26s} vol24h={vol} addr={addr}")
    time.sleep(2.2)

top_pools("USDY", "USDY")
top_pools("BRLA", "BRLA")
