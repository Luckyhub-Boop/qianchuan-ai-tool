$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$ExternalRoot = if ($env:QIANCHUAN_EXTERNAL_ROOT) { $env:QIANCHUAN_EXTERNAL_ROOT } else { Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
$python = Join-Path $ExternalRoot "runtime\python\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Project Python is missing: $python"
}

& $python -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    $bootstrap = Join-Path $env:TEMP "get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $bootstrap -UseBasicParsing -TimeoutSec 60
    & $python $bootstrap
    if ($LASTEXITCODE -ne 0) {
        throw "pip bootstrap failed"
    }
}

& $python -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot "requirements-whisper.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Whisper dependency installation failed"
}

$env:HF_ENDPOINT = "https://hf-mirror.com"
$modelsDir = Join-Path $ExternalRoot "models"
if (-not (Test-Path -LiteralPath $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir | Out-Null
}
$whisperDir = (Join-Path $modelsDir "whisper-large-v3").Replace("\", "/")
& $python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-large-v3', local_dir='$whisperDir')"
if ($LASTEXITCODE -ne 0) {
    throw "Whisper model download failed"
}

Write-Host "Local Whisper is ready: $modelsDir\whisper-large-v3"
