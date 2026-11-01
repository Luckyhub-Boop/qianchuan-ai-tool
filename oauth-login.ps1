$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Resolve-Python {
    $candidates = @()
    if ($env:QIANCHUAN_PYTHON) {
        $candidates += $env:QIANCHUAN_PYTHON.Trim('"')
    }
    foreach ($name in @("py.exe", "python.exe")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            $candidates += $command.Source
        }
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

$python = Resolve-Python
if (-not $python) {
    Write-Host "Python was not found. OAuth login cannot start." -ForegroundColor Red
    exit 1
}

& $python -X utf8 (Join-Path $PSScriptRoot "oauth_login.py") @args
exit $LASTEXITCODE
