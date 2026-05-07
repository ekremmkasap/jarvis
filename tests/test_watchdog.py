from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server import watchdog


class WatchdogCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.heartbeat = self.data_dir / "bridge_heartbeat.json"
        self.lock_file = self.data_dir / "bridge.lock"
        self.log_file = self.data_dir / "watchdog.log"

        self._patches = [
            patch.object(watchdog, "DATA", self.data_dir),
            patch.object(watchdog, "HEARTBEAT", self.heartbeat),
            patch.object(watchdog, "LOCK_FILE", self.lock_file),
            patch.object(watchdog, "WATCHDOG_LOG", self.log_file),
        ]
        for item in self._patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self._patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_cleanup_stale_bridge_state_removes_dead_heartbeat_and_lock(self) -> None:
        self.heartbeat.write_text(json.dumps({"pid": 4242, "updated_at": "2026-04-04T00:00:00Z"}), encoding="utf-8")
        self.lock_file.write_text("4242", encoding="utf-8")

        with patch.object(watchdog, "_pid_alive", return_value=False):
            watchdog._cleanup_stale_bridge_state()

        self.assertFalse(self.heartbeat.exists())
        self.assertFalse(self.lock_file.exists())

    def test_cleanup_bridge_state_for_pid_only_removes_matching_pid(self) -> None:
        self.heartbeat.write_text(json.dumps({"pid": 5000, "updated_at": "2026-04-04T00:00:00Z"}), encoding="utf-8")
        self.lock_file.write_text("5000", encoding="utf-8")

        watchdog._cleanup_bridge_state_for_pid(4000)

        self.assertTrue(self.heartbeat.exists())
        self.assertTrue(self.lock_file.exists())

    def test_cleanup_bridge_state_for_pid_removes_matching_pid(self) -> None:
        self.heartbeat.write_text(json.dumps({"pid": 6000, "updated_at": "2026-04-04T00:00:00Z"}), encoding="utf-8")
        self.lock_file.write_text("6000", encoding="utf-8")

        watchdog._cleanup_bridge_state_for_pid(6000)

        self.assertFalse(self.heartbeat.exists())
        self.assertFalse(self.lock_file.exists())


if __name__ == "__main__":
    unittest.main()
