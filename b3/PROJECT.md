# b3/PROJECT.md — Small caps da B3 (pesquisa + monitor)

> Arquivo de contexto entre sessões desta frente. **Leia primeiro ao retomar.** Independente do arb
> cripto (raiz do repo). Última atualização: 2026-10-12 (fases 1 e 2 concluídas).

## Objetivo
Entender as small caps da B3, manter **histórico confiável** e montar **monitoramento** de preço,
oportunidades e comportamento. Frente contínua: cada fase = uma sessão, aprofundando um tipo de
oportunidade.

## Decisões (usuário, 2026-10-12)
- **Foco:** os quatro, em fases — spreads estruturais, valor/fundamentos, quant/comportamento, eventos/fluxo.
- **Dados:** só gratuitos (B3 COTAHIST + endpoints públicos B3, CVM dados abertos, yfinance `.SA`).
- **Universo:** carteira **SMLL** ∪ (market cap < R$ 10 bi **e** ADTV21 > R$ 1 mi). Parâmetros em
  `build/universe.py --mcap-max/--adtv-min`.
- Pasta `b3/` neste repo. Só leitura de mercado, nenhuma ordem; não commitar sem o usuário pedir.

## Estado
- ✅ **Fase 1 — Fundação** (2026-10-12). Relatório: `reports/REPORT_fase1.md`.
  - `prices_raw`: COTAHIST 2010-01-04 → 2026-10-09, à vista ON/PN/UNIT (CODBDI 02/05/06/07/08) + BOVA11/SMAL11
    (1,40 mi linhas; coluna `codbdi`).
  - Universo em 2026-10-09: **308** emissoras negociadas → **143 incluídas** (103 SMLL + 40 pela regra), 6 em RJ/RE
    (coluna `distress`).
  - Ajuste: últimos 3 anos, **131/137** tickers principais batem com Yahoo Adj Close (p95 ≤ 1%).
    Fora: SYNE3, JSLG3 (proventos especiais/redução de capital), CASH3, LJQQ3, PGMN3, VULC3 (~1,5%).
  - 29 pares ON/PN/UNIT no universo (tabela §4 do relatório) → insumo da fase 2.
- ✅ **Fase 2 — Spreads estruturais** (2026-10-12). Relatório: `reports/REPORT_fase2.md`.
  - Units vs cesta: sem edge (meia-vida < 1 pregão, desvio < custo).
  - Pares ON/PN: robustos só BMEB, CLSC (ilíquidos), SAPR4/SAPR3 (+0,6%/op., ~R$ 260 mil/dia) e POMO4/POMO3
    (+0,8%/op., ~R$ 1 mi/dia, enfraquecendo). Uso = troca de classe, não L/S (aluguel de ON ilíquida > 20% a.a.).
  - Holdings (`config/holdings.json`): Bradespar 32,6% (menor em 12m, z −3,4), Simpar virou desconto de 9% (z +1,9);
    descontos não estacionários → monitorar, não reverter mecanicamente.
  - OPAs (`config/opas.json`, fonte CVM IPE): Desktop +6% (parcela diferida + prazo), Helbor +0,5% até 28/10,
    Unifique/Fras-le com tela acima da oferta. TASA3 com prêmio recorde sobre TASA4 sem fato relevante.
- ⏭️ **Próxima: fase 3 — valor/fundamentos** (`sessions/fase3_fundamentos.md`).

## Fontes (verificadas em 2026-10-12)
| Dado | Fonte | Observação |
|---|---|---|
| Cotações diárias | `bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP` | Oficial, não ajustado, layout fixo 245 col; anual do ano corrente é atualizado |
| Carteira de índices | `sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/<b64>` | Só o dia; **sem histórico grátis** → snapshot diário em `index_members` |
| Cadastro, nº de ações, eventos | `listedCompaniesProxy/CompanyCall/GetListedSupplementCompany` e `GetDetail` | Proventos em dinheiro só ~12 meses; eventos em ações **incompletos e às vezes errados** |
| Proventos longos + validação | yfinance `.SA` | Close/Dividends já ajustados por split; usar a razão D/Close_ant |
| Fundamentos / fatos relevantes | `dados.cvm.gov.br` (DFP, ITR, FCA, IPE) | A integrar (fases 3 e 5) |

