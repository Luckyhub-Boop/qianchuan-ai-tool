from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

import audio_capture


class AudioCaptureTests(unittest.TestCase):
    def test_wav_writer_keeps_a_valid_header_while_recording(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "part_000001.wav"
            writer = audio_capture.RecoverableWavWriter(path)
            writer.write(b"\x00\x00" * audio_capture.SAMPLE_RATE)

            with wave.open(str(path), "rb") as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getframerate(), 16_000)
                self.assertEqual(audio.getnframes(), 16_000)
                self.assertEqual(audio.readframes(16_000), b"\x00\x00" * 16_000)

            writer.write(b"\x00\x00" * audio_capture.SAMPLE_RATE)
            writer.close()
            with wave.open(str(path), "rb") as audio:
                self.assertEqual(audio.getnframes(), 32_000)

    def test_next_segment_number_uses_existing_audio_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "part_000001.wav").write_bytes(b"a")
            (root / "part_000004.flac").write_bytes(b"b")
            (root / "part_000003.ts").write_bytes(b"c")

            self.assertEqual(audio_capture.next_segment_number(root), 5)


if __name__ == "__main__":
    unittest.main()
