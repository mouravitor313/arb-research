# Starts topics/t3_brla_l2/collector.py hidden and detached. Read-only. Log: collector.log.
# Stop: .\run_collector.ps1 -Stop
param([switch]$Stop, [int]$Interval = 15, [double]$Hours = 24)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $here)
$pidFile = Join-Path $here "collector.pid"

if ($Stop) {
    if (Test-Path $pidFile) {
        $p = Get-Content $pidFile
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.CommandLine -match 'collector.py --interval' -and $_.CommandLine -notmatch 'xvenue|cycle|t5_' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Remove-Item $pidFile
        "stopped $p"
    } else { "no pid file" }
    return
}

$py = Join-Path $root ".venv\Scripts\python.exe"
$proc = Start-Process -FilePath $py -ArgumentList "collector.py", "--interval", $Interval, "--hours", $Hours `
    -WorkingDirectory $here -WindowStyle Hidden -PassThru `
    -RedirectStandardError (Join-Path $here "collector.stderr.log") `
    -RedirectStandardOutput (Join-Path $here "collector.stdout.log")
$proc.Id | Out-File -Encoding ascii $pidFile
"started t3 collector pid $($proc.Id)"
