from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import recording_store
import review_finalizer
from live_recorder import resolve_ffmpeg


ROOT = Path(__file__).resolve().parent
EXTERNAL_ROOT = Path(os.getenv("QIANCHUAN_EXTERNAL_ROOT", r"D:\AI投放产品"))
DATA_DIR = ROOT / "data"
RECORDINGS_DIR = recording_store.RECORDINGS_DIR
MODEL_DIR = EXTERNAL_ROOT / "models" / "whisper-large-v3"
STATE_PATH = DATA_DIR / "live-asr-state.json"
LOCK_PATH = DATA_DIR / "live-asr.lock"
LOG_PATH = DATA_DIR / "live-asr.log"
LIVE_SCREEN_STATE_PATH = DATA_DIR / "live-screen-metrics.json"
ARCHIVE_SESSIONS_DIR = DATA_DIR / "review-archive" / "sessions"
POLL_SECONDS = 3
TRANSCRIPTION_GRANULARITY_SECONDS = 300
try:
    from opencc import OpenCC

    SIMPLIFIED_CONVERTER = OpenCC("t2s")
except Exception:
    SIMPLIFIED_CONVERTER = None

# YouTube/Bilibili 片尾口播的常见关键词。直播带货+教育课程的直播里不会出现
# “订阅/转发/打赏/三连”这类片尾语，用于过滤 Whisper 在背景音乐上产生的幻觉。
HALLUCINATION_MARKERS = ("订阅", "转发", "打赏", "三连", "投币", "明镜与点点")


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
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary.write_text(content, encoding="utf-8")
    last_error: OSError | None = None
    for attempt in range(8):
        try:
            temporary.replace(path)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.2 * (attempt + 1))
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
    current = read_json(LOCK_PATH, {})
    owner = int(current.get("pid") or 0) if isinstance(current, dict) else 0
    if owner and owner != os.getpid() and pid_is_running(owner):
        return False
    atomic_write_json(LOCK_PATH, {"pid": os.getpid(), "startedAt": now_iso()})
    return True


def release_lock() -> None:
    current = read_json(LOCK_PATH, {})
    if isinstance(current, dict) and int(current.get("pid") or 0) not in {0, os.getpid()}:
        return
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def audio_duration(path: Path) -> float:
    try:
        import av

        with av.open(str(path)) as container:
            if container.duration:
                return max(0.0, float(container.duration / av.time_base))
    except Exception:
        pass
    return 30.0


def decode_audio_16k(path: Path) -> Any:
    import av
    import numpy as np

    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)
        chunks: list[Any] = []
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().reshape(-1))
        for resampled in resampler.resample(None):
            chunks.append(resampled.to_ndarray().reshape(-1))
    if not chunks:
        raise RuntimeError("直播分段中没有可识别音频")
    return np.concatenate(chunks).astype(np.float32)


def iso_from_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000).astimezone().isoformat(timespec="milliseconds")


def archive_session_assets(
    directory: Path,
    manifest: dict[str, Any],
    transcript: dict[str, Any],
    archive_sessions_dir: Path | None = None,
) -> None:
    session_id = str(manifest.get("id") or directory.name)
    target = (archive_sessions_dir or ARCHIVE_SESSIONS_DIR) / session_id
    (target / "asr").mkdir(parents=True, exist_ok=True)
    atomic_write_json(target / "manifest.json", {
        **manifest,
        "status": (
            "archived_analysis"
            if manifest.get("status") == "completed"
            else manifest.get("status")
        ),
        "archivedAt": now_iso(),
    })
    atomic_write_json(target / "asr" / "transcript.json", transcript)
    metrics = directory / "asr" / "metrics.json"
    if metrics.is_file():
        try:
            shutil.copy2(metrics, target / "asr" / "metrics.json")
        except OSError:
            pass


