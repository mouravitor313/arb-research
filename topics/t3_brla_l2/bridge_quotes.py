"""Quote-only: cost to move USDC from OKX-supported chains to USDC.e on Gnosis (and back) via LI.FI public API.

READ-ONLY (GET /v1/quote; no signing). Dummy fromAddress. Writes bridge_quotes.json.
"""
import json, os, time, requests
HERE = os.path.dirname(os.path.abspath(__file__))
DUMMY = "0x1111111111111111111111111111111111111111"
USDC = {1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 137: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        100: "0x2a22f9c3b484c3629090FeED35F17Ff8F88f76F0"}
NAME = {1: "ethereum", 8453: "base", 42161: "arbitrum", 137: "polygon", 100: "gnosis"}
out = []
for src, dst in [(8453, 100), (42161, 100), (137, 100), (1, 100), (100, 8453), (100, 42161)]:
    for usd in (2_000, 10_000, 50_000):
        p = {"fromChain": src, "toChain": dst, "fromToken": USDC[src], "toToken": USDC[dst],
             "fromAmount": str(usd * 10**6), "fromAddress": DUMMY, "slippage": 0.005}
        try:
            r = requests.get("https://li.quest/v1/quote", params=p, timeout=30)
            d = r.json()
            if r.ok:
                to = int(d["estimate"]["toAmount"]) / 1e6
                gas = sum(float(g.get("amountUSD") or 0) for g in d["estimate"].get("gasCosts", []))
                fees = sum(float(f.get("amountUSD") or 0) for f in d["estimate"].get("feeCosts", []) if not f.get("included"))
                rec = {"route": f"{NAME[src]}->{NAME[dst]}", "usd": usd, "tool": d.get("tool"), "to_amount": to,
                       "gas_usd": gas, "extra_fees_usd": fees,
                       "cost_bps": ((usd - to) + gas + fees) / usd * 1e4, "secs": d["estimate"].get("executionDuration")}
            else:
                rec = {"route": f"{NAME[src]}->{NAME[dst]}", "usd": usd, "error": str(d.get("message"))[:120]}
        except Exception as e:
            rec = {"route": f"{NAME[src]}->{NAME[dst]}", "usd": usd, "error": str(e)[:120]}
        print(rec)
        out.append(rec)
        time.sleep(2)
json.dump(out, open(os.path.join(HERE, "bridge_quotes.json"), "w"), indent=1)
