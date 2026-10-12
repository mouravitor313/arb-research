# t2_usdg — starts okx_fast.py hidden/detached (read-only OKX public books). Stop: .\run_okx_fast.ps1 -Stop
param([switch]$Stop, [int]$Interval = 10, [double]$Hours = 24)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $here "okx_fast.pid"
if ($Stop) {
    New-Item -ItemType File -Force (Join-Path $here "okx_fast.stop") | Out-Null
    if (Test-Path $pidFile) { $p = Get-Content $pidFile; Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; Remove-Item $pidFile; "stopped $p" } else { "no pid file (stop flag set)" }
    return
}
Remove-Item (Join-Path $here "okx_fast.stop") -ErrorAction SilentlyContinue
$py = Join-Path $here "..\..\.venv\Scripts\python.exe"
$proc = Start-Process -FilePath $py -ArgumentList "-u", "okx_fast.py", "--interval", $Interval, "--hours", $Hours `
    -WorkingDirectory $here -WindowStyle Hidden -PassThru `
    -RedirectStandardError (Join-Path $here "okx_fast.stderr.log") -RedirectStandardOutput (Join-Path $here "okx_fast.stdout.log")
"started okx_fast (launcher pid $($proc.Id))"
