from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import voiceprint


class VoiceprintStoreTests(unittest.TestCase):
    def _patch_paths(self, root: Path) -> None:
        voiceprint.DATA_DIR = root
        voiceprint.VOICEPRINTS_DIR = root / "voiceprints"
        voiceprint.INDEX_PATH = root / "voiceprints.json"

    def test_enroll_and_delete_with_mocked_embedding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._patch_paths(root)
            vector = (np.ones(512, dtype=np.float32) / np.sqrt(512.0)).astype(
                np.float32
            )
            waveform = np.zeros(16000 * 2, dtype=np.float32)
            source = root / "x.wav"
            source.write_bytes(b"not-a-real-audio")
            with (
                mock.patch.object(voiceprint, "decode_audio_16k", return_value=waveform),
                mock.patch.object(voiceprint, "embed_waveform", return_value=vector),
            ):
                record = voiceprint.enroll("alice", source, "x.wav")

            self.assertEqual(record["name"], "alice")
            profiles = voiceprint.profiles()
            self.assertEqual(len(profiles), 1)
            self.assertTrue(profiles[0]["embeddingReady"])
            self.assertIn("alice", voiceprint.known_vectors())

            deleted = voiceprint.delete("alice")
            self.assertEqual(deleted["name"], "alice")
            self.assertEqual(len(voiceprint.profiles()), 0)

    def test_match_embedding_uses_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._patch_paths(root)
            vectors = {"alice": np.array([1.0, 0.0, 0.0], dtype=np.float32)}
            with mock.patch.object(voiceprint, "known_vectors", return_value=vectors):
                result = voiceprint.match_embedding(
                    np.array([0.9, 0.1, 0.0], dtype=np.float32),
                    threshold=0.5,
                )

            self.assertTrue(result["matched"])
            self.assertEqual(result["name"], "alice")


if __name__ == "__main__":
    unittest.main()