def backfill_session_archives(
    recordings_dir: Path = RECORDINGS_DIR,
    archive_sessions_dir: Path = ARCHIVE_SESSIONS_DIR,
) -> list[str]:
    archived: list[str] = []
    if not recordings_dir.is_dir():
        return archived
    for manifest_path in sorted(recordings_dir.glob("*/manifest.json")):
        directory = manifest_path.parent
        manifest = read_json(manifest_path, {})
        transcript = read_json(directory / "asr" / "transcript.json", {})
        if (
            not isinstance(manifest, dict)
            or not isinstance(transcript, dict)
            or not isinstance(transcript.get("segments"), list)
            or not transcript["segments"]
        ):
            continue
        try:
            archive_session_assets(
                directory,
                manifest,
                transcript,
                archive_sessions_dir=archive_sessions_dir,
            )
        except OSError as exc:
            log(f"会话分析归档失败 {directory.name}：{exc}")
            continue
        archived.append(str(manifest.get("id") or directory.name))
    return archived


def to_simplified(text: str) -> str:
    if SIMPLIFIED_CONVERTER is None:
        return text
    try:
        return SIMPLIFIED_CONVERTER.convert(text)
    except Exception:
        return text


def normalize_transcript_text(text: str) -> str:
    value = to_simplified(str(text or "").strip())
    if not value:
        return ""
    previous = None
    while previous != value:
        previous = value
        value = re.sub(
            r"(.{2,10}?)(?:[，,、；;\s]*\1){3,}",
            r"\1",
            value,
        )
    value = re.sub(r"(.)\1{9,}", r"\1", value)
    return value.strip(" ，,、；;")


def is_hallucinated(text: str) -> bool:
    value = to_simplified(str(text or ""))
    if not value:
        return False
    hits = sum(1 for marker in HALLUCINATION_MARKERS if marker in value)
    return hits >= 2


