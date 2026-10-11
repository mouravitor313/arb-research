"""Item 1 collector — OKX (BRL pairs) ↔ OKX (USD pairs) ↔ DEX (Arbitrum/Base), + USDC/USDT basis.

READ-ONLY: OKX public REST order books (no keys) + eth_call quotes (QuoterV2 / V4Quoter) batched via
Multicall3. Nothing is signed or sent. Every ~10 s it computes, for $1k/$10k/$100k, walking the books:

  1a  okx_tri    OKX internal triangle  BRL → X → A → BRL  (cw) and BRL → A → X → BRL (ccw)
                 A ∈ {BTC, ETH, SOL}, X ∈ {USDT, USDC}. Fees VIP 9: BRL pairs taker 2 bps, others 11.
                 net_bps_maker = same, but the A-BRL leg as maker at the touch (−1.5 bps) = upper bound.
  1b  dex_brl    DEX (Arbitrum/Base Uni v3 0.05%, A ∈ {BTC, ETH}) ↔ OKX A-BRL, closing USDC↔BRL on
                 OKX USDC-BRL (same shape as the live xend-arb brla bot, asset swapped).
                 dex_buy = buy A on DEX with USDC, sell A on A-BRL; dex_sell = the reverse.
      dex_usd    reference: DEX ↔ OKX A-USDC (non-BRL, 11 bps), to see if BRL routing matters.
  2   usd_basis  USDC/USDT basis (secondary): OKX via BRL (USDC-BRL + USDT-BRL) or OKX USDC-USDT,
                 closed on Polygon Uni v4 USDC/USDT0 (fee 0.0008%); plus OKX-internal triangle.

Inventory model (like xend-arb): both venues pre-funded; transfer/withdrawal/rebalance costs are NOT
included. gross_bps = before OKX fees and gas (DEX pool fees are always inside the on-chain quote).

    python xvenue_collector.py [--interval 10] [--max-ticks N]
Tables (arb_tracker.db): xvenue_opps, xvenue_ticks.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from eth_abi import decode as abi_decode

from chains import CHAINS, rpc_list
from cycle_common import CS, build_w3, encode, multicall
from cycle_quote import V4_KEY, V4_QUOTER

DB = "arb_tracker.db"
OKX_BOOK = "https://www.okx.com/api/v5/market/books"
INSTS = ["BTC-BRL", "BTC-USDT", "BTC-USDC", "ETH-BRL", "ETH-USDT", "ETH-USDC", "SOL-BRL",
         "SOL-USDT", "SOL-USDC", "USDT-BRL", "USDC-BRL", "USDC-USDT", "POL-USDT"]
FEE_BRL, FEE_NB, MAKER_BRL = 2e-4, 11e-4, -1.5e-4
SIZES = (1_000, 10_000, 100_000)
DEX = {  # (chain, asset) -> (token symbol, fee tier) — validated by xvenue_discover.py
    ("arbitrum", "BTC"): ("WBTC", 500), ("arbitrum", "ETH"): ("WETH", 500),
    ("base", "BTC"): ("cbBTC", 500), ("base", "ETH"): ("WETH", 500),
}
SWAP_GAS = 150_000  # one Uni v3/v4 swap incl. tx overhead (approx.)

SCHEMA = """
CREATE TABLE IF NOT EXISTS xvenue_opps (
    ts TEXT, strategy TEXT, asset TEXT, venue TEXT, route TEXT, size_usd INTEGER,
    gross_bps REAL, net_bps REAL, net_bps_maker REAL, gas_usd REAL, ok INTEGER,
    PRIMARY KEY (ts, strategy, asset, venue, route, size_usd)
);
CREATE INDEX IF NOT EXISTS ix_xvenue_opps_q ON xvenue_opps(strategy, asset, size_usd);
CREATE TABLE IF NOT EXISTS xvenue_ticks (ts TEXT PRIMARY KEY, data TEXT);
"""
log = logging.getLogger("xvenue")
S = requests.Session()


# ---------------- order-book walking ----------------

def fee(inst: str, on: bool) -> float:
    return (FEE_BRL if inst.endswith("-BRL") else FEE_NB) if on else 0.0


def buy_with_quote(asks, quote_amt):
    """Spend quote_amt on asks -> base received (None if book too thin)."""
    base, left = 0.0, quote_amt
    for px, sz in asks:
        c = px * sz
        if c >= left:
            return base + left / px
        base, left = base + sz, left - c
    return None


def buy_base(asks, qty):
    """Cost in quote to buy qty base."""
    cost, left = 0.0, qty
    for px, sz in asks:
        if sz >= left:
            return cost + left * px
        cost, left = cost + sz * px, left - sz
    return None


def sell_base(bids, qty):
    """Quote received selling qty base."""
    got, left = 0.0, qty
    for px, sz in bids:
        if sz >= left:
            return got + left * px
        got, left = got + sz * px, left - sz
    return None


def fetch_books() -> dict:
    def one(inst):
        r = S.get(OKX_BOOK, params={"instId": inst, "sz": 400}, timeout=8).json()
        d = r["data"][0]
        return inst, {"asks": [(float(p), float(q)) for p, q, *_ in d["asks"]],
                      "bids": [(float(p), float(q)) for p, q, *_ in d["bids"]], "ts": d["ts"]}
    with ThreadPoolExecutor(8) as ex:
        return dict(ex.map(one, INSTS))


def mid(b):
    return (b["asks"][0][0] + b["bids"][0][0]) / 2


# ---------------- on-chain quotes ----------------

def _v3_q(quoter, tin, tout, fee_tier, amt):
    cd = encode("quoteExactInputSingle((address,address,uint256,uint24,uint160))",
                ["(address,address,uint256,uint24,uint160)"], [(CS(tin), CS(tout), int(amt), fee_tier, 0)])
    return quoter, cd


def _v4_q(tin, amt):
    cd = encode("quoteExactInputSingle(((address,address,uint24,int24,address),bool,uint128,bytes))",
                ["((address,address,uint24,int24,address),bool,uint128,bytes)"],
                [(V4_KEY, CS(tin) == V4_KEY[0], int(amt), b"")])
    return V4_QUOTER, cd


class Chains:
    def __init__(self):
        self.idx = {c: 0 for c in CHAINS}
        self.w3 = {c: build_w3(rpc_list(c)[0]) for c in CHAINS}
        self.fails = {c: 0 for c in CHAINS}

    def rotate(self, c):
        urls = rpc_list(c)
        self.idx[c] = (self.idx[c] + 1) % len(urls)
        self.w3[c] = build_w3(urls[self.idx[c]])
        log.warning("rotated %s RPC -> %s", c, urls[self.idx[c]])

    def run(self, c, jobs):
        """jobs: list of (key, target, calldata, decoder) -> {key: value|None}, plus gas price."""
        w3 = self.w3[c]
        try:
            res = multicall(w3, [(t, cd) for _, t, cd, _ in jobs]) if jobs else []
            gp = w3.eth.gas_price
            self.fails[c] = 0
        except Exception as e:  # noqa: BLE001
            self.fails[c] += 1
            log.error("%s multicall failed: %s", c, str(e)[:200])
            if self.fails[c] >= 2:
                self.rotate(c)
            return {}, None
        out = {}
        for (key, _, _, dec), (ok, raw) in zip(jobs, res):
            out[key] = dec(raw) if ok and raw else None
        return out, gp


def dec_v3(raw):
    return abi_decode(["uint256", "uint160", "uint32", "uint256"], raw)[0]


def dec_v4(raw):
    return abi_decode(["uint256", "uint256"], raw)[0]


# ---------------- strategies ----------------

def okx_triangles(bk, ts, rows):
    for a in ("BTC", "ETH", "SOL"):
        abrl = bk[f"{a}-BRL"]
        for x in ("USDT", "USDC"):
            xbrl, ax = bk[f"{x}-BRL"], bk[f"{a}-{x}"]
            for s in SIZES:
                brl0 = s * xbrl["asks"][0][0]
                res = {}
                for f_on in (False, True):
                    # cw: BRL -> X -> A -> BRL
                    xq = buy_with_quote(xbrl["asks"], brl0)
                    aq = xq and buy_with_quote(ax["asks"], xq * (1 - fee(f"{x}-BRL", f_on)))
                    aq = aq and aq * (1 - fee(f"{a}-{x}", f_on))
                    b1 = aq and sell_base(abrl["bids"], aq)
                    cw = b1 * (1 - fee(f"{a}-BRL", f_on)) if b1 else None
                    cw_mk = aq * abrl["asks"][0][0] * (1 - MAKER_BRL) if (aq and f_on) else None
                    # ccw: BRL -> A -> X -> BRL
                    aq2 = buy_with_quote(abrl["asks"], brl0)
                    aq2 = aq2 and aq2 * (1 - fee(f"{a}-BRL", f_on))
                    xq2 = aq2 and sell_base(ax["bids"], aq2)
                    xq2 = xq2 and xq2 * (1 - fee(f"{a}-{x}", f_on))
                    b2 = xq2 and sell_base(xbrl["bids"], xq2)
                    ccw = b2 * (1 - fee(f"{x}-BRL", f_on)) if b2 else None
                    ccw_mk = None
                    if f_on:  # maker on A-BRL: buy at best bid, rebate
                        aqm = brl0 / abrl["bids"][0][0] * (1 - MAKER_BRL)
                        xm = sell_base(ax["bids"], aqm)
                        xm = xm and xm * (1 - FEE_NB)
                        bm = xm and sell_base(xbrl["bids"], xm)
                        ccw_mk = bm * (1 - FEE_BRL) if bm else None
                    res[f_on] = (cw, ccw, cw_mk, ccw_mk)
                for i, route in enumerate((f"BRL>{x}>{a}>BRL", f"BRL>{a}>{x}>BRL")):
                    g, n, mk = res[False][i], res[True][i], res[True][2 + i]
                    bps = (lambda v: (v / brl0 - 1) * 1e4 if v else None)
                    rows.append((ts, "okx_tri", a, "okx", route, s, bps(g), bps(n), bps(mk), 0.0,
                                 int(n is not None)))


def dex_jobs(bk):
    """Build on-chain quote jobs per chain (needs OKX ref prices for the asset->USDC size)."""
    jobs = {c: [] for c in CHAINS}
    for (c, a), (sym, ft) in DEX.items():
        cfg = CHAINS[c]
        usdc, ud = cfg["tokens"]["USDC"]
        tok, td = cfg["tokens"][sym]
        ref = mid(bk[f"{a}-USDC"])
        for s in SIZES:
            t, cd = _v3_q(cfg["quoter_v2"], usdc, tok, ft, s * 10**ud)
            jobs[c].append(((a, "buy", s), t, cd, dec_v3))
            t, cd = _v3_q(cfg["quoter_v2"], tok, usdc, ft, s / ref * 10**td)
            jobs[c].append(((a, "sell", s), t, cd, dec_v3))
    return jobs


def dex_strats(bk, q, gas_usd, ts, rows):
    usdc_brl = bk["USDC-BRL"]
    for (c, a), (sym, _) in DEX.items():
        td = CHAINS[c]["tokens"][sym][1]
        ref = mid(bk[f"{a}-USDC"])
        abrl, ausd = bk[f"{a}-BRL"], bk[f"{a}-USDC"]
        g_usd = gas_usd.get(c)
        if g_usd is None:
            continue
        for s in SIZES:
            qb, qs = q.get(c, {}).get((a, "buy", s)), q.get(c, {}).get((a, "sell", s))

            def brl_rows():
                out = []
                # dex_buy: S USDC -> A on DEX -> sell A on A-BRL; replenish S USDC on USDC-BRL asks
                if qb:
                    qa = qb / 10**td
                    vals = []
                    for f_on in (False, True):
                        bo = sell_base(abrl["bids"], qa)
                        bc = buy_base(usdc_brl["asks"], s)
                        if bo is None or bc is None:
                            vals.append(None)
                            continue
                        bo *= 1 - fee("A-BRL", f_on)
                        bc /= 1 - fee("USDC-BRL", f_on)
                        gb = g_usd * usdc_brl["bids"][0][0] if f_on else 0
                        vals.append(((bo - gb) / bc - 1) * 1e4)
                    out.append(("dex_brl", "dex_buy>okx_sell", vals))
                    # reference vs OKX A-USDC (non-BRL)
                    v2 = []
                    for f_on in (False, True):
                        uo = sell_base(ausd["bids"], qa)
                        v2.append(None if uo is None else
                                  ((uo * (1 - fee("A-USDC", f_on)) - (g_usd if f_on else 0)) / s - 1) * 1e4)
                    out.append(("dex_usd", "dex_buy>okx_sell", v2))
                # dex_sell: buy qa on A-BRL with BRL -> sell on DEX -> sell USDC on USDC-BRL bids
                if qs:
                    qa = s / ref
                    uo = qs / 1e6
                    vals = []
                    for f_on in (False, True):
                        bc = buy_base(abrl["asks"], qa)
                        bo = sell_base(usdc_brl["bids"], uo)
                        if bo is None or bc is None:
                            vals.append(None)
                            continue
                        bc /= 1 - fee("A-BRL", f_on)
                        bo *= 1 - fee("USDC-BRL", f_on)
                        gb = g_usd * usdc_brl["bids"][0][0] if f_on else 0
                        vals.append(((bo - gb) / bc - 1) * 1e4)
                    out.append(("dex_brl", "okx_buy>dex_sell", vals))
                    v2 = []
                    for f_on in (False, True):
                        uc = buy_base(ausd["asks"], qa)
                        v2.append(None if uc is None else
                                  ((uo - (g_usd if f_on else 0)) / (uc / (1 - fee("A-USDC", f_on))) - 1) * 1e4)
                    out.append(("dex_usd", "okx_buy>dex_sell", v2))
                return out
            for strat, route, (g, n) in brl_rows():
                rows.append((ts, strat, a, c, route, s, g, n, None, g_usd, int(n is not None)))


def basis_jobs(bk):
    """USDC/USDT legs on Polygon v4: amounts from the OKX leg (computed with fees)."""
    usdc, usdt = CHAINS["polygon"]["tokens"]["USDC"][0], CHAINS["polygon"]["tokens"]["USDT"][0]
    jobs, plan = [], {}
    for s in SIZES:
        # (a) USDC -> BRL -> USDT on OKX, then USDT0 -> USDC on v4
        b = sell_base(bk["USDC-BRL"]["bids"], s)
        ut = b and buy_with_quote(bk["USDT-BRL"]["asks"], b * (1 - FEE_BRL))
        ut = ut and ut * (1 - FEE_BRL)
        # (b) USDT -> BRL -> USDC on OKX, then USDC -> USDT0 on v4
        b2 = sell_base(bk["USDT-BRL"]["bids"], s)
        uc = b2 and buy_with_quote(bk["USDC-BRL"]["asks"], b2 * (1 - FEE_BRL))
        uc = uc and uc * (1 - FEE_BRL)
        # (c) USDC -> USDT on OKX USDC-USDT (sell), then USDT0 -> USDC on v4
        ut3 = sell_base(bk["USDC-USDT"]["bids"], s)
        ut3 = ut3 and ut3 * (1 - FEE_NB)
        # (d) USDT -> USDC on OKX USDC-USDT (buy), then USDC -> USDT0 on v4
        uc4 = buy_with_quote(bk["USDC-USDT"]["asks"], s)
        uc4 = uc4 and uc4 * (1 - FEE_NB)
        for key, tin, amt in ((("a", s), usdt, ut), (("b", s), usdc, uc),
                              (("c", s), usdt, ut3), (("d", s), usdc, uc4)):
            plan[key] = amt
            if amt:
                t, cd = _v4_q(tin, amt * 1e6)
                jobs.append((key, t, cd, dec_v4))
    return jobs, plan


def basis_strats(bk, q, plan, gas_poly, ts, rows):
    routes = {"a": "USDC>BRL>USDT@okx>USDC@v4", "b": "USDT>BRL>USDC@okx>USDT@v4",
              "c": "USDC>USDT@okx_direct>USDC@v4", "d": "USDT>USDC@okx_direct>USDT@v4"}
    for s in SIZES:
        for k, route in routes.items():
            out = q.get((k, s))
            n = ((out / 1e6 - (gas_poly or 0)) / s - 1) * 1e4 if out else None
            rows.append((ts, "usd_basis", "USDC/USDT", "okx+polygon_v4", route, s, None, n, None,
                         gas_poly, int(n is not None)))
        # (e) OKX-internal: USDC -> BRL -> USDT -> USDC (buy USDC on USDC-USDT)
        b = sell_base(bk["USDC-BRL"]["bids"], s)
        ut = b and buy_with_quote(bk["USDT-BRL"]["asks"], b * (1 - FEE_BRL)) * (1 - FEE_BRL)
        uc = ut and buy_with_quote(bk["USDC-USDT"]["asks"], ut)
        n = (uc * (1 - FEE_NB) / s - 1) * 1e4 if uc else None
        rows.append((ts, "usd_basis", "USDC/USDT", "okx", "USDC>BRL>USDT>USDC", s, None, n, None, 0.0,
                     int(n is not None)))
        # (f) reverse: USDT -> BRL -> USDC -> USDT (sell USDC on USDC-USDT)
        b = sell_base(bk["USDT-BRL"]["bids"], s)
        uc = b and buy_with_quote(bk["USDC-BRL"]["asks"], b * (1 - FEE_BRL)) * (1 - FEE_BRL)
        ut = uc and sell_base(bk["USDC-USDT"]["bids"], uc)
        n = (ut * (1 - FEE_NB) / s - 1) * 1e4 if ut else None
        rows.append((ts, "usd_basis", "USDC/USDT", "okx", "USDT>BRL>USDC>USDT", s, None, n, None, 0.0,
                     int(n is not None)))


# ---------------- loop ----------------

class Collector:
    def __init__(self, interval):
        self.interval = interval
        self.db = sqlite3.connect(DB, timeout=30)
        self.db.executescript(SCHEMA)
        self.chains = Chains()

    def tick(self):
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        bk = fetch_books()
        jobs = dex_jobs(bk)
        bjobs, plan = basis_jobs(bk)
        jobs["polygon"] = jobs.get("polygon", []) + bjobs
        with ThreadPoolExecutor(3) as ex:
            res = dict(zip(jobs, ex.map(lambda c: self.chains.run(c, jobs[c]), jobs)))
        q = {c: r[0] for c, r in res.items()}
        native = {c: mid(bk[CHAINS[c]["native_okx"]]) for c in CHAINS}
        gas_usd = {c: (SWAP_GAS * r[1] / 1e18 * native[c]) if r[1] else None for c, r in res.items()}
        rows = []
        okx_triangles(bk, ts, rows)
        dex_strats(bk, q, gas_usd, ts, rows)
        basis_strats(bk, q.get("polygon", {}), plan, gas_usd.get("polygon"), ts, rows)
        tick = {i: [bk[i]["bids"][0][0], bk[i]["asks"][0][0]] for i in INSTS}
        tick["gas_usd"] = gas_usd
        with self.db:
            self.db.executemany("INSERT OR REPLACE INTO xvenue_opps VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
            self.db.execute("INSERT OR REPLACE INTO xvenue_ticks VALUES (?,?)", (ts, json.dumps(tick)))
        best = {}
        for r in rows:
            if r[7] is not None and r[5] == 10_000:
                k = r[1]
                if k not in best or r[7] > best[k][7]:
                    best[k] = r
        log.info("best $10k net: " + " | ".join(f"{k} {v[7]:.1f} ({v[2]} {v[3]} {v[4]})"
                                              for k, v in sorted(best.items())))

    def run(self, max_ticks=None):
        n = 0
        while max_ticks is None or n < max_ticks:
            t0 = time.time()
            try:
                self.tick()
            except Exception as e:  # noqa: BLE001
                log.error("tick failed: %s", str(e)[:300])
                time.sleep(5)
            n += 1
            time.sleep(max(0.0, self.interval - (time.time() - t0)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--max-ticks", type=int, default=None)
    ap.add_argument("--log", default="xvenue_collector.log")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(a.log, encoding="utf-8"), logging.StreamHandler()])
    Collector(a.interval).run(a.max_ticks)


if __name__ == "__main__":
    main()
