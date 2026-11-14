from __future__ import annotations

import json
import os
import re
import uuid
import wave
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
VOICEPRINTS_DIR = DATA_DIR / "voiceprints"
INDEX_PATH = DATA_DIR / "voiceprints.json"

DEFAULT_THRESHOLD = 0.55
WINDOW_SECONDS = 3.0
HOP_SECONDS = 1.5
MIN_SAMPLES_SECONDS = 0.5
REFERENCE_SAMPLE_RATE = 16000


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_name(raw_name: str) -> str:
    value = re.sub(r"[\r\n\t]+", " ", str(raw_name or "")).strip()
    return value[:40]


def _embedding_model_path() -> Path | None:
    try:
        import speaker_diarization
    except Exception:
        return None
    return Path(speaker_diarization.EMBEDDING_MODEL)


def available() -> bool:
    """Whether the voiceprint embedding model is present on this machine."""
    model = _embedding_model_path()
    return bool(model and model.is_file())


def _load_index() -> dict[str, Any]:
    try:
        value = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_index(payload: dict[str, Any]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = INDEX_PATH.with_name(f"{INDEX_PATH.name}.{os.getpid()}.tmp")
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(INDEX_PATH)


def _npy_path(voiceprint_id: str) -> Path:
    return VOICEPRINTS_DIR / f"{voiceprint_id}.npy"


def _wav_path(voiceprint_id: str) -> Path:
    return VOICEPRINTS_DIR / f"{voiceprint_id}.wav"


def profiles() -> list[dict[str, Any]]:
    payload = _load_index()
    items = payload.get("profiles") if isinstance(payload.get("profiles"), list) else []
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        voiceprint_id = str(item.get("id") or "")
        result.append(
            {
                **item,
                "embeddingReady": bool(voiceprint_id and _npy_path(voiceprint_id).is_file()),
                "referenceReady": bool(voiceprint_id and _wav_path(voiceprint_id).is_file()),
            }
        )
    return result


def index_signature() -> str:
    try:
        stat = INDEX_PATH.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        return "missing"


def decode_audio_16k(path: Path) -> Any:
    """Decode an uploaded audio file to a float32 mono 16 kHz numpy array."""
    import av
    import numpy as np

    with av.open(str(path)) as container:
        if not container.streams.audio:
            raise ValueError("音频文件中没有可识别的音频轨道")
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=REFERENCE_SAMPLE_RATE)
        chunks: list[Any] = []
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().reshape(-1))
        for resampled in resampler.resample(None):
            chunks.append(resampled.to_ndarray().reshape(-1))
    if not chunks:
        raise ValueError("音频文件中没有可识别的音频轨道")
    return np.concatenate(chunks).astype(np.float32)


def embed_waveform(waveform: Any, sample_rate: int = REFERENCE_SAMPLE_RATE) -> Any | None:
    """Compute a robust L2-normalized speaker embedding for a longer utterance."""
    import numpy as np

    import speaker_diarization

    samples = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if samples.size < int(sample_rate * MIN_SAMPLES_SECONDS):
        return None
    extractor = speaker_diarization._embedding_extractor()
    window = max(1, int(sample_rate * WINDOW_SECONDS))
    hop = max(1, int(sample_rate * HOP_SECONDS))
    vectors: list[np.ndarray] = []
    if samples.size <= window:
        embedding = speaker_diarization.extract_embedding(extractor, samples, sample_rate)
        if embedding is not None:
            vectors.append(embedding)
    else:
        for start in range(0, max(1, samples.size - window + 1), hop):
            embedding = speaker_diarization.extract_embedding(
                extractor, samples[start : start + window], sample_rate
            )
            if embedding is not None:
                vectors.append(embedding)
    if not vectors:
        return None
    mean = np.mean(np.stack(vectors), axis=0).astype(np.float32)
    norm = float(np.linalg.norm(mean))
    if norm <= 0:
        return None
    return (mean / norm).astype(np.float32)


def _write_reference_wav(path: Path, waveform: Any, sample_rate: int = REFERENCE_SAMPLE_RATE) -> None:
    import numpy as np

    samples = np.asarray(waveform, dtype=np.float32).reshape(-1)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    VOICEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(pcm.tobytes())


