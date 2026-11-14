from __future__ import annotations

import bisect
import copy
import json
import os
import re
import shutil
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import speaker_profile


ROOT = Path(__file__).resolve().parent
RECORDINGS_DIR = Path(
    os.getenv("QIANCHUAN_RECORDINGS_DIR", r"D:\DAI投放产品录屏备份")
).expanduser()
REVIEW_ARCHIVE_DIR = ROOT / "data" / "review-archive"
REVIEW_ARCHIVE_SESSIONS_DIR = REVIEW_ARCHIVE_DIR / "sessions"
RETENTION_DAYS = 1
SESSION_DIR_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})_[A-Za-z0-9_-]+$")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{datetime.now().timestamp():.6f}.tmp")
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


def safe_component(value: Any, fallback: str = "session") -> str:
    cleaned = "".join(
        character
        for character in str(value or "")
        if character.isalnum() or character in "-_"
    )
    return cleaned[:80] or fallback


def create_session_directory(
    room_id: str,
    started_at: datetime | None = None,
    recordings_dir: Path = RECORDINGS_DIR,
) -> Path:
    started_at = started_at or datetime.now().astimezone()
    directory = recordings_dir / (
        f"{started_at:%Y-%m-%d}_{safe_component(room_id)}_"
        f"{started_at:%H%M%S}"
    )
    (directory / "segments").mkdir(parents=True, exist_ok=True)
    return directory


def manifest_path(directory: Path) -> Path:
    return directory / "manifest.json"