class SpeechWorker:
    def __init__(self) -> None:
        self.ffmpeg = resolve_ffmpeg()
        self.model: Any = None
        self.model_error = ""
        self.current_session = ""
        self.current_part = ""
        self.last_error = ""
        self.processed_count = 0
        self.pending_count = 0
        self.last_metric_signature = ""
        self.diarizer: Any = None
        self.speaker_extractor: Any = None
        self.speaker_gallery: Any = None
        self.speaker_gallery_session = ""
        self.current_speaker = ""
        self.current_speaker_at = ""

    def _speaker_diarizer(self) -> Any:
        if self.diarizer is None:
            import speaker_diarization

            self.diarizer = speaker_diarization.get_diarizer()
        return self.diarizer

    def _speaker_extractor(self) -> Any:
        if self.speaker_extractor is None:
            import speaker_diarization

            self.speaker_extractor = speaker_diarization._embedding_extractor()
        return self.speaker_extractor

    def _speaker_gallery(self, session_dir: Path) -> Any:
        import speaker_diarization

        session_name = str(session_dir)
        if self.speaker_gallery is None or self.speaker_gallery_session != session_name:
            extractor = self._speaker_extractor()
            self.speaker_gallery = speaker_diarization.SpeakerGallery(
                dim=int(extractor.dim),
                state_path=session_dir / "asr" / "speaker-gallery.json",
                threshold=0.55,
            )
            self.speaker_gallery_session = session_name
        return self.speaker_gallery

    def publish_state(self, status: str, extra: dict[str, Any] | None = None) -> None:
        atomic_write_json(
            STATE_PATH,
            {
                "ok": status in {"idle", "processing", "finalizing", "ready"},
                "status": status,
                "updatedAt": now_iso(),
                "pid": os.getpid(),
                "engine": "faster-whisper",
                "model": "large-v3",
                "modelPath": str(MODEL_DIR),
                "modelReady": self.model is not None,
                "audioSource": "直播流 TS 分段 · ffmpeg 16k mono · 降噪(高通+低通+噪声门)",
                "transcriptionGranularitySeconds": 300,
                "currentSession": self.current_session,
                "currentPart": self.current_part,
                "currentSpeaker": self.current_speaker,
                "currentSpeakerAt": self.current_speaker_at,
                "processedParts": self.processed_count,
                "pendingParts": self.pending_count,
                "rawVideoPolicy": "analysis_first_then_delete",
                "error": self.last_error or self.model_error,
                **(extra or {}),
            },
        )

    def load_model(self) -> None:
        if self.model is not None or self.model_error:
            return
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("OMP_NUM_THREADS", "2")
        if not (MODEL_DIR / "model.bin").is_file():
            self.model_error = f"本地 Whisper 模型缺失：{MODEL_DIR}"
            return
        try:
            from faster_whisper import WhisperModel

            self.model = WhisperModel(
                str(MODEL_DIR),
                device="cpu",
                compute_type="int8",
                local_files_only=True,
                cpu_threads=max(1, min(4, os.cpu_count() or 1)),
            )
            log("faster-whisper large-v3 本地模型加载完成")
        except Exception as exc:
            self.model_error = f"Whisper 模型加载失败：{exc}"
            log(self.model_error)

    def sample_live_metrics(self) -> None:
        state = read_json(LIVE_SCREEN_STATE_PATH, {})
        if not isinstance(state, dict) or not state.get("live"):
            return
        room_id = str((state.get("room") or {}).get("id") or "")
        if not room_id:
            return
        signature = f"{state.get('syncedAt')}|{room_id}"
        if signature == self.last_metric_signature:
            return
        metrics = state.get("metrics") if isinstance(state.get("metrics"), dict) else {}
        sample = {
            "t": int(time.time() * 1000),
            "capturedAt": now_iso(),
            "sourceAt": state.get("syncedAt") or state.get("heartbeatAt"),
            "spend": metrics.get("spend"),
            "gmv": metrics.get("gmv"),
            "orders": metrics.get("orders"),
            "online": metrics.get("online"),
            "watch": metrics.get("watchCount"),
            "productClicks": metrics.get("productClicks"),
            "gpm": metrics.get("gpm"),
            "roi": metrics.get("roi"),
        }
        for directory, manifest in recording_store.list_manifests(RECORDINGS_DIR):
            if (
                str(manifest.get("roomId") or "") == room_id
                and str(manifest.get("status") or "") == "recording"
            ):
                asr_dir = directory / "asr"
                asr_dir.mkdir(parents=True, exist_ok=True)
                path = asr_dir / "metrics.json"
                payload = read_json(path, {"version": 1, "samples": []})
                samples = payload.get("samples") if isinstance(payload, dict) else []
                samples = samples if isinstance(samples, list) else []
                if not samples or sample["t"] - int(samples[-1].get("t") or 0) >= 4000:
                    samples.append(sample)
                    del samples[:-8640]
                    atomic_write_json(
                        path,
                        {"version": 1, "roomId": room_id, "samples": samples},
                    )
        self.last_metric_signature = signature

    def session_directories(self) -> list[tuple[Path, dict[str, Any]]]:
        records = recording_store.list_manifests(RECORDINGS_DIR)
        records.sort(
            key=lambda item: (
                str(item[1].get("status") or "") == "recording",
                item[0].stat().st_mtime,
            ),
            reverse=True,
        )
        return records

    def extract_audio(self, segment: Path, target: Path) -> None:
        if target.is_file() and target.stat().st_size > 0:
            return
        if not self.ffmpeg:
            raise RuntimeError("未找到 ffmpeg，无法从直播分段提取音频")
        target.parent.mkdir(parents=True, exist_ok=True)
        creation_flags = 0x08000000 if os.name == "nt" else 0
        import subprocess

        result = subprocess.run(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(segment),
                "-vn",
                "-af",
                (
                    "highpass=f=80,"
                    "lowpass=f=7500,"
                    "agate=threshold=-35dB:ratio=2:attack=20:release=250:makeup=1,"
                    "dynaudnorm=f=200:g=15"
                ),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "flac",
                str(target),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
            creationflags=creation_flags,
        )
        if result.returncode != 0 or not target.is_file():
            raise RuntimeError(
                result.stderr.decode("utf-8", errors="replace")[-400:]
                or "音频提取失败"
            )

    def transcribe(
        self,
        audio: Path,
        session_dir: Path | None = None,
    ) -> list[dict[str, Any]]:
        self.load_model()
        if self.model is None:
            raise RuntimeError(self.model_error or "Whisper 模型不可用")
        waveform = decode_audio_16k(audio)
        generated, info = self.model.transcribe(
            waveform,
            language="zh",
            task="transcribe",
            beam_size=5,
            best_of=5,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=(
                "这是直播带货和教育课程的话术转写，请输出简体中文，不要繁体字，"
                "尽量通顺准确，只转写主播实际说的话，不要输出点赞、订阅、转发、打赏等无关内容。"
            ),
            word_timestamps=False,
        )
        whisper_segments: list[dict[str, Any]] = []
        for segment in generated:
            text = normalize_transcript_text(str(segment.text or "").strip())
            if not text:
                continue
            if len(text) >= 6 and len(set(text)) <= 2:
                continue
            if float(segment.no_speech_prob or 0) > 0.9:
                continue
            if float(segment.avg_logprob or 0) < -1.2:
                continue
            if is_hallucinated(text):
                continue
            whisper_segments.append(
                {
                    "start": round(float(segment.start or 0), 3),
                    "end": round(float(segment.end or 0), 3),
                    "text": text,
                    "avgLogProb": round(float(segment.avg_logprob or 0), 4),
                    "noSpeechProb": round(float(segment.no_speech_prob or 0), 4),
                }
            )
        speaker_labels: list[str | None] = [None] * len(whisper_segments)
        try:
            if session_dir is not None:
                import speaker_diarization

                if speaker_diarization.available():
                    speaker_labels = self._speaker_diarizer().assign_global_speakers(
                        waveform,
                        whisper_segments,
                        self._speaker_extractor(),
                        self._speaker_gallery(session_dir),
                    )
        except Exception as exc:
            log(f"说话人分离失败（本轮不留 speaker 标签）：{exc}")
        results: list[dict[str, Any]] = []
        for index, segment in enumerate(whisper_segments):
            results.append(
                {
                    **segment,
                    "speaker": speaker_labels[index],
                }
            )
        return results

    def process_session(self, directory: Path, manifest: dict[str, Any]) -> bool:
        segments = [
            item
            for item in sorted((directory / "segments").glob("part_*"))
            if item.is_file() and item.stat().st_size > 0
            and item.suffix.lower() in {".ts", ".wav", ".flac"}
        ]
        if str(manifest.get("status") or "") == "recording" and segments:
            segments = segments[:-1]
        if not segments:
            return False
        asr_dir = directory / "asr"
        audio_dir = asr_dir / "audio"
        asr_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = asr_dir / "transcript.json"
        transcript = read_json(
            transcript_path,
            {
                "version": 1,
                "sessionId": directory.name,
                "roomId": manifest.get("roomId"),
                "accountId": manifest.get("accountId"),
                "model": "faster-whisper-large-v3",
                "language": "zh",
                "segmentSeconds": TRANSCRIPTION_GRANULARITY_SECONDS,
                "segments": [],
            },
        )
        if isinstance(transcript, dict):
            transcript["segmentSeconds"] = TRANSCRIPTION_GRANULARITY_SECONDS
        transcript_segments = (
            transcript.get("segments")
            if isinstance(transcript, dict)
            and isinstance(transcript.get("segments"), list)
            else []
        )
        normalized_existing = False
        for item in transcript_segments:
            if not isinstance(item, dict) or not item.get("text"):
                continue
            simplified = normalize_transcript_text(str(item["text"]))
            if simplified != item["text"]:
                item["text"] = simplified
                normalized_existing = True
        if normalized_existing:
            transcript["segments"] = transcript_segments
            transcript["updatedAt"] = now_iso()
            atomic_write_json(transcript_path, transcript)
            archive_session_assets(directory, manifest, transcript)
        processed_ids = {
            str(item.get("segmentId"))
            for item in transcript_segments
            if isinstance(item, dict)
        }
        try:
            session_start = datetime.fromisoformat(
                str(manifest.get("startedAt") or "").replace("Z", "+00:00")
            ).timestamp()
        except (TypeError, ValueError):
            session_start = datetime.now().astimezone().timestamp()
        cursor_seconds = 0.0
        for segment in segments:
            if segment.suffix.lower() in {".wav", ".flac"}:
                audio = segment
            else:
                audio = audio_dir / f"{segment.stem}.flac"
                self.extract_audio(segment, audio)
            duration = audio_duration(audio)
            start_seconds = cursor_seconds
            end_seconds = start_seconds + duration
            cursor_seconds = end_seconds
            if segment.stem in processed_ids:
                continue
            self.current_session = directory.name
            self.current_part = segment.stem
            self.publish_state("processing")
            log(
                f"转写 {directory.name}/{segment.stem} "
                f"audio={duration:.1f}s model=large-v3"
            )
            last_speaker = ""
            last_speaker_at = ""
            for item in self.transcribe(audio, session_dir=directory):
                absolute_start = int((session_start + start_seconds + item["start"]) * 1000)
                absolute_end = int((session_start + start_seconds + item["end"]) * 1000)
                transcript_segments.append(
                    {
                        "id": f"{directory.name}-{segment.stem}-{len(transcript_segments)}",
                        "segmentId": segment.stem,
                        "text": item["text"],
                        "startSeconds": round(start_seconds + item["start"], 3),
                        "endSeconds": round(start_seconds + item["end"], 3),
                        "startedAt": iso_from_ms(absolute_start),
                        "endedAt": iso_from_ms(absolute_end),
                        "avgLogProb": item["avgLogProb"],
                        "noSpeechProb": item["noSpeechProb"],
                        "speaker": item.get("speaker"),
                        "source": "faster-whisper-large-v3",
                    }
                )
                if item.get("speaker"):
                    last_speaker = str(item["speaker"])
                    last_speaker_at = iso_from_ms(absolute_end)
            if last_speaker:
                self.current_speaker = last_speaker
                self.current_speaker_at = last_speaker_at
            transcript["segments"] = transcript_segments
            transcript["updatedAt"] = now_iso()
            transcript["processedParts"] = sorted(
                processed_ids | {segment.stem}
            )
            processed_ids.add(segment.stem)
            atomic_write_json(transcript_path, transcript)
            archive_session_assets(directory, manifest, transcript)
            self.processed_count += 1
            return True
        return False

    def run(self) -> None:
        archived = backfill_session_archives()
        if archived:
            log(f"已回填 {len(archived)} 个会话的永久分析归档")
        self.publish_state("ready")
        while True:
            try:
                self.sample_live_metrics()
                pending = 0
                worked = False
                for directory, manifest in self.session_directories():
                    if not recording_store.manifest_path(directory).is_file():
                        continue
                    segments = [
                        item
                        for item in (directory / "segments").glob("part_*")
                        if item.is_file() and item.stat().st_size > 0
                        and item.suffix.lower() in {".ts", ".wav", ".flac"}
                    ]
                    if str(manifest.get("status") or "") == "recording" and segments:
                        segments = segments[:-1]
                    transcript = read_json(directory / "asr" / "transcript.json", {})
                    processed = {
                        str(item.get("segmentId"))
                        for item in transcript.get("segments", [])
                        if isinstance(item, dict)
                    } if isinstance(transcript, dict) else set()
                    pending += len(
                        [item for item in segments if item.stem not in processed]
                    )
                self.pending_count = pending
                for directory, manifest in self.session_directories():
                    if self.process_session(directory, manifest):
                        worked = True
                        break
                if not worked:
                    self.current_session = ""
                    self.current_part = ""
                    self.publish_state("finalizing")
                    finalized = review_finalizer.finalize_completed_sessions()
                    if finalized:
                        log(
                            "后台复盘归档完成并已删除原始录像: "
                            + ", ".join(finalized)
                        )
                    self.publish_state(
                        "idle",
                        {"lastFinalizedSessions": finalized},
                    )
            except Exception as exc:
                self.last_error = str(exc)
                self.publish_state("error")
                log(f"ASR 异常：{exc}")
            time.sleep(POLL_SECONDS)


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not acquire_lock():
        log("检测到 ASR 服务已在运行，本次启动退出")
        return 0
    worker = SpeechWorker()
    log(
        f"ASR 服务启动 model={MODEL_DIR} ffmpeg={worker.ffmpeg or 'not-found'}"
    )
    try:
        worker.run()
    except KeyboardInterrupt:
        pass
    finally:
        release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