def enroll(name: str, source_path: Path, source_filename: str = "") -> dict[str, Any]:
    import numpy as np

    name = _safe_name(name)
    if not name:
        raise ValueError("主播姓名不能为空")
    if not source_path.is_file():
        raise ValueError("标准录音文件不存在")
    waveform = decode_audio_16k(source_path)
    duration_seconds = round(float(waveform.size) / REFERENCE_SAMPLE_RATE, 2)
    if duration_seconds < 1.0:
        raise ValueError("标准录音过短，至少需要 1 秒有效语音")
    embedding = embed_waveform(waveform)
    if embedding is None:
        raise ValueError("无法从该录音中提取声纹，请使用更清晰、人声为主的一段录音")

    payload = _load_index()
    items = payload.get("profiles") if isinstance(payload.get("profiles"), list) else []
    items = [item for item in items if isinstance(item, dict)]
    existing = next(
        (item for item in items if str(item.get("name") or "") == name),
        None,
    )
    if existing is not None:
        voiceprint_id = str(existing.get("id") or uuid.uuid4().hex[:12])
    else:
        voiceprint_id = uuid.uuid4().hex[:12]

    VOICEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
    np.save(_npy_path(voiceprint_id), embedding, allow_pickle=False)
    _write_reference_wav(_wav_path(voiceprint_id), waveform)

    record = {
        "id": voiceprint_id,
        "name": name,
        "dim": int(embedding.size),
        "durationSeconds": duration_seconds,
        "sourceFilename": str(source_filename or source_path.name)[:160],
        "createdAt": existing.get("createdAt") if existing else _now_iso(),
        "updatedAt": _now_iso(),
        "threshold": DEFAULT_THRESHOLD,
    }
    if existing is not None:
        items = [record if item is existing else item for item in items]
    else:
        items.append(record)
    _save_index(
        {
            "version": 1,
            "threshold": DEFAULT_THRESHOLD,
            "embeddingModel": "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k",
            "profiles": items,
        }
    )
    return record


def delete(name: str) -> dict[str, Any] | None:
    name = _safe_name(name)
    if not name:
        raise ValueError("主播姓名不能为空")
    payload = _load_index()
    items = payload.get("profiles") if isinstance(payload.get("profiles"), list) else []
    items = [item for item in items if isinstance(item, dict)]
    target = next((item for item in items if str(item.get("name") or "") == name), None)
    if target is None:
        return None
    voiceprint_id = str(target.get("id") or "")
    remaining = [item for item in items if item is not target]
    payload["profiles"] = remaining
    _save_index(payload)
    if voiceprint_id:
        _npy_path(voiceprint_id).unlink(missing_ok=True)
        _wav_path(voiceprint_id).unlink(missing_ok=True)
    return target


def known_vectors() -> dict[str, Any]:
    import numpy as np

    result: dict[str, Any] = {}
    for item in profiles():
        if not item.get("embeddingReady"):
            continue
        try:
            vector = np.load(_npy_path(str(item.get("id") or "")), allow_pickle=False)
            vector = np.asarray(vector, dtype=np.float32).reshape(-1)
            if vector.size > 0:
                result[str(item.get("name") or "")] = vector
        except (OSError, ValueError):
            continue
    return result


def match_embedding(
    embedding: Any,
    threshold: float | None = None,
) -> dict[str, Any]:
    import numpy as np

    vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        return {"matched": False, "name": None, "similarity": None, "scores": []}
    vector = vector / norm
    threshold_value = float(threshold) if threshold is not None else float(
        _load_index().get("threshold") or DEFAULT_THRESHOLD
    )
    scores: list[dict[str, Any]] = []
    best_name: str | None = None
    best_similarity = -1.0
    for name, known in known_vectors().items():
        known = np.asarray(known, dtype=np.float32).reshape(-1)
        known_norm = float(np.linalg.norm(known))
        similarity = float(np.dot(vector, known)) / known_norm if known_norm > 0 else -1.0
        scores.append({"name": name, "similarity": round(similarity, 4)})
        if similarity > best_similarity:
            best_similarity = similarity
            best_name = name
    scores.sort(key=lambda item: item["similarity"], reverse=True)
    matched = bool(best_name and best_similarity >= threshold_value)
    return {
        "matched": matched,
        "name": best_name if matched else None,
        "similarity": round(best_similarity, 4) if best_name else None,
        "threshold": threshold_value,
        "scores": scores,
    }


def match_waveform(
    waveform: Any,
    threshold: float | None = None,
) -> dict[str, Any]:
    embedding = embed_waveform(waveform)
    if embedding is None:
        return {
            "matched": False,
            "name": None,
            "similarity": None,
            "scores": [],
            "error": "未能从音频中提取声纹",
        }
    return match_embedding(embedding, threshold)


def status() -> dict[str, Any]:
    items = profiles()
    names = sorted(str(item.get("name") or "") for item in items)
    return {
        "available": available(),
        "count": len(items),
        "names": names,
        "threshold": float(_load_index().get("threshold") or DEFAULT_THRESHOLD),
        "embeddingModel": "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k",
        "profiles": items,
        "error": "" if available() else "缺少 3dspeaker 声纹模型，请先安装说话人分离模型",
    }
