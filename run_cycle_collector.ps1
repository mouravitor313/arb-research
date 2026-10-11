# Starts cycle_collector.py hidden and detached (survives closing the terminal).
# Read-only on-chain collector (RECAP §5 item B). Log: cycle_collector.log. Stop: .\run_cycle_collector.ps1 -Stop
# Optional: $env:POLYGON_RPC_URL = "https://..." before running (otherwise public RPCs).
param([switch]$Stop, [int]$Interval = 12)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root "cycle_collector.pid"

if ($Stop) {
    if (Test-Path $pidFile) {
        $p = Get-Content $pidFile
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        Remove-Item $pidFile
        "stopped $p"
    } else { "no pid file" }
    return
}

$py = Join-Path $root ".venv\Scripts\python.exe"
$proc = Start-Process -FilePath $py -ArgumentList "cycle_collector.py", "--interval", $Interval `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru `
    -RedirectStandardError (Join-Path $root "cycle_collector.stderr.log") `
    -RedirectStandardOutput (Join-Path $root "cycle_collector.stdout.log")
$proc.Id | Out-File -Encoding ascii $pidFile
"started cycle_collector pid $($proc.Id)"
