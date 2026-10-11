# run_dashboard.ps1 — sobe o tracker (loop) + o dashboard Streamlit numa tacada só.
#
#   .\run_dashboard.ps1                # intervalo padrao 60s
#   .\run_dashboard.ps1 -Interval 30   # poll a cada 30s
#
# O tracker roda numa nova janela do PowerShell (escrevendo em arb_tracker.db);
# o dashboard roda nesta janela. Ctrl+C encerra o dashboard; feche a janela do
# tracker para pará-lo.

param(
    [int]$Interval = 60
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# Escolhe o Python do venv se existir, senão o do PATH.
$venvPy = Join-Path $here ".venv\Scripts\python.exe"
$py = if (Test-Path $venvPy) { $venvPy } else { "python" }

Write-Host "Iniciando tracker (--interval $Interval) em nova janela..." -ForegroundColor Cyan
Start-Process -FilePath $py `
    -ArgumentList @("$here\arb_tracker.py", "--interval", "$Interval") `
    -WorkingDirectory $here

Start-Sleep -Seconds 2
Write-Host "Iniciando dashboard (http://localhost:8501)..." -ForegroundColor Cyan
& $py -m streamlit run "$here\dashboard.py"
