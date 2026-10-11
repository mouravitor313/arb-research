"""Step 2 — collector loop for the Polygon atomic cycle (RECAP §5 item B).

READ-ONLY (eth_call / eth_getLogs). Every ~12 s, pinned to one block:
  * cycle_quotes      — every (direction × route × size) cycle: amount_in/out, gross/net bps, gas
  * cycle_ticks       — mid prices of each pool (slot0 / Curve 1-unit get_dy) + mid-cycle bps
  * cycle_pool_swaps  — Swap/TokenExchange events on the cycle pools since the last tick
                        (block, tx, sender/recipient, tx.from) to correlate with xend-arb bots.
All tables live in arb_tracker.db (new tables; existing tracker tables untouched).

    python cycle_collector.py                  # loop forever, 12 s
    python cycle_collector.py --interval 15 --max-ticks 10
RPC: POLYGON_RPC_URL / RPC_URL env, else public endpoints (rotated on failure).
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import time
from datetime import datetime, timezone

from eth_abi import decode as abi_decode
from web3 import Web3

from cycle_common import (
    CS, POOL_BRZ_BRLA, POOL_BRZ_USDT0, POOL_TESOURO, POOL_USDC_BRLA, build_w3, encode, multicall,
    rpc_urls,
)
from cycle_quote import (
    BRLA, BRZ, CURVE_IDX, V4_POOL_ID, gas_usd, pol_usd, quote_cycles,
)

DB = "arb_tracker.db"
V4_POOL_MANAGER = "0x67366782805870060151383f4bbff9dab53e5cd6"
V3_POOL_V3_CLOSE = "0x31083a78E11B18e450fd139F9ABEa98CD53181B7"  # USDC/USDT0 0.01%

POOL_LABELS = {
    CS(POOL_USDC_BRLA): "usdc_brla_v3",
    CS(POOL_BRZ_USDT0): "brz_usdt0_v3",
    CS(POOL_BRZ_BRLA): "brz_brla_v3",
    CS(POOL_TESOURO): "tesouro_curve",
}
T_SWAP_V3 = "0x" + Web3.keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex().removeprefix("0x")
T_CURVE_X = "0x" + Web3.keccak(text="TokenExchange(address,int128,uint256,int128,uint256)").hex().removeprefix("0x")
T_SWAP_V4 = "0x" + Web3.keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex().removeprefix("0x")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cycle_quotes (
    ts TEXT, block INTEGER, route TEXT, direction TEXT, size_usd INTEGER,
    amount_in REAL, amount_out REAL, gross_bps REAL, gas_units INTEGER, gas_usd REAL,
    net_bps REAL, venues TEXT, exhausted INTEGER, ok INTEGER,
    gas_price_gwei REAL, pol_usd REAL,
    PRIMARY KEY (block, route, direction, size_usd)
);
CREATE INDEX IF NOT EXISTS ix_cycle_quotes_ts ON cycle_quotes(ts);
CREATE TABLE IF NOT EXISTS cycle_ticks (
    ts TEXT, block INTEGER PRIMARY KEY,
    brla_per_usdc REAL, brz_per_usdt0 REAL, brla_per_brz_v3 REAL,
    brla_per_brz_curve REAL, brz_per_brla_curve REAL, usdt0_per_usdc_v3 REAL,
    mid_cycle_fwd_bps REAL, mid_cycle_fwd_curve_bps REAL, mid_cycle_rev_curve_bps REAL
);
CREATE TABLE IF NOT EXISTS cycle_pool_swaps (
    block INTEGER, tx_hash TEXT, log_index INTEGER, pool TEXT, tx_from TEXT,
    sender TEXT, recipient TEXT, amount0 TEXT, amount1 TEXT, tick INTEGER,
    PRIMARY KEY (tx_hash, log_index)
);
CREATE INDEX IF NOT EXISTS ix_cycle_pool_swaps_block ON cycle_pool_swaps(block);
"""

log = logging.getLogger("cycle")


def _sqrt_to_price(sp: int, d0: int, d1: int) -> float:
    return (sp / 2**96) ** 2 * 10 ** (d0 - d1)


