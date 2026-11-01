param(
    [switch]$Managed
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$dataDir = Join-Path $PSScriptRoot "data"
$logPath = Join-Path $dataDir "live-autostart.log"
$logFallbackPath = Join-Path $dataDir "live-autostart.active.log"
$watchdogPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "live_watchdog.py")).Path
$watchdogPidPath = Join-Path $dataDir "live-watchdog.pid"

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
            # Logging must never prevent the watchdog from starting.
        }
    }
}

function Resolve-Node {
    $candidates = @()
    if ($env:QIANCHUAN_NODE) {
        $candidates += $env:QIANCHUAN_NODE.Trim('"')
    }

    $candidates += (Join-Path $PSScriptRoot "runtime\node\node.exe")

    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($nodeCommand) {
        $candidates += $nodeCommand.Source
    }

    $candidates += @(
        (Join-Path $PSScriptRoot "node.exe"),
        (Join-Path $env:ProgramFiles "nodejs\node.exe")
    )
    if ($env:LOCALAPPDATA) {
        $codexNodeRoot = Join-Path $env:LOCALAPPDATA "OpenAI\Codex\runtimes\cua_node"
        if (Test-Path -LiteralPath $codexNodeRoot) {
            $candidates += @(Get-ChildItem -LiteralPath $codexNodeRoot -Directory -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending |
                ForEach-Object { Join-Path $_.FullName "bin\node.exe" })
        }
    }
    if (${env:ProgramFiles(x86)}) {
        $candidates += (Join-Path ${env:ProgramFiles(x86)} "nodejs\node.exe")
    }
    if ($env:LOCALAPPDATA) {
        $candidates += (Join-Path $env:LOCALAPPDATA "Programs\nodejs\node.exe")
    }

    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        try {
            $null = & $candidate --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                return (Resolve-Path -LiteralPath $candidate).Path
            }
        } catch {
            continue
        }
    }
    return $null
}

function Test-Python {
    param(
        [string]$File,
        [string[]]$Arguments
    )
    try {
        $null = & $File @($Arguments + @("-c", "import sys; raise SystemExit(0)")) 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Resolve-Python {
    $candidates = @()
    if ($env:QIANCHUAN_PYTHON) {
        $candidates += @{ File = $env:QIANCHUAN_PYTHON.Trim('"'); Arguments = @() }
    }

    $candidates += @(
        @{ File = (Join-Path $PSScriptRoot "runtime\python\python.exe"); Arguments = @() },
        @{ File = (Join-Path $PSScriptRoot "python\python.exe"); Arguments = @() },
        @{ File = (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"); Arguments = @() }
    )

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $candidates += @{ File = $pyCommand.Source; Arguments = @("-3") }
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidates += @{ File = $pythonCommand.Source; Arguments = @() }
    }

    foreach ($candidate in $candidates) {
        if (-not $candidate.File -or -not (Test-Path -LiteralPath $candidate.File -PathType Leaf)) {
            continue
        }
        if (-not (Test-Python -File $candidate.File -Arguments $candidate.Arguments)) {
            continue
        }
        return @{
            File = (Resolve-Path -LiteralPath $candidate.File).Path
            Arguments = $candidate.Arguments
        }
    }
    return $null
}

try {
    if (Test-Path -LiteralPath $watchdogPidPath -PathType Leaf) {
        $existingPidText = (Get-Content -LiteralPath $watchdogPidPath -Raw -ErrorAction SilentlyContinue).Trim()
        $existingPid = 0
        if ([int]::TryParse($existingPidText, [ref]$existingPid) -and $existingPid -gt 0) {
            $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
            if ($existingProcess) {
                Write-LauncherLog "Watchdog PID file reports a live process ($existingPid); no duplicate process started."
                exit 0
            }
        }
    }

    $existing = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine.IndexOf($watchdogPath, [StringComparison]::OrdinalIgnoreCase) -ge 0
        })
    if ($existing.Count -gt 0) {
        Write-LauncherLog "Watchdog is already running; no duplicate process started."
        exit 0
    }

    $python = Resolve-Python
    if (-not $python) {
        throw "Python was not found. Install Python 3.10+ or set QIANCHUAN_PYTHON."
    }

    $nodePath = Resolve-Node
    if ($nodePath) {
        $env:QIANCHUAN_NODE = $nodePath
    } else {
        Remove-Item Env:QIANCHUAN_NODE -ErrorAction SilentlyContinue
    }
    $env:QIANCHUAN_PYTHON = $python.File
    $env:PYTHONUTF8 = "1"
    $nodeStatus = if ($nodePath) { $nodePath } else { "not-found; server-only mode" }
    Write-LauncherLog "Starting watchdog. Python=$($python.File) Node=$nodeStatus Managed=$Managed"
    $watchdogArguments = @("-X", "utf8") + @($python.Arguments) + @($watchdogPath)
    & $python.File @watchdogArguments
    $exitCode = if ($null -eq $LASTEXITCODE) { 1 } else { [int]$LASTEXITCODE }
    Write-LauncherLog "Watchdog exited with code $exitCode."
    exit $exitCode
} catch {
    Write-LauncherLog "Background startup failed: $($_.Exception.Message)"
    exit 1
}
