"""One-shot: Hyperliquid spot BRLA/USDC book vs OKX USDC-BRL (public info API). READ-ONLY."""
import json, os, requests
from l2common import HERE, okx_book
I = "https://api.hyperliquid.xyz/info"
meta = requests.post(I, json={"type": "spotMeta"}, timeout=15).json()
toks = {t["index"]: t for t in meta["tokens"]}
pairs = [u for u in meta["universe"] if any(toks[i]["name"].upper() == "BRLA" for i in u["tokens"])]
ok = okx_book("USDC-BRL"); mid = (ok["bids"][0][0] + ok["asks"][0][0]) / 2
out = {"okx_mid": mid, "pairs": []}
for u in pairs:
    b = requests.post(I, json={"type": "l2Book", "coin": u["name"]}, timeout=15).json()
    bids = [(float(x["px"]), float(x["sz"])) for x in b["levels"][0]]
    asks = [(float(x["px"]), float(x["sz"])) for x in b["levels"][1]]
    names = [toks[i]["name"] for i in u["tokens"]]
    # px = USDC per BRLA -> BRLA per USDC = 1/px
    r = {"coin": u["name"], "tokens": names, "best_bid_usdc_per_brla": bids[0][0] if bids else None,
         "best_ask": asks[0][0] if asks else None,
         "bid_depth_usd": sum(p * q for p, q in bids), "ask_depth_usd": sum(p * q for p, q in asks)}
    if bids and asks:
        m = (bids[0][0] + asks[0][0]) / 2
        r["mid_brla_per_usd"] = 1 / m
        r["dev_vs_okx_bps"] = (1 / m / mid - 1) * 1e4
        r["spread_bps"] = (asks[0][0] / bids[0][0] - 1) * 1e4
    out["pairs"].append(r)
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(HERE, "hl_probe.json"), "w"), indent=1)