def mid_prices(w3: Web3, block: int) -> dict:
    slot0 = encode("slot0()", [], [])
    calls = [(POOL_USDC_BRLA, slot0), (POOL_BRZ_USDT0, slot0), (POOL_BRZ_BRLA, slot0),
             (V3_POOL_V3_CLOSE, slot0),
             (POOL_TESOURO, encode("get_dy(int128,int128,uint256)", ["int128", "int128", "uint256"],
                                   [CURVE_IDX[BRZ], CURVE_IDX[BRLA], 10**18])),
             (POOL_TESOURO, encode("get_dy(int128,int128,uint256)", ["int128", "int128", "uint256"],
                                   [CURVE_IDX[BRLA], CURVE_IDX[BRZ], 10**18]))]
    res = multicall(w3, calls, block=block)
    sp = [abi_decode(["uint160"], r[:32])[0] if ok else None for ok, r in res[:4]]
    brla_per_usdc = _sqrt_to_price(sp[0], 6, 18)        # token0 USDC, token1 BRLA
    usdt0_per_brz = _sqrt_to_price(sp[1], 18, 6)        # token0 BRZ, token1 USDT0
    brla_per_brz = _sqrt_to_price(sp[2], 18, 18)        # token0 BRZ, token1 BRLA
    usdt0_per_usdc = _sqrt_to_price(sp[3], 6, 6)        # token0 USDC, token1 USDT0
    # Curve 1-unit get_dy (includes the 0.03% fee) in each direction — the pool is not symmetric
    c_b2l = abi_decode(["uint256"], res[4][1])[0] / 1e18 if res[4][0] else None  # BRLA per 1 BRZ
    c_l2b = abi_decode(["uint256"], res[5][1])[0] / 1e18 if res[5][0] else None  # BRZ per 1 BRLA
    # spot mids (v3 legs without fees): fwd = USDC->BRLA->BRZ->USDT0->USDC; rev is ~1/fwd for v3
    fwd = brla_per_usdc / brla_per_brz * usdt0_per_brz / usdt0_per_usdc
    fwd_c = brla_per_usdc * c_l2b * usdt0_per_brz / usdt0_per_usdc if c_l2b else None
    rev_c = usdt0_per_usdc / usdt0_per_brz * c_b2l / brla_per_usdc if c_b2l else None
    return {"brla_per_usdc": brla_per_usdc, "brz_per_usdt0": 1 / usdt0_per_brz,
            "brla_per_brz_v3": brla_per_brz, "brla_per_brz_curve": c_b2l,
            "brz_per_brla_curve": c_l2b, "usdt0_per_usdc_v3": usdt0_per_usdc,
            "mid_cycle_fwd_bps": (fwd - 1) * 1e4,
            "mid_cycle_fwd_curve_bps": (fwd_c - 1) * 1e4 if fwd_c else None,
            "mid_cycle_rev_curve_bps": (rev_c - 1) * 1e4 if rev_c else None}


TICK_COLS = ["brla_per_usdc", "brz_per_usdt0", "brla_per_brz_v3", "brla_per_brz_curve",
             "brz_per_brla_curve", "usdt0_per_usdc_v3", "mid_cycle_fwd_bps",
             "mid_cycle_fwd_curve_bps", "mid_cycle_rev_curve_bps"]


def tick_row(ts: str, block: int, mids: dict) -> tuple:
    return (ts, block, *[mids[k] for k in TICK_COLS])


def fetch_swaps(w3: Web3, from_block: int, to_block: int) -> list[tuple]:
    rows = []
    logs = w3.eth.get_logs({"address": list(POOL_LABELS), "fromBlock": from_block, "toBlock": to_block})
    logs += w3.eth.get_logs({"address": CS(V4_POOL_MANAGER), "fromBlock": from_block,
                             "toBlock": to_block, "topics": [T_SWAP_V4, V4_POOL_ID]})
    from_cache: dict[str, str] = {}
    for lg in logs:
        t0 = "0x" + lg["topics"][0].hex().removeprefix("0x")
        txh = "0x" + lg["transactionHash"].hex().removeprefix("0x")
        data = bytes(lg["data"])
        addr = CS(lg["address"])
        if t0 == T_SWAP_V3:
            a0, a1, _sp, _liq, tick = abi_decode(["int256", "int256", "uint160", "uint128", "int24"], data)
            sender = CS("0x" + lg["topics"][1].hex()[-40:])
            recip = CS("0x" + lg["topics"][2].hex()[-40:])
            pool = POOL_LABELS.get(addr, addr)
        elif t0 == T_CURVE_X:
            sold_id, sold, bought_id, bought = abi_decode(["int128", "uint256", "int128", "uint256"], data)
            sender = CS("0x" + lg["topics"][1].hex()[-40:])
            recip, tick = sender, None
            a0, a1 = f"{sold_id}:{sold}", f"{bought_id}:{bought}"
            pool = "tesouro_curve"
        elif t0 == T_SWAP_V4:
            a0, a1, _sp, _liq, tick, _fee = abi_decode(
                ["int128", "int128", "uint160", "uint128", "int24", "uint24"], data)
            sender = CS("0x" + lg["topics"][2].hex()[-40:])
            recip = None
            pool = "usdc_usdt0_v4"
        else:
            continue
        if pool == "usdc_usdt0_v4":
            tx_from = None  # high-volume pool: skip per-tx lookup
        else:
            if txh not in from_cache:
                try:
                    from_cache[txh] = CS(w3.eth.get_transaction(txh)["from"])
                except Exception:  # noqa: BLE001
                    from_cache[txh] = None
            tx_from = from_cache[txh]
        rows.append((lg["blockNumber"], txh, lg["logIndex"], pool, tx_from, sender, recip,
                     str(a0), str(a1), tick))
    return rows


