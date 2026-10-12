"""Quote-only (dry): NEAR Intents 1Click USDC <-> Gnosis USDC.e. READ-ONLY, no deposit address used. Writes near_quotes.json."""
import datetime, json, os, time, requests
HERE = os.path.dirname(os.path.abspath(__file__))
A = {"base": "nep141:base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near",
     "arb": "nep141:arb-0xaf88d065e77c8cc2239327c5edb3a432268e5831.omft.near",
     "eth": "nep141:eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near",
     "gnosis": "nep141:gnosis-0x2a22f9c3b484c3629090feed35f17ff8f88f76f0.omft.near"}
D = "0x1111111111111111111111111111111111111111"
out = []
for src, dst in (("base", "gnosis"), ("arb", "gnosis"), ("eth", "gnosis"), ("gnosis", "base")):
    for usd in (2_000, 10_000, 50_000):
        body = {"dry": True, "swapType": "EXACT_INPUT", "slippageTolerance": 50, "originAsset": A[src],
                "depositType": "ORIGIN_CHAIN", "destinationAsset": A[dst], "amount": str(usd * 10**6),
                "refundTo": D, "refundType": "ORIGIN_CHAIN", "recipient": D, "recipientType": "DESTINATION_CHAIN",
                "deadline": (datetime.datetime.utcnow() + datetime.timedelta(minutes=30)).isoformat() + "Z"}
        r = requests.post("https://1click.chaindefuser.com/v0/quote", json=body, timeout=30)
        j = r.json()
        if r.ok:
            q = j["quote"]
            o = int(q["amountOut"]) / 1e6
            rec = {"route": f"{src}->{dst}", "usd": usd, "out": o, "cost_bps": (usd - o) / usd * 1e4,
                   "secs": q.get("timeEstimate")}
        else:
            rec = {"route": f"{src}->{dst}", "usd": usd, "error": str(j)[:150]}
        print(rec)
        out.append(rec)
        time.sleep(1.5)
json.dump(out, open(os.path.join(HERE, "near_quotes.json"), "w"), indent=1)
