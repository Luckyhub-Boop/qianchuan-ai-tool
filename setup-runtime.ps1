# ============================================================
# 直播投放工具 —— 运行环境一键安装
#
# 作用：在一台没有环境的电脑上，把跑起来需要的东西全部准备好
#   1. Python 3.12（含 pip）
#   2. Python 依赖（27 个包，读 requirements.txt）
#   3. Node + puppeteer-core（浏览器控制）
#   4. AI 模型（约 3 GB，可加 -SkipModels 跳过）
#
# 用法：
#   双击 setup-runtime.bat（推荐）
#   或右键本文件 →「使用 PowerShell 运行」
#   命令行：powershell -ExecutionPolicy Bypass -File setup-runtime.ps1
#
# 参数：
#   -TargetRoot <路径>  运行环境装哪，默认优先 D:\AI投放产品，无 D 盘则用
#                       %LOCALAPPDATA%\QianchuanTool
#   -SkipModels         不下载模型（只装环境，模型留给程序首次启动自动下）
#   -Force              已存在的组件也重装
#
# 特点：重复运行安全。已装好的组件会自动跳过，不会破坏现有环境。
# ============================================================

param(
    [string]$TargetRoot = "",
    [switch]$SkipModels,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

# ---------- 常量（都实测过可下载） ----------
$PyVersion   = '3.12.10'
$PyUrl       = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-amd64.exe"
$NodeVersion = 'v24.21.0'
$NodeUrl     = "https://nodejs.org/dist/$NodeVersion/node-$NodeVersion-win-x64.zip"
$PipIndex    = 'https://pypi.tuna.tsinghua.edu.cn/simple'
$NpmRegistry = 'https://registry.npmmirror.com'
$PuppeteerVer = '^24.23.0'

$ProjectRoot = $PSScriptRoot

# ---------- 输出小工具 ----------
function Write-Title($t) { Write-Host ""; Write-Host ("=" * 62) -ForegroundColor Cyan; Write-Host "  $t" -ForegroundColor Cyan; Write-Host ("=" * 62) -ForegroundColor Cyan }
function Write-Step($t)  { Write-Host "  → $t" -ForegroundColor Gray }
function Write-Ok($t)    { Write-Host "  OK  $t" -ForegroundColor Green }
function Write-Warn2($t) { Write-Host "  注意  $t" -ForegroundColor Yellow }
function Write-Err2($t)  { Write-Host "  失败  $t" -ForegroundColor Red }

function Get-FileWithCurl {
    param([string]$Url, [string]$OutFile, [string]$Label)
    Write-Step "下载 $Label"
    Write-Step "  地址：$Url"
    & curl.exe -L --fail --retry 3 --retry-delay 2 --connect-timeout 20 -o $OutFile $Url
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $OutFile)) {
        throw "下载失败：$Label。请检查网络后重跑本脚本。"
    }
    $size = [math]::Round((Get-Item -LiteralPath $OutFile).Length / 1MB, 1)
    Write-Ok "已下载 $Label（$size MB）"
}

# ---------- 0. 决定装在哪 ----------
Write-Title "直播投放工具 · 运行环境安装"

if (-not $TargetRoot) {
    $hasD = Test-Path -LiteralPath 'D:\'
    if ($hasD) { $TargetRoot = 'D:\AI投放产品' }
    else { $TargetRoot = Join-Path $env:LOCALAPPDATA 'QianchuanTool' }
}

$RuntimeDir   = Join-Path $TargetRoot 'runtime'
$PyDir        = Join-Path $RuntimeDir 'python'
$NodeDir      = Join-Path $RuntimeDir 'node'
$NodeModules  = Join-Path $TargetRoot 'node_modules'
$DownloadDir  = Join-Path $env:TEMP 'qianchuan-setup'
$ReqFile      = Join-Path $ProjectRoot 'requirements.txt'

Write-Host ""
Write-Step "安装位置：$TargetRoot"
Write-Step "项目目录：$ProjectRoot"
Write-Step "本次要装：Python / 依赖 / Node / puppeteer-core$(if(-not $SkipModels){' / 模型'} else {''})"
if (-not (Test-Path -LiteralPath $DownloadDir)) { New-Item -ItemType Directory -Path $DownloadDir -Force | Out-Null }

