from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from services.orchestrator import live_state


class OrchestratorLiveStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.events_file = self.base / "live_events.jsonl"
        self.state_file = self.base / "task_queue.json"
        self.runtime_file = self.base / "desktop_assistant.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_append_and_read_recent_live_events(self) -> None:
        live_state.append_live_event(
            {
                "event": "task_created",
                "task": {"id": "t-1", "agent": "planner", "goal": "prepare release", "status": "queued"},
            },
            events_file=self.events_file,
        )
        live_state.append_live_event(
            {
                "event": "runtime_state",
                "phase": "listening",
                "runtime": {"status": "online", "detail": "wake word active"},
                "voice": {"last_heard": "hey jarvis", "turn_count": 3},
            },
            events_file=self.events_file,
        )

        events = live_state.read_recent_live_events(limit=10, events_file=self.events_file)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event"], "task_created")
        self.assertEqual(events[1]["event"], "runtime_state")
        self.assertIn("queued", events[0]["message"])
        self.assertIn("voice listening", events[1]["message"])

    def test_load_task_queue_snapshot_matches_status_counts(self) -> None:
        payload = {
            "last_order": 7,
            "tasks": [
                {"id": "1", "status": "queued", "priority": "high", "created_at": "2026-04-10T10:00:00+00:00"},
                {"id": "2", "status": "running", "priority": "normal", "created_at": "2026-04-10T10:05:00+00:00"},
                {"id": "3", "status": "done", "priority": "normal", "created_at": "2026-04-10T10:10:00+00:00"},
                {"id": "4", "status": "failed", "priority": "critical", "created_at": "2026-04-10T10:15:00+00:00"},
            ],
        }
        self.state_file.write_text(json.dumps(payload), encoding="utf-8")

        snapshot = live_state.load_task_queue_snapshot(state_file=self.state_file)

        self.assertEqual(snapshot["total_tasks"], 4)
        self.assertEqual(snapshot["queued_tasks"], 1)
        self.assertEqual(snapshot["running_tasks"], 1)
        self.assertEqual(snapshot["done_tasks"], 1)
        self.assertEqual(snapshot["failed_tasks"], 1)
        self.assertEqual(snapshot["queued_by_priority"]["high"], 1)
        self.assertEqual(snapshot["last_queue_order"], 7)

    def test_load_runtime_snapshot_merges_defaults(self) -> None:
        self.runtime_file.write_text(
            json.dumps(
                {
                    "phase": "speaking",
                    "runtime": {"status": "online"},
                    "voice": {"last_response": "done"},
                }
            ),
            encoding="utf-8",
        )

        runtime = live_state.load_runtime_snapshot(runtime_file=self.runtime_file)

        self.assertEqual(runtime["phase"], "speaking")
        self.assertEqual(runtime["runtime"]["status"], "online")
        self.assertEqual(runtime["voice"]["last_response"], "done")
        self.assertIn("turn_count", runtime["voice"])
