param(
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$port = if ($env:QIANCHUAN_PORT) { $env:QIANCHUAN_PORT } else { '8765' }
$healthUrl = "http://127.0.0.1:$port/api/health"

function Get-ProjectServerProcess {
    Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine.Contains('server.py') -and
            $_.CommandLine.Contains($root)
        }
}

function Get-ProjectWatchdogProcess {
    Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine.Contains('live_watchdog.py') -and
            $_.CommandLine.Contains($root)
        }
}

$oldServer = @(Get-ProjectServerProcess)
foreach ($process in $oldServer) {
    Write-Host "Stopping project server.py PID=$($process.ProcessId)"
    Stop-Process -Id $process.ProcessId -Force
}

$watchdog = @(Get-ProjectWatchdogProcess)
if ($watchdog.Count -eq 0) {
    Write-Host "Watchdog not found; starting background supervisor."
    $backgroundScript = Join-Path $root 'start-background.ps1'
    $powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    Start-Process -FilePath $powershell `
        -ArgumentList @(
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-WindowStyle', 'Hidden',
            '-File', "`"$backgroundScript`"",
            '-Managed'
        ) `
        -WorkingDirectory $root `
        -WindowStyle Hidden
}

$healthy = $false
$payload = $null
for ($attempt = 0; $attempt -lt $TimeoutSeconds; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $payload = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3 -ErrorAction Stop
        if ($payload.ok) {
            $healthy = $true
            break
        }
    } catch {
        # Supervisor may still be starting server.py.
    }
}

if (-not $healthy) {
    Write-Error "Backend did not become healthy within $TimeoutSeconds seconds. Check data/live-watchdog.log and data/live-server.log."
    exit 1
}

$newServer = @(Get-ProjectServerProcess)
$watchdogAfter = @(Get-ProjectWatchdogProcess)

[pscustomobject]@{
    OldServerPids = ($oldServer.ProcessId -join ',')
    NewServerPids = ($newServer.ProcessId -join ',')
    WatchdogPids = ($watchdogAfter.ProcessId -join ',')
    HealthOk = $payload.ok
    Status = $payload.status
    SyncedAt = $payload.syncedAt
} | Format-List

Write-Host "Backend restarted and healthy: $healthUrl"
