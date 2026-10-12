"""t2_usdg — OKX USDG books: depth at $1k/$10k/$100k + implied USDG vs USDT/USDC. READ-ONLY public REST."""
import json, sys, time
from datetime import datetime, timezone
sys.path.insert(0, "../..")
import requests
from xvenue_collector import buy_with_quote, sell_base, buy_base

URL = "https://www.okx.com/api/v5/market/books"
INSTS = ["USDG-BRL", "USDG-USDT", "USDT-BRL", "USDC-BRL", "USDC-USDT"]
SIZES = (1_000, 10_000, 100_000)


def book(inst):
    d = requests.get(URL, params={"instId": inst, "sz": 400}, timeout=8).json()["data"][0]
    f = lambda side: [(float(p), float(q)) for p, q, *_ in d[side]]
    return {"asks": f("asks"), "bids": f("bids")}


def depth(b, usd, px_usd=1.0):
    """bps slippage vs mid to buy/sell `usd` worth of base (None if book too thin)."""
    m = (b["asks"][0][0] + b["bids"][0][0]) / 2
    q = usd / px_usd
    c, g = buy_base(b["asks"], q), sell_base(b["bids"], q)
    return (None if c is None else round((c / q / m - 1) * 1e4, 2),
            None if g is None else round((1 - g / q / m) * 1e4, 2))


def main():
    bk = {i: book(i) for i in INSTS}
    out = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "books": {}}
    brl = (bk["USDT-BRL"]["asks"][0][0] + bk["USDT-BRL"]["bids"][0][0]) / 2
    for i, b in bk.items():
        px_usd = brl if i.endswith("-BRL") else 1.0
        tot = lambda side: sum(p * q for p, q in b[side]) / px_usd
        r = {"bid": b["bids"][0][0], "ask": b["asks"][0][0],
             "spread_bps": round((b["asks"][0][0] / b["bids"][0][0] - 1) * 1e4, 2),
             "levels": [len(b["bids"]), len(b["asks"])],
             "depth_usd_400lv": [round(tot("bids")), round(tot("asks"))],
             "slip_bps_buy_sell": {s: depth(b, s * px_usd, px_usd) if i.endswith("-BRL") else depth(b, s) for s in SIZES}}
        out["books"][i] = r
        print(i, r)
    m = lambda i: (bk[i]["asks"][0][0] + bk[i]["bids"][0][0]) / 2
    out["implied"] = {"USDG/USDT via BRL": m("USDG-BRL") / m("USDT-BRL"), "USDG/USDC via BRL": m("USDG-BRL") / m("USDC-BRL"),
                      "USDG-USDT direct": m("USDG-USDT"), "USDC-USDT direct": m("USDC-USDT")}
    print(json.dumps(out["implied"], indent=1))
    with open(f"okx_books_{out['ts'][:19].replace(':','')}.json", "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
