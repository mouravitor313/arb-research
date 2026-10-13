# b3/ — Small caps da B3

Pesquisa e monitoramento das small caps da B3 com dados gratuitos. Contexto e estado: `PROJECT.md`.

```powershell
pip install -r requirements.txt   # na raiz (inclui yfinance)
$env:PYTHONIOENCODING = "utf-8"

# carga inicial (~15 min; baixa ~600 MB de COTAHIST)
python b3/ingest/cotahist.py --years 2010-2026
python b3/ingest/index_portfolio.py
python b3/ingest/corporate.py
python b3/ingest/yahoo.py
python b3/build/adjust.py --validate
python b3/build/universe.py --report     # -> b3/reports/REPORT_fase1.md

# atualização diária (após o fechamento)
python b3/update.py
```
