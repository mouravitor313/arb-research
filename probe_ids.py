"""Capture full pool ids ({network}_{address}) + token addresses for config wiring."""
import json, sys, time, requests
sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "arb-probe/1.0", "Accept": "application/json"}
GT = "https://api.geckoterminal.com/api/v2"

def jget(url, params=None):
    r = requests.get(url, params=params, headers=UA, timeout=25)
    return r.json() if r.status_code == 200 else {"_status": r.status_code}

def show(query, want):
    res = jget(f"{GT}/search/pools", {"query": query})
    data = res.get("data", []) if isinstance(res, dict) else []
    rows = []
    for p in data:
        a = p.get("attributes", {}) or {}
        rows.append((float(a.get("reserve_in_usd") or 0), p.get("id", "?"),
                     a.get("name", "?"), (a.get("volume_usd", {}) or {}).get("h24")))
    rows.sort(reverse=True)
    print(f"\n=== {query} (top {want}) ===")
    for liq, pid, name, vol in rows[:want]:
        print(f"  liq=${liq:>13,.0f}  vol24h={str(vol)[:10]:>10}  {name:26s}  id={pid}")
    time.sleep(2.2)

show("BRLA", 6)
show("BRZ", 5)
show("USDY", 6)

# Polygon USDC/USDT direct
res = jget(f"{GT}/networks/polygon_pos/pools", {"page": 1})
print("\n=== polygon_pos top pools (find USDC/USDT) ===")
for p in (res.get("data", []) if isinstance(res, dict) else [])[:12]:
    a = p.get("attributes", {}) or {}
    if "USDC" in a.get("name", "") and "USDT" in a.get("name", ""):
        print(f"  liq=${float(a.get('reserve_in_usd') or 0):>13,.0f}  id={p.get('id')}  {a.get('name')}")
