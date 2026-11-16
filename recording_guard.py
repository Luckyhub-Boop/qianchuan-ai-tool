from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import recording_store


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RECORDINGS_DIR = recording_store.RECORDINGS_DIR
STATE_PATH = DATA_DIR / "live-recording-guard-state.json"
LOCK_PATH = DATA_DIR / "live-recording-guard.lock"
ACTIVE_PATH = DATA_DIR / "live-recording-active.json"
LOG_PATH = DATA_DIR / "live-recording-guard.log"
PRIMARY_STATE_PATH = DATA_DIR / "live-recorder-state.json"
PRIMARY_LOCK_PATH = DATA_DIR / "live-recorder.lock"
BACKUP_STATE_PATH = DATA_DIR / "live-backup-recorder-state.json"
BACKUP_LOCK_PATH = DATA_DIR / "live-backup-recorder.lock"
BACKUP_STOP_PATH = DATA_DIR / "live-backup-stop"
DEFAULT_SERVER_URL = "http://127.0.0.1:8765"

POLL_SECONDS = 4
PRIMARY_ERROR_SECONDS = 45
PRIMARY_STALE_SECONDS = 60
PRIMARY_STALL_SECONDS = 180
BACKUP_ERROR_SECONDS = 45
BACKUP_STALE_SECONDS = 60
BACKUP_STALL_SECONDS = 180
SWITCH_BACK_SECONDS = 180
STARTUP_GRACE_SECONDS = 45


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{now_iso()}] {message}", flush=True)


