from __future__ import annotations

import json
import importlib.util
import os
import shutil
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
STATE_PATH = DATA_DIR / "live-recorder-state.json"
LOCK_PATH = DATA_DIR / "live-recorder.lock"
PAUSE_PATH = DATA_DIR / "live-recorder-pause.json"
LOG_PATH = DATA_DIR / "live-recorder.log"
RECORDINGS_DIR = recording_store.RECORDINGS_DIR
AUDIO_CAPTURE_PATH = ROOT / "audio_capture.py"
DEFAULT_SERVER_URL = "http://127.0.0.1:8765"
POLL_SECONDS = 5
RETENTION_DAYS = recording_store.RETENTION_DAYS
SEGMENT_SECONDS = 300


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log(message: str) -> None:
    line = f"[{now_iso()}] {message}"
    print(line, flush=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary.write_text(content, encoding="utf-8")
    last_error: OSError | None = None
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.15 * (attempt + 1))
    try:
        path.write_text(content, encoding="utf-8")
        temporary.unlink(missing_ok=True)
    except OSError:
        if last_error:
            raise last_error
        raise


def pid_is_running(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        synchronize = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
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
        {"pid": os.getpid(), "startedAt": now_iso(), "mode": "recorder"},
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


def resolve_ffmpeg() -> str:
    candidates = [
        os.getenv("QIANCHUAN_FFMPEG", "").strip(),
        r"C:\Program Files (x86)\MarukoToolbox\tools\ffmpeg.exe",
        r"C:\Program Files (x86)\damai\resources\app\node_modules\ffmpeg-static-electron\bin\win\x64\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        shutil.which("ffmpeg") or "",
    ]
    return next((item for item in candidates if item and Path(item).is_file()), "")


def audio_capture_available() -> bool:
    return AUDIO_CAPTURE_PATH.is_file() and bool(
        importlib.util.find_spec("av")
    )


def media_duration(path: Path) -> float:
    try:
        import av

        with av.open(str(path)) as container:
            if container.duration:
                return max(0.0, float(container.duration / av.time_base))
    except Exception:
        pass
    return float(SEGMENT_SECONDS)


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


class LiveRecorder:
    def __init__(self) -> None:
        self.ffmpeg = resolve_ffmpeg()
        self.capture_available = audio_capture_available()
        self.process: subprocess.Popen[Any] | None = None
        self.log_handle: Any = None
        self.directory: Path | None = None
        self.manifest: dict[str, Any] = {}
        self.room_id = ""
        self.last_cleanup_date = ""
        self.last_error = ""
        self.lost_stream_at: float | None = None
        self.not_live_since: float | None = None

    def publish_state(self, status: str, extra: dict[str, Any] | None = None) -> None:
        segments = 0
        if self.directory:
            for pattern in ("part_*.wav", "part_*.flac", "part_*.ts"):
                segments += len([
                    item
                    for item in (self.directory / "segments").glob(pattern)
                    if item.stat().st_size > 0
                ])
        state = {
            "ok": status in {"recording", "waiting_stream", "idle", "finalizing"},
            "status": status,
            "updatedAt": now_iso(),
            "pid": os.getpid(),
            "ffmpegAvailable": self.capture_available,
            "captureMode": "audio_only_pyav",
            "roomId": self.room_id,
            "sessionId": self.manifest.get("id"),
            "sessionDirectory": str(self.directory) if self.directory else "",
            "playlistUrl": (
                f"/recordings/{self.directory.name}/index.m3u8"
                if self.directory and (self.directory / "index.m3u8").is_file()
                else ""
            ),
            "segmentCount": segments,
            "segmentSeconds": SEGMENT_SECONDS,
            "retentionDays": RETENTION_DAYS,
            "videoPolicy": "analysis_first_then_delete",
            "error": self.last_error,
            **(extra or {}),
        }
        atomic_write_json(STATE_PATH, state)

    def cleanup(self, force: bool = False) -> None:
        today = datetime.now().astimezone().date().isoformat()
        if not force and today == self.last_cleanup_date:
            return
        removed = recording_store.cleanup_recordings(
            RETENTION_DAYS,
            recordings_dir=RECORDINGS_DIR,
        )
        self.last_cleanup_date = today
        if removed:
            log(f"录像保留策略已删除 {len(removed)} 个过期场次: {', '.join(removed)}")

    def segment_start_number(self) -> int:
        if not self.directory:
            return 1
        numbers: list[int] = []
        for pattern in ("part_*.wav", "part_*.flac", "part_*.ts"):
            for item in (self.directory / "segments").glob(pattern):
                try:
                    numbers.append(int(item.stem.split("_")[-1]))
                except (IndexError, ValueError):
                    continue
        return max(numbers, default=0) + 1

    def start_ffmpeg(self) -> None:
        if not self.capture_available:
            raise RuntimeError("PyAV 音频采集器不可用")
        if not self.directory:
            raise RuntimeError("录像目录尚未创建")
        base_url = os.getenv("QIANCHUAN_SERVER_URL", DEFAULT_SERVER_URL).rstrip("/")
        proxy_url = (
            f"{base_url}/api/live/stream.flv?room="
            + urllib.request.quote(self.room_id, safe="")
        )
        segment_start = self.segment_start_number()
        capture_log = self.directory / "audio-capture.log"
        self.log_handle = capture_log.open("ab", buffering=0)
        creation_flags = 0x08000000 if os.name == "nt" else 0
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(AUDIO_CAPTURE_PATH),
                "--url",
                proxy_url,
                "--directory",
                str(self.directory / "segments"),
                "--segment-seconds",
                str(SEGMENT_SECONDS),
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
            message = f"音频采集启动失败：{tail or '未知错误'}"
            self.manifest["status"] = "error"
            self.manifest["error"] = message
            recording_store.write_manifest(self.directory, self.manifest)
            raise RuntimeError(message)
        self.manifest["status"] = "recording"
        self.manifest["lastRunStartedAt"] = now_iso()
        self.manifest["segmentStartNumber"] = segment_start
        recording_store.write_manifest(self.directory, self.manifest)
        self.rebuild_playlist()
        log(f"开始音频录制 room={self.room_id} session={self.manifest.get('id')}")

    def rebuild_playlist(self, final: bool = False) -> None:
        if not self.directory:
            return
        segments = [
            item
            for item in sorted((self.directory / "segments").glob("part_*.ts"))
            if item.stat().st_size > 0
        ]
        if (
            not final
            and self.process
            and self.process.poll() is None
            and segments
        ):
            segments = segments[:-1]
        segment_durations = {segment: media_duration(segment) for segment in segments}
        target_duration = max(
            SEGMENT_SECONDS,
            int(round(max(segment_durations.values(), default=SEGMENT_SECONDS) + 0.499)),
        )
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"#EXT-X-TARGETDURATION:{target_duration}",
            "#EXT-X-MEDIA-SEQUENCE:0",
        ]
        for segment in segments:
            duration = segment_durations[segment]
            lines.extend(
                [
                    f"#EXTINF:{duration:.3f},",
                    f"segments/{segment.name}",
                ]
            )
        if final:
            lines.append("#EXT-X-ENDLIST")
        temporary = self.directory / "index.m3u8.tmp"
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temporary.replace(self.directory / "index.m3u8")

    def begin_session(self, room_id: str, screen: dict[str, Any]) -> None:
        self.stop_session(finalize=False)
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
                log(f"恢复中断中的整场录像 session={directory.name}")
                return
        self.directory = recording_store.create_session_directory(
            room_id,
            started_at,
            RECORDINGS_DIR,
        )
        self.room_id = room_id
        room = screen.get("room") if isinstance(screen.get("room"), dict) else {}
        self.manifest = {
            "id": self.directory.name,
            "accountId": str(screen.get("accountId") or "fashion"),
            "roomId": room_id,
            "awemeName": str(room.get("awemeName") or ""),
            "date": started_at.date().isoformat(),
            "title": (
                f"{started_at:%Y-%m-%d %H:%M} "
                f"{room.get('awemeName') or '直播'} · 整场录像"
            ),
            "startedAt": started_at.isoformat(timespec="seconds"),
            "status": "starting",
            "sourceLabel": "千川直播大屏签名FLV · 本地临时音频采集",
            "videoPolicy": "音频临时落盘，复盘归档后立即删除",
            "segmentSeconds": SEGMENT_SECONDS,
            "retentionDays": RETENTION_DAYS,
        }
        self.lost_stream_at = None
        self.not_live_since = None
        recording_store.write_manifest(self.directory, self.manifest)
        log(f"创建整场录像 session={self.directory.name}")

    def append_endlist(self) -> None:
        if not self.directory:
            return
        self.rebuild_playlist(final=True)

    def finalize_mp4(self) -> str:
        if not self.directory or not self.ffmpeg:
            return ""
        segments = [
            item
            for item in sorted((self.directory / "segments").glob("*.ts"))
            if item.stat().st_size > 0
        ]
        if not segments:
            return ""
        concat_file = self.directory / "segments.txt"
        try:
            concat_file.write_text(
                "\n".join(
                    f"file '{segment.as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'"
                    for segment in segments
                )
                + "\n",
                encoding="utf-8",
            )
            target = self.directory / "session.mp4"
            creation_flags = 0x08000000 if os.name == "nt" else 0
            result = subprocess.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
                    "-c",
                    "copy",
                    "-bsf:a",
                    "aac_adtstoasc",
                    "-movflags",
                    "+faststart",
                    str(target),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=1800,
                creationflags=creation_flags,
            )
            if result.returncode == 0 and target.is_file() and target.stat().st_size > 0:
                log(f"整场录像已合并 MP4 session={self.directory.name}")
                return f"/recordings/{self.directory.name}/session.mp4"
            error = result.stderr.decode("utf-8", errors="replace")[-500:]
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
            log(f"MP4 合并失败，保留 HLS 录像: {error}")
        except Exception as exc:
            try:
                (self.directory / "session.mp4").unlink(missing_ok=True)
            except OSError:
                pass
            log(f"MP4 合并失败，保留 HLS 录像: {exc}")
        return ""

    def stop_session(self, finalize: bool = True) -> None:
        if not self.directory:
            return
        self.publish_state("finalizing")
        stop_process(self.process)
        self.process = None
        if self.log_handle:
            try:
                self.log_handle.close()
            except OSError:
                pass
            self.log_handle = None
        self.append_endlist()
        self.manifest["endedAt"] = now_iso()
        self.manifest["status"] = "completed"
        self.manifest["videoUrl"] = ""
        self.manifest["videoPolicy"] = "analysis_first_then_delete"
        self.manifest["segmentCount"] = sum(
            len([
                item
                for item in (self.directory / "segments").glob(pattern)
                if item.stat().st_size > 0
            ])
            for pattern in ("part_*.wav", "part_*.flac", "part_*.ts")
        )
        recording_store.write_manifest(self.directory, self.manifest)
        log(f"结束音频采集，等待后台分析归档后删除 session={self.directory.name}")
        self.directory = None
        self.manifest = {}
        self.room_id = ""
        self.lost_stream_at = None
        self.not_live_since = None
        self.cleanup(force=True)

    def ensure_recording(self) -> None:
        try:
            stream = fetch_json("/api/live/stream/status")
            screen = fetch_json("/api/live/screen")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            self.last_error = f"读取直播状态失败：{exc}"
            if self.process and self.process.poll() is not None:
                self.stop_session(finalize=True)
            self.publish_state("idle", {"error": self.last_error})
            return
        room_id = str(stream.get("roomId") or "")
        captured = bool(stream.get("captured"))
        live = bool(screen.get("live")) and str(screen.get("status")) in {"ok", "partial", "stale"}
        if not captured:
            if self.directory:
                self.lost_stream_at = self.lost_stream_at or time.monotonic()
                if time.monotonic() - self.lost_stream_at >= 90:
                    self.stop_session(finalize=True)
                else:
                    self.publish_state(
                        "waiting_stream",
                        {"error": "画面流暂时中断，等待同一场次重新注册"},
                    )
                    return
            self.publish_state(
                "waiting_stream",
                {
                    "error": (
                        "直播中，等待千川大屏签名画面流"
                        if live
                        else "当前无可用直播画面流"
                    )
                },
            )
            return
        self.lost_stream_at = None
        if not live and str(screen.get("status") or "") == "not_live":
            self.not_live_since = self.not_live_since or time.monotonic()
            if time.monotonic() - self.not_live_since >= 90:
                if self.directory:
                    self.stop_session(finalize=True)
                self.publish_state("idle", {"error": "直播已结束，等待下一场开播"})
                return
        else:
            self.not_live_since = None
        if self.directory and room_id and self.room_id != room_id:
            self.stop_session(finalize=True)
        if not self.directory:
            self.begin_session(room_id, screen)
        if not self.process or self.process.poll() is not None:
            if self.process:
                self.process = None
                if self.log_handle:
                    try:
                        self.log_handle.close()
                    except OSError:
                        pass
                    self.log_handle = None
            self.start_ffmpeg()
        self.manifest["status"] = "recording"
        self.manifest["lastHeartbeatAt"] = now_iso()
        self.rebuild_playlist()
        recording_store.write_manifest(self.directory, self.manifest)
        self.last_error = ""
        self.publish_state("recording")

    def run(self) -> None:
        self.cleanup(force=True)
        while True:
            try:
                self.cleanup()
                paused = read_json(PAUSE_PATH).get("paused") is True
                if paused:
                    if self.directory:
                        self.stop_session(finalize=True)
                    self.publish_state("paused", {"error": ""})
                else:
                    self.ensure_recording()
            except Exception as exc:
                self.last_error = str(exc)
                self.publish_state("error", {"error": self.last_error})
                log(f"录制器异常：{exc}")
                if self.process and self.process.poll() is not None:
                    self.process = None
            time.sleep(POLL_SECONDS)


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    if not acquire_lock():
        log("检测到录制器已在运行，本次启动退出")
        return 0
    recorder = LiveRecorder()
    log(
        f"录制器启动 capture={'pyav-audio' if recorder.capture_available else 'not-found'} "
        f"dir={RECORDINGS_DIR} retention={RETENTION_DAYS}d"
    )
    try:
        recorder.run()
    except KeyboardInterrupt:
        pass
    finally:
        recorder.stop_session(finalize=True)
        release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
