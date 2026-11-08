from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import recording_store


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEFAULT_HISTORY_PATH = DATA_DIR / "live-screen-history.json"
DEFAULT_AUDIENCE_HISTORY_PATH = DATA_DIR / "buyin-live-audience-history.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def transcription_is_complete(directory: Path, manifest: dict[str, Any]) -> bool:
    if str(manifest.get("status") or "") != "completed":
        return False
    segments = {
        item.stem
        for item in (directory / "segments").glob("part_*")
        if item.is_file() and item.stat().st_size > 0
        and item.suffix.lower() in {".ts", ".wav", ".flac"}
    }
    if not segments:
        return False
    transcript = read_json(directory / "asr" / "transcript.json")
    processed = {
        str(item)
        for item in transcript.get("processedParts") or []
        if str(item).strip()
    }
    if isinstance(transcript.get("segments"), list):
        processed.update(
            str(item.get("segmentId"))
            for item in transcript["segments"]
            if isinstance(item, dict) and item.get("segmentId")
        )
    return segments.issubset(processed)


def _find_recorded_session(
    daily_sessions: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    session_id = str(manifest.get("id") or "")
    for session in daily_sessions:
        if str(session.get("id") or "") == session_id:
            return session
        for part in session.get("recordingParts") or []:
            if isinstance(part, dict) and str(part.get("id") or "") == session_id:
                return session
    return {}


def finalize_completed_sessions(
    *,
    recordings_dir: Path = recording_store.RECORDINGS_DIR,
    archive_dir: Path = recording_store.REVIEW_ARCHIVE_DIR,
    history_path: Path = DEFAULT_HISTORY_PATH,
    audience_history_path: Path = DEFAULT_AUDIENCE_HISTORY_PATH,
    history: dict[str, Any] | None = None,
    audience_history: dict[str, Any] | None = None,
) -> list[str]:
    """Archive completed reviews, then remove their temporary raw recordings."""
    candidates = [
        (directory, manifest)
        for directory, manifest in reversed(
            recording_store.list_manifests(recordings_dir)
        )
        if transcription_is_complete(directory, manifest)
    ]
    if not candidates:
        return []
    history_value = history if isinstance(history, dict) else read_json(history_path)
    audience_value = (
        audience_history
        if isinstance(audience_history, dict)
        else read_json(audience_history_path)
    )
    recordings_root = recordings_dir.resolve()
    finalized: list[str] = []
    for directory, manifest in candidates:
        session = recording_store.build_review_session(
            directory,
            manifest,
            history_value,
        )
        recording_store.attach_buyin_audience([session], audience_value)
        session["summary"] = recording_store.review_overview_summary(session)
        account_id = str(manifest.get("accountId") or "fashion")
        day = str(manifest.get("date") or "")
        daily_sessions = recording_store.review_sessions(
            history_value,
            account_id=account_id,
            recordings_dir=recordings_dir,
            archive_dir=archive_dir,
            day=day,
        )
        recording_store.attach_buyin_audience(daily_sessions, audience_value)
        for daily in daily_sessions:
            daily["summary"] = recording_store.review_overview_summary(daily)
        recording_store.archive_daily_sessions(daily_sessions, archive_dir)
        target = recording_store.archive_session_review(
            directory,
            manifest,
            session,
            archive_dir / "sessions",
        )
        archived_manifest = read_json(target / "manifest.json")
        archived_manifest.update(
            {
                "status": "archived_analysis",
                "analysisArchivedAt": recording_store.now_iso(),
                "videoDeletedAt": recording_store.now_iso(),
                "videoPolicy": "analysis_first_then_delete",
                "reviewDocument": str(target / "review.md"),
                "structuredReview": str(target / "review.json"),
            }
        )
        recording_store.atomic_write_json(target / "manifest.json", archived_manifest)

        required = [
            target / "manifest.json",
            target / "review.json",
            target / "review.md",
            target / "asr" / "transcript.json",
            archive_dir
            / (
                f"{recording_store.safe_component(account_id, 'account')}_{day}.json"
            ),
            archive_dir
            / (
                f"{recording_store.safe_component(account_id, 'account')}_{day}.md"
            ),
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(
                "复盘文档未完整落盘，保留原始录像用于重试："
                + "、".join(missing)
            )

        resolved = directory.resolve()
        if resolved.parent != recordings_root:
            raise RuntimeError(f"拒绝删除录像目录之外的路径：{resolved}")
        shutil.rmtree(resolved)
        finalized.append(str(manifest.get("id") or directory.name))
    return finalized
