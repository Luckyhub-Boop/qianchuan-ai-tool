from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import recording_store
import review_finalizer


class ReviewFinalizerTests(unittest.TestCase):
    def make_session(self, root: Path) -> tuple[Path, dict]:
        recordings = root / "recordings"
        directory = recordings / "2026-11-08_room-1_120000"
        (directory / "segments").mkdir(parents=True)
        (directory / "segments" / "part_000001.ts").write_bytes(b"video")
        manifest = {
            "id": directory.name,
            "accountId": "fashion",
            "roomId": "room-1",
            "date": "2026-11-08",
            "startedAt": "2026-11-08T12:00:00+08:00",
            "endedAt": "2026-11-08T12:05:00+08:00",
            "status": "completed",
            "videoPolicy": "analysis_first_then_delete",
        }
        recording_store.write_manifest(directory, manifest)
        transcript = {
            "model": "faster-whisper-large-v3",
            "segments": [
                {
                    "id": "line-1",
                    "segmentId": "part_000001",
                    "text": "测试复盘话术",
                    "startedAt": "2026-11-08T12:00:01+08:00",
                    "endedAt": "2026-11-08T12:00:05+08:00",
                }
            ],
            "processedParts": ["part_000001"],
        }
        recording_store.atomic_write_json(
            directory / "asr" / "transcript.json",
            transcript,
        )
        archive_target = root / "archive" / "sessions" / directory.name
        (archive_target / "asr").mkdir(parents=True)
        recording_store.atomic_write_json(
            archive_target / "manifest.json",
            manifest,
        )
        shutil.copy2(
            directory / "asr" / "transcript.json",
            archive_target / "asr" / "transcript.json",
        )
        return directory, manifest

    def history(self) -> dict:
        first = int(
            datetime.fromisoformat("2026-11-08T12:00:00+08:00").timestamp()
            * 1000
        )
        return {
            "days": {
                "2026-11-08": {
                    "room-1": [
                        {
                            "t": first,
                            "spend": 100,
                            "gmv": 180,
                            "orders": 2,
                            "watch": 300,
                        }
                    ]
                }
            }
        }

    def test_completed_session_is_archived_then_raw_video_is_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            directory, manifest = self.make_session(root)

            finalized = review_finalizer.finalize_completed_sessions(
                recordings_dir=root / "recordings",
                archive_dir=root / "archive",
                history=self.history(),
                audience_history={},
            )

            self.assertEqual(finalized, [manifest["id"]])
            self.assertFalse(directory.exists())
            target = root / "archive" / "sessions" / manifest["id"]
            self.assertTrue((target / "review.json").is_file())
            self.assertTrue((target / "review.md").is_file())
            self.assertTrue((target / "asr" / "transcript.json").is_file())
            daily = root / "archive" / "fashion_2026-11-08.json"
            daily_markdown = root / "archive" / "fashion_2026-11-08.md"
            self.assertTrue(daily.is_file())
            self.assertTrue(daily_markdown.is_file())
            archived_manifest = json.loads(
                (target / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(archived_manifest["status"], "archived_analysis")
            self.assertEqual(
                archived_manifest["videoPolicy"],
                "analysis_first_then_delete",
            )
            self.assertIn(
                "原始录像在分析归档成功后立即删除",
                (target / "review.md").read_text(encoding="utf-8"),
            )

    def test_incomplete_transcription_keeps_raw_video_for_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            directory, _manifest = self.make_session(root)
            transcript_path = directory / "asr" / "transcript.json"
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
            transcript["processedParts"] = []
            transcript["segments"] = []
            recording_store.atomic_write_json(transcript_path, transcript)

            finalized = review_finalizer.finalize_completed_sessions(
                recordings_dir=root / "recordings",
                archive_dir=root / "archive",
                history=self.history(),
                audience_history={},
            )

            self.assertEqual(finalized, [])
            self.assertTrue(directory.is_dir())
            self.assertFalse(
                (root / "archive" / "sessions" / directory.name / "review.md").is_file()
            )


if __name__ == "__main__":
    unittest.main()
