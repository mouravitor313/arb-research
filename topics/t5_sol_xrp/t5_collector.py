"""Tópico 5 — SOL (Jupiter) e XRP (XRPL DEX) vs OKX SOL-BRL / XRP-BRL.  Só leitura.

Modelo de inventário pré-posicionado: stable no DEX, BRL/ativo na OKX. Toda perna OKX é taker.
  DtoO: S stable -> compra A no DEX -> vende A em A-BRL -> compra stable em <stable>-BRL
  OtoD: vende stable em <stable>-BRL -> compra A em A-BRL -> vende A no DEX -> stable
  net_bps = (stable final / S - 1) * 1e4, já com taxa OKX VIP 9 (BRL 2 bps), fee do DEX (embutida na
  cotação) e custo de tx (Solana: base + prioridade estimada; XRPL: ~0).
  Referência "nb": mesma coisa fechando no par A-USDT/A-USDC da OKX (taker 11 bps), sem BRL.
RLUSD não tem par BRL na OKX: fecha via USDT-BRL valendo RLUSD = 1 USDT (registramos RLUSD-USDT mid).
Memes (PEPE/PI/TRUMP): triângulo interno OKX  USDT -> A-USDT -> A-BRL -> USDT-BRL  e o inverso.

Uso:  python t5_collector.py --once            (um tick, imprime)
      python t5_collector.py --interval 60 --hours 3   (coletor; pára com arquivo STOP ou .pid)
"""
import argparse, json, logging, os, sqlite3, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data.db")
STOP = os.path.join(HERE, "STOP")
PID = os.path.join(HERE, "collector.pid")

OKX_BOOK = "https://www.okx.com/api/v5/market/books"
INSTS = ["SOL-BRL", "SOL-USDT", "SOL-USDC", "XRP-BRL", "XRP-USDT", "XRP-USDC", "USDT-BRL",
         "USDC-BRL", "RLUSD-USDT", "PEPE-BRL", "PEPE-USDT", "PI-BRL", "PI-USDT", "TRUMP-BRL",
         "TRUMP-USDT"]
FEE_BRL, FEE_NB = 2e-4, 11e-4
SIZES = (1_000, 10_000, 100_000)
BAND = 0.05

JUP = "https://api.jup.ag/swap/v1/quote"   # lite-api.jup.ag/swap/v1 deu 503 em 11/10; este é keyless
JUP_GAP = 2.2                              # ≤ 0,5 req/s
MINT = {"SOL": ("So11111111111111111111111111111111111111112", 9),
        "USDC": ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 6),
        "USDT": ("Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", 6)}
# custo por swap Solana: 5000 lamports base + ~300k CU × 1e6 µlamports/CU de prioridade (folgado)
SOL_TX_SOL = 0.000005 + 0.0003

XRPL = ["https://s1.ripple.com:51234", "https://s2.ripple.com:51234", "https://xrplcluster.com"]
XTOK = {"RLUSD": ({"currency": "524C555344000000000000000000000000000000",
                   "issuer": "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De"}, "rLoD9U2ghXP2xUYbtML6G6v1p8LhM9mSnc"),
        "USDC": ({"currency": "5553444300000000000000000000000000000000",
                  "issuer": "rGm7WCVp9gb4jZHWTEtGUr4dd74z2XuWhE"}, "r39TAwuqkA5BNxxfL5YXewRGtCgBcADjcx")}
# (as contas acima só servem de "source" com saldo para o path finder; nada é assinado)

SCHEMA = """
CREATE TABLE IF NOT EXISTS opps (
  ts TEXT, asset TEXT, venue TEXT, stable TEXT, dir TEXT, close TEXT, size_usd INTEGER,
  net_bps REAL, dex_px REAL, okx_px REAL, ok INTEGER,
  PRIMARY KEY (ts, asset, venue, stable, dir, close, size_usd));
CREATE TABLE IF NOT EXISTS ticks (ts TEXT PRIMARY KEY, data TEXT);
"""
log = logging.getLogger("t5")
S = requests.Session()


# ---------------- OKX ----------------
def fetch_books():
    def one(inst):
        d = S.get(OKX_BOOK, params={"instId": inst, "sz": 400}, timeout=8).json()["data"][0]
        a = [(float(p), float(q)) for p, q, *_ in d["asks"]]
        b = [(float(p), float(q)) for p, q, *_ in d["bids"]]
        # livros BRL rasos têm ordens-isca muito longe do topo: só conta até ±5% (fora disso = "não cabe")
        return inst, {"asks": [x for x in a if x[0] <= a[0][0] * (1 + BAND)],
                      "bids": [x for x in b if x[0] >= b[0][0] * (1 - BAND)]}
    with ThreadPoolExecutor(8) as ex:
        return dict(ex.map(one, INSTS))


