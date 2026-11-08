from __future__ import annotations

import argparse
import os
import struct
import sys
import time
from pathlib import Path

import av


SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2


class RecoverableWavWriter:
    """Write a playable mono PCM WAV and keep header sizes current."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.handle = path.open("wb")
        self.data_bytes = 0
        self._write_header()

    def _header(self) -> bytes:
        byte_rate = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH
        block_align = CHANNELS * SAMPLE_WIDTH
        return (
            b"RIFF"
            + struct.pack("<I", min(0xFFFFFFFF, 36 + self.data_bytes))
            + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, CHANNELS, SAMPLE_RATE, byte_rate, block_align, 16)
            + b"data"
            + struct.pack("<I", min(0xFFFFFFFF, self.data_bytes))
        )

    def _write_header(self) -> None:
        self.handle.write(self._header())

    def write(self, data: bytes) -> None:
        if not data:
            return
        self.handle.write(data)
        self.data_bytes += len(data)
        self.handle.flush()
        position = self.handle.tell()
        self.handle.seek(0)
        self._write_header()
        self.handle.seek(position)

    @property
    def duration_seconds(self) -> float:
        return self.data_bytes / (SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH)

    def close(self) -> None:
        if self.handle.closed:
            return
        position = self.handle.tell()
        self.handle.seek(0)
        self._write_header()
        self.handle.seek(position)
        self.handle.flush()
        os.fsync(self.handle.fileno())
        self.handle.close()


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] {message}", flush=True)


def next_segment_number(directory: Path) -> int:
    numbers: list[int] = []
    for pattern in ("part_*.wav", "part_*.flac", "part_*.ts"):
        for item in directory.glob(pattern):
            try:
                numbers.append(int(item.stem.split("_")[-1]))
            except (IndexError, ValueError):
                continue
    return max(numbers, default=0) + 1


def run(url: str, directory: Path, segment_seconds: int) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    segment_number = next_segment_number(directory)
    writer: RecoverableWavWriter | None = None
    container: av.container.InputContainer | None = None
    try:
        log(f"打开音频源 room-url={url.split('room=')[-1]} timeout=90s")
        container = av.open(url, timeout=90)
        audio_stream = next(
            (stream for stream in container.streams if stream.type == "audio"),
            None,
        )
        if audio_stream is None:
            raise RuntimeError("直播流中没有音频轨道")
        resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=SAMPLE_RATE,
        )
        log(
            "音频流已连接 "
            f"codec={audio_stream.codec_context.name} "
            f"segment={segment_seconds}s output={directory}"
        )
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                if writer is None:
                    writer = RecoverableWavWriter(
                        directory / f"part_{segment_number:06d}.wav"
                    )
                    log(f"开始音频分段 part_{segment_number:06d}.wav")
                payload = resampled.to_ndarray().reshape(-1).astype("<i2").tobytes()
                writer.write(payload)
                if writer.duration_seconds >= segment_seconds:
                    writer.close()
                    writer = None
                    segment_number += 1
        for resampled in resampler.resample(None):
            if writer is None:
                writer = RecoverableWavWriter(
                    directory / f"part_{segment_number:06d}.wav"
                )
            payload = resampled.to_ndarray().reshape(-1).astype("<i2").tobytes()
            writer.write(payload)
        return 0
    finally:
        if writer is not None:
            writer.close()
        if container is not None:
            container.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--segment-seconds", type=int, default=300)
    args = parser.parse_args()
    try:
        return run(
            args.url,
            Path(args.directory),
            max(30, int(args.segment_seconds)),
        )
    except Exception as exc:
        log(f"音频采集异常：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
