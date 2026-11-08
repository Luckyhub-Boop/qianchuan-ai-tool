param(
    [string]$TaskName = "QianchuanLiveScreenAutostart",
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$loopPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "start-autostart-loop.ps1")).Path
$hiddenPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "start-hidden.vbs")).Path
$powershellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$wscriptPath = Join-Path $env:SystemRoot "System32\wscript.exe"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$startupDir = [Environment]::GetFolderPath("Startup")
$fallbackPath = Join-Path $startupDir "QianchuanLiveScreenAutostart.lnk"
$dataDir = Join-Path $PSScriptRoot "data"
$logPath = Join-Path $dataDir "live-autostart.log"
$logFallbackPath = Join-Path $dataDir "live-autostart.active.log"

if (-not (Test-Path -LiteralPath $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

function Write-InstallerLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date).ToString("o"), $Message
    try {
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    } catch {
        try {
            Add-Content -LiteralPath $logFallbackPath -Value $line -Encoding UTF8
        } catch {
            # Logging must never prevent installation.
        }
    }
}

Write-Host "Installing logon autostart: $TaskName"
Write-Host "User: $currentUser"
Write-Host "Project: $PSScriptRoot"
Write-InstallerLog "Autostart installer started. Task=$TaskName User=$currentUser Project=$PSScriptRoot"

$actionArguments = @(
    "-NoLogo",
    "-NoProfile",
    "-NonInteractive",
    "-ExecutionPolicy Bypass",
    "-WindowStyle Hidden",
    "-File `"$loopPath`"",
    "-RestartDelaySeconds 30"
) -join " "

try {
    $action = New-ScheduledTaskAction `
        -Execute $powershellPath `
        -Argument $actionArguments `
        -WorkingDirectory $PSScriptRoot

    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
    $trigger.Delay = "PT15S"

    $principal = New-ScheduledTaskPrincipal `
        -UserId $currentUser `
        -LogonType Interactive `
        -RunLevel Limited

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "Start the Qianchuan backend and live-screen watchdog after Windows logon." `
        -Force | Out-Null

    if (Test-Path -LiteralPath $fallbackPath) {
        Remove-Item -LiteralPath $fallbackPath -Force
    }
    if (-not $NoStart) {
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 3
    }
    $task = Get-ScheduledTask -TaskName $TaskName
    Write-Host "Autostart task installed. State: $($task.State)"
    Write-InstallerLog "Scheduled task installed. Task=$TaskName State=$($task.State)"
} catch {
    Write-Warning "Scheduled Task installation failed: $($_.Exception.Message)"
    Write-InstallerLog "Scheduled task installation failed: $($_.Exception.Message)"
    try {
        $partialTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($partialTask) {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        }
    } catch {
        # Continue with the Startup folder fallback.
    }

    Write-Host "Falling back to the current user's Startup folder."
    try {
        if (-not (Test-Path -LiteralPath $startupDir)) {
            New-Item -ItemType Directory -Path $startupDir -Force | Out-Null
        }
        $wsh = New-Object -ComObject WScript.Shell
        $shortcut = $wsh.CreateShortcut($fallbackPath)
        $shortcut.TargetPath = $wscriptPath
        $shortcut.Arguments = "`"$hiddenPath`""
        $shortcut.WorkingDirectory = $PSScriptRoot
        $shortcut.WindowStyle = 7
        $shortcut.Description = "Start the Qianchuan and Buyin capture backend and watchdog."
        $shortcut.Save()
        if (-not $NoStart) {
            Start-Process -FilePath $wscriptPath -ArgumentList "`"$hiddenPath`"" -WindowStyle Hidden
        }
        Write-Host "Startup fallback installed: $fallbackPath"
        Write-InstallerLog "Startup fallback installed: $fallbackPath"
    } catch {
        Write-Host "Unable to install Startup fallback: $($_.Exception.Message)" -ForegroundColor Red
        Write-InstallerLog "Startup fallback installation failed: $($_.Exception.Message)"
        exit 1
    }
}

$wsh = New-Object -ComObject WScript.Shell
Get-ChildItem -LiteralPath $startupDir -Filter "*.lnk" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -ne $fallbackPath } |
    ForEach-Object {
        try {
            $shortcut = $wsh.CreateShortcut($_.FullName)
            $targetText = @($shortcut.TargetPath, $shortcut.Arguments) -join " "
            if (
                $targetText.IndexOf("start-hidden.vbs", [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                $targetText.IndexOf($PSScriptRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
            ) {
                Remove-Item -LiteralPath $_.FullName -Force
                Write-Host "Legacy startup shortcut removed: $($_.FullName)"
            }
        } catch {
            Write-Warning "Could not inspect startup shortcut $($_.FullName): $($_.Exception.Message)"
        }
    }

Write-Host "Runtime log: $(Join-Path $PSScriptRoot 'data\live-autostart.log')"
Write-Host "Health: http://127.0.0.1:8765/api/health"
Write-Host "Capture: http://127.0.0.1:8765/api/live/screen"