def buy_with_quote(asks, amt):
    base, left = 0.0, amt
    for px, sz in asks:
        if px * sz >= left:
            return base + left / px
        base, left = base + sz, left - px * sz
    return None


def sell_base(bids, qty):
    got, left = 0.0, qty
    for px, sz in bids:
        if sz >= left:
            return got + left * px
        got, left = got + sz * px, left - sz
    return None


def mid(b):
    return (b["asks"][0][0] + b["bids"][0][0]) / 2


def fee(inst):
    return FEE_BRL if inst.endswith("-BRL") else FEE_NB


def okx_sell_A(bk, A, qty, close):
    """Vende qty de A na OKX e devolve stable `close` (USDT/USDC) recomprado. Via BRL ou direto."""
    if close.endswith("@nb"):
        st = close[:-3]
        out = sell_base(bk[f"{A}-{st}"]["bids"], qty)
        return None if out is None else out * (1 - fee(f"{A}-{st}"))
    brl = sell_base(bk[f"{A}-BRL"]["bids"], qty)
    if brl is None:
        return None
    brl *= 1 - FEE_BRL
    st = buy_with_quote(bk[f"{close}-BRL"]["asks"], brl)
    return None if st is None else st * (1 - FEE_BRL)


def okx_buy_A(bk, A, s_amt, close):
    """Gasta s_amt de stable `close` na OKX e devolve quantidade de A."""
    if close.endswith("@nb"):
        st = close[:-3]
        q = buy_with_quote(bk[f"{A}-{st}"]["asks"], s_amt)
        return None if q is None else q * (1 - fee(f"{A}-{st}"))
    brl = sell_base(bk[f"{close}-BRL"]["bids"], s_amt)
    if brl is None:
        return None
    q = buy_with_quote(bk[f"{A}-BRL"]["asks"], brl * (1 - FEE_BRL))
    return None if q is None else q * (1 - FEE_BRL)


# ---------------- Jupiter ----------------
_last_jup = [0.0]


def jup(inp, out, amt_units):
    for attempt in range(3):
        w = JUP_GAP - (time.time() - _last_jup[0])
        if w > 0:
            time.sleep(w)
        _last_jup[0] = time.time()
        try:
            r = S.get(JUP, params={"inputMint": MINT[inp][0], "outputMint": MINT[out][0],
                                   "amount": int(amt_units), "slippageBps": 50}, timeout=15)
            if r.status_code == 200:
                d = r.json()
                return int(d["outAmount"]) / 10 ** MINT[out][1], [x["swapInfo"]["label"] for x in d["routePlan"]]
            log.warning("jup %s %s", r.status_code, r.text[:120])
        except Exception as e:
            log.warning("jup err %s", e)
        time.sleep(5 * (attempt + 1))
    return None, None


# ---------------- XRPL ----------------
def xrpl(method, p):
    for u in XRPL:
        try:
            return S.post(u, json={"method": method, "params": [p]}, timeout=30).json()["result"]
        except Exception as e:
            log.warning("xrpl %s %s", u, e)
    return {}


def xrpl_cost(tok, want_xrp=None, want_tok=None):
    """Exact-out via ripple_path_find (CLOB+AMM, regras do rippled). Retorna custo no outro ativo."""
    t, acct = XTOK[tok]
    if want_xrp is not None:   # comprar XRP pagando tok
        p = {"destination_amount": str(int(want_xrp * 1e6)), "source_currencies": [t]}
    else:                      # comprar tok pagando XRP
        p = {"destination_amount": dict(t, value=f"{want_tok:.6f}"), "source_currencies": [{"currency": "XRP"}]}
    r = xrpl("ripple_path_find", dict(p, source_account=acct, destination_account=acct))
    a = r.get("alternatives") or []
    if not a:
        return None
    sa = a[0]["source_amount"]
    return float(sa["value"]) if isinstance(sa, dict) else int(sa) / 1e6


