from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable


def external_root() -> Path:
    return Path(os.getenv("QIANCHUAN_EXTERNAL_ROOT", r"D:\AI投放产品"))


def _emit(log: Callable[[str], None] | None, message: str) -> None:
    if log is not None:
        log(message)
    else:
        print(message, flush=True)


# check 为 models 目录下的相对路径；下载始终落到 external_root/models 下。
MODEL_SPECS: list[dict[str, Any]] = [
    {
        "key": "whisper-large-v3",
        "check": "whisper-large-v3/model.bin",
        "kind": "snapshot",
        "repo_id": "Systran/faster-whisper-large-v3",
        "target_dir": "whisper-large-v3",
    },
    {
        "key": "speaker-segmentation",
        "check": "speaker-diarization/model.onnx",
        "kind": "file",
        "repo_id": "csukuangfj/sherpa-onnx-pyannote-segmentation-3-0",
        "filename": "model.onnx",
        "target_dir": "speaker-diarization",
    },
    {
        "key": "speaker-embedding",
        "check": (
            "speaker-diarization/"
            "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
        ),
        "kind": "file",
        "repo_id": "onemira/eres2net-base-3dspeaker-onnx",
        "filename": "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx",
        "target_dir": "speaker-diarization",
    },
]


def ensure_models(
    root: Path | str | None = None,
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Ensure all required model files exist under root/models, downloading any
    missing ones to that same D:-drive directory. Never writes to C:."""
    root = Path(root) if root is not None else external_root()
    models_dir = root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Keep the HuggingFace download cache on the external drive as well so
    # partial downloads never land on the C: drive.
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HOME", str(root / ".hf-home"))
    os.environ.setdefault("HF_HUB_CACHE", str(root / ".hf-cache"))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(root / ".hf-cache"))

    present: list[str] = []
    downloaded: list[str] = []
    errors: list[str] = []
    for spec in MODEL_SPECS:
        target = models_dir / spec["check"]
        if target.is_file() and target.stat().st_size > 0:
            present.append(spec["key"])
            continue
        _emit(log, f"检测到模型缺失：{spec['key']}，开始下载到 {models_dir}")
        try:
            target_dir = models_dir / spec["target_dir"]
            target_dir.mkdir(parents=True, exist_ok=True)
            if spec["kind"] == "snapshot":
                from huggingface_hub import snapshot_download

                snapshot_download(
                    spec["repo_id"],
                    local_dir=str(target_dir),
                )
            else:
                from huggingface_hub import hf_hub_download

                hf_hub_download(
                    repo_id=spec["repo_id"],
                    filename=spec["filename"],
                    local_dir=str(target_dir),
                )
            downloaded.append(spec["key"])
            _emit(log, f"模型下载完成：{spec['key']}")
        except Exception as exc:
            errors.append(f"{spec['key']}: {exc}")
            _emit(log, f"模型下载失败：{spec['key']}: {exc}")
    return {
        "modelsDir": str(models_dir),
        "present": present,
        "downloaded": downloaded,
        "errors": errors,
    }


if __name__ == "__main__":
    result = ensure_models()
    print(result)
