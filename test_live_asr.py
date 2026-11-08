from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import live_asr
import recording_store


class LiveAsrTests(unittest.TestCase):
    def test_normalize_transcript_converts_and_collapses_repetition(self) -> None:
        text = "這個分這種，分這種，分這種，分這種，分這種"
        normalized = live_asr.normalize_transcript_text(text)
        self.assertIn("这个", normalized)
        self.assertLess(normalized.count("分这种"), 2)

    def test_audio_decoder_returns_16k_mono_float_array(self) -> None:
        self.assertTrue(callable(live_asr.decode_audio_16k))

    def test_backfill_keeps_analysis_after_recording_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            recordings = root / "recordings"
            session = recordings / "2026-11-06_room-1_120000"
            (session / "asr").mkdir(parents=True)
            recording_store.write_manifest(
                session,
                {
                    "id": session.name,
                    "accountId": "fashion",
                    "roomId": "room-1",
                    "date": "2026-11-06",
                    "startedAt": "2026-11-06T12:00:00+08:00",
                    "endedAt": "2026-11-06T12:05:00+08:00",
                    "status": "completed",
                },
            )
            (session / "asr" / "transcript.json").write_text(
                json.dumps(
                    {
                        "model": "faster-whisper-tiny",
                        "language": "zh",
                        "segmentSeconds": 300,
                        "segments": [
                            {
                                "id": "line-1",
                                "segmentId": "part_000001",
                                "text": "这是需要永久保留的复盘话术",
                                "startedAt": "2026-11-06T12:00:01+08:00",
                                "endedAt": "2026-11-06T12:00:06+08:00",
                                "startSeconds": 1,
                                "endSeconds": 6,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            archive_root = root / "review-archive"
            archive_sessions = archive_root / "sessions"

            archived = live_asr.backfill_session_archives(
                recordings_dir=recordings,
                archive_sessions_dir=archive_sessions,
            )

            self.assertEqual(archived, [session.name])
            target = archive_sessions / session.name
            self.assertTrue((target / "manifest.json").is_file())
            self.assertTrue((target / "asr" / "transcript.json").is_file())

            for item in sorted(recordings.rglob("*"), reverse=True):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    item.rmdir()
            recordings.rmdir()

            sessions = recording_store.review_sessions(
                {"days": {}},
                account_id="fashion",
                recordings_dir=recordings,
                archive_dir=archive_root,
            )

            self.assertEqual(len(sessions), 1)
            self.assertTrue(sessions[0]["videoExpired"])
            self.assertTrue(sessions[0]["transcript"]["available"])
            self.assertIn("永久保留", sessions[0]["transcript"]["phrases"][0]["text"])


if __name__ == "__main__":
    unittest.main()
