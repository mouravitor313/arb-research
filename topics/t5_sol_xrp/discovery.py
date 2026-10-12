"""Descoberta: AMMs + CLOB do XRPL para XRP/RLUSD e XRP/USDC; profundidade dos livros OKX. Só leitura."""
import json, time, requests
from t5_collector import XTOK, xrpl, S, OKX_BOOK

out = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "xrpl": {}, "okx": {}}
for tok, (t, _) in XTOK.items():
    a = xrpl("amm_info", {"asset": {"currency": "XRP"}, "asset2": t})["amm"]
    x, y = int(a["amount"]) / 1e6, float(a["amount2"]["value"])
    px = y / x
    d = {"amm_account": a["account"], "xrp": x, "stable": y, "px": px, "tvl_usd": 2 * y,
         "trading_fee_pct": a["trading_fee"] / 1000}
    # CLOB: ofertas vendendo XRP (asks) e comprando XRP (bids), em USD dentro de ±1% e ±5%
    for side, gets, pays in (("asks", {"currency": "XRP"}, t), ("bids", t, {"currency": "XRP"})):
        offs = xrpl("book_offers", {"taker_gets": gets, "taker_pays": pays, "limit": 400}).get("offers", [])
        lv = []
        for o in offs:
            g = o.get("taker_gets_funded", o["TakerGets"]); p = o.get("taker_pays_funded", o["TakerPays"])
            if side == "asks":
                q = int(g) / 1e6 if isinstance(g, str) else float(g["value"]); usd = float(p["value"])
            else:
                usd = float(g["value"]); q = int(p) / 1e6
            if q > 0: lv.append((usd / q, usd))
        for band in (0.01, 0.05):
            ok = [u for pr, u in lv if (pr <= px * (1 + band) if side == "asks" else pr >= px * (1 - band))]
            d[f"clob_{side}_usd_{int(band*100)}pct"] = round(sum(ok))
        d[f"clob_{side}_n"] = len(lv)
    out["xrpl"][f"XRP/{tok}"] = d
for inst in ["SOL-BRL", "XRP-BRL", "USDT-BRL", "USDC-BRL", "PEPE-BRL", "PI-BRL", "TRUMP-BRL", "RLUSD-USDT"]:
    b = S.get(OKX_BOOK, params={"instId": inst, "sz": 400}, timeout=8).json()["data"][0]
    a = [(float(p), float(q)) for p, q, *_ in b["asks"]]; bi = [(float(p), float(q)) for p, q, *_ in b["bids"]]
    m = (a[0][0] + bi[0][0]) / 2
    d = {"spread_bps": round((a[0][0] - bi[0][0]) / m * 1e4, 1)}
    for band in (0.01, 0.05):
        d[f"ask_quote_{int(band*100)}pct"] = round(sum(p * q for p, q in a if p <= m * (1 + band)))
        d[f"bid_quote_{int(band*100)}pct"] = round(sum(p * q for p, q in bi if p >= m * (1 - band)))
    out["okx"][inst] = d
tk = {x["instId"]: x for x in S.get("https://www.okx.com/api/v5/market/tickers", params={"instType": "SPOT"}).json()["data"]}
for inst in out["okx"]:
    out["okx"][inst]["vol24h_quote"] = round(float(tk[inst]["volCcy24h"]))
json.dump(out, open("discovery.json", "w"), indent=1)
print(json.dumps(out, indent=1))
