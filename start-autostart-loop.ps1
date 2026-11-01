param(
    [int]$RestartDelaySeconds = 30
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$dataDir = Join-Path $PSScriptRoot "data"
$logPath = Join-Path $dataDir "live-autostart.log"
$logFallbackPath = Join-Path $dataDir "live-autostart.active.log"
$backgroundScript = Join-Path $PSScriptRoot "start-background.ps1"
$powershellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path -LiteralPath $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

function Write-LoopLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date).ToString("o"), $Message
    try {
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    } catch {
        try {
            Add-Content -LiteralPath $logFallbackPath -Value $line -Encoding UTF8
        } catch {
            # Logging must never stop the autostart loop.
        }
    }
}

while ($true) {
    Write-LoopLog "Autostart loop launching background watchdog."
    try {
        $arguments = @(
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy Bypass",
            "-WindowStyle Hidden",
            "-File `"$backgroundScript`"",
            "-Managed"
        )
        $process = Start-Process `
            -FilePath $powershellPath `
            -ArgumentList $arguments `
            -WorkingDirectory $PSScriptRoot `
            -WindowStyle Hidden `
            -Wait `
            -PassThru
        Write-LoopLog "Background watchdog exited with code $($process.ExitCode); restarting in $RestartDelaySeconds seconds."
    } catch {
        Write-LoopLog "Autostart loop error: $($_.Exception.Message); retrying in $RestartDelaySeconds seconds."
    }
    Start-Sleep -Seconds ([Math]::Max(5, $RestartDelaySeconds))
}