$summary = [ordered]@{}

# ---------- 1. Python ----------
Write-Title "第 1 步 / 4 · Python $PyVersion"

$pyExe = Join-Path $PyDir 'python.exe'
if ((Test-Path -LiteralPath $pyExe) -and -not $Force) {
    $ver = & $pyExe --version 2>&1
    Write-Ok "已存在，跳过（$ver）"
    $summary['Python'] = "已存在 $ver"
} else {
    if ((Test-Path -LiteralPath $PyDir) -and (Test-Path -LiteralPath $PyDir) -and -not (Test-Path -LiteralPath $pyExe)) {
        throw "目录 $PyDir 存在但没有 python.exe。为避免覆盖你自己的东西，请手动清空该目录后重跑。"
    }
    $installer = Join-Path $DownloadDir "python-$PyVersion-amd64.exe"
    Get-FileWithCurl -Url $PyUrl -OutFile $installer -Label "Python $PyVersion 安装包"
    Write-Step "静默安装到 $PyDir（约 1-2 分钟）"
    $installArgs = @(
        '/quiet',
        'InstallAllUsers=0',
        "TargetDir=$PyDir",
        'PrependPath=0',
        'Include_test=0',
        'Include_launcher=0',
        'InstallLauncherAllUsers=0',
        'AssociateFiles=0',
        'Shortcuts=0',
        'Include_pip=1'
    )
    $p = Start-Process -FilePath $installer -ArgumentList $installArgs -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Python 安装程序返回错误码 $($p.ExitCode)" }
    if (-not (Test-Path -LiteralPath $pyExe)) { throw "安装后找不到 $pyExe" }
    $ver = & $pyExe --version 2>&1
    Write-Ok "Python 就绪（$ver）"
    $summary['Python'] = "已安装 $ver"
}

# ---------- 2. Python 依赖 ----------
Write-Title "第 2 步 / 4 · Python 依赖（requirements.txt）"

if (-not (Test-Path -LiteralPath $ReqFile)) { throw "找不到 requirements.txt：$ReqFile" }
$probe = & $pyExe -c "import av, numpy, sherpa_onnx; print('ok')" 2>&1
if ($LASTEXITCODE -eq 0 -and -not $Force) {
    Write-Ok "核心包已就绪，跳过 pip 安装"
    $summary['Python依赖'] = "已就绪"
} else {
    Write-Step "升级 pip"
    & $pyExe -m pip install --upgrade pip --index-url $PipIndex --quiet
    Write-Step "安装 requirements.txt（27 个包，约 200 MB，3-8 分钟）"
    & $pyExe -m pip install -r $ReqFile --index-url $PipIndex
    if ($LASTEXITCODE -ne 0) { throw "pip 安装失败（退出码 $LASTEXITCODE）。可重跑本脚本，pip 会续装已下好的包。" }
    $probe2 = & $pyExe -c "import av, numpy, sherpa_onnx, faster_whisper, opencc; print('ok')" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "依赖装完但仍 import 失败：$probe2" }
    Write-Ok "27 个包安装完成，import 验证通过"
    $summary['Python依赖'] = "已安装并验证"
}

# ---------- 3. Node + puppeteer-core ----------
Write-Title "第 3 步 / 4 · Node $NodeVersion + puppeteer-core"

$nodeExe = Join-Path $NodeDir 'node.exe'
if ((Test-Path -LiteralPath $nodeExe) -and -not $Force) {
    $nv = & $nodeExe --version 2>&1
    Write-Ok "已存在，跳过（$nv）"
    $summary['Node'] = "已存在 $nv"
} else {
    $zip = Join-Path $DownloadDir "node-$NodeVersion-win-x64.zip"
    Get-FileWithCurl -Url $NodeUrl -OutFile $zip -Label "Node $NodeVersion（37 MB）"
    Write-Step "解压到 $NodeDir"
    $tmpDir = Join-Path $DownloadDir 'node-extract'
    if (Test-Path -LiteralPath $tmpDir) { Remove-Item -LiteralPath $tmpDir -Recurse -Force }
    Expand-Archive -LiteralPath $zip -DestinationPath $tmpDir -Force
    $inner = Get-ChildItem -LiteralPath $tmpDir -Directory | Select-Object -First 1
    if (-not (Test-Path -LiteralPath $NodeDir)) { New-Item -ItemType Directory -Path $NodeDir -Force | Out-Null }
    Copy-Item -Path (Join-Path $inner.FullName '*') -Destination $NodeDir -Recurse -Force
    if (-not (Test-Path -LiteralPath $nodeExe)) { throw "解压后找不到 node.exe" }
    $nv = & $nodeExe --version 2>&1
    Write-Ok "Node 就绪（$nv）"
    $summary['Node'] = "已安装 $nv"
}

