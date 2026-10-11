"""Step 1 — one-shot probe of the Polygon cycle (both directions, both bridges, $1k/$10k/$100k).

READ-ONLY. Prints per-cycle legs, gross/net bps and gas; cross-checks the all-v3 path with
QuoterV2.quoteExactInput (multi-hop) and writes cycle_probe_<ts>.json.

    python cycle_probe.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from cycle_common import USDC, USDT0, build_w3
from cycle_quote import BRLA, BRZ, gas_usd, pol_usd, quote_cycles, v3_multihop_quote


def main():
    w3 = build_w3()
    block = w3.eth.block_number - 1
    gp = w3.eth.gas_price
    pol = pol_usd(w3, block)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"block {block}  gasPrice {gp/1e9:.1f} gwei  POL ${pol:.4f}  ({ts})\n")
    cycles = quote_cycles(w3, block)
    rows = []
    for c in cycles:
        g_usd = gas_usd(c.gas, gp, pol)
        row = {"direction": c.direction, "route": c.route, "size_usd": c.size_usd,
               "ok": c.ok, "exhausted": c.exhausted, "venues": c.venues,
               "amount_in": c.amount_in / 1e6, "amount_out": c.amount_out / 1e6,
               "gross_bps": round(c.gross_bps, 2) if c.ok else None,
               "gas": c.gas, "gas_usd": round(g_usd, 5),
               "net_bps": round(c.net_bps(g_usd), 2) if c.ok else None,
               "legs": [{"venue": lg.venue, "in": lg.amount_in, "out": lg.amount_out,
                         "gas": lg.gas, "exhausted": lg.exhausted, "ok": lg.ok} for lg in c.legs]}
        rows.append(row)
        flag = " EXHAUSTED(partial fill)" if c.exhausted else ""
        print(f"{c.direction:3} {c.route:5} ${c.size_usd:>7,}  out {row['amount_out']:>12,.4f}  "
              f"gross {row['gross_bps']!s:>8} bps  gas {c.gas:>7,} (${g_usd:.4f})  "
              f"net {row['net_bps']!s:>8} bps  [{c.venues}]{flag}")

    # Cross-check: QuoterV2 multi-hop for the all-v3 path (v3 0.01% close)
    print("\nQuoterV2.quoteExactInput cross-check (all-v3 path):")
    checks = []
    for d, toks, fees in (("fwd", [USDC, BRLA, BRZ, USDT0, USDC], [500, 500, 500, 100]),
                          ("rev", [USDC, USDT0, BRZ, BRLA, USDC], [100, 500, 500, 500])):
        for s in (1_000, 10_000, 100_000):
            out, gas = v3_multihop_quote(w3, toks, fees, s * 10**6, block)
            if out is None:
                print(f"  {d} ${s:,}: revert")
                continue
            g = gas + 21_000 + 60_000
            gu = gas_usd(g, gp, pol)
            gross = (out - s * 1e6) / (s * 1e6) * 1e4
            net = ((out - s * 1e6) / 1e6 - gu) / s * 1e4
            checks.append({"direction": d, "size_usd": s, "out": out / 1e6,
                           "quoter_gas": gas, "gas_total": g, "gas_usd": gu,
                           "gross_bps": gross, "net_bps": net})
            print(f"  {d} ${s:>7,}: out {out/1e6:,.4f}  gross {gross:.2f} bps  quoterGas {gas:,}"
                  f"  (+81k overhead = ${gu:.4f})  net {net:.2f} bps")

    rep = {"ts": ts, "block": block, "gas_price_gwei": gp / 1e9, "pol_usd": pol,
           "cycles": rows, "v3_multihop_check": checks}
    fn = f"cycle_probe_{ts[:19].replace(':', '').replace('-', '')}.json"
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print(f"\n-> {fn}")


if __name__ == "__main__":
    main()
