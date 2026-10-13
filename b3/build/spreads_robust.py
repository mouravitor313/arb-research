#!/usr/bin/env python3
"""
spreads_robust.py — robustez do backtest de reversão dos pares de classe (fase 2).

Para cada par da tabela `spreads` (snapshot mais recente):
  * grade de parâmetros: win ∈ {63, 126, 252} × z_in ∈ {1.5, 2, 2.5} → % das 9 configs com média líquida > 0
  * divisão temporal na config padrão (126, 2): 2019–2022 (dentro) vs 2023+ (fora)
  * t-stat da média líquida por operação (troca, sem aluguel)
  * capacidade: 10% do ADTV21 da perna menos líquida
Saída: data/spreads_robust.csv + impressão.

Uso: python b3/build/spreads_robust.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common  # noqa: E402
from spreads import backtest, load  # noqa: E402

SPLIT = "2023-01-01"


def series(con, r, since):
    la, lb = load(con, r.leg_a, since), load(con, r.leg_b, since)
    if r.kind == "classes":
        j = pd.concat([la.close_tr, lb.close_tr], axis=1, keys=["a", "b"]).dropna()
        return np.log(j.a) - np.log(j.b)
    return None


def tstat(x):
    x = np.asarray(x)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else np.nan


def main():
    con = common.db()
    asof = con.execute("SELECT max(asof) FROM spreads").fetchone()[0]
    sp = pd.read_sql("SELECT * FROM spreads WHERE asof=? AND kind='classes'", con, params=(asof,))
    rows = []
    for r in sp.itertuples():
        s = series(con, r, "2019-01-01")
        grid = []
        for win in (63, 126, 252):
            for z in (1.5, 2.0, 2.5):
                t = pd.DataFrame(backtest(s, r.cost_rt, 0.03, win, z, 0.5, 126))
                grid.append(t.net_swap.mean() if len(t) else np.nan)
        base = pd.DataFrame(backtest(s, r.cost_rt, 0.03, 126, 2.0, 0.5, 126))
        ins = base[base.entry < SPLIT] if len(base) else base
        oos = base[base.entry >= SPLIT] if len(base) else base
        rows.append({
            "pair": r.pair, "z252": r.z252, "half_life": r.half_life, "cost_rt": r.cost_rt,
            "grid_pos": float(np.nanmean(np.array(grid) > 0)), "grid_med": float(np.nanmedian(grid)),
            "n": len(base), "mean": base.net_swap.mean() if len(base) else np.nan,
            "t": tstat(base.net_swap) if len(base) else np.nan,
            "n_in": len(ins), "mean_in": ins.net_swap.mean() if len(ins) else np.nan,
            "n_oos": len(oos), "mean_oos": oos.net_swap.mean() if len(oos) else np.nan,
            "win_oos": (oos.net_swap > 0).mean() if len(oos) else np.nan,
            "cap_brl": 0.1 * min(r.adtv_a or 0, r.adtv_b or 0),
        })
    df = pd.DataFrame(rows).sort_values("mean_oos", ascending=False)
    df.to_csv(os.path.join(common.DATA, "spreads_robust.csv"), index=False)
    pd.set_option("display.width", 250)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
