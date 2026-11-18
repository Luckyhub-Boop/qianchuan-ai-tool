param(
    [switch]$DryRun,
    [int]$HealthTimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$port = if ($env:QIANCHUAN_PORT) { $env:QIANCHUAN_PORT } else { '8765' }
$healthUrl = "http://127.0.0.1:$port/api/health"
$logPath = Join-Path $root 'data\restart-stack.log'

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'), $Message
    Write-Host $line
    try {
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    } catch {
        # logging must never break the restart
    }
}

function Get-Health {
    try {
        return Invoke-RestMethod -Uri $healthUrl -TimeoutSec 6 -ErrorAction Stop
    } catch {
        return $null
    }
}

function Get-ProjectProcess {
    param([string]$Pattern)
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine.Contains($root) -and
            $_.CommandLine -match $Pattern -and
            $_.Name -ne 'msedge.exe'
        }
}

function Stop-ProjectProcess {
    param([string]$Label, [string]$Pattern)
    $found = @(Get-ProjectProcess -Pattern $Pattern)
    if ($found.Count -eq 0) {
        Write-Log "SKIP $Label (not running)"
        return 0
    }
    foreach ($p in $found) {
        Write-Log "STOP $Label pid=$($p.ProcessId)"
        if (-not $DryRun) {
            try {
                Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            } catch {
                Write-Log "WARN cannot stop $Label pid=$($p.ProcessId): $($_.Exception.Message)"
            }
        }
    }
    return $found.Count
}

# ---- 0. safety gates -------------------------------------------------------
$health = Get-Health
$liveNow = $false
$recorderStatus = ''
if ($health) {
    $liveNow = [bool]($health.liveRecordingGuard.live) -or [bool]($health.liveScreenCapture.live)
    $recorderStatus = [string]($health.liveRecorder.status)
}
Write-Log "PRE health=$(if($health){$health.status}else{'unreachable'}) live=$liveNow recorder=$recorderStatus"

if ($liveNow) {
    Write-Log "ABORT reason=stream_is_live (restart would cut an ongoing recording)"
    exit 3
}
if ($recorderStatus -eq 'recording') {
    Write-Log "ABORT reason=recorder_mid_segment (wait for a waiting_stream state)"
    exit 4
}

# ---- 1. stop supervisors first so nothing is respawned ----------------------
Write-Log "STEP 1 supervisors"
[void](Stop-ProjectProcess -Label 'autostart-loop' -Pattern 'start-autostart-loop\.ps1')
[void](Stop-ProjectProcess -Label 'start-background' -Pattern 'start-background\.ps1')
[void](Stop-ProjectProcess -Label 'watchdog' -Pattern 'live_watchdog\.py')

# ---- 2. stop children -----------------------------------------------------
Write-Log "STEP 2 children"
[void](Stop-ProjectProcess -Label 'guard' -Pattern 'recording_guard\.py')
[void](Stop-ProjectProcess -Label 'asr' -Pattern 'live_asr\.py')
[void](Stop-ProjectProcess -Label 'audio-capture' -Pattern 'audio_capture\.py')
[void](Stop-ProjectProcess -Label 'recorder' -Pattern 'live_recorder\.py')
[void](Stop-ProjectProcess -Label 'buyin-agent' -Pattern 'buyin-live-agent\.js')
[void](Stop-ProjectProcess -Label 'screen-agent' -Pattern 'live-screen-agent\.js')
[void](Stop-ProjectProcess -Label 'server' -Pattern 'server\.py')

if ($DryRun) {
    Write-Log "DRY RUN finished; nothing was stopped"
    exit 0
}

# ---- 3. verify everything project-side is gone -----------------------------
Start-Sleep -Seconds 8
$left = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains($root) -and
        $_.Name -in @('python.exe', 'pythonw.exe', 'node.exe', 'powershell.exe')
    })
if ($left.Count -gt 0) {
    foreach ($l in $left) {
        Write-Log "WARN still running pid=$($l.ProcessId) $($l.Name)"
    }
}

# ---- 4. start through the same entry as autostart --------------------------
Write-Log "STEP 3 start via start-hidden.vbs"
$vbs = Join-Path $root 'start-hidden.vbs'
$wscript = Join-Path $env:SystemRoot 'System32\wscript.exe'
Start-Process -FilePath $wscript -ArgumentList @("`"$vbs`"") -WorkingDirectory $root -WindowStyle Hidden

# ---- 5. wait for health ----------------------------------------------------
$deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
$ok = $false
$last = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    $last = Get-Health
    if ($last -and $last.ok) {
        $ok = $true
        break
    }
}
if (-not $ok) {
    Write-Log "FAIL health not ok within $HealthTimeoutSeconds s; check data\live-watchdog.log"
    exit 2
}

$guardState = $last.liveRecordingGuard
Write-Log ("OK status={0} capture={1} buyin={2} recorder={3} asr={4} guard={5} backup={6}" -f
    $last.status,
    $last.liveScreenCapture.status,
    $last.buyinLiveCapture.status,
    $last.liveRecorder.status,
    $last.localAsr.status,
    $guardState.status,
    $guardState.backup.status)

$procs = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains($root) })
foreach ($p in $procs) {
    Write-Log ("RUN pid={0} name={1} start={2}" -f $p.ProcessId, $p.Name, $p.CreationDate)
}
Write-Log "DONE"
exit 0