class Collector:
    def __init__(self, interval: float):
        self.interval = interval
        self.urls = rpc_urls()
        self.url_i = 0
        self.w3 = build_w3(self.urls[0])
        self.db = sqlite3.connect(DB, timeout=30)
        self.db.executescript(SCHEMA)
        self.db.commit()
        r = self.db.execute("SELECT MAX(block) FROM cycle_ticks").fetchone()
        self.last_log_block = r[0] if r and r[0] else None
        self.pol = None
        self.pol_ts = 0.0

    def rotate(self):
        self.url_i = (self.url_i + 1) % len(self.urls)
        self.w3 = build_w3(self.urls[self.url_i])
        log.warning("rotated RPC -> %s", self.urls[self.url_i])

    def tick(self):
        w3 = self.w3
        block = w3.eth.block_number - 1  # 1 block of slack for lagging LB nodes
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        gp = w3.eth.gas_price
        if self.pol is None or time.time() - self.pol_ts > 300:
            self.pol, self.pol_ts = pol_usd(w3, block), time.time()
        cycles = quote_cycles(w3, block)
        mids = mid_prices(w3, block)
        q_rows = []
        for c in cycles:
            gu = gas_usd(c.gas, gp, self.pol)
            q_rows.append((ts, block, c.route, c.direction, c.size_usd, c.amount_in / 1e6,
                           c.amount_out / 1e6, c.gross_bps if c.ok else None, c.gas, gu,
                           c.net_bps(gu) if c.ok else None, c.venues, int(c.exhausted), int(c.ok),
                           gp / 1e9, self.pol))
        swaps = []
        frm = (self.last_log_block + 1) if self.last_log_block else block - 5
        if block - frm > 2000:  # after a long gap, don't backfill beyond public RPC limits
            frm = block - 2000
        if frm <= block:
            swaps = fetch_swaps(w3, frm, block)
        with self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO cycle_quotes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", q_rows)
            self.db.execute("INSERT OR REPLACE INTO cycle_ticks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            tick_row(ts, block, mids))
            self.db.executemany(
                "INSERT OR IGNORE INTO cycle_pool_swaps VALUES (?,?,?,?,?,?,?,?,?,?)", swaps)
        self.last_log_block = block
        best = max((r for r in q_rows if r[10] is not None and not r[12]), key=lambda r: r[10],
                   default=None)
        log.info("block %d mid_fwd %.2f bps | best net %s | swaps %d", block,
                 mids["mid_cycle_fwd_bps"],
                 f"{best[10]:.2f} bps ({best[3]} {best[2]} ${best[4]:,})" if best else "n/a", len(swaps))

    def run(self, max_ticks: int | None = None):
        n, fails = 0, 0
        while max_ticks is None or n < max_ticks:
            t0 = time.time()
            try:
                self.tick()
                fails = 0
            except Exception as e:  # noqa: BLE001
                fails += 1
                log.error("tick failed (%d): %s", fails, str(e)[:300])
                if fails >= 2:
                    self.rotate()
                if fails >= 10:
                    time.sleep(60)
            n += 1
            time.sleep(max(0.0, self.interval - (time.time() - t0)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=12.0)
    ap.add_argument("--max-ticks", type=int, default=None)
    ap.add_argument("--log", default="cycle_collector.log")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(a.log, encoding="utf-8"), logging.StreamHandler()])
    Collector(a.interval).run(a.max_ticks)


if __name__ == "__main__":
    main()
