#!/usr/bin/env python3
"""
dashboard.py — PoC realtime dashboard (PT-BR) para a estratégia de arbitragem.

Lê (somente leitura) o SQLite gerado por `arb_tracker.py` (arb_tracker.db) e desenha
uma página única que conta a tese e mostra os dados ao vivo. O tracker continua sendo
o único que ESCREVE no banco — rode-o em paralelo com `python arb_tracker.py --interval 60`.

Uso:
  streamlit run dashboard.py

Fallback: se o banco ainda não tiver dados (tracker não iniciado), a página cai para os
CSVs e, se estes também estiverem vazios, para números estáticos da pesquisa (research_v2.md),
para que a demo sempre renderize.
"""

import os
import sqlite3

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "arb_tracker.db")

# ----------------------------------------------------------------------------- constantes de pesquisa
# Fonte: research_v2.md §2 (profundidade reconciliada, medido 2026-09-18) + PROJECT.md.
# Usadas para (a) anotar/ordenar o gráfico de profundidade e (b) fallback quando não há dados vivos.

# tier: "core" (absorve $100k), "regional" ($10k ok / $100k via split), "morto" (não executável)
POOL_VERDICTS = {
    "USDC/USDT core depth (Polygon)":            {"short": "USDC/USDT (Polygon)", "tier": "core",     "verdict": "Núcleo — $100k limpo"},
    "USDe top pool (Ethena)":                    {"short": "USDe (Ethereum)",     "tier": "core",     "verdict": "Profundo — $100k ok"},
    "USDY/USDC (Solana) — real USDY venue":      {"short": "USDY (Solana)",       "tier": "core",     "verdict": "Real; $100k via split"},
    "BRLA/USDC (Polygon) — primary BRL peg pool":{"short": "BRLA (Polygon)",      "tier": "regional", "verdict": "Melhor peg regional; $10k limpo"},
    "BRLA/USDC.e (Gnosis) — 2nd deepest BRL peg":{"short": "BRLA (Gnosis)",       "tier": "regional", "verdict": "2º peg BRL; parte do split $100k"},
    "BRLA/USDC.e Curve (Gnosis) — 3rd BRL peg venue": {"short": "BRLA (Curve/Gnosis)", "tier": "regional", "verdict": "Suplementar p/ split"},
    "BRLA/USDC (Base) — 4th BRL peg venue":      {"short": "BRLA (Base)",         "tier": "regional", "verdict": "Suplementar p/ split"},
    "BRZ (Polygon, thin) — secondary BRL peg":   {"short": "BRZ (Polygon)",       "tier": "regional", "verdict": "Fino; só $10k c/ slippage"},
    "USDY top pool (ETH, thin — monitor only)":  {"short": "USDY (ETH, fino)",    "tier": "morto",    "verdict": "Fino — só monitorar"},
    "MXNe on Base (dead — monitoring only)":     {"short": "MXNe (Base)",         "tier": "morto",    "verdict": "Não executável (~$558)"},
    "cCOP on Celo (dead — monitoring only)":     {"short": "cCOP (Celo)",         "tier": "morto",    "verdict": "Não executável (~$444)"},
}

TIER_COLOR = {"core": "#1f9d55", "regional": "#d69e2e", "morto": "#c53030"}
TIER_LABEL = {"core": "Núcleo ($100k)", "regional": "Regional ($10k / split $100k)", "morto": "Morto (monitorar)"}

# Números estáticos de fallback (research_v2.md §1-2), caso não haja NENHUM dado vivo/CSV.
STATIC_FALLBACK_POOLS = [
    ("USDC/USDT (Polygon)", 8_297_662, "core"),
    ("USDe (Ethereum)",     34_000_000, "core"),
    ("USDY (Solana)",        2_920_000, "core"),
    ("BRLA (Polygon)",         139_009, "regional"),
    ("BRLA (Gnosis)",          103_000, "regional"),
    ("BRZ (Polygon)",          170_000, "regional"),
    ("BRLA (Curve/Gnosis)",     56_000, "regional"),
    ("BRLA (Base)",             45_000, "regional"),
    ("MXNe (Base)",                558, "morto"),
    ("cCOP (Celo)",                444, "morto"),
]
STATIC_TERMINAL = {"mid": 5.168, "ask": 5.1683, "bid": 5.1677}

N10K, N100K = 10_000, 100_000

# ----------------------------------------------------------------------------- acesso a dados (somente leitura)

def _db_exists_with_rows(table):
    if not os.path.exists(DB_PATH):
        return False
    try:
        uri = f"file:{DB_PATH}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        con.close()
        return n > 0
    except Exception:
        return False


def _read_sql(query):
    uri = f"file:{DB_PATH}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        return pd.read_sql(query, con)
    finally:
        con.close()


