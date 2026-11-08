from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import numpy as np
import sherpa_onnx


ROOT = Path(__file__).resolve().parent
EXTERNAL_ROOT = Path(os.getenv("QIANCHUAN_EXTERNAL_ROOT", r"D:\AI投放产品"))
MODEL_DIR = EXTERNAL_ROOT / "models" / "speaker-diarization"
SEGMENTATION_MODEL = MODEL_DIR / "model.onnx"
EMBEDDING_MODEL = MODEL_DIR / "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"

_instance: "SpeakerDiarizer | None" = None
_instance_lock = threading.Lock()


def available() -> bool:
    return SEGMENTATION_MODEL.is_file() and EMBEDDING_MODEL.is_file()


class SpeakerDiarizer:
    """Offline speaker diarization backed by sherpa-onnx (pure CPU)."""

    def __init__(self, num_threads: int = 2, threshold: float = 0.7) -> None:
        if not available():
            raise RuntimeError(
                "说话人分离模型缺失，请先下载到 "
                f"{MODEL_DIR}（model.onnx + 3dspeaker 嵌入模型）"
            )
        config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                    model=str(SEGMENTATION_MODEL),
                ),
                num_threads=max(1, int(num_threads)),
                provider="cpu",
            ),
            embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=str(EMBEDDING_MODEL),
                num_threads=max(1, int(num_threads)),
                provider="cpu",
            ),
            clustering=sherpa_onnx.FastClusteringConfig(
                num_clusters=-1,
                threshold=max(0.0, min(1.0, float(threshold))),
                compute_confidence=True,
            ),
            min_duration_on=0.3,
            min_duration_off=0.5,
        )
        self._diarizer = sherpa_onnx.OfflineSpeakerDiarization(config)

    def process(self, waveform: Any) -> dict[str, Any]:
        result = self._diarizer.process(waveform)
        timeline: list[dict[str, Any]] = []
        for segment in result.sort_by_start_time():
            timeline.append(
                {
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "speaker": int(segment.speaker),
                    "confidence": round(float(getattr(segment, "confidence", 0) or 0), 4),
                }
            )
        return {
            "numSpeakers": int(result.num_speakers),
            "numSegments": int(result.num_segments),
            "timeline": timeline,
        }

    def label_segments(
        self,
        waveform: Any,
        segments: list[dict[str, Any]],
    ) -> list[int | None]:
        """Assign a speaker index to each ASR segment by maximum overlap."""
        if not segments:
            return []
        diarization = self.process(waveform)
        timeline = diarization["timeline"]
        labels: list[int | None] = []
        for segment in segments:
            start = float(segment.get("start") or 0)
            end = float(segment.get("end") or start)
            best_speaker: int | None = None
            best_overlap = 0.0
            for turn in timeline:
                overlap = max(0.0, min(end, turn["end"]) - max(start, turn["start"]))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = turn["speaker"]
            labels.append(best_speaker if best_overlap > 0 else None)
        return labels

    def assign_global_speakers(
        self,
        waveform: Any,
        segments: list[dict[str, Any]],
        extractor: sherpa_onnx.SpeakerEmbeddingExtractor,
        gallery: "SpeakerGallery",
    ) -> list[str | None]:
        """Assign a session-wide speaker name to each ASR segment."""
        if not segments:
            return []
        diarization = self.process(waveform)
        timeline = diarization["timeline"]
        local_to_global = gallery.label_turns(extractor, waveform, timeline)
        labels: list[str | None] = []
        for segment in segments:
            start = float(segment.get("start") or 0)
            end = float(segment.get("end") or start)
            best_turn: dict[str, Any] | None = None
            best_overlap = 0.0
            for turn in timeline:
                overlap = max(0.0, min(end, turn["end"]) - max(start, turn["start"]))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_turn = turn
            if best_turn is None or best_overlap <= 0:
                labels.append(None)
                continue
            labels.append(
                local_to_global.get(int(best_turn["speaker"]))
            )
        return labels


