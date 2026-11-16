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
from live_recorder import resolve_ffmpeg


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RECORDINGS_DIR = recording_store.RECORDINGS_DIR
STATE_PATH = DATA_DIR / "live-backup-recorder-state.json"
LOCK_PATH = DATA_DIR / "live-backup-recorder.lock"
STOP_PATH = DATA_DIR / "live-backup-stop"
LOG_PATH = DATA_DIR / "live-backup-recorder.log"
DEFAULT_SERVER_URL = "http://127.0.0.1:8765"
POLL_SECONDS = 5
SEGMENT_SECONDS = 300


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{now_iso()}] {message}", flush=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except OSError:
            time.sleep(0.15 * (attempt + 1))
    try:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.unlink(missing_ok=True)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


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


def acquire_lock() -> bool:
    current = read_json(LOCK_PATH)
    owner = int(current.get("pid") or 0)
    if owner and owner != os.getpid() and pid_is_running(owner):
        return False
    atomic_write_json(
        LOCK_PATH,
        {"pid": os.getpid(), "startedAt": now_iso(), "mode": "backup-recorder"},
    )
    return True


def release_lock() -> None:
    current = read_json(LOCK_PATH)
    if int(current.get("pid") or 0) not in {0, os.getpid()}:
        return
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def fetch_json(path: str, timeout: float = 4.0) -> dict[str, Any]:
    base = os.getenv("QIANCHUAN_SERVER_URL", DEFAULT_SERVER_URL).rstrip("/")
    request = urllib.request.Request(
        f"{base}{path}",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else {}


def stop_process(process: subprocess.Popen[Any] | None) -> None:
    if not process or process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()
            process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


class BackupRecorder:
    def __init__(self) -> None:
        self.ffmpeg = resolve_ffmpeg()
        self.process: subprocess.Popen[Any] | None = None
        self.log_handle: Any = None
        self.directory: Path | None = None
        self.manifest: dict[str, Any] = {}
        self.room_id = ""
        self.last_error = ""
        self.error_since: str | None = None

    def _segments(self) -> list[Path]:
        if not self.directory:
            return []
        return sorted(
            item
            for item in (self.directory / "segments").glob("part_*.wav")
            if item.is_file() and item.stat().st_size > 0
        )

    def publish_state(self, status: str, extra: dict[str, Any] | None = None) -> None:
        if status == "error":
            self.error_since = self.error_since or now_iso()
        else:
            self.error_since = None
        segments = self._segments()
        last_segment_at = ""
        if segments:
            last_segment_at = datetime.fromtimestamp(
                max(item.stat().st_mtime for item in segments)
            ).astimezone().isoformat(timespec="seconds")
        atomic_write_json(
            STATE_PATH,
            {
                "ok": status in {"recording", "waiting_stream", "idle", "finalizing"},
                "status": status,
                "updatedAt": now_iso(),
                "errorSince": self.error_since,
                "pid": os.getpid(),
                "method": "ffmpeg-segment-wav",
                "ffmpegAvailable": bool(self.ffmpeg),
                "roomId": self.room_id,
                "sessionId": self.manifest.get("id"),
                "sessionDirectory": str(self.directory) if self.directory else "",
                "segmentCount": len(segments),
                "lastSegmentAt": last_segment_at,
                "segmentSeconds": SEGMENT_SECONDS,
                "recordingsDirectory": str(RECORDINGS_DIR),
                "error": self.last_error,
                **(extra or {}),
            },
        )

    def next_segment_number(self) -> int:
        numbers: list[int] = []
        for item in self._segments():
            try:
                numbers.append(int(item.stem.split("_")[-1]))
            except (IndexError, ValueError):
                continue
        return max(numbers, default=0) + 1

    def rebuild_playlist(self) -> None:
        if not self.directory:
            return
        segments = self._segments()
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"#EXT-X-TARGETDURATION:{SEGMENT_SECONDS}",
            "#EXT-X-MEDIA-SEQUENCE:0",
        ]
        for segment in segments:
            lines.extend([f"#EXTINF:{SEGMENT_SECONDS:.3f},", f"segments/{segment.name}"])
        lines.append("#EXT-X-ENDLIST")
        temporary = self.directory / "index.m3u8.tmp"
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temporary.replace(self.directory / "index.m3u8")

    def begin_session(self, room_id: str, screen: dict[str, Any]) -> None:
        started_at = datetime.now().astimezone()
        for directory, existing in recording_store.list_manifests(RECORDINGS_DIR):
            if (
                str(existing.get("roomId") or "") == str(room_id)
                and str(existing.get("date") or "") == started_at.date().isoformat()
                and str(existing.get("status") or "") == "recording"
            ):
                self.directory = directory
                self.room_id = str(room_id)
                self.manifest = existing
                log(f"备用录制器接管既有场次 session={directory.name}")
                return
        self.directory = recording_store.create_session_directory(
            room_id,
            started_at,
            RECORDINGS_DIR,
        )
        self.room_id = str(room_id)
        room = screen.get("room") if isinstance(screen.get("room"), dict) else {}
        self.manifest = {
            "id": self.directory.name,
            "accountId": str(screen.get("accountId") or "fashion"),
            "roomId": str(room_id),
            "awemeName": str(room.get("awemeName") or ""),
            "date": started_at.date().isoformat(),
            "title": (
                f"{started_at:%Y-%m-%d %H:%M} "
                f"{room.get('awemeName') or '直播'} · 整场录像"
            ),
            "startedAt": started_at.isoformat(timespec="seconds"),
            "status": "starting",
            "sourceLabel": "千川直播大屏签名FLV · 备用ffmpeg音频采集",
            "videoPolicy": "音频临时落盘，复盘归档后立即删除",
            "segmentSeconds": SEGMENT_SECONDS,
            "retentionDays": recording_store.RETENTION_DAYS,
        }
        recording_store.write_manifest(self.directory, self.manifest)
        log(f"备用录制器创建场次 session={self.directory.name}")

    def start_ffmpeg(self) -> None:
        if not self.ffmpeg:
            raise RuntimeError("未找到 ffmpeg，备用录制不可用")
        if not self.directory:
            raise RuntimeError("备用录制目录尚未创建")
        base_url = os.getenv("QIANCHUAN_SERVER_URL", DEFAULT_SERVER_URL).rstrip("/")
        proxy_url = (
            f"{base_url}/api/live/stream.flv?room="
            + urllib.request.quote(self.room_id, safe="")
        )
        segments_dir = self.directory / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)
        capture_log = self.directory / "backup-capture.log"
        if self.log_handle is not None:
            try:
                self.log_handle.close()
            except OSError:
                pass
        self.log_handle = capture_log.open("ab", buffering=0)
        start_number = self.next_segment_number()
        creation_flags = 0x08000000 if os.name == "nt" else 0
        self.process = subprocess.Popen(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-reconnect",
                "1",
                "-reconnect_streamed",
                "1",
                "-reconnect_delay_max",
                "10",
                "-rw_timeout",
                "15000000",
                "-i",
                proxy_url,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-f",
                "segment",
                "-segment_time",
                str(SEGMENT_SECONDS),
                "-reset_timestamps",
                "1",
                "-segment_start_number",
                str(start_number),
                str(segments_dir / "part_%06d.wav"),
            ],
            stdout=self.log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        time.sleep(2.0)
        if self.process.poll() is not None:
            tail = ""
            try:
                tail = " | ".join(
                    capture_log.read_text(encoding="utf-8", errors="replace")
                    .strip()
                    .splitlines()[-5:]
                )
            except OSError:
                pass
            message = f"备用 ffmpeg 采集启动失败：{tail or '未知错误'}"
            self.manifest["status"] = "error"
            self.manifest["error"] = message
            recording_store.write_manifest(self.directory, self.manifest)
            raise RuntimeError(message)
        self.manifest["status"] = "recording"
        self.manifest["lastRunStartedAt"] = now_iso()
        self.manifest["captureMethod"] = "ffmpeg"
        recording_store.write_manifest(self.directory, self.manifest)
        self.rebuild_playlist()
        log(f"备用 ffmpeg 开始录制 room={self.room_id} session={self.manifest.get('id')}")

    def finalize_session(self) -> None:
        if not self.directory:
            return
        self.publish_state("finalizing")
        stop_process(self.process)
        self.process = None
        if self.log_handle is not None:
            try:
                self.log_handle.close()
            except OSError:
                pass
            self.log_handle = None
        for segment in self._segments():
            try:
                with segment.open("rb") as handle:
                    head = handle.read(12)
                if not (head[:4] == b"RIFF" and head[8:12] == b"WAVE"):
                    segment.unlink(missing_ok=True)
                    log(f"移除未完成的备用分段 {segment.name}")
            except OSError:
                pass
        self.rebuild_playlist()
        self.manifest["endedAt"] = now_iso()
        self.manifest["status"] = "completed"
        self.manifest["segmentCount"] = len(self._segments())
        self.manifest["captureMethod"] = "ffmpeg"
        recording_store.write_manifest(self.directory, self.manifest)
        log(f"备用录制结束，等待后台分析归档后删除 session={self.directory.name}")
        self.directory = None
        self.manifest = {}
        self.room_id = ""

    def ensure_recording(self) -> None:
        try:
            stream = fetch_json("/api/live/stream/status")
            screen = fetch_json("/api/live/screen")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            self.last_error = f"读取直播状态失败：{exc}"
            self.publish_state("idle", {"error": self.last_error})
            return
        room_id = str(stream.get("roomId") or "")
        captured = bool(stream.get("captured"))
        live = bool(screen.get("live")) and str(screen.get("status")) in {"ok", "partial", "stale"}
        if not captured:
            self.publish_state("waiting_stream", {"error": "等待千川大屏签名画面流"})
            return
        if not live and str(screen.get("status") or "") == "not_live":
            if self.directory:
                self.finalize_session()
            self.publish_state("idle", {"error": "直播已结束，等待下一场开播"})
            return
        if self.directory and self.room_id and self.room_id != room_id:
            self.finalize_session()
        if not self.directory:
            self.begin_session(room_id, screen)
        if not self.process or self.process.poll() is not None:
            if self.process:
                self.process = None
            self.start_ffmpeg()
        self.manifest["lastHeartbeatAt"] = now_iso()
        recording_store.write_manifest(self.directory, self.manifest)
        self.last_error = ""
        self.publish_state("recording")

    def run(self) -> None:
        while True:
            if STOP_PATH.is_file():
                log("收到停止信号，完成当前场次归档后退出")
                self.finalize_session()
                try:
                    STOP_PATH.unlink(missing_ok=True)
                except OSError:
                    pass
                break
            try:
                self.ensure_recording()
            except Exception as exc:
                self.last_error = str(exc)
                self.publish_state("error", {"error": self.last_error})
                log(f"备用录制器异常：{exc}")
            time.sleep(POLL_SECONDS)


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    if not acquire_lock():
        log("检测到备用录制器已在运行，本次启动退出")
        return 0
    recorder = BackupRecorder()
    log(f"备用录制器启动 method=ffmpeg dir={RECORDINGS_DIR}")
    try:
        recorder.run()
    except KeyboardInterrupt:
        pass
    finally:
        recorder.finalize_session()
        release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
