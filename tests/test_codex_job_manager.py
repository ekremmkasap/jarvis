from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.codex_job_manager import CodexJobManager


class CodexJobManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        self.manager = CodexJobManager(root_dir=self.temp_root)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_enqueue_persists_to_jsonl_and_legacy_snapshot(self) -> None:
        job_id = self.manager.enqueue(
            {
                "role": "backend",
                "priority": 8,
                "task": {"description": "bridge endpoint", "type": "backend", "payload": {}},
            }
        )

        self.assertTrue((self.temp_root / "state" / "codex_jobs.jsonl").exists())
        self.assertTrue((self.temp_root / "state" / "codex-accounts" / "job_queue.json").exists())
        self.assertEqual(self.manager.get_job(job_id)["status"], "pending")
        self.assertEqual(self.manager.get_job(job_id)["type"], "backend")

    def test_dequeue_picks_highest_priority_pending_job(self) -> None:
        self.manager.enqueue({"role": "backend", "priority": 2, "task": {"description": "low", "type": "backend", "payload": {}}})
        high_id = self.manager.enqueue({"role": "backend", "priority": 9, "task": {"description": "high", "type": "backend", "payload": {}}})

        job = self.manager.dequeue(role="backend")

        self.assertIsNotNone(job)
        self.assertEqual(job["id"], high_id)
        self.assertEqual(job["status"], "running")

    def test_retry_and_cancel_job_update_state(self) -> None:
        job_id = self.manager.enqueue({"role": "backend", "priority": 5, "task": {"description": "job", "type": "backend", "payload": {}}})
        self.manager.update_job(job_id, status="failed", failure_reason="boom")

        retried = self.manager.retry_job(job_id)
        cancelled = self.manager.cancel_job(job_id)

        self.assertEqual(retried["status"], "pending")
        self.assertEqual(retried["retries"], 1)
        self.assertEqual(cancelled["status"], "cancelled")

    def test_find_stuck_jobs_returns_old_running_jobs(self) -> None:
        job_id = self.manager.enqueue({"role": "backend", "priority": 5, "task": {"description": "job", "type": "backend", "payload": {}}})
        old_started = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
        self.manager.update_job(job_id, status="running", started_at=old_started)

        stuck = self.manager.find_stuck_jobs(timeout_minutes=30)

        self.assertEqual(len(stuck), 1)
        self.assertEqual(stuck[0]["id"], job_id)

    def test_purge_old_jobs_removes_terminal_records(self) -> None:
        old_completed = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        old_id = self.manager.enqueue({"role": "backend", "priority": 5, "task": {"description": "old", "type": "backend", "payload": {}}})
        new_id = self.manager.enqueue({"role": "backend", "priority": 5, "task": {"description": "new", "type": "backend", "payload": {}}})
        self.manager.update_job(old_id, status="done", completed_at=old_completed, finished_at=old_completed)
        self.manager.update_job(new_id, status="running")

        removed = self.manager.purge_old_jobs(days=7)
        jobs = self.manager.list_jobs(limit=10)

        self.assertEqual(removed, 1)
        self.assertTrue(all(job["id"] != old_id for job in jobs))
        self.assertTrue(any(job["id"] == new_id for job in jobs))

    def test_enqueue_accepts_flat_description_payload_and_normalizes_task(self) -> None:
        job_id = self.manager.enqueue(
            {
                "role": "backend",
                "description": "smoke test job",
                "payload": {"source": "bridge"},
            }
        )

        job = self.manager.get_job(job_id)

        self.assertEqual(job["task"], "smoke test job")
        self.assertEqual(job["type"], "backend")

    def test_list_jobs_can_filter_by_status_and_slot(self) -> None:
        pending_id = self.manager.enqueue({"role": "backend", "priority": 4, "task": {"description": "pending", "type": "backend", "payload": {}}})
        running_id = self.manager.enqueue({"role": "voice", "priority": 7, "task": {"description": "running", "type": "voice", "payload": {}}})
        self.manager.update_job(running_id, status="running", slot_id="spark")

        running_jobs = self.manager.list_jobs(status="running", slot_id="spark", limit=10)
        empty_jobs = self.manager.list_jobs(limit=0)

        self.assertEqual([job["id"] for job in running_jobs], [running_id])
        self.assertTrue(any(job["id"] == pending_id for job in self.manager.list_jobs(limit=10)))
        self.assertEqual(empty_jobs, [])


if __name__ == "__main__":
    unittest.main()
