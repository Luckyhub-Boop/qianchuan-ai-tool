from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import json

import recording_store


class RecordingStoreTests(unittest.TestCase):
    def test_cleanup_keeps_latest_ten_calendar_days(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            now = datetime(2026, 11, 6, 12, 0, 0).astimezone()
            for days_ago in range(15):
                session_date = (now - timedelta(days=days_ago)).date()
                directory = root / f"{session_date.isoformat()}_room_{days_ago}"
                directory.mkdir()
                (directory / "manifest.json").write_text("{}", encoding="utf-8")

            removed = recording_store.cleanup_recordings(
                retention_days=10,
                now=now,
                recordings_dir=root,
            )

            self.assertEqual(len(removed), 5)
            remaining = [path.name[:10] for path in root.iterdir() if path.is_dir()]
            self.assertNotIn("2026-10-27", remaining)
            self.assertIn("2026-10-28", remaining)
            self.assertIn("2026-11-06", remaining)

    def test_review_session_uses_recording_and_real_screen_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            directory = root / "2026-11-06_7704532779547085622_120000"
            (directory / "segments").mkdir(parents=True)
            (directory / "index.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
            (directory / "segments" / "part_000001.ts").write_bytes(b"video")
            manifest = {
                "id": directory.name,
                "accountId": "fashion",
                "roomId": "7704532779547085622",
                "awemeName": "赵镭精讲小数基本功",
                "date": "2026-11-06",
                "title": "赵镭精讲小数基本功 · 整场录像",
                "startedAt": "2026-11-06T12:00:00+08:00",
                "endedAt": "2026-11-06T12:10:00+08:00",
                "status": "completed",
            }
            recording_store.write_manifest(directory, manifest)
            first = int(
                datetime.fromisoformat(manifest["startedAt"]).timestamp() * 1000
            )
            history = {
                "days": {
                    "2026-11-06": {
                        "7704532779547085622": [
                            {
                                "t": first,
                                "spend": 0,
                                "gmv": 0,
                                "orders": 0,
                                "watch": 0,
                                "online": 20,
                            },
                            {
                                "t": first + 5 * 60 * 1000,
                                "spend": 100,
                                "gmv": 180,
                                "orders": 2,
                                "watch": 300,
                                "online": 24,
                            },
                            {
                                "t": first + 10 * 60 * 1000,
                                "spend": 200,
                                "gmv": 190,
                                "orders": 2,
                                "watch": 500,
                                "online": 12,
                            },
                        ]
                    }
                }
            }

            sessions = recording_store.review_sessions(
                history,
                account_id="fashion",
                recordings_dir=root,
                archive_dir=root / "archive",
            )

            self.assertEqual(len(sessions), 1)
            session = sessions[0]
            self.assertEqual(session["metrics"]["spend"], 200)
            self.assertEqual(session["metrics"]["gmv"], 190)
            self.assertEqual(session["metrics"]["orders"], 2)
            self.assertEqual(session["videoType"], "hls")
            self.assertEqual(session["segmentCount"], 1)
            self.assertTrue(any(item["type"] == "problem" for item in session["annotations"]))
            self.assertTrue(any("千川直播大屏" in item for item in session["dataSources"]))
            self.assertIn("本地 Whisper", " ".join(session["analysisSteps"]))

    def test_speech_analysis_links_phrases_to_order_and_online_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            asr_dir = directory / "asr"
            asr_dir.mkdir()
            start = datetime(2026, 11, 6, 12, 0, 0).astimezone()
            first_ms = int(start.timestamp() * 1000)
            transcript = {
                "model": "faster-whisper-tiny",
                "language": "zh",
                "segments": [
                    {
                        "id": "p1",
                        "text": "这款今天活动价一百六十八",
                        "startedAt": start.isoformat(timespec="milliseconds"),
                        "endedAt": (start + timedelta(seconds=8)).isoformat(timespec="milliseconds"),
                    },
                    {
                        "id": "p2",
                        "text": "后面再讲一下别的",
                        "startedAt": (start + timedelta(seconds=30)).isoformat(timespec="milliseconds"),
                        "endedAt": (start + timedelta(seconds=38)).isoformat(timespec="milliseconds"),
                    },
                ],
            }
            metrics = {
                "samples": [
                    {"t": first_ms, "spend": 100, "gmv": 100, "orders": 1, "online": 20},
                    {"t": first_ms + 20000, "spend": 120, "gmv": 268, "orders": 2, "online": 24},
                    {"t": first_ms + 50000, "spend": 150, "gmv": 268, "orders": 2, "online": 14},
                    {"t": first_ms + 70000, "spend": 170, "gmv": 268, "orders": 2, "online": 12},
                ]
            }
            (asr_dir / "transcript.json").write_text(
                json.dumps(transcript, ensure_ascii=False),
                encoding="utf-8",
            )
            (asr_dir / "metrics.json").write_text(
                json.dumps(metrics, ensure_ascii=False),
                encoding="utf-8",
            )

            result = recording_store.analyze_speech(directory, [])

            self.assertTrue(result["available"])
            self.assertEqual(result["good"][0]["effectLabel"], "对应窗口出单")
            self.assertEqual(result["bad"][0]["effectLabel"], "对应窗口掉人")
            self.assertIn("效果较好", result["summary"])
            self.assertIn("效果较差", result["summary"])

    def test_daily_review_groups_parts_and_builds_15_minute_buckets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            started = datetime(2026, 11, 6, 12, 0, 0).astimezone()
            first_ms = int(started.timestamp() * 1000)
            for index, minute in enumerate((0, 10)):
                session_start = started + timedelta(minutes=minute)
                directory = root / f"2026-11-06_room_{minute:02d}0000"
                (directory / "segments").mkdir(parents=True)
                (directory / "index.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
                (directory / "segments" / "part_000001.ts").write_bytes(b"video")
                recording_store.write_manifest(
                    directory,
                    {
                        "id": directory.name,
                        "accountId": "fashion",
                        "roomId": "room",
                        "date": "2026-11-06",
                        "startedAt": session_start.isoformat(timespec="seconds"),
                        "endedAt": (session_start + timedelta(minutes=5)).isoformat(timespec="seconds"),
                        "status": "completed",
                    },
                )
            history = {
                "days": {
                    "2026-11-06": {
                        "room": [
                            {"t": first_ms + offset * 60000, "exposure": offset * 100,
                             "watch": offset * 20, "productClicks": offset * 2,
                             "orders": offset // 2, "spend": offset * 2, "gmv": offset * 3}
                            for offset in range(0, 31, 5)
                        ]
                    }
                }
            }

            sessions = recording_store.review_sessions(
                history,
                account_id="fashion",
                recordings_dir=root,
                archive_dir=root / "archive",
            )

            self.assertEqual(len(sessions), 1)
            session = sessions[0]
            self.assertTrue(session["id"].startswith("daily-fashion-"))
            self.assertEqual(len(session["recordingParts"]), 2)
            self.assertGreaterEqual(len(session["timeBuckets"]), 1)
            self.assertEqual(session["timeBucketGranularityMinutes"], 15)
            self.assertEqual(session["durationSeconds"], 15 * 60)
            self.assertLess(session["series"][-1]["time"], 24 * 60 * 60)

    def test_attaches_buyin_audience_to_nearest_review_time(self) -> None:
        start_ms = int(datetime(2026, 11, 6, 12, 0, tzinfo=datetime.now().astimezone().tzinfo).timestamp() * 1000)
        sessions = [
            {
                "roomId": "room-1",
                "series": [
                    {"t": start_ms, "orders": 0},
                    {"t": start_ms + 20 * 60 * 1000, "orders": 2},
                ],
            }
        ]
        history = {
            "items": [
                {
                    "t": start_ms + 60 * 1000,
                    "capturedAt": "2026-11-06T12:01:00+08:00",
                    "roomId": "room-1",
                    "profiles": {
                        "realtimeViewer": {
                            "available": True,
                            "label": "近1分钟看播用户",
                            "gender": {"top": "女性", "distribution": [{"label": "女性", "value": 68}]},
                            "age": {"top": "31-35岁", "distribution": [{"label": "31-35岁", "value": 42}]},
                            "region": {"top": "四川", "distribution": [{"label": "四川", "value": 21}]},
                            "summary": "女性居多",
                        },
                        "recentBuyer": {
                            "available": True,
                            "label": "近5分钟购买用户",
                            "gender": {"top": "女性", "distribution": [{"label": "女性", "value": 80}]},
                            "age": {"top": "25-30岁", "distribution": [{"label": "25-30岁", "value": 35}]},
                            "region": {"top": "广东", "distribution": [{"label": "广东", "value": 18}]},
                            "summary": "女性居多",
                        },
                    },
                }
            ]
        }

        matched = recording_store.attach_buyin_audience(sessions, history)

        self.assertEqual(matched, 1)
        first = sessions[0]["series"][0]
        second = sessions[0]["series"][1]
        self.assertEqual(first["viewerPersona"]["gender"], "女性")
        self.assertEqual(first["viewerPersona"]["age"], "31-35岁")
        self.assertEqual(first["buyerPersona"]["region"], "广东")
        self.assertEqual(first["viewerPersona"]["source"], "buyin_compass_live_screen_dom")
        self.assertNotIn("viewerPersona", second)

    def test_review_overview_points_to_structured_speech_details(self) -> None:
        summary = recording_store.review_overview_summary(
            {
                "durationSeconds": 3600,
                "recordingParts": [{"id": "part-1"}, {"id": "part-2"}],
                "metrics": {"gmv": 1680, "orders": 10, "roi": 0.56},
                "transcript": {
                    "available": True,
                    "good": [{"text": "这是一段不应该塞进总述里的完整长句话术"}],
                    "bad": [{"text": "这也是一段完整长句"}],
                },
            }
        )

        self.assertIn("2 段录像", summary)
        self.assertIn("净成交 ¥1680.00", summary)
        self.assertIn("逐条话术复盘", summary)
        self.assertNotIn("不应该塞进总述", summary)

    def test_daily_recording_availability_checks_external_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            directory = root / "2026-11-06_room_120000"
            (directory / "segments").mkdir(parents=True)
            recording_store.write_manifest(
                directory,
                {
                    "id": directory.name,
                    "accountId": "fashion",
                    "roomId": "room",
                    "date": "2026-11-06",
                },
            )
            self.assertFalse(
                recording_store.has_daily_recording("fashion", "2026-11-06", root)
            )
            (directory / "segments" / "part_000001.ts").write_bytes(b"video")
            self.assertTrue(
                recording_store.has_daily_recording("fashion", "2026-11-06", root)
            )


if __name__ == "__main__":
    unittest.main()
