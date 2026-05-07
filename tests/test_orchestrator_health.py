from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch


class OrchestratorHealthTests(unittest.TestCase):
    def test_health_exposes_queue_snapshot(self) -> None:
        with patch("uvicorn.run"):
            from fastapi.testclient import TestClient
            from services.orchestrator.main import app, queue

        original_all = queue._all
        original_last_order = queue._last_order
        try:
            queue._all = {}
            queue._last_order = 0

            with patch("services.orchestrator.main.runner.run_loop", new=AsyncMock()):
                with patch("services.orchestrator.main._mirror_voice_runtime_events", new=AsyncMock()):
                    with TestClient(app) as client:
                        response = client.get("/health")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["queue_size"], 0)
            self.assertEqual(payload["awaiting_confirmation"], 0)
            self.assertEqual(payload["running_tasks"], 0)
            self.assertIn("queue_snapshot", payload)
            self.assertIn("recent_events", payload)
            self.assertIn("voice_runtime", payload)
            self.assertEqual(payload["queue_snapshot"]["queued_by_priority"]["critical"], 0)
            self.assertEqual(payload["queue_snapshot"]["total_tasks"], 0)
        finally:
            queue._all = original_all
            queue._last_order = original_last_order

    def test_health_exposes_live_contract_used_by_dashboard(self) -> None:
        with patch("uvicorn.run"):
            from fastapi.testclient import TestClient
            from services.orchestrator.main import app, queue

        original_all = queue._all
        original_last_order = queue._last_order
        try:
            queue._all = {}
            queue._last_order = 0

            with patch("services.orchestrator.main.runner.run_loop", new=AsyncMock()):
                with patch("services.orchestrator.main._mirror_voice_runtime_events", new=AsyncMock()):
                    with TestClient(app) as client:
                        response = client.get("/health")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIsInstance(payload["recent_events"], list)
            self.assertEqual(
                set(payload["queue_snapshot"]["queued_by_priority"].keys()),
                {"critical", "high", "normal", "low"},
            )
            self.assertEqual(
                set(payload["voice_runtime"].keys()),
                {"phase", "status", "updated_at"},
            )
            self.assertIn(payload["voice_runtime"]["phase"], {"idle", "listening", "thinking", "speaking"})
            self.assertIsInstance(payload["voice_runtime"]["updated_at"], (float, int))
        finally:
            queue._all = original_all
            queue._last_order = original_last_order
