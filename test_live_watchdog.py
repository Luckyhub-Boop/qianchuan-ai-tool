from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import live_watchdog


class WatchdogStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temp_dir.name) / "live-screen-metrics.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_heartbeat(self, value: str | None) -> None:
        payload = {} if value is None else {"heartbeatAt": value}
        self.state_path.write_text(json.dumps(payload), encoding="utf-8")

    def test_state_age_uses_heartbeat_timestamp(self) -> None:
        heartbeat = datetime.now(timezone.utc) - timedelta(seconds=12)
        self.write_heartbeat(heartbeat.isoformat())

        with patch.object(live_watchdog, "SCREEN_STATE_PATH", self.state_path):
            age = live_watchdog.state_age_seconds()

        self.assertIsNotNone(age)
        self.assertGreaterEqual(age or 0, 11)
        self.assertLess(age or 0, 20)

    def test_state_age_returns_none_without_heartbeat(self) -> None:
        self.write_heartbeat(None)

        with patch.object(live_watchdog, "SCREEN_STATE_PATH", self.state_path):
            age = live_watchdog.state_age_seconds()

        self.assertIsNone(age)

    def test_state_age_returns_none_for_invalid_heartbeat(self) -> None:
        self.write_heartbeat("not-a-timestamp")

        with patch.object(live_watchdog, "SCREEN_STATE_PATH", self.state_path):
            age = live_watchdog.state_age_seconds()

        self.assertIsNone(age)

    def test_startup_grace_covers_initial_page_load(self) -> None:
        self.assertGreaterEqual(live_watchdog.AGENT_STARTUP_GRACE_SECONDS, 180)

    def test_pid_is_running_distinguishes_current_and_missing_process(self) -> None:
        self.assertTrue(live_watchdog.pid_is_running(os.getpid()))
        self.assertFalse(live_watchdog.pid_is_running(2_000_000_000))

    def test_running_agent_pid_reads_the_agent_lock(self) -> None:
        lock_path = Path(self.temp_dir.name) / "live-screen-agent.lock"
        lock_path.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
        with patch.object(live_watchdog, "AGENT_LOCK_PATH", lock_path):
            self.assertEqual(live_watchdog.running_agent_pid(), os.getpid())

    def test_running_agent_pid_ignores_stale_lock(self) -> None:
        lock_path = Path(self.temp_dir.name) / "live-screen-agent.lock"
        lock_path.write_text(json.dumps({"pid": 2_000_000_000}), encoding="utf-8")
        with patch.object(live_watchdog, "AGENT_LOCK_PATH", lock_path):
            self.assertIsNone(live_watchdog.running_agent_pid())

    def test_ensure_agent_started_reuses_existing_instance(self) -> None:
        with (
            patch.object(live_watchdog, "running_agent_pid", return_value=43210),
            patch.object(live_watchdog, "start_agent") as start_agent,
        ):
            process, pid = live_watchdog.ensure_agent_started("node.exe")

        self.assertIsNone(process)
        self.assertEqual(pid, 43210)
        start_agent.assert_not_called()

    def test_ensure_agent_started_launches_when_no_instance_exists(self) -> None:
        fake_process = object()
        with (
            patch.object(live_watchdog, "running_agent_pid", return_value=None),
            patch.object(live_watchdog, "start_agent", return_value=fake_process) as start_agent,
        ):
            process, pid = live_watchdog.ensure_agent_started("node.exe")

        self.assertIs(process, fake_process)
        self.assertIsNone(pid)
        start_agent.assert_called_once_with("node.exe")

    def test_ensure_buyin_agent_uses_its_own_lock_and_script(self) -> None:
        fake_process = object()
        with (
            patch.object(live_watchdog, "running_agent_pid", return_value=None) as running,
            patch.object(
                live_watchdog,
                "start_agent",
                return_value=fake_process,
            ) as start_agent,
        ):
            process, pid = live_watchdog.ensure_buyin_agent_started("node.exe")

        self.assertIs(process, fake_process)
        self.assertIsNone(pid)
        running.assert_called_once_with(live_watchdog.BUYIN_AGENT_LOCK_PATH)
        start_agent.assert_called_once_with(
            "node.exe",
            live_watchdog.BUYIN_AGENT_PATH,
            live_watchdog.BUYIN_AGENT_LOG_PATH,
            "百应直播中控台采集器",
        )

    def test_ensure_recorder_uses_python_recorder_lock(self) -> None:
        fake_process = object()
        with (
            patch.object(live_watchdog, "running_agent_pid", return_value=None) as running,
            patch.object(
                live_watchdog,
                "start_recorder",
                return_value=fake_process,
            ) as start_recorder,
        ):
            process, pid = live_watchdog.ensure_recorder_started()

        self.assertIs(process, fake_process)
        self.assertIsNone(pid)
        running.assert_called_once_with(live_watchdog.RECORDER_LOCK_PATH)
        start_recorder.assert_called_once_with()

    def test_ensure_asr_uses_local_whisper_lock(self) -> None:
        fake_process = object()
        with (
            patch.object(live_watchdog, "running_agent_pid", return_value=None) as running,
            patch.object(
                live_watchdog,
                "start_asr",
                return_value=fake_process,
            ) as start_asr,
        ):
            process, pid = live_watchdog.ensure_asr_started()

        self.assertIs(process, fake_process)
        self.assertIsNone(pid)
        running.assert_called_once_with(live_watchdog.ASR_LOCK_PATH)
        start_asr.assert_called_once_with()

    def test_login_pause_is_cleared_when_login_process_already_exited(self) -> None:
        pause_path = Path(self.temp_dir.name) / "buyin-live-pause"
        pause_path.write_text(
            json.dumps({"mode": "login", "pid": 2_000_000_000}),
            encoding="utf-8",
        )

        active = live_watchdog.screen_pause_active(
            pause_path,
            "百应登录暂停",
        )

        self.assertFalse(active)
        self.assertFalse(pause_path.exists())

    def test_open_append_log_falls_back_when_primary_is_read_only(self) -> None:
        primary = Path(self.temp_dir.name) / "live-server.log"
        primary.write_text("existing", encoding="utf-8")
        primary.chmod(stat.S_IREAD)
        try:
            handle = live_watchdog.open_append_log(primary)
            try:
                handle.write("fallback")
            finally:
                handle.close()
            fallback = primary.with_name("live-server.active.log")
            self.assertEqual(fallback.read_text(encoding="utf-8"), "fallback")
        finally:
            primary.chmod(stat.S_IWRITE | stat.S_IREAD)


if __name__ == "__main__":
    unittest.main()