def _read_csv(name):
    path = os.path.join(HERE, name)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if len(df):
                return df
        except Exception:
            pass
    return None


@st.cache_data(ttl=5)
def load_source():
    """Decide a fonte de dados: 'db', 'csv' ou 'static'. Retorna string de status."""
    if _db_exists_with_rows("fx_refs") or _db_exists_with_rows("dex_pools"):
        return "db"
    if _read_csv("arb_tracker_fx_refs.csv") is not None or _read_csv("arb_tracker_dex_pools.csv") is not None:
        return "csv"
    return "static"


@st.cache_data(ttl=5)
def get_table(table, csv_name):
    src = load_source()
    if src == "db" and _db_exists_with_rows(table):
        return _read_sql(f"SELECT * FROM {table}")
    if src in ("db", "csv"):
        df = _read_csv(csv_name)
        if df is not None:
            return df
    return pd.DataFrame()


def latest_rows(df, ts_col="ts"):
    if df.empty or ts_col not in df.columns:
        return df
    return df[df[ts_col] == df[ts_col].max()].copy()


# ----------------------------------------------------------------------------- helpers de formatação

def fmt_money(x):
    try:
        return f"${x:,.0f}"
    except (TypeError, ValueError):
        return "n/d"


def tier_of(label):
    v = POOL_VERDICTS.get(label)
    return v["tier"] if v else "regional"


def short_of(label):
    v = POOL_VERDICTS.get(label)
    return v["short"] if v else (label[:24] + "…" if len(label) > 25 else label)


# ----------------------------------------------------------------------------- seções (fragmentos ao vivo)

def render_kpis():
    fx = latest_rows(get_table("fx_refs", "arb_tracker_fx_refs.csv"))
    spreads = latest_rows(get_table("cex_spreads", "arb_tracker_cex_spreads.csv"))
    pools = latest_rows(get_table("dex_pools", "arb_tracker_dex_pools.csv"))

    # terminal USD/BRL
    if not fx.empty and pd.notna(fx["usd_brl"].iloc[0]):
        brl = float(fx["usd_brl"].iloc[0])
        brl_src = ""
    else:
        brl = STATIC_TERMINAL["mid"]
        brl_src = " (estático)"

    # melhor spread líquido
    best_net, best_sym = None, None
    if not spreads.empty and "net_spread_bps" in spreads.columns:
        s = spreads.dropna(subset=["net_spread_bps"])
        if len(s):
            row = s.loc[s["net_spread_bps"].idxmax()]
            best_net, best_sym = float(row["net_spread_bps"]), row["symbol"]

    # pools executáveis
    if not pools.empty and "liquidity_usd" in pools.columns:
        liq = pd.to_numeric(pools["liquidity_usd"], errors="coerce").dropna()
        n_100k = int((liq >= 1_000_000).sum())
        n_10k = int((liq >= 130_000).sum())
    else:
        liq_static = [x[1] for x in STATIC_FALLBACK_POOLS]
        n_100k = sum(1 for x in liq_static if x >= 1_000_000)
        n_10k = sum(1 for x in liq_static if x >= 130_000)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Terminal USD/BRL (Foxbit)", f"R$ {brl:.4f}{brl_src}")
    if best_net is not None:
        c2.metric("Melhor spread líquido", f"{best_net:+.1f} bps",
                  help=f"Par: {best_sym} (bruto − taxas taker de ambas as pernas)")
    else:
        c2.metric("Melhor spread líquido", "n/d")
    c3.metric("Pools p/ $100k", f"{n_100k}", help="Pools com liquidez ≥ $1M")
    c4.metric("Pools p/ $10k", f"{n_10k}", help="Pools com liquidez ≥ $130k")


def render_terminal():
    st.subheader("🇧🇷 Terminal BRL — saída via Foxbit USDC/BRL")
    fx = latest_rows(get_table("fx_refs", "arb_tracker_fx_refs.csv"))
    if not fx.empty and pd.notna(fx["usd_brl"].iloc[0]):
        r = fx.iloc[0]
        mid = float(r["usd_brl"])
        ask = float(r["usd_brl_ask"]) if pd.notna(r.get("usd_brl_ask")) else None
        bid = float(r["usd_brl_bid"]) if pd.notna(r.get("usd_brl_bid")) else None
    else:
        mid, ask, bid = STATIC_TERMINAL["mid"], STATIC_TERMINAL["ask"], STATIC_TERMINAL["bid"]

    spread_bps = ((ask - bid) / mid) * 1e4 if (ask and bid and mid) else None
    c1, c2, c3 = st.columns(3)
    c1.metric("Bid / Ask", f"{bid:.4f} / {ask:.4f}" if (bid and ask) else "n/d")
    c2.metric("Mid (BRL por USDC)", f"R$ {mid:.4f}")
    c3.metric("Spread do book", f"{spread_bps:+.1f} bps" if spread_bps is not None else "n/d")
    st.caption(
        f"Vender **$10k** USDC → **R$ {mid * N10K:,.2f}**  ·  "
        f"Vender **$100k** → **R$ {mid * N100K:,.2f}**.  "
        "Medido: $100k absorve ~0 bps de impacto — o terminal **não** é o gargalo."
    )


