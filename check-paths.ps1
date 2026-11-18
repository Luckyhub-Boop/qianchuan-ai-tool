# Wrapper: run check_paths.py with the bundled Python runtime.
# All output (Chinese) comes from the Python script, so this file stays ASCII-only
# and never hits PowerShell script-encoding problems.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$externalRoot = Split-Path -Parent (Split-Path -Parent $projectRoot)
$python = Join-Path $externalRoot 'runtime\python\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "python runtime not found: $python"
    Write-Host "run setup-runtime.ps1 first"
    exit 2
}

& $python -X utf8 (Join-Path $projectRoot 'check_paths.py')
exit $LASTEXITCODE
