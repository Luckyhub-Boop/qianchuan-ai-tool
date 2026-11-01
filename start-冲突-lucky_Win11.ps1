$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$pythonCandidates = @()
$pythonCandidates += @{ File = (Join-Path $PSScriptRoot "runtime\python\python.exe"); Args = @() }
$pythonCandidates += @{ File = (Join-Path $PSScriptRoot "python\python.exe"); Args = @() }
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $pythonCandidates += @{ File = $pyLauncher.Source; Args = @("-3") }
}
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $pythonCandidates += @{ File = $pythonCommand.Source; Args = @() }
}
$pythonCandidates += @{
    File = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    Args = @()
}

$python = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path -LiteralPath $candidate.File) {
        $python = $candidate
        break
    }
}

if (-not $python) {
    Write-Host "未找到 Python。请安装 Python 3，或把 python.exe 加入 PATH 后重试。" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

$port = if ($env:QIANCHUAN_PORT) { $env:QIANCHUAN_PORT } else { "8765" }
$url = "http://127.0.0.1:$port/"
Write-Host "正在启动千川 AI 投放诊断：$url" -ForegroundColor Green
Write-Host "首次启动会自动同步；未配置千川凭证时展示已确认快照。"

try {
    Write-Host "正在结束所有旧 Python 进程..." -ForegroundColor Yellow
    $oldPythonProcesses = @(Get-Process -Name python,pythonw,py -ErrorAction SilentlyContinue)
    foreach ($oldPython in $oldPythonProcesses) {
        Stop-Process -Id $oldPython.Id -Force -ErrorAction SilentlyContinue
    }

    Write-Host "正在清理本项目遗留的采集器和无头浏览器..."
    $oldNodeProcesses = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*live-screen-agent.js*" })
    foreach ($oldNode in $oldNodeProcesses) {
        Stop-Process -Id $oldNode.ProcessId -Force -ErrorAction SilentlyContinue
    }

    $profilePath = Join-Path $PSScriptRoot "data\chrome-profile"
    $oldEdgeProcesses = @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains($profilePath) })
    foreach ($oldEdge in $oldEdgeProcesses) {
        Stop-Process -Id $oldEdge.ProcessId -Force -ErrorAction SilentlyContinue
    }

    $listenerPids = @(Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($listenerPid in $listenerPids) {
        if ($listenerPid -and $listenerPid -ne $PID) {
            Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
    Write-Host "旧进程清理完成，现在启动全新进程。"

    try {
        $existingHealth = Invoke-RestMethod -Uri "${url}api/health" -TimeoutSec 3 -ErrorAction Stop
        if ($existingHealth.ok -and -not ($existingHealth.PSObject.Properties.Name -contains "liveScreenCapture")) {
            Write-Host "检测到旧版服务仍在占用端口，正在切换到新版双通道服务..."
            $listenerPids = Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($listenerPid in $listenerPids) {
                if ($listenerPid -and $listenerPid -ne $PID) {
                    Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
                }
            }
            Start-Sleep -Seconds 2
        }
    } catch {
        # Port is free or no compatible health endpoint is running.
    }

    $nodeCandidates = @()
    if ($env:QIANCHUAN_NODE) {
        $nodeCandidates += $env:QIANCHUAN_NODE.Trim('"')
    }
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($nodeCommand) {
        $nodeCandidates += $nodeCommand.Source
    }
    $nodeCandidates += @(
        (Join-Path $PSScriptRoot "runtime\node\node.exe"),
        (Join-Path $PSScriptRoot "node.exe"),
        (Join-Path $env:ProgramFiles "nodejs\node.exe")
    )
    if (${env:ProgramFiles(x86)}) {
        $nodeCandidates += (Join-Path ${env:ProgramFiles(x86)} "nodejs\node.exe")
    }
    if ($env:LOCALAPPDATA) {
        $nodeCandidates += (Join-Path $env:LOCALAPPDATA "Programs\nodejs\node.exe")
        $codexNodeRoot = Join-Path $env:LOCALAPPDATA "OpenAI\Codex\runtimes\cua_node"
        if (Test-Path -LiteralPath $codexNodeRoot) {
            $nodeCandidates += @(Get-ChildItem -LiteralPath $codexNodeRoot -Directory -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending |
                ForEach-Object { Join-Path $_.FullName "bin\node.exe" })
        }
    }

    $nodePath = $null
    foreach ($candidate in ($nodeCandidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        try {
            $null = & $candidate --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                $nodePath = (Resolve-Path -LiteralPath $candidate).Path
                break
            }
        } catch {
            continue
        }
    }

    $puppeteerReady = Test-Path -LiteralPath (Join-Path $PSScriptRoot "node_modules\puppeteer-core\package.json")
    if ($nodePath -and $puppeteerReady) {
        $env:QIANCHUAN_PYTHON = $python.File
        $env:QIANCHUAN_NODE = $nodePath
        $watchdogArgs = @($python.Args) + @((Join-Path $PSScriptRoot "live_watchdog.py"))
        $watchdog = Start-Process -FilePath $python.File -ArgumentList $watchdogArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru
        $pidLabel = "看门狗"
        $pidValue = $watchdog.Id
        Write-Host "直播大屏双通道看门狗已启动；采集器崩溃会自动拉起。"
    } else {
        $serverArgs = @($python.Args) + @("server.py")
        $server = Start-Process -FilePath $python.File -ArgumentList $serverArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru
        $pidLabel = "服务"
        $pidValue = $server.Id
        Write-Host "未检测到 Node.js 或 puppeteer-core，本次只启动主服务。运行 login-live-screen.bat 完成双通道安装和登录。" -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 5
    Start-Process $url
    Write-Host "$pidLabel 已启动（PID $pidValue）。关闭本窗口不会停止后台进程。"
    Write-Host "停止后台进程：Stop-Process -Id $pidValue"
} catch {
    Write-Host "后台启动失败，改为前台运行：$($_.Exception.Message)" -ForegroundColor Yellow
    Start-Process $url
    & $python.File @($python.Args + "server.py")
}
