from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from services.orchestrator.task_queue import Task, TaskPriority, TaskQueue, TaskStatus


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskQueueTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "task_queue.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _queue(self) -> TaskQueue:
        return TaskQueue(state_file=self.state_file)

    def _task(
        self,
        task_id: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        *,
        requires_confirmation: bool = False,
    ) -> Task:
        return Task(
            id=task_id,
            goal=f"goal-{task_id}",
            agent="planner",
            priority=priority,
            created_at=_now(),
            requires_confirmation=requires_confirmation,
        )

    async def test_priority_order_is_respected(self) -> None:
        queue = self._queue()
        low = self._task("low", TaskPriority.LOW)
        critical = self._task("critical", TaskPriority.CRITICAL)
        normal = self._task("normal", TaskPriority.NORMAL)

        await queue.enqueue(low)
        await queue.enqueue(critical)
        await queue.enqueue(normal)

        first = await asyncio.wait_for(queue.get_next(), timeout=1)
        self.assertEqual(first.id, "critical")
        queue.task_done()

        second = await asyncio.wait_for(queue.get_next(), timeout=1)
        self.assertEqual(second.id, "normal")
        queue.task_done()

        third = await asyncio.wait_for(queue.get_next(), timeout=1)
        self.assertEqual(third.id, "low")
        queue.task_done()

    async def test_queue_persists_and_recovers_running_tasks(self) -> None:
        queue = self._queue()
        queued = self._task("queued")
        awaiting = self._task("awaiting", requires_confirmation=True)
        running = self._task("running")
        running.status = TaskStatus.RUNNING
        running.started_at = _now()

        await queue.enqueue(queued)
        await queue.enqueue(awaiting)
        await queue.save_task(running)

        reloaded = self._queue()

        self.assertEqual(reloaded.get("queued").status, TaskStatus.QUEUED)
        self.assertEqual(reloaded.get("awaiting").status, TaskStatus.AWAITING_CONFIRMATION)
        self.assertEqual(reloaded.get("running").status, TaskStatus.QUEUED)

        first = await asyncio.wait_for(reloaded.get_next(), timeout=1)
        self.assertEqual(first.id, "queued")
        reloaded.task_done()

        second = await asyncio.wait_for(reloaded.get_next(), timeout=1)
        self.assertEqual(second.id, "running")
        reloaded.task_done()

    async def test_confirm_moves_task_back_to_queue(self) -> None:
        queue = self._queue()
        task = self._task("confirm-me", requires_confirmation=True)
        await queue.enqueue(task)

        self.assertEqual(queue.get(task.id).status, TaskStatus.AWAITING_CONFIRMATION)
        confirmed = await queue.confirm(task.id)

        self.assertIsNotNone(confirmed)
        self.assertFalse(confirmed.requires_confirmation)
        self.assertEqual(confirmed.status, TaskStatus.QUEUED)

        next_task = await asyncio.wait_for(queue.get_next(), timeout=1)
        self.assertEqual(next_task.id, "confirm-me")
        queue.task_done()

    async def test_confirm_rejects_non_awaiting_task(self) -> None:
        queue = self._queue()
        task = self._task("plain")
        await queue.enqueue(task)

        with self.assertRaisesRegex(ValueError, "task_not_awaiting_confirmation"):
            await queue.confirm(task.id)

    async def test_snapshot_reports_status_and_priority_counts(self) -> None:
        queue = self._queue()
        queued = self._task("queued", TaskPriority.HIGH)
        waiting = self._task("waiting", requires_confirmation=True)
        running = self._task("running", TaskPriority.CRITICAL)
        running.status = TaskStatus.RUNNING
        running.started_at = _now()

        await queue.enqueue(queued)
        await queue.enqueue(waiting)
        await queue.save_task(running)

        snapshot = queue.snapshot()

        self.assertEqual(snapshot["total_tasks"], 3)
        self.assertEqual(snapshot["queued_tasks"], 1)
        self.assertEqual(snapshot["running_tasks"], 1)
        self.assertEqual(snapshot["awaiting_confirmation_tasks"], 1)
        self.assertEqual(snapshot["queued_by_priority"]["high"], 1)
        self.assertEqual(snapshot["queued_by_priority"]["critical"], 0)
        self.assertEqual(snapshot["status_counts"]["running"], 1)
        self.assertEqual(snapshot["state_file"], str(self.state_file))


if __name__ == "__main__":
    unittest.main()
