param(
    [string]$At = '2026-11-19 01:00:00',
    [int]$MaxWaitHours = 12
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$logPath = Join-Path $root 'data\night-restart.log'

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'), $Message
    try {
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    } catch {
        # logging must not stop the timer
    }
}

$target = [datetime]::ParseExact($At, 'yyyy-MM-dd HH:mm:ss', $null)
$deadline = $target.AddHours($MaxWaitHours)
Write-Log "ARMED target=$($target.ToString('yyyy-MM-dd HH:mm:ss')) windowHours=$MaxWaitHours pid=$PID"

# Wall-clock loop, not a countdown: after sleep/hibernate the clock is compared
# again, so a delayed wake still fires instead of drifting by hours.
while ((Get-Date) -lt $target) {
    if ((Get-Date) -gt $deadline) {
        Write-Log "ABORT reason=wait_window_expired now=$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))"
        exit 1
    }
    Start-Sleep -Seconds 30
}

Write-Log "TRIGGER calling restart-stack.ps1"
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
& $powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $root 'restart-stack.ps1') *>> $logPath
$code = $LASTEXITCODE
Write-Log "EXIT restart-stack code=$code"
exit $code
