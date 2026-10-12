"""Resumo do coletor: p50/p95/%>0/episódios por estratégia. RLUSD também avaliado ao mid OKX RLUSD-USDT."""
import json, sqlite3, statistics as st
con = sqlite3.connect("data.db")
ticks = {ts: json.loads(d) for ts, d in con.execute("SELECT ts, data FROM ticks")}
rows = con.execute("SELECT ts, asset, venue, stable, dir, close, size_usd, net_bps, ok FROM opps ORDER BY ts").fetchall()
groups = {}
for ts, a, v, s, d, c, sz, net, ok in rows:
    groups.setdefault((a, v, s, d, c, sz), []).append((ts, net))
    if s == "RLUSD" and net is not None:   # RLUSD a mercado: DtoO paga RLUSD (vale r), OtoD recebe RLUSD
        r = ticks[ts]["rlusd_usdt"]
        adj = net - (r - 1) * 1e4 if d == "DtoO" else net + (r - 1) * 1e4
        groups.setdefault((a, v, s + "@mkt", d, c, sz), []).append((ts, adj))
def pct(x, p):
    x = sorted(x); return x[min(len(x) - 1, int(round(p * (len(x) - 1))))]
out = []
print(f"ticks={len(ticks)}  {min(ticks)} -> {max(ticks)}")
print(f"{'asset':5} {'venue':7} {'stable':10} {'dir':8} {'close':9} {'size':>6} {'n':>4} {'fit%':>5} {'p50':>7} {'p95':>7} {'max':>7} {'%>0':>5} {'ep':>3}")
for k, v in sorted(groups.items()):
    vals = [n for _, n in v if n is not None]
    if not vals:
        print(*k, "não cabe"); out.append(dict(zip("asset venue stable dir close size".split(), k), fit=0)); continue
    ep, prev = 0, False
    for _, n in v:
        cur = n is not None and n > 0; ep += cur and not prev; prev = cur
    rec = dict(zip("asset venue stable dir close size".split(), k), n=len(v), fit=round(100*len(vals)/len(v)),
               p50=round(st.median(vals), 1), p95=round(pct(vals, .95), 1), max=round(max(vals), 1),
               pos=round(100 * sum(x > 0 for x in vals) / len(vals), 1), episodes=ep)
    out.append(rec)
    print(f"{k[0]:5} {k[1]:7} {k[2]:10} {k[3]:8} {k[4]:9} {k[5]:>6} {len(v):>4} {rec['fit']:>5} {rec['p50']:>7} {rec['p95']:>7} {rec['max']:>7} {rec['pos']:>5} {ep:>3}")
r = [t["rlusd_usdt"] for t in ticks.values()]
m = {k: [t[k] for t in ticks.values() if k in t] for k in ("PEPE_brl_vs_usdt_bps", "PI_brl_vs_usdt_bps", "TRUMP_brl_vs_usdt_bps")}
print("RLUSD-USDT mid p50/min/max", st.median(r), min(r), max(r))
for k, x in m.items(): print(k, "p50", st.median(x), "min", min(x), "max", max(x))
json.dump({"summary": out, "rlusd_usdt": [st.median(r), min(r), max(r)],
           "meme_mid_gap": {k: [st.median(x), min(x), max(x)] for k, x in m.items()}}, open("summary.json", "w"), indent=1)