def render_depth_chart():
    st.subheader("📊 Profundidade DEX — onde dá pra executar $10k–$100k")
    pools = latest_rows(get_table("dex_pools", "arb_tracker_dex_pools.csv"))

    rows = []
    if not pools.empty and "liquidity_usd" in pools.columns:
        for _, r in pools.iterrows():
            liq = pd.to_numeric(r.get("liquidity_usd"), errors="coerce")
            if pd.isna(liq):
                continue
            label = r["label"]
            rows.append((short_of(label), float(liq), tier_of(label)))
    if not rows:
        rows = [(name, liq, tier) for name, liq, tier in STATIC_FALLBACK_POOLS]

    rows.sort(key=lambda x: x[1], reverse=True)
    names = [x[0] for x in rows]
    liqs = [x[1] for x in rows]
    colors = [TIER_COLOR[x[2]] for x in rows]

    if HAS_PLOTLY:
        fig = go.Figure()
        fig.add_bar(x=names, y=liqs, marker_color=colors,
                    text=[fmt_money(v) for v in liqs], textposition="outside",
                    hovertemplate="%{x}<br>Liquidez: %{text}<extra></extra>")
        fig.add_hline(y=N100K, line_dash="dash", line_color="#4a5568",
                      annotation_text="$100k", annotation_position="right")
        fig.add_hline(y=N10K, line_dash="dot", line_color="#a0aec0",
                      annotation_text="$10k", annotation_position="right")
        fig.update_yaxes(type="log", title="Liquidez do pool (USD, escala log)")
        fig.update_layout(height=430, margin=dict(t=10, b=40, l=10, r=10),
                          showlegend=False)
        st.plotly_chart(fig, width='stretch')
        legend = "  ".join(f"<span style='color:{TIER_COLOR[t]}'>■</span> {TIER_LABEL[t]}"
                           for t in ("core", "regional", "morto"))
        st.markdown(legend, unsafe_allow_html=True)
    else:
        st.bar_chart(pd.DataFrame({"Liquidez (USD)": liqs}, index=names))

    st.caption("Escala logarítmica: USDC/USDT (~$8,3M) e USDe (~$34M) absorvem $100k; "
               "BRLA (~$139k) é o único peg regional viável; MXNe/cCOP (~$500) estão mortos.")