def _embedding_extractor(num_threads: int = 2) -> sherpa_onnx.SpeakerEmbeddingExtractor:
    return sherpa_onnx.SpeakerEmbeddingExtractor(
        sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(EMBEDDING_MODEL),
            num_threads=max(1, int(num_threads)),
            provider="cpu",
        )
    )


def extract_embedding(
    extractor: sherpa_onnx.SpeakerEmbeddingExtractor,
    waveform: Any,
    sample_rate: int = 16000,
) -> np.ndarray | None:
    """Extract one L2-normalized speaker embedding from an audio slice."""
    samples = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if samples.size < int(sample_rate * 0.5):
        return None
    stream = extractor.create_stream()
    stream.accept_waveform(float(sample_rate), samples)
    stream.input_finished()
    if not extractor.is_ready(stream):
        return None
    embedding = extractor.compute(stream)
    vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
    if vector.size == 0:
        return None
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        return None
    return (vector / norm).astype(np.float32)


class SpeakerGallery:
    """Session-wide speaker identity gallery (consistent across segments)."""

    def __init__(self, dim: int, state_path: Path | None = None, threshold: float = 0.48) -> None:
        self.dim = int(dim)
        self.threshold = float(threshold)
        self.state_path = state_path
        self.means: dict[str, np.ndarray] = {}
        self.counts: dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if not self.state_path or not self.state_path.is_file():
            return
        import json

        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for name, vector in (payload.get("speakers") or {}).items():
            if not isinstance(vector, list) or not vector:
                continue
            try:
                mean = np.asarray(vector, dtype=np.float32).reshape(-1)
                if mean.size != self.dim:
                    continue
                self.means[str(name)] = mean / float(np.linalg.norm(mean))
                self.counts[str(name)] = int(payload.get("counts", {}).get(str(name), 1))
            except Exception:
                continue

    def _save(self) -> None:
        if not self.state_path:
            return
        import json

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(f"{self.state_path.name}.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "version": 1,
                    "speakers": {name: vector.tolist() for name, vector in self.means.items()},
                    "counts": self.counts,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.state_path)

    def resolve(self, embedding: np.ndarray) -> str:
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vector.size != self.dim:
            raise ValueError(f"嵌入维度不匹配：{vector.size} != {self.dim}")
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector = vector / norm
        best_name = ""
        best_similarity = -1.0
        for name, mean in self.means.items():
            similarity = float(np.dot(vector, mean))
            if similarity > best_similarity:
                best_similarity = similarity
                best_name = name
        if best_name and best_similarity >= self.threshold:
            count = self.counts.get(best_name, 1)
            updated = self.means[best_name] * count + vector
            updated_norm = float(np.linalg.norm(updated))
            if updated_norm > 0:
                self.means[best_name] = updated / updated_norm
            self.counts[best_name] = count + 1
            self._save()
            return best_name
        name = f"speaker_{len(self.means)}"
        self.means[name] = vector
        self.counts[name] = 1
        self._save()
        return name

    def label_turns(
        self,
        extractor: sherpa_onnx.SpeakerEmbeddingExtractor,
        waveform: Any,
        turns: list[dict[str, Any]],
        sample_rate: int = 16000,
    ) -> dict[int, str]:
        samples = np.asarray(waveform, dtype=np.float32).reshape(-1)
        mapping: dict[int, str] = {}
        for turn in turns:
            local = int(turn.get("speaker"))
            if local in mapping:
                continue
            start_sample = int(float(turn.get("start") or 0) * sample_rate)
            end_sample = int(float(turn.get("end") or start_sample / sample_rate) * sample_rate)
            slice_ = samples[start_sample:end_sample]
            embedding = extract_embedding(extractor, slice_, sample_rate)
            if embedding is None:
                continue
            try:
                mapping[local] = self.resolve(embedding)
            except Exception:
                continue
        return mapping


def get_diarizer(num_threads: int = 2) -> SpeakerDiarizer:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = SpeakerDiarizer(num_threads=num_threads)
        return _instance
