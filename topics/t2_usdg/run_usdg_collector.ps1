# t2_usdg — starts usdg_probe.py --loop hidden/detached (read-only). Stop: .\run_usdg_collector.ps1 -Stop
param([switch]$Stop, [int]$Interval = 90, [double]$Hours = 24)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $here "usdg_probe.pid"
if ($Stop) {
    New-Item -ItemType File -Force (Join-Path $here "usdg.stop") | Out-Null
    if (Test-Path $pidFile) { $p = Get-Content $pidFile; Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; Remove-Item $pidFile; "stopped $p" } else { "no pid file (stop flag set)" }
    return
}
Remove-Item (Join-Path $here "usdg.stop") -ErrorAction SilentlyContinue
$py = Join-Path $here "..\..\.venv\Scripts\python.exe"
$proc = Start-Process -FilePath $py -ArgumentList "-u", "usdg_probe.py", "--loop", $Interval, "--hours", $Hours `
    -WorkingDirectory $here -WindowStyle Hidden -PassThru `
    -RedirectStandardError (Join-Path $here "collector.stderr.log") -RedirectStandardOutput (Join-Path $here "collector.stdout.log")
"started usdg collector (launcher pid $($proc.Id)); python pid in usdg_probe.pid"
