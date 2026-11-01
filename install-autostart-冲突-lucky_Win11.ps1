param(
    [string]$TaskName = "QianchuanLiveScreenAutostart"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$loopPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "start-autostart-loop.ps1")).Path
$powershellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$currentUser = "{0}\{1}" -f $env:COMPUTERNAME, $env:USERNAME
$startupDir = [Environment]::GetFolderPath("Startup")
$fallbackPath = Join-Path $startupDir "QianchuanLiveScreenAutostart.vbs"

Write-Host "Installing logon autostart task: $TaskName"
Write-Host "Task user: $currentUser"
Write-Host "Project: $PSScriptRoot"

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
        -Description "Start the Qianchuan live-screen watchdog after Windows logon." `
        -Force | Out-Null

    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 3
    $task = Get-ScheduledTask -TaskName $TaskName
    if (Test-Path -LiteralPath $fallbackPath) {
        Remove-Item -LiteralPath $fallbackPath -Force
    }
    Write-Host "Autostart task installed. State: $($task.State)"
} catch {
    Write-Warning "Scheduled Task installation failed: $($_.Exception.Message)"
    try {
        $partialTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($partialTask) {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        }
    } catch {
        # The task service may be unavailable; the Startup fallback is still attempted.
    }

    Write-Host "Falling back to the current user's Startup folder."
    try {
        if (-not (Test-Path -LiteralPath $startupDir)) {
            New-Item -ItemType Directory -Path $startupDir -Force | Out-Null
        }
        $vbsLines = @(
            'Set shell = CreateObject("WScript.Shell")',
            ('shell.Run """{0}"" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{1}""", 0, False' -f $powershellPath, $loopPath)
        )
        Set-Content -LiteralPath $fallbackPath -Value $vbsLines -Encoding ASCII
        Start-Process -FilePath $fallbackPath -WindowStyle Hidden
        Write-Host "Startup fallback installed: $fallbackPath"
    } catch {
        Write-Host "Unable to install Startup fallback: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Runtime log: $(Join-Path $PSScriptRoot 'data\live-autostart.log')"
Write-Host "Health: http://127.0.0.1:8765/api/health"
Write-Host "Capture: http://127.0.0.1:8765/api/live/screen"
