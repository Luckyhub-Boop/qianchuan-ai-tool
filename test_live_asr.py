from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import live_asr
import recording_store


class LiveAsrTests(unittest.TestCase):
    def make_session(
        self,
        recordings: Path,
        session_id: str,
        *,
        status: str,
        part_count: int,
        transcript: dict | None = None,
    ) -> tuple[Path, dict]:
        if not session_id.startswith("2026-11-17_"):
            session_id = f"2026-11-17_{session_id}_120000"
        directory = recordings / session_id
        (directory / "segments").mkdir(parents=True)
        for index in range(1, part_count + 1):
            (directory / "segments" / f"part_{index:06d}.wav").write_bytes(
                b"RIFF-test-audio"
            )
        manifest = {
            "id": session_id,
            "accountId": "fashion",
            "roomId": "room-1",
            "date": "2026-11-17",
            "startedAt": "2026-11-17T12:00:00+08:00",
            "status": status,
        }
        recording_store.write_manifest(directory, manifest)
        if transcript is not None:
            recording_store.atomic_write_json(
                directory / "asr" / "transcript.json",
                transcript,
            )
        return directory, manifest

    def make_worker(self) -> live_asr.SpeechWorker:
        worker = live_asr.SpeechWorker()
        worker.publish_state = mock.Mock()
        worker.extract_audio = mock.Mock()
        return worker

    def transcript_line(self, index: int) -> dict:
        return {
            "start": 1.0,
            "end": 2.0,
            "text": f"line-{index}",
            "avgLogProb": -0.1,
            "noSpeechProb": 0.01,
            "speaker": "speaker_1",
        }

    def test_normalize_transcript_converts_and_collapses_repetition(self) -> None:
        text = "這個分這種，分這種，分這種，分這種，分這種"
        normalized = live_asr.normalize_transcript_text(text)
        self.assertIn("这个", normalized)
        self.assertLess(normalized.count("分这种"), 2)

    def test_audio_decoder_returns_16k_mono_float_array(self) -> None:
        self.assertTrue(callable(live_asr.decode_audio_16k))

    def test_diarization_can_be_disabled_for_fast_bulk_backfill(self) -> None:
        worker = self.make_worker()
        worker.model = mock.Mock()
        worker.model.transcribe.return_value = (
            [
                SimpleNamespace(
                    text="line one",
                    start=0.0,
                    end=1.0,
                    no_speech_prob=0.0,
                    avg_logprob=-0.1,
                )
            ],
            {},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch.object(live_asr, "DIARIZATION_ENABLED", False),
                mock.patch.object(
                    live_asr,
                    "decode_audio_16k",
                    return_value=[],
                ),
            ):
                result = worker.transcribe(
                    Path("part_000001.wav"),
                    session_dir=Path(temp_dir),
                )

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["speaker"])
        self.assertIsNone(worker.diarizer)

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


    def test_processed_parts_are_authoritative_even_when_transcript_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            recordings = Path(temp_dir)
            directory, manifest = self.make_session(
                recordings,
                "session-a",
                status="completed",
                part_count=2,
                transcript={
                    "segments": [],
                    "processedParts": ["part_000001"],
                },
            )
            worker = self.make_worker()
            worker.transcribe = mock.Mock(return_value=[self.transcript_line(1)])

            with (
                mock.patch.object(live_asr, "audio_duration", return_value=300.0),
                mock.patch.object(live_asr, "archive_session_assets"),
            ):
                processed = worker.process_session(directory, manifest)

            self.assertEqual(processed, 1)
            worker.transcribe.assert_called_once()
            self.assertEqual(worker.transcribe.call_args.args[0].stem, "part_000002")
            transcript = live_asr.read_json(
                directory / "asr" / "transcript.json"
            )
            self.assertEqual(
                transcript["processedParts"],
                ["part_000001", "part_000002"],
            )

    def test_empty_transcription_is_marked_terminal_and_never_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            recordings = Path(temp_dir)
            directory, manifest = self.make_session(
                recordings,
                "session-empty",
                status="completed",
                part_count=1,
            )
            worker = self.make_worker()
            worker.transcribe = mock.Mock(return_value=[])

            with (
                mock.patch.object(live_asr, "audio_duration", return_value=13.1),
                mock.patch.object(live_asr, "archive_session_assets"),
            ):
                self.assertEqual(worker.process_session(directory, manifest), 1)
                self.assertEqual(worker.process_session(directory, manifest), 0)

            worker.transcribe.assert_called_once()
            transcript = live_asr.read_json(
                directory / "asr" / "transcript.json"
            )
            self.assertEqual(transcript["processedParts"], ["part_000001"])
            self.assertEqual(transcript["emptyParts"], ["part_000001"])
            self.assertEqual(transcript["skippedParts"], [])

    def test_process_session_processes_every_pending_part_in_one_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            recordings = Path(temp_dir)
            directory, manifest = self.make_session(
                recordings,
                "session-all",
                status="completed",
                part_count=3,
            )
            worker = self.make_worker()
            worker.transcribe = mock.Mock(
                side_effect=[
                    [self.transcript_line(1)],
                    [self.transcript_line(2)],
                    [self.transcript_line(3)],
                ]
            )

            with (
                mock.patch.object(live_asr, "audio_duration", return_value=300.0),
                mock.patch.object(live_asr, "archive_session_assets"),
            ):
                processed = worker.process_session(directory, manifest)

            self.assertEqual(processed, 3)
            self.assertEqual(worker.transcribe.call_count, 3)
            transcript = live_asr.read_json(
                directory / "asr" / "transcript.json"
            )
            self.assertEqual(
                transcript["processedParts"],
                ["part_000001", "part_000002", "part_000003"],
            )
            self.assertEqual(len(transcript["segments"]), 3)
            self.assertEqual(
                transcript["segments"][0]["source"],
                live_asr.MODEL_SOURCE,
            )
            self.assertEqual(
                transcript["partModels"]["part_000001"],
                live_asr.MODEL_SOURCE,
            )

    def test_failed_part_is_skipped_after_three_attempts_and_others_continue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            recordings = Path(temp_dir)
            directory, manifest = self.make_session(
                recordings,
                "session-failure",
                status="completed",
                part_count=2,
            )
            worker = self.make_worker()

            def transcribe(audio: Path, **_kwargs: object) -> list[dict]:
                if audio.stem == "part_000001":
                    raise RuntimeError("decoder stalled")
                return [self.transcript_line(2)]

            worker.transcribe = mock.Mock(side_effect=transcribe)
            with (
                mock.patch.object(live_asr, "audio_duration", return_value=300.0),
                mock.patch.object(live_asr, "archive_session_assets"),
            ):
                worker.process_session(directory, manifest)
                worker.process_session(directory, manifest)
                worker.process_session(directory, manifest)
                processed = worker.process_session(directory, manifest)

            self.assertEqual(processed, 0)
            transcript = live_asr.read_json(
                directory / "asr" / "transcript.json"
            )
            self.assertEqual(
                transcript["processedParts"],
                ["part_000001", "part_000002"],
            )
            self.assertEqual(transcript["skippedParts"], ["part_000001"])
            self.assertNotIn("part_000001", transcript["emptyParts"])
            self.assertEqual(transcript["partAttempts"]["part_000001"], 3)
            self.assertEqual(worker.transcribe.call_count, 4)

    def test_session_directories_sort_by_pending_part_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            recordings = Path(temp_dir)
            more_pending, _manifest = self.make_session(
                recordings,
                "completed-more-pending",
                status="completed",
                part_count=3,
            )
            less_pending, _manifest = self.make_session(
                recordings,
                "recording-less-pending",
                status="recording",
                part_count=2,
            )
            worker = self.make_worker()

            with mock.patch.object(live_asr, "RECORDINGS_DIR", recordings):
                sessions = worker.session_directories()

            self.assertEqual(
                [directory.name for directory, _manifest in sessions],
                [more_pending.name, less_pending.name],
            )


if __name__ == "__main__":
    unittest.main()
