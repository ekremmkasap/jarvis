from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    id: str
    goal: str
    agent: str
    priority: TaskPriority = TaskPriority.NORMAL
    context: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    status: TaskStatus = TaskStatus.QUEUED
    result: Optional[str] = None
    error: Optional[str] = None
    requires_confirmation: bool = False
    retries: int = 0
    max_retries: int = 2

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "agent": self.agent,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
            "dry_run": self.dry_run,
            "requires_confirmation": self.requires_confirmation,
            "retries": self.retries,
        }


class TaskQueue:
    def __init__(self, broadcaster=None):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._all: dict[str, Task] = {}
        self._broadcaster = broadcaster
        self._lock = asyncio.Lock()

    async def enqueue(self, task: Task):
        if task.requires_confirmation:
            task.status = TaskStatus.AWAITING_CONFIRMATION
        async with self._lock:
            self._all[task.id] = task
        if not task.requires_confirmation:
            await self._queue.put(task)

    async def get_next(self) -> Task:
        return await self._queue.get()

    def get(self, task_id: str) -> Optional[Task]:
        return self._all.get(task_id)

    def get_all(self, limit: int = 50) -> list[Task]:
        items = list(self._all.values())
        items.sort(key=lambda t: t.created_at, reverse=True)
        return items[:limit]

    def size(self) -> int:
        return self._queue.qsize()

    def task_done(self):
        self._queue.task_done()
