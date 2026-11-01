param(
    [string]$TaskName = "QianchuanLiveScreenAutostart"
)

$ErrorActionPreference = "Stop"
$startupDir = [Environment]::GetFolderPath("Startup")
$fallbackPath = Join-Path $startupDir "QianchuanLiveScreenAutostart.vbs"
$loopPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "start-autostart-loop.ps1")).Path
$backgroundPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "start-background.ps1")).Path
$watchdogPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "live_watchdog.py")).Path
$agentPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "live-screen-agent.js")).Path

try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        if ($task.State -eq "Running") {
            Stop-ScheduledTask -TaskName $TaskName
        }
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Autostart task removed: $TaskName"
    } else {
        Write-Host "Autostart task does not exist: $TaskName"
    }
} catch {
    Write-Warning "Could not remove the Scheduled Task: $($_.Exception.Message)"
}

if (Test-Path -LiteralPath $fallbackPath) {
    Remove-Item -LiteralPath $fallbackPath -Force
    Write-Host "Startup fallback removed: $fallbackPath"
}

$matchingProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine.IndexOf($loopPath, [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            $_.CommandLine.IndexOf($backgroundPath, [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            $_.CommandLine.IndexOf($watchdogPath, [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            $_.CommandLine.IndexOf($agentPath, [StringComparison]::OrdinalIgnoreCase) -ge 0
        )
    })
foreach ($process in $matchingProcesses) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host "Background collector processes stopped: $($matchingProcesses.Count)"