def render_spreads_table():
    st.subheader("💱 Spreads cross-venue — bruto vs. líquido (as taxas comem o spread)")
    spreads = latest_rows(get_table("cex_spreads", "arb_tracker_cex_spreads.csv"))
    if spreads.empty:
        st.info("Sem dados de spread ainda — rode o tracker (`python arb_tracker.py --interval 60`).")
        return

    cols = ["symbol", "best_ask_exchange", "best_ask_price", "best_bid_exchange",
            "best_bid_price", "gross_spread_bps", "net_spread_bps"]
    cols = [c for c in cols if c in spreads.columns]
    df = spreads[cols].copy()
    for c in ("gross_spread_bps", "net_spread_bps"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values("net_spread_bps", ascending=False) if "net_spread_bps" in df.columns else df
    df = df.rename(columns={
        "symbol": "Par", "best_ask_exchange": "Comprar em", "best_ask_price": "Preço compra",
        "best_bid_exchange": "Vender em", "best_bid_price": "Preço venda",
        "gross_spread_bps": "Bruto (bps)", "net_spread_bps": "Líquido (bps)",
    })

    def _color_net(v):
        if pd.isna(v):
            return ""
        return "color: #1f9d55; font-weight:600" if v > 0 else "color: #c53030"

    styler = df.style.format({
        "Preço compra": "{:.5f}", "Preço venda": "{:.5f}",
        "Bruto (bps)": "{:+.1f}", "Líquido (bps)": "{:+.1f}",
    }, na_rep="n/d")
    if "Líquido (bps)" in df.columns:
        styler = styler.map(_color_net, subset=["Líquido (bps)"])
    st.dataframe(styler, width='stretch', hide_index=True)
    st.caption("Líquido = bruto − taxa taker de compra − taxa taker de venda. "
               "Round-trip: ~14 bps Binance · ~20 bps OKX/Bybit/Bitget · ~40 bps Kraken/Gate. "
               "**Um spread bruto positivo não é lucro** até o líquido superar 0.")


def render_timeseries():
    st.subheader("⏱️ Séries temporais — o dado ao vivo")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Spread líquido (bps) por par**")
        spreads = get_table("cex_spreads", "arb_tracker_cex_spreads.csv")
        if not spreads.empty and {"ts", "symbol", "net_spread_bps"}.issubset(spreads.columns):
            s = spreads.copy()
            s["net_spread_bps"] = pd.to_numeric(s["net_spread_bps"], errors="coerce")
            pivot = s.pivot_table(index="ts", columns="symbol",
                                  values="net_spread_bps", aggfunc="last")
            if len(pivot):
                st.line_chart(pivot, height=280)
            else:
                st.caption("Aguardando pontos suficientes…")
        else:
            st.caption("Sem histórico de spreads ainda.")

    with col2:
        st.markdown("**Peg-dev BRLA vs. R$1,00 (bps)**")
        pools = get_table("dex_pools", "arb_tracker_dex_pools.csv")
        if not pools.empty and {"ts", "label", "peg_dev_bps"}.issubset(pools.columns):
            brla = pools[pools["label"].str.contains("BRLA/USDC \\(Polygon\\)", regex=True, na=False)].copy()
            brla["peg_dev_bps"] = pd.to_numeric(brla["peg_dev_bps"], errors="coerce")
            series = brla.set_index("ts")["peg_dev_bps"].dropna()
            if len(series):
                st.line_chart(series, height=280)
            else:
                st.caption("Aguardando pontos suficientes…")
        else:
            st.caption("Sem histórico de peg ainda.")


def render_live_sections():
    """Tudo que atualiza sozinho fica aqui dentro (fragmento com run_every)."""
    render_kpis()
    st.divider()
    render_terminal()
    st.divider()
    render_depth_chart()
    st.divider()
    render_spreads_table()
    st.divider()
    render_timeseries()

    # rodapé com timestamp do último poll
    fx = latest_rows(get_table("fx_refs", "arb_tracker_fx_refs.csv"))
    last_ts = fx["ts"].iloc[0] if (not fx.empty and "ts" in fx.columns) else "—"
    st.caption(f"Último poll: **{last_ts}**  ·  fonte: {load_source().upper()}  ·  "
               "Aviso: spreads brutos excluem taxas/slippage. Ver fila de verificação em `research_v2.md` "
               "antes de alocar capital.")


# fragmento com auto-refresh (Streamlit >= 1.33). Se indisponível, roda sem auto-refresh.
if hasattr(st, "fragment"):
    render_live_sections = st.fragment(run_every="10s")(render_live_sections)


# ----------------------------------------------------------------------------- página

def main():
    st.set_page_config(page_title="Arb Tracker — PoC", page_icon="📈", layout="wide")

    st.title("📈 Arbitragem de stablecoins/RWA — PoC ao vivo")
    st.caption("DEX-first, terminal em BRL. Dados vivos do `arb_tracker` + achados da pesquisa. "
               "Para trader operando **$10k–$100k**.")

    src = load_source()
    if src != "db":
        st.warning(
            "⏳ Aguardando o tracker escrever no banco. Exibindo "
            + ("CSVs salvos." if src == "csv" else "números estáticos da pesquisa (research_v2.md).")
            + "  Inicie: `python arb_tracker.py --interval 60`.",
            icon="⏳",
        )

    with st.expander("💡 A tese (clique para ler)", expanded=False):
        st.markdown(
            """
**O problema.** Um trader precisa entrar/sair de stablecoins e ativos tokenizados e conseguir
**sacar em USD/USDC** — de verdade — movimentando **$10k a $100k**. A maioria dos ativos regionais
promete arbitragem mas **não tem liquidez real** para sair no tamanho necessário.

**O reframe (v1 → v2).**
- *v1 perguntava:* "esse token tem **listagem em CEX** com saque em USD?"
- *v2 pergunta:* "esse token tem **profundidade em DEX** até USDC/USDT no tamanho?"

A última milha (`USDC/USDT → BRL`) já roda via **Foxbit** (terminal USDC/BRL). Isso **inverte o teste**:
o gargalo deixa de ser acesso a CEX e passa a ser **profundidade executável on-chain**.

**O que já medimos (2026-09-18).**
- **Terminal resolvido:** USDC/BRL ≈ R$5,168; **$100k sai com ~0 bps** de impacto.
- **Núcleo USD pronto:** USDC/USDT on-chain ~**$8,3M**; USDe ~**$34M** → round-trip de $100k viável.
- **Peg regional:** **BRLA (~$139k)** é o único viável; $10k limpo, $100k via split multi-chain.
- **Resultado negativo forte:** **MXNe (~$558)** e **cCOP (~$444)** confirmados **não executáveis**.
- **Cuidado com taxas:** spreads brutos raramente cobrem ~14–40 bps de round-trip → olhar o **líquido**.
            """
        )

    st.divider()
    render_live_sections()


# `streamlit run dashboard.py` executa o arquivo como __main__.
main()