## Lições de dados (não reaprender)
- **Eventos em ações:** B3 ∪ Yahoo, e evento > 30% só entra se o salto de preço do COTAHIST confirmar
  (exceto se houver lacuna > 30 dias sem negócio). Depois, **inferência por degrau persistente** vs a série
  ajustada do Yahoo (|Δ| > 6%, persistente 5 pregões) pega o que falta nas duas listas (199 inferidos).
  Exemplos de erro da B3: ITUB "grupamento 0,01" em 2011 inexistente; MGLU sem os desdobramentos de 2017/2019.
- **Reuso de ticker:** NATU3 (Natura antiga até 2019 → volta em 2025) e afins: a série tem lacunas longas;
  conferir `data_quality` (`jump_gt_45pct`) antes de usar histórico antigo.
- Pares com razão variando > 2× em 12 meses (AZEV, RCSL) são penny stocks em estresse — movimento real.
- **CODBDI de RJ/RE:** a B3 move a ação do CODBDI 02 para 07 (recuperação extrajudicial) ou 08 (judicial).
  Filtrar só 02 apaga Americanas, Braskem, Oncoclínicas, Oi… (corrigido na fase 2; 86 tickers no histórico).
- Units: composição oficial em https://www.b3.com.br/en_us/market-data-and-indices/data-services/market-data/reports/equities/units
  (CPLE11 obsoleto: Copel unificou ações em dez/25).
- Documentos da CVM (`rad.cvm.gov.br/ENET/frmDownloadDocumento.aspx?...`) vêm como PDF ou HTML; base IPE anual em
  `dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{ano}.zip` (fatos relevantes, editais de OPA).
- Console Windows: rodar com `PYTHONIOENCODING=utf-8` (as APIs da B3 respondem UTF-8 correto).

## Arquivos
- `common.py` — paths, `db()`, `http_get` (retry/pausa), `b3_json` (base64 + cache), `br_num`, `br_date`.
- `ingest/cotahist.py`, `ingest/index_portfolio.py`, `ingest/corporate.py`, `ingest/yahoo.py`.
- `build/adjust.py` (`--validate`), `build/universe.py` (`--report`), `build/report_fase1.py`.
- `build/spreads.py` (pares de classe + unit vs cesta + backtest), `build/spreads_robust.py` (grade, dentro/fora),
  `build/holdings.py` (+ `config/holdings.json`), `build/opas.py` (+ `config/opas.json`), `build/report_fase2.py`.
- `update.py` — atualização incremental diária (≈ 5 min), inclui a fase 2.
- `data/b3.db` (~420 MB, gitignored via `*.db`), `data/raw/` (~600 MB, gitignored).

## Tabelas (`data/b3.db`)
`prices_raw` (bruto COTAHIST) · `prices_adj` (`close`, `close_split`, `close_tr`) · `yf_daily` ·
`companies` (setor, nº ações ON/PN) · `corp_actions` · `index_members` (snapshots) · `universe`
(por emissora, datado) · `universe_tickers` · `data_quality`.

## Próximos passos (fases)
3. **Valor/fundamentos** — CVM DFP/ITR → múltiplos, percentis históricos por empresa/setor, screening.
4. **Quant/comportamento** — momentum, reversão, volume anômalo, efeito rebalanceamento SMLL, backtest walk-forward
   com custo de impacto para ilíquidas.
5. **Eventos + monitor ao vivo** — IPE (fatos relevantes, recompras, OPA), cotação atrasada, tabela `signals`,
   página Streamlit (padrão `../dashboard.py`).
- Pendentes: agendar `update.py` diário (Task Scheduler) para acumular snapshots da SMLL; taxa de aluguel por
  ativo (Boletim Diário B3, endpoint não identificado); Yahoo incremental só traz 60 dias para ticker novo.