$puppeteerDir = Join-Path $NodeModules 'puppeteer-core'
if ((Test-Path -LiteralPath $puppeteerDir) -and -not $Force) {
    Write-Ok "puppeteer-core 已存在，跳过"
    $summary['puppeteer-core'] = "已存在"
} else {
    $npmCmd = Join-Path $NodeDir 'npm.cmd'
    if (-not (Test-Path -LiteralPath $npmCmd)) { throw "找不到 npm.cmd（$npmCmd）。Node 包不完整，请删除 $NodeDir 后重跑。" }
    Write-Step "安装 puppeteer-core（用国内镜像）"
    Push-Location $TargetRoot
    try {
        & $npmCmd install "puppeteer-core@$PuppeteerVer" --registry $NpmRegistry --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "npm install 失败（退出码 $LASTEXITCODE）" }
    } finally { Pop-Location }
    if (-not (Test-Path -LiteralPath $puppeteerDir)) { throw "npm 报成功但找不到 puppeteer-core 目录" }
    Write-Ok "puppeteer-core 安装完成"
    $summary['puppeteer-core'] = "已安装"
}

# ---------- 4. 模型 ----------
Write-Title "第 4 步 / 4 · AI 模型"

if ($SkipModels) {
    Write-Warn2 "按参数要求跳过。程序首次启动时看门狗会自动补下。"
    $summary['模型'] = "跳过（首次启动自动下载）"
} else {
    Write-Step "检查模型（whisper-large-v3 / 声纹分离 / 声纹特征）"
    Write-Step "缺失的会自动下载，合计约 3 GB，走 hf-mirror 国内镜像，10-40 分钟"
    $env:QIANCHUAN_EXTERNAL_ROOT = $TargetRoot
    Push-Location $ProjectRoot
    try {
        $json = & $pyExe -c "import json, model_bootstrap; print(json.dumps(model_bootstrap.ensure_models(), ensure_ascii=False))" 2>&1
        if ($LASTEXITCODE -ne 0) { throw "模型准备失败：$json" }
    } finally { Pop-Location }
    if ($json -match '"errors": \[\]') {
        Write-Ok "模型齐备"
        $summary['模型'] = "齐备"
    } else {
        Write-Warn2 "部分模型下载失败，详情：$json"
        $summary['模型'] = "部分失败，首次启动会自动重试"
    }
}

# ---------- 环境变量 ----------
if ($TargetRoot -ne 'D:\AI投放产品') {
    Write-Title "额外设置"
    Write-Step "本机没有 D:\AI投放产品，需要让程序知道环境装在哪"
    [Environment]::SetEnvironmentVariable('QIANCHUAN_EXTERNAL_ROOT', $TargetRoot, 'User')
    Write-Ok "已设置用户环境变量 QIANCHUAN_EXTERNAL_ROOT=$TargetRoot（重开窗口后生效）"
    $summary['环境变量'] = "QIANCHUAN_EXTERNAL_ROOT=$TargetRoot"
}

# ---------- 汇总 ----------
Write-Title "完成，结果如下"
foreach ($k in $summary.Keys) { Write-Host ("  {0,-16} {1}" -f $k, $summary[$k]) }
Write-Host ""
Write-Host "  下一步：" -ForegroundColor Cyan
Write-Host "    1. 设置 DeepSeek API Key 环境变量（如果还没设）："
Write-Host "         setx DEEPSEEK_API_KEY `"你的key`""
Write-Host "    2. 双击 start.bat 启动程序"
Write-Host "    3. 首次使用要登录千川：双击 login-live-screen.bat"
Write-Host "    4. 要用百应采集：双击 login-buyin.bat"
Write-Host ""
Write-Host "  出问题就把本窗口的报错截图发我。" -ForegroundColor Yellow
Write-Host ""
