$ErrorActionPreference = "Stop"

$Background = $args -contains "-Background"

Set-Location -Path $PSScriptRoot

$dataDir = Join-Path $PSScriptRoot "data"
$logPath = Join-Path $dataDir "live-autostart.log"
$logFallbackPath = Join-Path $dataDir "live-autostart.active.log"
$backgroundScript = Join-Path $PSScriptRoot "start-background.ps1"
$installScript = Join-Path $PSScriptRoot "install-autostart.ps1"
$powershellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$port = if ($env:QIANCHUAN_PORT) { $env:QIANCHUAN_PORT } else { "8765" }
$url = "http://127.0.0.1:$port/"
$openUrl = "http://127.0.0.1:$port/?v=20261025-export#diagnosis"

if (-not (Test-Path -LiteralPath $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

function Write-LauncherLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date).ToString("o"), $Message
    try {
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    } catch {
        try {
            Add-Content -LiteralPath $logFallbackPath -Value $line -Encoding UTF8
        } catch {
            # Logging must never prevent the backend from starting.
        }
    }
}

function Resolve-Python {
    $candidates = @()
    if ($env:QIANCHUAN_PYTHON) {
        $candidates += $env:QIANCHUAN_PYTHON.Trim('"')
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $candidates += $pyCommand.Source
    }
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidates += $pythonCommand.Source
    }

    $candidates += @(
        (Join-Path $PSScriptRoot "runtime\python\python.exe"),
        (Join-Path $PSScriptRoot "python\python.exe"),
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
    )

    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        try {
            $null = & $candidate -c "import sys; raise SystemExit(0)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return (Resolve-Path -LiteralPath $candidate).Path
            }
        } catch {
            continue
        }
    }
    return $null
}

function Test-AutostartConfigured {
    try {
        $task = Get-ScheduledTask -TaskName "QianchuanLiveScreenAutostart" -ErrorAction SilentlyContinue
        if ($task) {
            return $true
        }
    } catch {
        # Fall back to checking the current user's Startup shortcut.
    }

    $startupDir = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupDir "QianchuanLiveScreenAutostart.lnk"
    return Test-Path -LiteralPath $shortcutPath
}

function Open-DashboardPage {
    param([string]$TargetUrl)

    $browserCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe")
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }

    foreach ($browser in $browserCandidates) {
        try {
            Start-Process -FilePath $browser -ArgumentList @($TargetUrl)
            Write-LauncherLog "Opened dashboard with $browser"
            return $true
        } catch {
            Write-LauncherLog "Explicit browser launch failed for ${browser}: $($_.Exception.Message)"
        }
    }

    try {
        Start-Process $TargetUrl
        Write-LauncherLog "Opened dashboard with the default URL handler."
        return $true
    } catch {
        Write-LauncherLog "The server is ready, but no browser could be opened: $($_.Exception.Message)"
        return $false
    }
}

try {
    $pythonPath = Resolve-Python
    if (-not $pythonPath) {
        throw "Python was not found. The bundled runtime/python/python.exe is missing or invalid."
    }

    $env:QIANCHUAN_PYTHON = $pythonPath
    Write-LauncherLog "Foreground launcher requested. Python=$pythonPath Port=$port"

    if (-not (Test-AutostartConfigured)) {
        Write-LauncherLog "Autostart was not configured; attempting one-time installation."
        Write-Host "Autostart was not configured. Attempting one-time installation..."
        try {
            $installArguments = @(
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy Bypass",
                "-WindowStyle Hidden",
                "-File `"$installScript`""
                "-NoStart"
            )
            $installProcess = Start-Process `
                -FilePath $powershellPath `
                -ArgumentList $installArguments `
                -WorkingDirectory $PSScriptRoot `
                -WindowStyle Hidden `
                -Wait `
                -PassThru
            if ($installProcess.ExitCode -ne 0) {
                Write-LauncherLog "Autostart installation exited with code $($installProcess.ExitCode); continuing with the current launch."
            }
        } catch {
            Write-LauncherLog "Autostart installation failed; continuing with the current launch: $($_.Exception.Message)"
        }
    }

    $arguments = @(
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy Bypass",
        "-WindowStyle Hidden",
        "-File `"$backgroundScript`"",
        "-Managed"
    )
    $launcher = Start-Process `
        -FilePath $powershellPath `
        -ArgumentList $arguments `
        -WorkingDirectory $PSScriptRoot `
        -WindowStyle Hidden `
        -PassThru

    Write-Host "Backend supervisor requested (PID $($launcher.Id))."
    Write-Host "Waiting for $url ..."

    $healthy = $false
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "${url}api/health" -TimeoutSec 2 -ErrorAction Stop
            if ($health.ok) {
                $healthy = $true
                break
            }
        } catch {
            # The supervisor may still be starting server.py.
        }
        Start-Sleep -Seconds 1
    }

    if (-not $healthy) {
        $launcherState = if ($launcher.HasExited) { "exited with code $($launcher.ExitCode)" } else { "is still running" }
        throw "server.py did not become healthy within 120 seconds; the background supervisor $launcherState. See data/live-autostart.log, data/live-watchdog.log and data/live-server.log."
    }

    Write-LauncherLog "Server health confirmed at ${url}api/health"
    Write-Host "Server is ready: $url"
    if (-not (Open-DashboardPage -TargetUrl $openUrl)) {
        Write-Host "Server is running. Open manually: $openUrl" -ForegroundColor Yellow
    }
} catch {
    $message = "Startup failed: $($_.Exception.Message)"
    Write-LauncherLog $message
    Write-Host $message -ForegroundColor Red
    if (-not $Background) {
        Write-Host "Logs: data\live-autostart.log, data\live-watchdog.log, data\live-server.log"
    }
    exit 1
}