def read_manifest(directory: Path) -> dict[str, Any]:
    try:
        value = json.loads(manifest_path(directory).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_manifest(directory: Path, manifest: dict[str, Any]) -> None:
    atomic_write_json(
        manifest_path(directory),
        {
            **manifest,
            "updatedAt": now_iso(),
        },
    )


def manifest_directories(recordings_dir: Path = RECORDINGS_DIR) -> list[Path]:
    if not recordings_dir.is_dir():
        return []
    return sorted(
        (
            item
            for item in recordings_dir.iterdir()
            if item.is_dir() and SESSION_DIR_PATTERN.match(item.name)
        ),
        key=lambda item: item.name,
        reverse=True,
    )


def cleanup_recordings(
    retention_days: int = RETENTION_DAYS,
    now: datetime | None = None,
    recordings_dir: Path = RECORDINGS_DIR,
) -> list[str]:
    retention_days = max(1, int(retention_days))
    now = now or datetime.now().astimezone()
    cutoff = now.date() - timedelta(days=retention_days - 1)
    removed: list[str] = []
    recordings_dir = recordings_dir.resolve()
    for directory in reversed(manifest_directories(recordings_dir)):
        match = SESSION_DIR_PATTERN.match(directory.name)
        if not match:
            continue
        try:
            session_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if session_date >= cutoff:
            continue
        resolved = directory.resolve()
        if resolved.parent != recordings_dir:
            continue
        shutil.rmtree(resolved)
        removed.append(directory.name)
    return removed


def public_recording_files(
    directory: Path,
    recordings_dir: Path = RECORDINGS_DIR,
) -> dict[str, Any]:
    relative = directory.resolve().relative_to(recordings_dir.resolve()).as_posix()
    playlist = directory / "index.m3u8"
    video = directory / "session.mp4"
    segments = [
        item
        for item in sorted((directory / "segments").glob("part_*"))
        if item.is_file()
        and item.stat().st_size > 0
        and item.suffix.lower() in {".ts", ".wav", ".flac"}
    ]
    size_bytes = sum(
        item.stat().st_size
        for item in [playlist, video, *segments]
        if item.is_file()
    )
    return {
        "playlistUrl": f"/recordings/{relative}/index.m3u8" if playlist.is_file() else "",
        "videoUrl": (
            f"/recordings/{relative}/session.mp4"
            if video.is_file() and video.stat().st_size > 1024
            else ""
        ),
        "hlsUrl": f"/recordings/{relative}/index.m3u8" if playlist.is_file() else "",
        "segmentCount": len(segments),
        "sizeBytes": size_bytes,
    }


def list_manifests(
    recordings_dir: Path = RECORDINGS_DIR,
) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    for directory in manifest_directories(recordings_dir):
        manifest = read_manifest(directory)
        if manifest:
            records.append((directory, manifest))
    return records


def _archived_manifest(
    directory: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    normalized = copy.deepcopy(manifest)
    transcript = _load_asr_transcript(directory)
    transcript_segments = (
        transcript.get("segments")
        if isinstance(transcript.get("segments"), list)
        else []
    )
    normalized["status"] = "archived_analysis"
    normalized["recordingStatusLabel"] = "分析已归档 · 原始录像已删除"
    normalized["videoExpired"] = True
    normalized["videoUrl"] = ""
    if not str(normalized.get("endedAt") or "").strip() and transcript_segments:
        end_times: list[datetime] = []
        for item in transcript_segments:
            if not isinstance(item, dict):
                continue
            try:
                end_times.append(
                    datetime.fromisoformat(
                        str(item.get("endedAt") or "").replace("Z", "+00:00")
                    )
                )
            except (TypeError, ValueError):
                continue
        if end_times:
            normalized["endedAt"] = max(end_times).isoformat(timespec="seconds")
    if not str(normalized.get("endedAt") or "").strip():
        try:
            normalized["endedAt"] = datetime.fromtimestamp(
                directory.stat().st_mtime
            ).astimezone().isoformat(timespec="seconds")
        except OSError:
            pass
    return normalized


def list_archived_manifests(
    archive_sessions_dir: Path = REVIEW_ARCHIVE_SESSIONS_DIR,
) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    if not archive_sessions_dir.is_dir():
        return records
    for manifest_file in sorted(archive_sessions_dir.glob("*/manifest.json")):
        try:
            value = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        records.append(
            (
                manifest_file.parent,
                _archived_manifest(manifest_file.parent, value),
            )
        )
    return records


def script_session_sources(
    recordings_dir: Path = RECORDINGS_DIR,
    archive_sessions_dir: Path = REVIEW_ARCHIVE_SESSIONS_DIR,
) -> list[tuple[Path, dict[str, Any], str]]:
    """Return raw and archived sessions with a stable source label.

    A raw directory wins only when it has usable transcript data. Otherwise the
    durable archive copy is used, which is the normal path after raw video was
    deleted following analysis.
    """
    archived = {
        str(manifest.get("id") or directory.name): (directory, manifest)
        for directory, manifest in list_archived_manifests(archive_sessions_dir)
    }
    sources: list[tuple[Path, dict[str, Any], str]] = []
    raw_ids: set[str] = set()
    for directory, manifest in list_manifests(recordings_dir):
        session_id = str(manifest.get("id") or directory.name)
        raw_ids.add(session_id)
        raw_has_transcript = has_asr_transcript(directory)
        if not raw_has_transcript and session_id in archived:
            archive_directory, archive_manifest = archived[session_id]
            sources.append((archive_directory, archive_manifest, "archive"))
        else:
            sources.append((directory, manifest, "recording"))
    for session_id, (directory, manifest) in archived.items():
        if session_id not in raw_ids:
            sources.append((directory, manifest, "archive"))
    return sources


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _floor_seconds(raw_value: Any, fallback: float = 0.0) -> int:
    value = _number(raw_value)
    return max(0, int(round(value if value is not None else fallback)))


def _load_asr_transcript(directory: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            (directory / "asr" / "transcript.json").read_text(encoding="utf-8")
        )
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def has_asr_transcript(directory: Path) -> bool:
    transcript = _load_asr_transcript(directory)
    segments = transcript.get("segments")
    return isinstance(segments, list) and any(
        isinstance(item, dict) and str(item.get("text") or "").strip()
        for item in segments
    )


def _load_speaker_map(directory: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            (directory / "asr" / "speaker-map.json").read_text(encoding="utf-8")
        )
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def resolve_session_directory(
    session_id: str,
    recordings_dir: Path = RECORDINGS_DIR,
    archive_sessions_dir: Path = REVIEW_ARCHIVE_SESSIONS_DIR,
) -> Path | None:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(session_id or ""))[:160]
    candidates = [
        recordings_dir / safe,
        archive_sessions_dir / safe,
    ]
    for candidate in candidates:
        if (candidate / "asr" / "transcript.json").is_file():
            return candidate
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def load_segment_speaker_overrides(directory: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            (directory / "asr" / "segment-speaker-overrides.json").read_text(
                encoding="utf-8"
            )
        )
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def update_segment_speakers(
    session_id: str,
    segment_ids: list[str],
    speaker: str,
    recordings_dir: Path = RECORDINGS_DIR,
    archive_sessions_dir: Path = REVIEW_ARCHIVE_SESSIONS_DIR,
) -> dict[str, Any]:
    """Reassign one or more transcribed sentences to another speaker."""
    directory = resolve_session_directory(
        session_id, recordings_dir, archive_sessions_dir
    )
    if directory is None:
        raise ValueError(f"找不到场次 {session_id} 的转写目录")
    transcript = _load_asr_transcript(directory)
    segments = transcript.get("segments") if isinstance(transcript, dict) else []
    segments = [item for item in segments if isinstance(item, dict)]
    wanted = {str(value) for value in (segment_ids or []) if value}
    if not wanted:
        raise ValueError("缺少需要修正的句子标识")
    speaker_value = re.sub(r"[\r\n\t]+", " ", str(speaker or "")).strip()[:40]
    updated = 0
    for item in segments:
        if str(item.get("id") or "") not in wanted:
            continue
        if str(item.get("speaker") or "") == speaker_value:
            continue
        item["speaker"] = speaker_value
        item["speakerSource"] = "manual"
        updated += 1
    if updated:
        transcript["segments"] = segments
        transcript["updatedAt"] = now_iso()
        atomic_write_json(directory / "asr" / "transcript.json", transcript)
        overrides_path = directory / "asr" / "segment-speaker-overrides.json"
        existing = load_segment_speaker_overrides(directory)
        overrides = (
            existing.get("overrides")
            if isinstance(existing.get("overrides"), dict)
            else {}
        )
        overrides = dict(overrides)
        for segment_id in wanted:
            overrides[str(segment_id)] = {
                "speaker": speaker_value,
                "updatedAt": now_iso(),
            }
        atomic_write_json(
            overrides_path,
            {"version": 1, "overrides": overrides, "updatedAt": now_iso()},
        )
    return {
        "ok": True,
        "sessionId": session_id,
        "directory": directory.name,
        "speaker": speaker_value,
        "updated": updated,
        "segmentIds": sorted(wanted),
    }


def _load_asr_metrics(directory: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(
            (directory / "asr" / "metrics.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return []
    samples = value.get("samples") if isinstance(value, dict) else []
    return sorted(
        [item for item in samples if isinstance(item, dict)],
        key=lambda item: _number(item.get("t")) or 0,
    )


def phrase_clock(item: dict[str, Any]) -> str:
    try:
        return datetime.fromisoformat(
            str(item.get("startedAt") or "").replace("Z", "+00:00")
        ).astimezone().strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return "--:--:--"


def _nearest_metric(
    samples: list[dict[str, Any]],
    timestamp_ms: int,
) -> dict[str, Any] | None:
    if not samples:
        return None
    return min(
        samples,
        key=lambda item: abs((_number(item.get("t")) or 0) - timestamp_ms),
    )


def build_15_minute_buckets(
    samples: list[dict[str, Any]],
    start_ms: int | None,
) -> list[dict[str, Any]]:
    valid = [
        item for item in samples
        if _number(item.get("t")) is not None
    ]
    valid.sort(key=lambda item: _number(item.get("t")) or 0)
    if len(valid) < 2:
        return []

    def interpolate(timestamp_ms: float, key: str) -> float | None:
        if not valid:
            return None
        right_index = next(
            (
                index
                for index, item in enumerate(valid)
                if (_number(item.get("t")) or 0) >= timestamp_ms
            ),
            len(valid) - 1,
        )
        right = valid[right_index]
        left = valid[max(0, right_index - 1)]
        right_value = _number(right.get(key))
        left_value = _number(left.get(key))
        if right_value is None or left_value is None:
            return right_value if right_value is not None else left_value
        right_time = _number(right.get("t")) or timestamp_ms
        left_time = _number(left.get("t")) or timestamp_ms
        if right_time == left_time:
            return right_value
        ratio = max(0.0, min(1.0, (timestamp_ms - left_time) / (right_time - left_time)))
        return left_value + (right_value - left_value) * ratio

    first_time = _number(valid[0].get("t")) or (start_ms or 0)
    last_time = _number(valid[-1].get("t")) or first_time
    first_dt = datetime.fromtimestamp(first_time / 1000).astimezone()
    cursor = first_dt.replace(
        minute=(first_dt.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    end_dt = datetime.fromtimestamp(last_time / 1000).astimezone()
    buckets: list[dict[str, Any]] = []
    fields = (
        ("exposure", "exposure"),
        ("watch", "watch"),
        ("productClicks", "productClicks"),
        ("orders", "orders"),
        ("spend", "spend"),
        ("gmv", "gmv"),
    )
    while cursor <= end_dt:
        next_cursor = cursor + timedelta(minutes=15)
        start_value = cursor.timestamp() * 1000
        end_value = next_cursor.timestamp() * 1000
        values: dict[str, Any] = {}
        has_any = False
        for key, _ in fields:
            start_metric = interpolate(start_value, key)
            end_metric = interpolate(end_value, key)
            if start_metric is None or end_metric is None:
                values[key] = None
                continue
            delta = max(0.0, end_metric - start_metric)
            values[key] = round(delta, 4)
            has_any = True
        if has_any:
            buckets.append(
                {
                    "label": f"{cursor:%H:%M}-{next_cursor:%H:%M}",
                    "start": cursor.isoformat(),
                    "end": next_cursor.isoformat(),
                    "exposure": values["exposure"],
                    "watch": values["watch"],
                    "productClicks": values["productClicks"],
                    "orders": values["orders"],
                    "spend": values["spend"],
                    "gmv": values["gmv"],
                    "source": "qianchuan_live_screen_5m_to_15m",
                }
            )
        cursor = next_cursor
    return buckets


def coalesce_speech_phrases(
    phrases: list[dict[str, Any]],
    max_gap_seconds: float = 3.5,
    max_duration_seconds: float = 45.0,
    max_characters: int = 220,
) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    for item in phrases:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        current = copy.deepcopy(item)
        if _number(current.get("startSeconds")) is None:
            try:
                current["startSeconds"] = datetime.fromisoformat(
                    str(current.get("startedAt") or "").replace("Z", "+00:00")
                ).timestamp()
            except (TypeError, ValueError):
                current["startSeconds"] = 0
        if _number(current.get("endSeconds")) is None:
            try:
                current["endSeconds"] = datetime.fromisoformat(
                    str(current.get("endedAt") or "").replace("Z", "+00:00")
                ).timestamp()
            except (TypeError, ValueError):
                current["endSeconds"] = current["startSeconds"]
        ordered.append(current)
    ordered.sort(key=lambda item: _number(item.get("startSeconds")) or 0)
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for item in ordered:
        if not current:
            current = [item]
            continue
        previous = current[-1]
        gap = (_number(item.get("startSeconds")) or 0) - (
            _number(previous.get("endSeconds")) or 0
        )
        duration = (_number(item.get("endSeconds")) or 0) - (
            _number(current[0].get("startSeconds")) or 0
        )
        characters = sum(len(str(part.get("text") or "")) for part in current) + len(
            str(item.get("text") or "")
        )
        if (
            gap > max_gap_seconds
            or duration > max_duration_seconds
            or characters > max_characters
            or str(item.get("speaker") or "") != str(previous.get("speaker") or "")
        ):
            groups.append(current)
            current = [item]
        else:
            current.append(item)
    if current:
        groups.append(current)
    merged: list[dict[str, Any]] = []
    terminal = re.compile(r"[。！？!?；;]$")
    for group in groups:
        text = ""
        for part in group:
            fragment = str(part.get("text") or "").strip()
            if not fragment:
                continue
            if not text:
                text = fragment
            elif terminal.search(text):
                text += fragment
            else:
                text += "，" + fragment
        text = re.sub(r"[，,]{2,}", "，", text).strip("，, ")
        if not text:
            continue
        first = group[0]
        last = group[-1]
        merged.append(
            {
                **first,
                "id": f"utterance-{first.get('id') or len(merged)}",
                "text": text,
                "endSeconds": last.get("endSeconds"),
                "endedAt": last.get("endedAt"),
                "sourceSegmentIds": [
                    str(item.get("id") or "") for item in group
                ],
            }
        )
    return merged


def analyze_speech(
    directory: Path,
    history_series: list[dict[str, Any]],
) -> dict[str, Any]:
    transcript = _load_asr_transcript(directory)
    phrases = transcript.get("segments") if isinstance(transcript, dict) else []
    phrases = phrases if isinstance(phrases, list) else []
    phrases = [item for item in phrases if isinstance(item, dict) and item.get("text")]
    phrases = coalesce_speech_phrases(phrases)
    for item in phrases:
        item["sessionId"] = directory.name
    if not phrases:
        return {
            "available": False,
            "engine": "faster-whisper-tiny",
            "phrases": [],
            "good": [],
            "bad": [],
            "summary": "本地 Whisper 尚未生成该场次转写。",
            "source": "本地 Whisper 未产出",
        }
    metric_samples = _load_asr_metrics(directory)
    if not metric_samples:
        metric_samples = [
            {
                "t": int((_number(item.get("t")) or 0)),
                "spend": item.get("spend"),
                "gmv": item.get("gmv"),
                "orders": item.get("orders"),
                "online": item.get("online"),
                "watch": item.get("watch"),
            }
            for item in history_series
        ]
    enriched: list[dict[str, Any]] = []
    good: list[dict[str, Any]] = []
    bad: list[dict[str, Any]] = []
    for phrase in phrases:
        try:
            start_ms = int(
                datetime.fromisoformat(
                    str(phrase.get("startedAt") or "").replace("Z", "+00:00")
                ).timestamp()
                * 1000
            )
            end_ms = int(
                datetime.fromisoformat(
                    str(phrase.get("endedAt") or "").replace("Z", "+00:00")
                ).timestamp()
                * 1000
            )
        except (TypeError, ValueError):
            continue
        start_metric = _nearest_metric(metric_samples, start_ms)
        end_metric = _nearest_metric(metric_samples, end_ms + 20000)
        if not start_metric or not end_metric:
            enriched.append(
                {
                    **copy.deepcopy(phrase),
                    "effect": "unknown",
                    "effectLabel": "指标未对齐",
                    "scriptScore": None,
                }
            )
            continue
        spend_delta = max(
            0.0,
            (_number(end_metric.get("spend")) or 0)
            - (_number(start_metric.get("spend")) or 0),
        )
        gmv_delta = max(
            0.0,
            (_number(end_metric.get("gmv")) or 0)
            - (_number(start_metric.get("gmv")) or 0),
        )
        orders_delta = max(
            0.0,
            (_number(end_metric.get("orders")) or 0)
            - (_number(start_metric.get("orders")) or 0),
        )
        online_start = _number(start_metric.get("online"))
        online_end = _number(end_metric.get("online"))
        online_delta = (
            online_end - online_start
            if online_start is not None and online_end is not None
            else None
        )
        online_rate = (
            online_delta / online_start
            if online_delta is not None and online_start
            else None
        )
        if orders_delta > 0:
            effect = "good"
            effect_label = "对应窗口出单"
            script_score = min(96, 74 + min(20, orders_delta * 4))
        elif online_rate is not None and online_rate <= -0.15:
            effect = "bad"
            effect_label = "对应窗口掉人"
            script_score = max(18, 48 + online_rate * 80)
        elif online_delta is not None and online_delta > 0:
            effect = "good"
            effect_label = "对应窗口留人"
            script_score = 68
        else:
            effect = "neutral"
            effect_label = "无明显变化"
            script_score = 52
        item = {
            **copy.deepcopy(phrase),
            "effect": effect,
            "effectLabel": effect_label,
            "scriptScore": round(script_score, 1),
            "metrics": {
                "windowStart": start_metric.get("capturedAt")
                or start_metric.get("syncedAt"),
                "windowEnd": end_metric.get("capturedAt")
                or end_metric.get("syncedAt"),
                "spendDelta": round(spend_delta, 2),
                "gmvDelta": round(gmv_delta, 2),
                "ordersDelta": round(orders_delta, 4),
                "onlineStart": online_start,
                "onlineEnd": online_end,
                "onlineDelta": round(online_delta, 2) if online_delta is not None else None,
                "onlineRate": round(online_rate * 100, 2) if online_rate is not None else None,
            },
        }
        enriched.append(item)
        if effect == "good":
            good.append(item)
        elif effect == "bad":
            bad.append(item)
    good.sort(
        key=lambda item: (
            _number(item.get("metrics", {}).get("ordersDelta")) or 0,
            item.get("scriptScore") or 0,
        ),
        reverse=True,
    )
    bad.sort(
        key=lambda item: _number(item.get("metrics", {}).get("onlineRate")) or 0
    )
    top_orders = [
        item for item in good
        if (_number(item.get("metrics", {}).get("ordersDelta")) or 0) > 0
    ]
    top_orders.sort(
        key=lambda item: (
            _number(item.get("metrics", {}).get("ordersDelta")) or 0,
            _number(item.get("metrics", {}).get("gmvDelta")) or 0,
        ),
        reverse=True,
    )
    good_summary = "；".join(
        f"{phrase_clock(item)} 「{item['text']}」{item['effectLabel']}"
        f"（订单 +{(item['metrics'].get('ordersDelta') or 0):.0f}）"
        for item in good[:5]
    ) or "暂无明确出单/留人话术"
    bad_summary = "；".join(
        f"{phrase_clock(item)} 「{item['text']}」{item['effectLabel']}"
        f"（在线 {(item['metrics'].get('onlineDelta') or 0):+.0f}）"
        for item in bad[:5]
    ) or "暂无明确掉人话术"
    return {
        "available": True,
        "engine": str(transcript.get("model") or "faster-whisper-tiny"),
        "language": str(transcript.get("language") or "zh"),
        "audioDirectory": str(directory / "asr" / "audio"),
        "audioSegmentSeconds": int(
            _number(transcript.get("segmentSeconds")) or 300
        ),
        "metricResolution": "约 5 秒",
        "phrases": enriched,
        "good": good[:8],
        "bad": bad[:8],
        "topOrders": top_orders[:5],
        "summary": f"效果较好：{good_summary}。效果较差：{bad_summary}。",
        "source": "直播流音频 · 本地 faster-whisper-tiny",
        "speakerProfiles": speaker_profile.apply_speaker_map(
            speaker_profile.attach_speaker_metrics(
                speaker_profile.build_speaker_profiles(transcript),
                enriched,
            ),
            _load_speaker_map(directory),
        ),
    }


def _text_bigrams(text: str) -> set[str]:
    compact = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "", str(text or "").lower())
    return {compact[index : index + 2] for index in range(len(compact) - 1)}


def _bigram_similarity(left: str, right: str) -> float:
    left_bigrams = _text_bigrams(left)
    right_bigrams = _text_bigrams(right)
    if not left_bigrams or not right_bigrams:
        return 0.0
    return len(left_bigrams & right_bigrams) / len(left_bigrams | right_bigrams)


def _phrase_order_metric(
    samples: list[dict[str, Any]],
    timestamp_ms: int,
) -> dict[str, Any] | None:
    return _nearest_metric(samples, timestamp_ms)


def build_script_analysis(
    directory: Path,
    manifest: dict[str, Any],
    history_series: list[dict[str, Any]],
    order_window_seconds: float = 300.0,
) -> dict[str, Any]:
    """话术页专用分析：完整长句 + 5 分钟出单窗口 + 相似话术归类。"""
    transcript = _load_asr_transcript(directory)
    raw_phrases = transcript.get("segments") if isinstance(transcript, dict) else []
    raw_phrases = raw_phrases if isinstance(raw_phrases, list) else []
    raw_phrases = [
        item for item in raw_phrases if isinstance(item, dict) and item.get("text")
    ]
    phrases = coalesce_speech_phrases(raw_phrases)
    if not phrases:
        return {
            "available": False,
            "engine": str(transcript.get("model") or "faster-whisper"),
            "language": str(transcript.get("language") or "zh"),
            "session": {
                "id": str(manifest.get("id") or ""),
                "date": str(manifest.get("date") or ""),
                "startTime": str(manifest.get("startedAt") or ""),
                "roomId": str(manifest.get("roomId") or ""),
                "accountId": str(manifest.get("accountId") or ""),
            },
            "phrases": [],
            "quality": [],
            "low": [],
            "summary": "本地 Whisper 尚未生成该场次转写。",
            "source": "本地 Whisper 未产出",
        }
    metric_samples = _load_asr_metrics(directory)
    if not metric_samples:
        metric_samples = [
            {
                "t": int(_number(item.get("t")) or 0),
                "spend": item.get("spend"),
                "gmv": item.get("gmv"),
                "orders": item.get("orders"),
                "online": item.get("online"),
                "watch": item.get("watch"),
            }
            for item in history_series
        ]

    enriched: list[dict[str, Any]] = []
    order_phrases: list[dict[str, Any]] = []
    low_phrases: list[dict[str, Any]] = []
    for phrase in phrases:
        try:
            start_ms = int(
                datetime.fromisoformat(
                    str(phrase.get("startedAt") or "").replace("Z", "+00:00")
                ).timestamp()
                * 1000
            )
            end_ms = int(
                datetime.fromisoformat(
                    str(phrase.get("endedAt") or "").replace("Z", "+00:00")
                ).timestamp()
                * 1000
            )
        except (TypeError, ValueError):
            continue
        start_metric = _nearest_metric(metric_samples, start_ms)
        order_metric = _nearest_metric(
            metric_samples,
            end_ms + int(order_window_seconds * 1000),
        )
        online_metric = _nearest_metric(metric_samples, end_ms + 30000)
        if not start_metric:
            continue
        orders_delta = max(
            0.0,
            (_number(order_metric.get("orders")) or 0)
            - (_number(start_metric.get("orders")) or 0),
        ) if order_metric else 0.0
        gmv_delta = max(
            0.0,
            (_number(order_metric.get("gmv")) or 0)
            - (_number(start_metric.get("gmv")) or 0),
        ) if order_metric else 0.0
        spend_delta = max(
            0.0,
            (_number(order_metric.get("spend")) or 0)
            - (_number(start_metric.get("spend")) or 0),
        ) if order_metric else 0.0
        online_start = _number(start_metric.get("online"))
        online_end = (
            _number(online_metric.get("online"))
            if online_metric
            else online_start
        )
        online_delta = (
            online_end - online_start
            if online_start is not None and online_end is not None
            else None
        )
        online_rate = (
            online_delta / online_start
            if online_delta is not None and online_start
            else None
        )
        watch_delta = (
            (_number(order_metric.get("watch")) or 0)
            - (_number(start_metric.get("watch")) or 0)
            if order_metric
            else 0.0
        )
        if orders_delta > 0:
            effect = "good"
            effect_label = "5 分钟内出单"
        elif online_rate is not None and online_rate <= -0.12:
            effect = "bad"
            effect_label = "说完后掉人"
        elif orders_delta <= 0 and (spend_delta > 0 or watch_delta > 0):
            effect = "bad"
            effect_label = "有流量无转化"
        else:
            effect = "neutral"
            effect_label = "无明显变化"
        item = {
            **copy.deepcopy(phrase),
            "effect": effect,
            "effectLabel": effect_label,
            "clock": phrase_clock(phrase),
            "metrics": {
                "windowStart": start_metric.get("capturedAt")
                or start_metric.get("sourceAt"),
                "windowEnd": (
                    order_metric.get("capturedAt") or order_metric.get("sourceAt")
                    if order_metric
                    else None
                ),
                "ordersDelta": round(orders_delta, 4),
                "gmvDelta": round(gmv_delta, 2),
                "spendDelta": round(spend_delta, 2),
                "watchDelta": round(watch_delta, 2),
                "onlineStart": online_start,
                "onlineEnd": online_end,
                "onlineDelta": (
                    round(online_delta, 2)
                    if online_delta is not None
                    else None
                ),
                "onlineRate": (
                    round(online_rate * 100, 2)
                    if online_rate is not None
                    else None
                ),
            },
        }
        enriched.append(item)
        if effect == "good":
            order_phrases.append(item)
        elif effect == "bad":
            low_phrases.append(item)

    quality_groups = _group_similar_script_phrases(order_phrases, mode="orders")
    quality = quality_groups[:5]
    low_groups = _group_similar_script_phrases(
        low_phrases,
        mode="low",
    )
    low = low_groups[:12]
    order_total = sum(
        _number(item.get("metrics", {}).get("ordersDelta")) or 0
        for item in order_phrases
    )
    summary = (
        f"本场转写 {len(enriched)} 个完整长句，其中 {len(order_phrases)} 句在说完后 "
        f"{int(order_window_seconds / 60)} 分钟内对应出单（累计订单 +{order_total:.0f}），"
        f"{len(low_phrases)} 句对应掉人或流量无转化。"
        if enriched
        else "本场暂无可用 Whisper 长句。"
    )
    return {
        "available": True,
        "engine": str(transcript.get("model") or "faster-whisper"),
        "language": str(transcript.get("language") or "zh"),
        "orderWindowSeconds": int(order_window_seconds),
        "session": {
            "id": str(manifest.get("id") or ""),
            "date": str(manifest.get("date") or ""),
            "startTime": str(manifest.get("startedAt") or ""),
            "endedAt": str(manifest.get("endedAt") or ""),
            "roomId": str(manifest.get("roomId") or ""),
            "accountId": str(manifest.get("accountId") or ""),
            "status": str(manifest.get("status") or ""),
        },
        "phrases": enriched,
        "quality": quality,
        "low": low,
        "summary": summary,
        "source": "直播流音频 · 本地 Whisper 转写 · 5 分钟出单窗口归因",
    }


def _group_similar_script_phrases(
    items: list[dict[str, Any]],
    mode: str = "orders",
    similarity_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """把语义/语法/场景基本相同的长句归并成一类，按出单数汇总。"""
    groups: list[dict[str, Any]] = []
    for item in items:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        matched = next(
            (
                group
                for group in groups
                if _bigram_similarity(text, str(group.get("text") or ""))
                >= similarity_threshold
            ),
            None,
        )
        orders = _number(item.get("metrics", {}).get("ordersDelta")) or 0
        if matched is None:
            groups.append(
                {
                    "text": text,
                    "orders": orders,
                    "occurrences": 1,
                    "members": [item],
                    "reason": str(item.get("effectLabel") or ""),
                }
            )
            continue
        matched["orders"] = (matched.get("orders") or 0) + orders
        matched["occurrences"] = int(matched.get("occurrences") or 0) + 1
        matched["members"].append(item)
        representative = max(
            matched["members"],
            key=lambda entry: (
                _number(entry.get("metrics", {}).get("ordersDelta")) or 0,
                len(str(entry.get("text") or "")),
            ),
        )
        matched["text"] = str(representative.get("text") or matched.get("text") or "")
    for group in groups:
        representative = max(
            group["members"],
            key=lambda entry: (
                _number(entry.get("metrics", {}).get("ordersDelta")) or 0,
                len(str(entry.get("text") or "")),
            ),
        )
        group["representative"] = representative
        group["text"] = str(representative.get("text") or group.get("text") or "")
        group["reason"] = str(
            representative.get("effectLabel") or group.get("reason") or ""
        )
        group["orders"] = round(float(group.get("orders") or 0), 4)
        group["gmv"] = round(
            sum(
                _number(entry.get("metrics", {}).get("gmvDelta")) or 0
                for entry in group["members"]
            ),
            2,
        )
        group["spend"] = round(
            sum(
                _number(entry.get("metrics", {}).get("spendDelta")) or 0
                for entry in group["members"]
            ),
            2,
        )
        online_rates = [
            _number(entry.get("metrics", {}).get("onlineRate"))
            for entry in group["members"]
            if _number(entry.get("metrics", {}).get("onlineRate")) is not None
        ]
        group["onlineRate"] = (
            round(sum(online_rates) / len(online_rates), 2)
            if online_rates
            else None
        )
        group["members"] = [
            {
                "text": str(entry.get("text") or ""),
                "clock": str(entry.get("clock") or phrase_clock(entry)),
                "ordersDelta": (
                    _number(entry.get("metrics", {}).get("ordersDelta")) or 0
                ),
            }
            for entry in group["members"]
        ]
    if mode == "low":
        groups.sort(
            key=lambda entry: (
                -int(entry.get("occurrences") or 0),
                entry.get("onlineRate") if entry.get("onlineRate") is not None else 0,
                -float(entry.get("spend") or 0),
            )
        )
    else:
        groups.sort(
            key=lambda entry: (
                -float(entry.get("orders") or 0),
                -float(entry.get("gmv") or 0),
            )
        )
    return groups


def build_review_session(
    directory: Path,
    manifest: dict[str, Any],
    history: dict[str, Any],
    archived: bool = False,
) -> dict[str, Any]:
    room_id = str(manifest.get("roomId") or "")
    day = str(manifest.get("date") or "")
    days = history.get("days") if isinstance(history, dict) else {}
    rooms = (days or {}).get(day, {}) if isinstance(days, dict) else {}
    raw_samples = rooms.get(room_id, []) if isinstance(rooms, dict) else []
    samples = [item for item in raw_samples if isinstance(item, dict)]
    start_ms: int | None = None
    try:
        start_ms = int(
            datetime.fromisoformat(
                str(manifest.get("startedAt") or "").replace("Z", "+00:00")
            ).timestamp()
            * 1000
        )
    except (TypeError, ValueError):
        start_ms = None
    if start_ms is not None:
        samples = [
            item
            for item in samples
            if int(_number(item.get("t")) or 0) >= start_ms
        ]
    samples.sort(key=lambda item: _number(item.get("t")) or 0)
    series: list[dict[str, Any]] = []
    for item in samples:
        sample_t = _floor_seconds(item.get("t"))
        series.append(
            {
                **copy.deepcopy(item),
                "time": max(0, round((sample_t - (start_ms or sample_t)) / 1000)),
            }
        )
    final = samples[-1] if samples else {}
    first = samples[0] if samples else {}
    started_at = str(manifest.get("startedAt") or "")
    ended_at = str(manifest.get("endedAt") or "")
    try:
        start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        start_dt = datetime.now().astimezone()
    try:
        end_dt = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        end_dt = datetime.now().astimezone()
    duration = max(0, int((end_dt - start_dt).total_seconds()))
    if series:
        duration = max(duration, int(series[-1].get("time") or 0) + 300)
    time_buckets = build_15_minute_buckets(samples, start_ms)

    def cumulative(key: str) -> float | None:
        return _number(final.get(key))

    spend = cumulative("spend")
    gmv = cumulative("gmv")
    orders = cumulative("orders")
    watch = cumulative("watch")
    annotations: list[dict[str, Any]] = []
    for previous, current in zip(samples, samples[1:]):
        previous_time = _floor_seconds(previous.get("t"))
        current_time = _floor_seconds(current.get("t"))
        offset = max(0, round((current_time - (start_ms or current_time)) / 1000))
        spend_delta = (_number(current.get("spend")) or 0) - (
            _number(previous.get("spend")) or 0
        )
        gmv_delta = (_number(current.get("gmv")) or 0) - (
            _number(previous.get("gmv")) or 0
        )
        order_delta = (_number(current.get("orders")) or 0) - (
            _number(previous.get("orders")) or 0
        )
        watch_delta = (_number(current.get("watch")) or 0) - (
            _number(previous.get("watch")) or 0
        )
        online_now = _number(current.get("online"))
        online_before = _number(previous.get("online"))
        interval_roi = gmv_delta / spend_delta if spend_delta > 0 else None
        if spend_delta > 0 and order_delta <= 0:
            annotations.append(
                {
                    "id": f"{manifest.get('id')}-no-order-{offset}",
                    "time": offset,
                    "type": "problem",
                    "title": "有消耗但订单未增长",
                    "desc": (
                        f"该 5 分钟窗口消耗增加 ¥{spend_delta:.2f}，"
                        f"净成交订单增加 {order_delta:.0f}。"
                    ),
                }
            )
        elif spend_delta > 0 and interval_roi is not None and interval_roi < 0.56 * 0.7:
            annotations.append(
                {
                    "id": f"{manifest.get('id')}-low-roi-{offset}",
                    "time": offset,
                    "type": "problem",
                    "title": "窗口成交效率偏低",
                    "desc": (
                        f"该窗口增量 ROI {interval_roi:.2f}，低于参考线 0.56。"
                    ),
                }
            )
        elif spend_delta > 0 and interval_roi is not None and interval_roi >= 0.56 * 1.2:
            annotations.append(
                {
                    "id": f"{manifest.get('id')}-high-roi-{offset}",
                    "time": offset,
                    "type": "advantage",
                    "title": "窗口成交效率较好",
                    "desc": (
                        f"该窗口增量 ROI {interval_roi:.2f}，"
                        f"净成交 ¥{gmv_delta:.2f}。"
                    ),
                }
            )
        if (
            online_now is not None
            and online_before
            and online_now < online_before * 0.7
        ):
            annotations.append(
                {
                    "id": f"{manifest.get('id')}-online-drop-{offset}",
                    "time": offset,
                    "type": "problem",
                    "title": "实时在线明显回落",
                    "desc": (
                        f"在线人数由 {online_before:.0f} 降至 {online_now:.0f}，"
                        f"同期新增观看 {watch_delta:+.0f}。"
                    ),
                }
            )
    annotations = annotations[-8:]
    speech = analyze_speech(directory, series)
    for item in speech["good"][:4]:
        metrics = item.get("metrics") or {}
        annotations.append(
            {
                "id": item.get("id"),
                "time": _floor_seconds(
                    (
                        datetime.fromisoformat(
                            str(item.get("startedAt")).replace("Z", "+00:00")
                        ).timestamp()
                        * 1000
                    )
                    - (start_ms or 0)
                )
                / 1000,
                "type": "advantage",
                "clock": phrase_clock(item),
                "title": "话术对应窗口出单",
                "desc": (
                    f"「{item.get('text')}」对应窗口订单 +"
                    f"{_number(metrics.get('ordersDelta')) or 0:.0f}，"
                    f"成交 ¥{_number(metrics.get('gmvDelta')) or 0:.2f}。"
                ),
                "source": "local_whisper",
            }
        )
    for item in speech["bad"][:4]:
        metrics = item.get("metrics") or {}
        annotations.append(
            {
                "id": item.get("id"),
                "time": _floor_seconds(
                    (
                        datetime.fromisoformat(
                            str(item.get("startedAt")).replace("Z", "+00:00")
                        ).timestamp()
                        * 1000
                    )
                    - (start_ms or 0)
                )
                / 1000,
                "type": "problem",
                "clock": phrase_clock(item),
                "title": "话术对应窗口掉人",
                "desc": (
                    f"「{item.get('text')}」对应窗口在线 "
                    f"{_number(metrics.get('onlineDelta')) or 0:+.0f}，"
                    f"订单 +{_number(metrics.get('ordersDelta')) or 0:.0f}。"
                ),
                "source": "local_whisper",
            }
        )
    annotations = sorted(annotations, key=lambda item: item.get("time") or 0)[-12:]
    problem_count = sum(item["type"] == "problem" for item in annotations)
    advantage_count = sum(item["type"] == "advantage" for item in annotations)
    roi = gmv / spend if spend and gmv is not None else None
    cvr = orders / watch * 100 if watch and orders is not None else None
    summary = (
        f"本场复盘已归档，读取千川直播大屏 {len(samples)} 个 5 分钟节点。"
        f"累计消耗 ¥{(spend or 0):.2f}、净成交 ¥{(gmv or 0):.2f}、"
        f"净成交订单 {(orders or 0):.0f}、净成交ROI "
        f"{roi:.2f}。" if roi is not None else
        f"本场复盘已归档，读取千川直播大屏 {len(samples)} 个 5 分钟节点；"
        "消耗、成交或订单尚未返回，暂不计算 ROI。"
    )
    if annotations:
        summary += (
            f" 本地分析识别 {problem_count} 个问题窗口、"
            f"{advantage_count} 个优势窗口。"
        )
    else:
        summary += " 当前样本未触发问题/优势阈值。"
    if speech["available"]:
        summary += " 话术明细已按长句和时间在复盘结论中逐条列出。"
    if archived:
        files = {
            "playlistUrl": "",
            "videoUrl": "",
            "hlsUrl": "",
            "segmentCount": 0,
            "sizeBytes": 0,
        }
    else:
        files = public_recording_files(directory, directory.parent)
    return {
        "id": str(manifest.get("id") or directory.name),
        "accountId": str(manifest.get("accountId") or "fashion"),
        "roomId": room_id,
        "date": day,
        "title": str(
            manifest.get("title")
            or f"{manifest.get('awemeName') or '直播'} · 整场录像"
        ),
        "startTime": start_dt.astimezone().strftime("%H:%M"),
        "startedAt": start_dt.astimezone().isoformat(timespec="seconds"),
        "endedAt": end_dt.astimezone().isoformat(timespec="seconds"),
        "durationSeconds": duration,
        "recordingStatus": str(manifest.get("status") or "completed"),
        "recordingStatusLabel": (
            "录制中"
            if manifest.get("status") == "recording"
            else "录像已过期 · 分析保留"
            if archived
            else "已录制"
        ),
        "videoUrl": (
            files["hlsUrl"]
            if manifest.get("status") == "recording"
            else files["videoUrl"] or files["hlsUrl"]
        ),
        "videoType": (
            (
                "hls"
                if manifest.get("status") == "recording" or not files["videoUrl"]
                else "mp4"
            )
            if files["videoUrl"] or files["hlsUrl"]
            else ""
        ),
        "hlsUrl": files["hlsUrl"],
        "segmentCount": files["segmentCount"],
        "sizeBytes": files["sizeBytes"],
        "videoExpired": archived,
        "metrics": {
            "viewers": watch,
            "watchCount": watch,
            "spend": spend,
            "gmv": gmv,
            "orders": orders,
            "roi": roi,
            "cvr": cvr,
            "firstSpend": _number(first.get("spend")),
            "firstOrders": _number(first.get("orders")),
        },
        "series": series,
        "timeBuckets": time_buckets,
        "timeBucketGranularityMinutes": 15,
        "timeBucketSource": "qianchuan_live_screen_5m_to_15m",
        "timeBucketSourceLabel": "千川直播大屏 5 分钟历史聚合为 15 分钟",
        "mcpTimeSeriesAvailable": False,
        "annotations": annotations,
        "transcript": speech,
        "speakerMap": _load_speaker_map(directory),
        "summary": summary,
        "analysisSteps": [
            f"读取本地录像清单：{files['segmentCount']} 个视频分段",
            f"聚合千川直播大屏 5 分钟历史：{len(samples)} 个节点",
            "按增量 ROI、有消耗无订单和在线人数回落规则生成问题/优势窗口",
            (
                f"读取本地 Whisper 转写：{len(speech['phrases'])} 句，"
                "与约 5 秒在线/成交采样对齐"
                if speech["available"]
                else "话术：本地 Whisper 尚未产出该场转写"
            ),
        ],
        "dataSources": [
            "视频：本地临时录制，复盘归档后删除",
            "交易/流量：千川直播大屏 5 分钟历史",
            "分析：本地规则引擎",
            (
                f"话术：本地 {speech['engine']} 转写与指标对齐"
                if speech["available"]
                else "话术：本地 Whisper 尚未产出"
            ),
        ],
        "sourceNote": (
            "数据来源：本地临时录像转写归档 + 千川直播大屏历史；"
            + (
                "话术来自本地 Whisper，出单/掉人为时间窗口关联而非因果证明。"
                if speech["available"]
                else "本地 Whisper 尚未产出话术。"
            )
        ),
        "persona": {
            "viewer": {"age": "未接入", "region": "未接入", "gender": "未接入"},
            "buyer": {"age": "未接入", "region": "未接入", "gender": "未接入"},
        },
    }


def load_archived_recording_sessions(
    history: dict[str, Any],
    account_id: str | None,
    archive_sessions_dir: Path = REVIEW_ARCHIVE_SESSIONS_DIR,
    day: str | None = None,
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for directory, manifest in list_archived_manifests(archive_sessions_dir):
        if account_id and str(manifest.get("accountId")) != str(account_id):
            continue
        if day and str(manifest.get("date") or "") != str(day):
            continue
        sessions.append(
            build_review_session(
                directory,
                manifest,
                history,
                archived=True,
            )
        )
    return sessions


def available_review_dates(
    account_id: str | None = None,
    recordings_dir: Path = RECORDINGS_DIR,
    archive_dir: Path = REVIEW_ARCHIVE_DIR,
) -> list[str]:
    dates: set[str] = set()
    for _, manifest in list_manifests(recordings_dir):
        if account_id and str(manifest.get("accountId")) != str(account_id):
            continue
        day = str(manifest.get("date") or "").strip()
        if day:
            dates.add(day)
    if archive_dir.is_dir():
        for path in archive_dir.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(value, dict):
                continue
            if account_id and str(value.get("accountId")) != str(account_id):
                continue
            day = str(value.get("date") or "").strip()
            if day:
                dates.add(day)
    return sorted(dates)


def has_daily_recording(
    account_id: str | None,
    day: str,
    recordings_dir: Path = RECORDINGS_DIR,
) -> bool:
    for directory, manifest in list_manifests(recordings_dir):
        if account_id and str(manifest.get("accountId")) != str(account_id):
            continue
        if str(manifest.get("date") or "") != str(day):
            continue
        if any(
            item.is_file() and item.stat().st_size > 0
            for item in (directory / "segments").glob("part_*.ts")
        ):
            return True
        session_mp4 = directory / "session.mp4"
        if session_mp4.is_file() and session_mp4.stat().st_size > 1024:
            return True
    return False


def review_sessions(
    history: dict[str, Any],
    account_id: str | None = None,
    recordings_dir: Path = RECORDINGS_DIR,
    archive_dir: Path = REVIEW_ARCHIVE_DIR,
    day: str | None = None,
) -> list[dict[str, Any]]:
    sessions = []
    live_ids: set[str] = set()
    for directory, manifest in list_manifests(recordings_dir):
        if account_id and str(manifest.get("accountId")) != str(account_id):
            continue
        if day and str(manifest.get("date") or "") != str(day):
            continue
        segment_files = [
            item
            for item in (directory / "segments").glob("part_*")
            if item.is_file()
            and item.stat().st_size > 0
            and item.suffix.lower() in {".ts", ".wav", ".flac"}
        ]
        has_segments = any(item.suffix.lower() == ".ts" for item in segment_files)
        has_audio_capture = any(
            item.suffix.lower() in {".wav", ".flac"} for item in segment_files
        )
        if not (
            (has_segments and (directory / "index.m3u8").is_file())
            or ((directory / "session.mp4").is_file()
                and (directory / "session.mp4").stat().st_size > 1024)
            or has_audio_capture
        ):
            continue
        session = build_review_session(directory, manifest, history)
        live_ids.add(str(session.get("id") or ""))
        sessions.append(session)
    for archived in load_archived_recording_sessions(
        history,
        account_id,
        archive_dir / "sessions",
        day,
    ):
        if str(archived.get("id") or "") in live_ids:
            continue
        sessions.append(archived)
    sessions.sort(key=lambda item: (item.get("date", ""), item.get("startTime", "")), reverse=True)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for session in sessions:
        key = (str(session.get("accountId") or ""), str(session.get("date") or ""))
        grouped.setdefault(key, []).append(session)
    daily_sessions = [
        aggregate_daily_session(items)
        for _, items in sorted(grouped.items(), reverse=True)
    ]
    daily_sessions.sort(key=lambda item: item.get("date", ""), reverse=True)
    for index, session in enumerate(daily_sessions):
        prior = daily_sessions[index + 1 : index + 4]
        rhythms = [
            item.get("realOrderRhythm")
            for item in prior
            if isinstance(item.get("realOrderRhythm"), list)
        ]
        if rhythms:
            session["historyRhythm"] = [
                round(sum(values[i] for values in rhythms) / len(rhythms), 2)
                for i in range(len(rhythms[0]))
            ]
    archive_daily_sessions(daily_sessions, archive_dir)
    current_keys = {
        (str(item.get("accountId") or ""), str(item.get("date") or ""))
        for item in daily_sessions
    }
    for archived in load_archived_daily_sessions(account_id, archive_dir, day=day):
        key = (
            str(archived.get("accountId") or ""),
            str(archived.get("date") or ""),
        )
        if key not in current_keys:
            daily_sessions.append(archived)
    daily_sessions.sort(key=lambda item: item.get("date", ""), reverse=True)
    return daily_sessions


def aggregate_daily_session(items: list[dict[str, Any]]) -> dict[str, Any]:
    items = sorted(
        items,
        key=lambda item: (str(item.get("date") or ""), str(item.get("startTime") or "")),
    )
    if len(items) == 1:
        session = copy.deepcopy(items[0])
        session["recordingParts"] = [
            {
                "id": session.get("id"),
                "startTime": session.get("startTime"),
                "durationSeconds": session.get("durationSeconds"),
                "videoUrl": session.get("videoUrl"),
                "videoType": session.get("videoType"),
                "segmentCount": session.get("segmentCount"),
            }
        ]
        return session
    account_id = str(items[0].get("accountId") or "")
    day = str(items[0].get("date") or "")
    start_epochs: list[int] = []
    for item in items:
        try:
            start_epochs.append(
                int(
                    datetime.fromisoformat(
                        str(item.get("startedAt") or "").replace("Z", "+00:00")
                    ).timestamp()
                    * 1000
                )
            )
        except (TypeError, ValueError):
            try:
                fallback_start = datetime.fromisoformat(
                    f"{str(item.get('date') or day)}T"
                    f"{str(item.get('startTime') or '00:00')}:00"
                ).astimezone()
                start_epochs.append(int(fallback_start.timestamp() * 1000))
            except (TypeError, ValueError):
                start_epochs.append(0)
    day_start_ms = min((value for value in start_epochs if value), default=0)
    combined_series: list[dict[str, Any]] = []
    for item, start_epoch in zip(items, start_epochs):
        for point in item.get("series") or []:
            absolute = _number(point.get("t")) or start_epoch + (
                (_number(point.get("time")) or 0) * 1000
            )
            combined_series.append(
                {
                    **copy.deepcopy(point),
                    "t": int(absolute),
                    "time": max(0, round((absolute - day_start_ms) / 1000)),
                }
            )
    combined_series.sort(key=lambda point: _number(point.get("t")) or 0)
    deduped_series: list[dict[str, Any]] = []
    for point in combined_series:
        if deduped_series and point["t"] == deduped_series[-1]["t"]:
            deduped_series[-1] = point
        else:
            deduped_series.append(point)
    combined_series = deduped_series
    bucket_map: dict[str, dict[str, Any]] = {}
    for item in items:
        for bucket in item.get("timeBuckets") or []:
            label = str(bucket.get("label") or "")
            if not label:
                continue
            current = bucket_map.get(label)
            if current is None:
                bucket_map[label] = copy.deepcopy(bucket)
                continue
            for field in ("exposure", "watch", "productClicks", "orders", "spend", "gmv"):
                previous_value = _number(current.get(field))
                next_value = _number(bucket.get(field))
                if next_value is not None:
                    current[field] = max(previous_value or 0, next_value)
    time_buckets = sorted(
        bucket_map.values(),
        key=lambda item: str(item.get("start") or ""),
    )
    phrases: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    analysis_steps: list[str] = []
    data_sources: list[str] = []
    for item, start_epoch in zip(items, start_epochs):
        for phrase in (item.get("transcript") or {}).get("phrases") or []:
            try:
                phrase_start = int(
                    datetime.fromisoformat(
                        str(phrase.get("startedAt") or "").replace("Z", "+00:00")
                    ).timestamp()
                    * 1000
                )
            except (TypeError, ValueError):
                phrase_start = start_epoch + (
                    (_number(phrase.get("startSeconds")) or 0) * 1000
                )
            try:
                phrase_end = int(
                    datetime.fromisoformat(
                        str(phrase.get("endedAt") or "").replace("Z", "+00:00")
                    ).timestamp()
                    * 1000
                )
            except (TypeError, ValueError):
                phrase_end = start_epoch + (
                    (_number(phrase.get("endSeconds")) or 0) * 1000
                )
            phrases.append(
                {
                    **copy.deepcopy(phrase),
                    "startSeconds": max(0, (phrase_start - day_start_ms) / 1000),
                    "endSeconds": max(0, (phrase_end - day_start_ms) / 1000),
                }
            )
        for annotation in item.get("annotations") or []:
            annotations.append(
                {
                    **copy.deepcopy(annotation),
                    "time": max(
                        0,
                        ((start_epoch - day_start_ms) / 1000)
                        + (_number(annotation.get("time")) or 0),
                    ),
                }
            )
        analysis_steps.extend(item.get("analysisSteps") or [])
        data_sources.extend(item.get("dataSources") or [])
    phrases.sort(key=lambda item: _number(item.get("startSeconds")) or 0)
    good = [
        item for item in phrases if item.get("effect") == "good"
    ]
    bad = [
        item for item in phrases if item.get("effect") == "bad"
    ]
    good.sort(
        key=lambda item: (
            _number(item.get("metrics", {}).get("ordersDelta")) or 0,
            _number(item.get("scriptScore")) or 0,
        ),
        reverse=True,
    )
    bad.sort(
        key=lambda item: _number(item.get("metrics", {}).get("onlineRate")) or 0
    )
    top_orders = [
        item for item in good
        if (_number(item.get("metrics", {}).get("ordersDelta")) or 0) > 0
    ]
    top_orders.sort(
        key=lambda item: (
            _number(item.get("metrics", {}).get("ordersDelta")) or 0,
            _number(item.get("metrics", {}).get("gmvDelta")) or 0,
        ),
        reverse=True,
    )
    top_orders = top_orders[:5]
    synthetic_segments = [
        {
            "text": item.get("text"),
            "speaker": item.get("speaker"),
            "startSeconds": item.get("startSeconds"),
            "endSeconds": item.get("endSeconds"),
        }
        for item in phrases
        if isinstance(item, dict) and item.get("text")
    ]
    aggregated_speaker_profiles = speaker_profile.apply_speaker_map(
        speaker_profile.attach_speaker_metrics(
            speaker_profile.build_speaker_profiles(
                {"segments": synthetic_segments}
            ),
            phrases,
        ),
        {},
    )
    latest = max(
        items,
        key=lambda item: (
            _number(item.get("metrics", {}).get("orders")) or 0,
            _number(item.get("metrics", {}).get("gmv")) or 0,
        ),
    )
    start_datetimes: list[datetime] = []
    end_datetimes: list[datetime] = []
    for item in items:
        for key, target in (
            ("startedAt", start_datetimes),
            ("endedAt", end_datetimes),
        ):
            try:
                target.append(
                    datetime.fromisoformat(
                        str(item.get(key) or "").replace("Z", "+00:00")
                    )
                )
            except (TypeError, ValueError):
                continue
    duration = 0
    if start_datetimes and end_datetimes:
        duration = max(
            0,
            round((max(end_datetimes) - min(start_datetimes)).total_seconds()),
        )
    if duration <= 0:
        duration = round(
            max((_number(point.get("time")) or 0 for point in combined_series), default=0)
            + 300
        )
    parts = [
        {
            "id": item.get("id"),
            "startTime": item.get("startTime"),
            "durationSeconds": item.get("durationSeconds"),
            "videoUrl": item.get("videoUrl"),
            "videoType": item.get("videoType"),
            "segmentCount": item.get("segmentCount"),
            "recordingStatus": item.get("recordingStatus"),
        }
        for item in items
    ]
    speech_summary = ""
    if phrases:
        try:
            base_hour, base_minute = [
                int(part) for part in str(items[0].get("startTime") or "00:00").split(":")[:2]
            ]
        except (TypeError, ValueError):
            base_hour, base_minute = 0, 0

        def daily_clock(item: dict[str, Any]) -> str:
            total = (
                base_hour * 3600
                + base_minute * 60
                + int(_number(item.get("startSeconds")) or 0)
            )
            return (
                f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"
            )

        good_summary = "；".join(
            f"「{item.get('text')}」{item.get('effectLabel')} "
            f"({daily_clock(item)} · 订单 +{_number(item.get('metrics', {}).get('ordersDelta')) or 0:.0f})"
            for item in good[:5]
        ) or "暂无明确出单/留人话术"
        bad_summary = "；".join(
            f"「{item.get('text')}」{item.get('effectLabel')} "
            f"({daily_clock(item)} · 在线 {_number(item.get('metrics', {}).get('onlineDelta')) or 0:+.0f})"
            for item in bad[:5]
        ) or "暂无明确掉人话术"
        speech_summary = f"效果较好：{good_summary}。效果较差：{bad_summary}。"
    return {
        **copy.deepcopy(latest),
        "id": f"daily-{account_id}-{day}",
        "accountId": account_id,
        "date": day,
        "title": f"{day} · 全天直播复盘",
        "startTime": items[0].get("startTime"),
        "startedAt": items[0].get("startedAt"),
        "endedAt": items[-1].get("endedAt"),
        "durationSeconds": duration,
        "recordingStatus": (
            "recording"
            if any(item.get("recordingStatus") == "recording" for item in items)
            else "completed"
        ),
        "recordingParts": parts,
        "videoUrl": "",
        "videoType": "daily_hls",
        "videoExpired": False,
        "series": combined_series,
        "timeBuckets": time_buckets,
        "timeBucketGranularityMinutes": 15,
        "timeBucketSource": "qianchuan_live_screen_5m_to_15m",
        "timeBucketSourceLabel": "千川直播大屏 5 分钟历史聚合为 15 分钟",
        "mcpTimeSeriesAvailable": False,
        "transcript": {
            **(latest.get("transcript") or {}),
            "available": bool(phrases),
            "phrases": phrases,
            "good": good[:8],
            "bad": bad[:8],
            "topOrders": top_orders,
            "speakerProfiles": aggregated_speaker_profiles,
            "summary": speech_summary or "全天暂无可用话术转写。",
        },
        "annotations": sorted(
            annotations,
            key=lambda item: _number(item.get("time")) or 0,
        )[:20],
        "summary": (
            f"全天共合并 {len(items)} 段录像，累计时长约 {duration / 3600:.1f} 小时。"
            + (
                f" 最新累计净成交 ¥{(_number(latest.get('metrics', {}).get('gmv')) or 0):.2f}、"
                f"订单 {(_number(latest.get('metrics', {}).get('orders')) or 0):.0f}。"
                if latest.get("metrics")
                else " 交易指标尚未返回。"
            )
            + (
                " 话术明细已按长句、时间和对应效果逐条列出。"
                if speech_summary
                else " 当日暂无可用于复盘的 Whisper 长句。"
            )
        ),
        "analysisSteps": list(dict.fromkeys(
            analysis_steps
            + [f"合并当日 {len(items)} 段录像为全天复盘"]
        )),
        "dataSources": list(dict.fromkeys(data_sources)),
        "sourceNote": (
            "数据来源：全天临时录像的 Whisper 转写归档 + 千川直播大屏历史；"
            "出单/掉人为时间窗口关联，不是因果证明。"
        ),
    }


def _duration_label(seconds: Any) -> str:
    total = max(0, int(_number(seconds) or 0))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours} 小时 {minutes} 分"
    if minutes:
        return f"{minutes} 分 {secs} 秒"
    return f"{secs} 秒"


def review_markdown(session: dict[str, Any]) -> str:
    """Generate a durable, human-readable review document from review JSON."""
    metrics = session.get("metrics") if isinstance(session.get("metrics"), dict) else {}
    transcript = (
        session.get("transcript")
        if isinstance(session.get("transcript"), dict)
        else {}
    )
    lines = [
        f"# {session.get('title') or '直播复盘'}",
        "",
        f"- 日期：{session.get('date') or '未记录'}",
        f"- 场次：{session.get('startTime') or '--:--'} - {session.get('endedAt') or '--'}",
        f"- 时长：{_duration_label(session.get('durationSeconds'))}",
        f"- 录像状态：{session.get('recordingStatusLabel') or session.get('recordingStatus') or '已归档'}",
        "",
        "## 核心指标",
        "",
        f"- 消耗：¥{_number(metrics.get('spend')) or 0:.2f}",
        f"- 净成交：¥{_number(metrics.get('gmv')) or 0:.2f}",
        f"- 净成交订单：{_number(metrics.get('orders')) or 0:.0f}",
        f"- 净成交 ROI：{_number(metrics.get('roi')) or 0:.2f}",
        f"- 累计观看：{_number(metrics.get('watchCount')) or 0:.0f}",
        "",
        "## 复盘结论",
        "",
        str(session.get("summary") or "暂无复盘结论。"),
        "",
    ]
    annotations = [
        item
        for item in session.get("annotations") or []
        if isinstance(item, dict)
    ]
    if annotations:
        lines.extend(["## 问题与优势窗口", ""])
        for item in annotations:
            offset = max(0, int(_number(item.get("time")) or 0))
            clock = f"{offset // 3600:02d}:{offset % 3600 // 60:02d}:{offset % 60:02d}"
            kind = "问题" if item.get("type") == "problem" else "优势"
            lines.append(
                f"- {clock} · {kind} · {item.get('title') or ''}："
                f"{item.get('desc') or ''}"
            )
        lines.append("")
    phrases = [
        item
        for item in transcript.get("phrases") or []
        if isinstance(item, dict)
    ]
    if phrases:
        lines.extend(["## 话术明细", ""])
        for item in phrases[:100]:
            clock = phrase_clock(item)
            effect = str(item.get("effectLabel") or "未归因")
            lines.append(f"- {clock} · {effect}：{item.get('text') or ''}")
        if len(phrases) > 100:
            lines.append(f"- 其余 {len(phrases) - 100} 条话术请查看同目录 review.json。")
        lines.append("")
    sources = [
        str(item)
        for item in session.get("dataSources") or []
        if str(item).strip()
    ]
    if sources:
        lines.extend(["## 数据来源", ""])
        lines.extend(f"- {item}" for item in sources)
        lines.append("")
    lines.extend(
        [
            "## 归档说明",
            "",
            "本复盘文档在原始录像完成后由后台自动生成。复盘文档和结构化 JSON 永久保留；"
            "原始录像在分析归档成功后立即删除，不再提供视频回放。",
            "",
        ]
    )
    return "\n".join(lines)


def archive_session_review(
    directory: Path,
    manifest: dict[str, Any],
    session: dict[str, Any],
    archive_sessions_dir: Path = REVIEW_ARCHIVE_SESSIONS_DIR,
) -> Path:
    session_id = safe_component(
        manifest.get("id") or directory.name,
        directory.name,
    )
    target = archive_sessions_dir / session_id
    target.mkdir(parents=True, exist_ok=True)
    archived_session = copy.deepcopy(session)
    archived_session["videoUrl"] = ""
    archived_session["videoType"] = ""
    archived_session["hlsUrl"] = ""
    archived_session["segmentCount"] = 0
    archived_session["sizeBytes"] = 0
    archived_session["videoExpired"] = True
    archived_session["recordingStatus"] = "archived_analysis"
    archived_session["recordingStatusLabel"] = "分析已归档 · 原始录像已删除"
    archived_session["analysisArchivedAt"] = now_iso()
    atomic_write_json(target / "review.json", archived_session)
    (target / "review.md").write_text(
        review_markdown(archived_session),
        encoding="utf-8",
    )
    return target


def archive_daily_sessions(
    sessions: list[dict[str, Any]],
    archive_dir: Path = REVIEW_ARCHIVE_DIR,
) -> None:
    for session in sessions:
        account_id = safe_component(session.get("accountId"), "account")
        day = str(session.get("date") or "")
        if not day:
            continue
        archive = copy.deepcopy(session)
        archive["videoUrl"] = ""
        archive["videoType"] = ""
        archive["videoExpired"] = True
        archive["recordingStatus"] = "archived_analysis"
        archive["recordingStatusLabel"] = "分析已归档 · 原始录像已删除"
        stem = f"{account_id}_{day}"
        atomic_write_json(archive_dir / f"{stem}.json", archive)
        (archive_dir / f"{stem}.md").write_text(
            review_markdown(archive),
            encoding="utf-8",
        )


def load_archived_daily_sessions(
    account_id: str | None,
    archive_dir: Path = REVIEW_ARCHIVE_DIR,
    day: str | None = None,
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    if not archive_dir.is_dir():
        return sessions
    for path in sorted(archive_dir.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        if account_id and str(value.get("accountId")) != str(account_id):
            continue
        if day and str(value.get("date") or "") != str(day):
            continue
        sessions.append(value)
    return sessions


def _persona_from_profile(
    profile: dict[str, Any] | None,
    captured_at: str,
    distance_seconds: float | None,
) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {
            "available": False,
            "age": "未采集",
            "region": "未采集",
            "gender": "未采集",
            "source": "buyin_compass_live_screen_dom",
            "sourceLabel": "巨量百应直播大屏·专业版 · 用户画像",
            "capturedAt": captured_at,
            "distanceSeconds": distance_seconds,
            "unavailableReason": "该时间点附近没有对应的百应画像",
        }
    age = profile.get("age") if isinstance(profile.get("age"), dict) else {}
    region = profile.get("region") if isinstance(profile.get("region"), dict) else {}
    gender = profile.get("gender") if isinstance(profile.get("gender"), dict) else {}
    available = bool(profile.get("available")) and any(
        str(value.get("top") or "").strip()
        for value in (age, region, gender)
    )
    return {
        "available": available,
        "label": str(profile.get("label") or ""),
        "age": str(age.get("top") or "未采集"),
        "ageDistribution": copy.deepcopy(age.get("distribution") or []),
        "region": str(region.get("top") or "未采集"),
        "regionDistribution": copy.deepcopy(region.get("distribution") or []),
        "gender": str(gender.get("top") or "未采集"),
        "genderDistribution": copy.deepcopy(gender.get("distribution") or []),
        "summary": str(profile.get("summary") or ""),
        "source": "buyin_compass_live_screen_dom",
        "sourceLabel": str(
            profile.get("sourceLabel")
            or "巨量百应直播大屏·专业版 · 用户画像"
        ),
        "capturedAt": captured_at,
        "distanceSeconds": distance_seconds,
        "unavailableReason": str(profile.get("unavailableReason") or ""),
    }


def attach_buyin_audience(
    sessions: list[dict[str, Any]],
    audience_history: dict[str, Any],
    max_delta_seconds: int = 600,
) -> int:
    raw_items = (
        audience_history.get("items")
        if isinstance(audience_history, dict)
        else []
    )
    snapshots = [
        item
        for item in (raw_items if isinstance(raw_items, list) else [])
        if isinstance(item, dict)
        and _number(item.get("t")) is not None
        and str(item.get("roomId") or "").strip()
    ]
    by_room: dict[str, list[dict[str, Any]]] = {}
    for item in snapshots:
        by_room.setdefault(str(item.get("roomId")), []).append(item)
    for items in by_room.values():
        items.sort(key=lambda item: _number(item.get("t")) or 0)
    matched = 0
    for session in sessions:
        room_id = str(session.get("roomId") or "").strip()
        room_snapshots = by_room.get(room_id, [])
        timestamps = [_number(item.get("t")) or 0 for item in room_snapshots]
        matched_session_points = 0
        for point in session.get("series") or []:
            timestamp = _number(point.get("t"))
            if timestamp is None or not room_snapshots:
                continue
            index = bisect.bisect_left(timestamps, timestamp)
            candidates = [
                room_snapshots[pos]
                for pos in (index - 1, index)
                if 0 <= pos < len(room_snapshots)
            ]
            nearest = min(
                candidates,
                key=lambda item: abs((_number(item.get("t")) or 0) - timestamp),
            )
            distance_seconds = abs(
                ((_number(nearest.get("t")) or 0) - timestamp) / 1000
            )
            if distance_seconds > max_delta_seconds:
                continue
            profiles = (
                nearest.get("profiles")
                if isinstance(nearest.get("profiles"), dict)
                else {}
            )
            viewer = (
                profiles.get("realtimeViewer")
                or profiles.get("fullViewer")
            )
            buyer = (
                profiles.get("recentBuyer")
                or profiles.get("fullBuyer")
            )
            captured_at = str(nearest.get("capturedAt") or "")
            point["viewerPersona"] = _persona_from_profile(
                viewer,
                captured_at,
                round(distance_seconds, 2),
            )
            point["buyerPersona"] = _persona_from_profile(
                buyer,
                captured_at,
                round(distance_seconds, 2),
            )
            matched_session_points += 1
            if point["viewerPersona"]["available"] or point["buyerPersona"]["available"]:
                matched += 1
        if room_snapshots:
            session["buyinAudienceSnapshotCount"] = len(room_snapshots)
            session["buyinAudienceMatchedPoints"] = matched_session_points
            session["buyinAudienceSource"] = "buyin_compass_live_screen_dom"
            session["buyinAudienceSourceLabel"] = "巨量百应直播大屏·专业版 · 用户画像"
    return matched


def review_overview_summary(session: dict[str, Any]) -> str:
    metrics = session.get("metrics") if isinstance(session.get("metrics"), dict) else {}
    transcript = (
        session.get("transcript")
        if isinstance(session.get("transcript"), dict)
        else {}
    )
    parts = session.get("recordingParts")
    part_count = len(parts) if isinstance(parts, list) else 1
    duration_hours = (_number(session.get("durationSeconds")) or 0) / 3600
    gmv = _number(metrics.get("gmv"))
    orders = _number(metrics.get("orders"))
    roi = _number(metrics.get("roi"))
    data_text = (
        f"净成交 ¥{gmv:.2f}、净成交订单 {orders:.0f}、净成交 ROI {roi:.2f}。"
        if gmv is not None and orders is not None and roi is not None
        else "交易指标尚未完整返回，暂不计算缺失值。"
    )
    good_count = len(transcript.get("good") or [])
    bad_count = len(transcript.get("bad") or [])
    speech_text = (
        f"Whisper 识别到 {good_count} 段对应出单或留人的长句、"
        f"{bad_count} 段对应掉人的长句，明细见下方逐条话术复盘。"
        if transcript.get("available")
        else "本场暂无可用 Whisper 长句，话术明细不补造。"
    )
    return (
        f"本场共合并 {part_count} 段录像，累计约 {duration_hours:.1f} 小时；"
        f"{data_text}{speech_text}"
    )


def media_duration(path: Path) -> float:
    try:
        import av

        with av.open(str(path)) as container:
            if container.duration:
                return max(0.0, float(container.duration / av.time_base))
    except Exception:
        pass
    return 300.0


def daily_playlist(
    account_id: str,
    day: str,
    recordings_dir: Path = RECORDINGS_DIR,
) -> str:
    manifests = [
        (directory, manifest)
        for directory, manifest in list_manifests(recordings_dir)
        if str(manifest.get("accountId") or "") == str(account_id)
        and str(manifest.get("date") or "") == str(day)
    ]
    manifests.sort(key=lambda item: str(item[1].get("startedAt") or ""))
    entries: list[tuple[Path, str, float, bool]] = []
    active = False
    for directory, manifest in manifests:
        segments = [
            item
            for item in sorted((directory / "segments").glob("part_*.ts"))
            if item.is_file() and item.stat().st_size > 0
        ]
        is_active = str(manifest.get("status") or "") == "recording"
        active = active or is_active
        if is_active and segments:
            segments = segments[:-1]
        relative = directory.resolve().relative_to(recordings_dir.resolve()).as_posix()
        for index, segment in enumerate(segments):
            entries.append(
                (
                    segment,
                    f"/recordings/{relative}/segments/{segment.name}",
                    media_duration(segment),
                    index == 0,
                )
            )
    if not entries:
        return ""
    target = max(300, int(max(item[2] for item in entries) + 0.999))
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{target}",
        "#EXT-X-MEDIA-SEQUENCE:0",
    ]
    current_session = ""
    for segment, url, duration, first_in_session in entries:
        session = str(segment.parent.parent)
        if session != current_session:
            if current_session:
                lines.append("#EXT-X-DISCONTINUITY")
            current_session = session
        lines.extend([f"#EXTINF:{duration:.3f},", url])
    if not active:
        lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines) + "\n"