def read_json(path: Path, fallback: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for attempt in range(8):
        try:
            temporary.replace(path)
            return
        except OSError:
            time.sleep(0.15 * (attempt + 1))
    try:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def pid_is_running(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5
        try:
            return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == 258
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def running_pid(lock_path: Path) -> int | None:
    payload = read_json(lock_path, {})
    if not isinstance(payload, dict):
        return None
    try:
        pid = int(payload.get("pid") or 0)
    except (TypeError, ValueError):
        return None
    return pid if pid_is_running(pid) else None


def acquire_lock() -> bool:
    current = read_json(LOCK_PATH, {})
    owner = int(current.get("pid") or 0) if isinstance(current, dict) else 0
    if owner and owner != os.getpid() and pid_is_running(owner):
        return False
    atomic_write_json(
        LOCK_PATH,
        {"pid": os.getpid(), "startedAt": now_iso(), "mode": "recording-guard"},
    )
    return True


def release_lock() -> None:
    current = read_json(LOCK_PATH, {})
    if isinstance(current, dict) and int(current.get("pid") or 0) not in {0, os.getpid()}:
        return
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def fetch_health(timeout: float = 5.0) -> dict[str, Any]:
    base = os.getenv("QIANCHUAN_SERVER_URL", DEFAULT_SERVER_URL).rstrip("/")
    request = urllib.request.Request(
        f"{base}/api/health",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else {}


def start_process(script: str, log_path: Path) -> subprocess.Popen[Any]:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    handle = (log_path.parent / f"{log_path.name}.active").open("ab", buffering=0)
    creation_flags = 0x08000000 if os.name == "nt" else 0
    return subprocess.Popen(
        [sys.executable, str(ROOT / script)],
        cwd=str(ROOT),
        stdout=handle,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=creation_flags,
    )


def stop_pid(pid: int | None) -> None:
    if not pid_is_running(pid):
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.kill(int(pid), 15)
        except OSError:
            pass


def request_backup_stop(pid: int | None) -> None:
    """Gracefully stop the ffmpeg backup so it finalizes its current segment."""
    if not pid_is_running(pid):
        return
    atomic_write_json(BACKUP_STOP_PATH, {"requestedAt": now_iso(), "pid": pid})
    for _ in range(7):
        if not pid_is_running(pid):
            break
        time.sleep(1)
    if pid_is_running(pid):
        stop_pid(pid)
    try:
        BACKUP_STOP_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def iso_age(value: Any) -> float | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return max(0.0, (datetime.now(parsed.tzinfo) - parsed).total_seconds())
    except (TypeError, ValueError):
        return None


class RecordingGuard:
    def __init__(self) -> None:
        self.actions: list[dict[str, str]] = []
        self.primary_ok_since: float | None = None
        self.backup_started_at: float | None = None
        self.last_alert_at = 0.0
        self.primary_start_failures = 0

    def note_action(self, action: str, reason: str) -> None:
        self.actions.append({"at": now_iso(), "action": action, "reason": reason})
        del self.actions[:-20]
        log(f"{action}：{reason}")

    def read_active(self) -> dict[str, Any]:
        payload = read_json(ACTIVE_PATH, {})
        return payload if isinstance(payload, dict) else {}

    def write_active(self, method: str) -> None:
        atomic_write_json(
            ACTIVE_PATH,
            {
                "method": method,
                "updatedAt": now_iso(),
                "pid": os.getpid(),
            },
        )

    def ensure_primary(self) -> bool:
        if running_pid(PRIMARY_LOCK_PATH):
            self.primary_start_failures = 0
            return True
        self.note_action("启动主录制器", "录制进程缺失")
        start_process("live_recorder.py", DATA_DIR / "live-recorder.log")
        time.sleep(2)
        ok = bool(running_pid(PRIMARY_LOCK_PATH))
        if ok:
            self.primary_start_failures = 0
        else:
            self.primary_start_failures += 1
        return ok

    def ensure_backup(self) -> bool:
        if running_pid(BACKUP_LOCK_PATH):
            return True
        self.note_action("启动备用录制器(ffmpeg)", "主录制不可用，切换备用方式")
        start_process("backup_recorder.py", DATA_DIR / "live-backup-recorder.log")
        time.sleep(2)
        return bool(running_pid(BACKUP_LOCK_PATH))

    def component_health(
        self,
        pid: int | None,
        state: dict[str, Any],
        error_seconds: float,
        stale_seconds: float,
        stall_seconds: float,
    ) -> dict[str, Any]:
        running = pid is not None
        status = str(state.get("status") or "unknown")
        updated_age = iso_age(state.get("updatedAt"))
        last_segment_age = iso_age(state.get("lastSegmentAt"))
        error_age = iso_age(state.get("errorSince"))
        stale = updated_age is None or updated_age > stale_seconds
        error = (
            status == "error"
            and error_age is not None
            and error_age >= error_seconds
        )
        stalled = (
            status == "recording"
            and last_segment_age is not None
            and last_segment_age >= stall_seconds
        )
        healthy = running and not error and not stale and not stalled
        return {
            "running": running,
            "status": status,
            "updatedAge": round(updated_age, 1) if updated_age is not None else None,
            "lastSegmentAge": (
                round(last_segment_age, 1) if last_segment_age is not None else None
            ),
            "error": error,
            "stale": stale,
            "stalled": stalled,
            "healthy": healthy,
            "detail": state.get("error") or "",
        }

    def run(self) -> None:
        while True:
            try:
                self.tick()
            except Exception as exc:
                self.publish(
                    "error",
                    {"error": str(exc)},
                )
                log(f"录制守护异常：{exc}")
            time.sleep(POLL_SECONDS)

    def tick(self) -> None:
        try:
            health = fetch_health()
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            health = {}
        stream_status: dict[str, Any] = {}
        try:
            base = os.getenv("QIANCHUAN_SERVER_URL", DEFAULT_SERVER_URL).rstrip("/")
            request = urllib.request.Request(
                f"{base}/api/live/stream/status",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=5.0) as response:
                stream_status = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            stream_status = {}
        if not isinstance(stream_status, dict):
            stream_status = {}
        screen = health.get("liveScreenCapture") or {}
        live = bool(screen.get("live"))
        captured = bool(stream_status.get("captured", health.get("streamCaptureOnline")))
        room_id = str(
            stream_status.get("roomId")
            or (screen.get("room") or {}).get("id")
            or ""
        )
        primary_state = read_json(PRIMARY_STATE_PATH, {})
        backup_state = read_json(BACKUP_STATE_PATH, {})
        primary_pid = running_pid(PRIMARY_LOCK_PATH)
        backup_pid = running_pid(BACKUP_LOCK_PATH)
        primary = self.component_health(
            primary_pid,
            primary_state if isinstance(primary_state, dict) else {},
            PRIMARY_ERROR_SECONDS,
            PRIMARY_STALE_SECONDS,
            PRIMARY_STALL_SECONDS,
        )
        backup = self.component_health(
            backup_pid,
            backup_state if isinstance(backup_state, dict) else {},
            BACKUP_ERROR_SECONDS,
            BACKUP_STALE_SECONDS,
            BACKUP_STALL_SECONDS,
        )
        writable = recording_store.dir_is_writable(RECORDINGS_DIR)
        active = self.read_active()
        method = str(active.get("method") or ("primary" if primary["running"] else ""))

        should_record = bool(live and captured and room_id)
        if should_record:
            if not primary["running"] and not backup["running"]:
                if self.ensure_primary():
                    method = "primary"
                    self.write_active(method)
                elif self.primary_start_failures >= 3 and self.ensure_backup():
                    method = "backup"
                    self.backup_started_at = time.monotonic()
                    self.write_active(method)
                else:
                    self.note_action(
                        "主录制器启动等待",
                        f"连续 {self.primary_start_failures} 次未就绪，继续巡检",
                    )
            elif method != "backup":
                if primary["healthy"]:
                    if backup["running"]:
                        request_backup_stop(backup_pid)
                        self.note_action("停止备用录制器", "主录制已恢复健康")
                    method = "primary"
                    self.write_active(method)
                elif primary["stalled"]:
                    stop_pid(primary_pid)
                    self.note_action("主录制停滞切换备用", "主录制超过阈值无新音频段")
                    if self.ensure_backup():
                        method = "backup"
                        self.backup_started_at = time.monotonic()
                        self.write_active(method)
                elif primary["error"] or primary["stale"]:
                    stop_pid(primary_pid)
                    reason = primary["detail"] or "主录制状态异常/心跳超时"
                    self.note_action("主录制异常切换备用", reason)
                    if self.ensure_backup():
                        method = "backup"
                        self.backup_started_at = time.monotonic()
                        self.write_active(method)
            else:
                if backup["healthy"]:
                    if primary["healthy"]:
                        if self.backup_started_at is None:
                            self.backup_started_at = time.monotonic()
                        if time.monotonic() - self.backup_started_at >= SWITCH_BACK_SECONDS:
                            request_backup_stop(backup_pid)
                            self.note_action("切回主录制", "主录制已稳定健康")
                            method = "primary"
                            self.write_active(method)
                else:
                    request_backup_stop(backup_pid)
                    self.note_action("备用录制异常，重启备用", backup["detail"] or "备用录制状态异常")
                    if self.ensure_backup():
                        self.backup_started_at = time.monotonic()
                    elif self.ensure_primary():
                        method = "primary"
                        self.write_active(method)
        else:
            if backup["running"] and not live:
                request_backup_stop(backup_pid)
                self.note_action("停止备用录制器", "直播已结束或无签名画面流")
                method = "primary" if primary["running"] else ""
                self.write_active(method)

        if not writable:
            now = time.monotonic()
            if now - self.last_alert_at >= 600:
                self.last_alert_at = now
                self.note_action(
                    "录制目录不可写",
                    f"{RECORDINGS_DIR} 无法写入，请检查磁盘/权限",
                )

        self.publish(
            "active" if method else "standby",
            {
                "activeMethod": method,
                "live": live,
                "captured": captured,
                "roomId": room_id,
                "primary": primary,
                "backup": backup,
                "recordingsDirectory": str(RECORDINGS_DIR),
                "recordingsDirectoryWritable": writable,
                "detections": {
                    "processAlive": True,
                    "persistentError": True,
                    "staleHeartbeat": True,
                    "segmentStall": True,
                    "directoryWritable": writable,
                },
            },
        )

    def publish(self, status: str, extra: dict[str, Any] | None = None) -> None:
        atomic_write_json(
            STATE_PATH,
            {
                "ok": status in {"active", "standby"},
                "status": status,
                "updatedAt": now_iso(),
                "pid": os.getpid(),
                "lastActions": self.actions[-10:],
                **(extra or {}),
            },
        )


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not acquire_lock():
        log("检测到录制守护已在运行，本次启动退出")
        return 0
    log(f"录制守护启动 recordings_dir={RECORDINGS_DIR}")
    guard = RecordingGuard()
    try:
        guard.run()
    except KeyboardInterrupt:
        pass
    finally:
        release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