# ---------------- tick ----------------
def tick():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bk = fetch_books()
    usdt_brl, usdc_brl = mid(bk["USDT-BRL"]), mid(bk["USDC-BRL"])
    ref = {"SOL": mid(bk["SOL-BRL"]) / usdc_brl, "XRP": mid(bk["XRP-BRL"]) / usdc_brl}
    rows, raw = [], {"usdt_brl": usdt_brl, "usdc_brl": usdc_brl, "rlusd_usdt": mid(bk["RLUSD-USDT"]),
                     "okx_mid_usd": ref, "dex": {}}

    def add(asset, venue, st, d, close, size, net, dpx, opx):
        rows.append((ts, asset, venue, st, d, close, size, None if net is None else round(net, 3),
                     dpx, opx, int(net is not None)))

    # SOL via Jupiter
    sol_tx_usd = SOL_TX_SOL * ref["SOL"]
    for st in ("USDC", "USDT"):
        for size in SIZES:
            q, r1 = jup(st, "SOL", size * 1e6)                       # DtoO: compra SOL no DEX
            x, r2 = jup("SOL", st, size / ref["SOL"] * 1e9)           # OtoD: vende SOL no DEX
            raw["dex"][f"SOL/{st}/{size}"] = {"buy_q": q, "sell_out": x, "routes": [r1, r2]}
            for close in (st, st + "@nb"):
                if q:
                    out = okx_sell_A(bk, "SOL", q, close)
                    add("SOL", "jupiter", st, "DtoO", close, size,
                        None if out is None else ((out - sol_tx_usd) / size - 1) * 1e4, size / q, None)
                if x:
                    q2 = okx_buy_A(bk, "SOL", size, close)
                    if q2 is None:
                        add("SOL", "jupiter", st, "OtoD", close, size, None, None, None)
                    else:
                        px = x / (size / ref["SOL"])
                        add("SOL", "jupiter", st, "OtoD", close, size,
                            ((q2 * px - sol_tx_usd) / size - 1) * 1e4, px, size / q2)
    # XRP via XRPL (CLOB+AMM)
    for st in ("RLUSD", "USDC"):
        okx_st = "USDT" if st == "RLUSD" else "USDC"
        for size in SIZES:
            qx = size / ref["XRP"]
            cost = xrpl_cost(st, want_xrp=qx)          # DtoO: compra qx XRP pagando ~size stable
            xneed = xrpl_cost(st, want_tok=size)       # OtoD: vende XRP -> recebe size stable
            raw["dex"][f"XRP/{st}/{size}"] = {"buy_cost": cost, "sell_xrp_needed": xneed}
            for close in (okx_st, okx_st + "@nb"):
                if cost:
                    out = okx_sell_A(bk, "XRP", qx, close)
                    add("XRP", "xrpl", st, "DtoO", close, size,
                        None if out is None else (out / cost - 1) * 1e4, cost / qx, None)
                if xneed:
                    q2 = okx_buy_A(bk, "XRP", size, close)
                    if q2 is None:
                        add("XRP", "xrpl", st, "OtoD", close, size, None, None, None)
                    else:
                        px = size / xneed
                        add("XRP", "xrpl", st, "OtoD", close, size, (q2 * px / size - 1) * 1e4, px, size / q2)
    # Memes: triângulo interno OKX (USDT -> A-USDT -> A-BRL -> USDT-BRL e inverso)
    for A in ("PEPE", "PI", "TRUMP"):
        for size in (1_000, 10_000):
            q = buy_with_quote(bk[f"{A}-USDT"]["asks"], size)
            out = None if q is None else okx_sell_A(bk, A, q * (1 - FEE_NB), "USDT")
            add(A, "okx", "USDT", "USDT>BRL", "USDT", size, None if out is None else (out / size - 1) * 1e4, None, None)
            q = okx_buy_A(bk, A, size, "USDT")
            out = None if q is None else sell_base(bk[f"{A}-USDT"]["bids"], q)
            add(A, "okx", "USDT", "BRL>USDT", "USDT", size,
                None if out is None else (out * (1 - FEE_NB) / size - 1) * 1e4, None, None)
        raw[f"{A}_brl_vs_usdt_bps"] = round((mid(bk[f"{A}-BRL"]) / usdt_brl / mid(bk[f"{A}-USDT"]) - 1) * 1e4, 2)
    return ts, rows, raw


def save(con, ts, rows, raw):
    con.executemany("INSERT OR REPLACE INTO opps VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute("INSERT OR REPLACE INTO ticks VALUES (?,?)", (ts, json.dumps(raw)))
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=60)
    ap.add_argument("--hours", type=float, default=3)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(HERE, "collector.log")),
                                  logging.StreamHandler(sys.stdout)])
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    if a.once:
        ts, rows, raw = tick()
        save(con, ts, rows, raw)
        for r in rows:
            print(r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])
        print(json.dumps({k: v for k, v in raw.items() if k != "dex"}))
        return
    with open(PID, "w") as f:
        f.write(str(os.getpid()))
    end = time.time() + a.hours * 3600
    n = 0
    try:
        while time.time() < end and not os.path.exists(STOP):
            t0 = time.time()
            try:
                ts, rows, raw = tick()
                save(con, ts, rows, raw)
                n += 1
                best = max((r[7] for r in rows if r[7] is not None and r[1] in ("SOL", "XRP")), default=None)
                log.info("tick %d %s rows=%d best_sol_xrp=%s", n, ts, len(rows), best)
            except Exception as e:
                log.exception("tick failed: %s", e)
            time.sleep(max(0, a.interval - (time.time() - t0)))
    finally:
        if os.path.exists(PID):
            os.remove(PID)
        log.info("stopped after %d ticks", n)


if __name__ == "__main__":
    main()
