# -*- coding: utf-8 -*-
# 下载 sherpa-onnx 说话人分离模型到 D:\AI投放产品\models\speaker-diarization。
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXTERNAL_ROOT = Path(os.getenv("QIANCHUAN_EXTERNAL_ROOT", r"D:\AI投放产品"))
DEST = EXTERNAL_ROOT / "models" / "speaker-diarization"

def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from huggingface_hub import hf_hub_download

    hf_hub_download(
        repo_id="csukuangfj/sherpa-onnx-pyannote-segmentation-3-0",
        filename="model.onnx",
        local_dir=DEST,
    )
    hf_hub_download(
        repo_id="onemira/eres2net-base-3dspeaker-onnx",
        filename="3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx",
        local_dir=DEST,
    )
    seg_target = DEST / "model.onnx"
    emb_target = DEST / "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
    print("分割模型:", seg_target, seg_target.stat().st_size)
    print("嵌入模型:", emb_target, emb_target.stat().st_size)


if __name__ == "__main__":
    main()
