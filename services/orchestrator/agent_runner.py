from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.orchestrator.task_queue import TaskQueue, Task, TaskStatus

log = logging.getLogger("orchestrator.runner")

MAX_CONCURRENT = 4


class AgentRunner:
    """Pulls tasks from queue and dispatches to agent implementations."""

    def __init__(self, queue: TaskQueue, broadcaster, safety):
        self._queue = queue
        self._broadcaster = broadcaster
        self._safety = safety
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._agent_registry: dict[str, Any] = {}
        self._register_agents()

    def _register_agents(self):
        try:
            from agents.planner_agent import PlannerAgent
            from agents.repo_analyst_agent import RepoAnalystAgent
            from agents.developer_agent import DeveloperAgent
            from agents.reviewer_agent import ReviewerAgent
            from agents.debug_agent import DebugAgent
            from agents.release_agent import ReleaseAgent
            from agents.docs_agent import DocsAgent
            from agents.voice_narrator_agent import VoiceNarratorAgent
            from agents.mission_control_agent import MissionControlAgent

            self._agent_registry = {
                "planner": PlannerAgent,
                "repo_analyst": RepoAnalystAgent,
                "developer": DeveloperAgent,
                "reviewer": ReviewerAgent,
                "debug": DebugAgent,
                "release": ReleaseAgent,
                "docs": DocsAgent,
                "voice_narrator": VoiceNarratorAgent,
                "mission_control": MissionControlAgent,
            }
            log.info("Registered agents: %s", list(self._agent_registry.keys()))
        except ImportError as e:
            log.warning("Agent import error: %s", e)

    def list_agents(self) -> list[dict]:
        return [
            {"name": name, "class": cls.__name__}
            for name, cls in self._agent_registry.items()
        ]

    async def run_loop(self):
        log.info("Agent runner loop started")
        while True:
            task = await self._queue.get_next()
            asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: Task):
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc).isoformat()
            await self._broadcaster.broadcast({"event": "task_started", "task": task.to_dict()})
            log.info("Executing task %s via agent '%s'", task.id, task.agent)

            try:
                result = await self._dispatch(task)
                task.status = TaskStatus.DONE
                task.result = str(result)
                task.finished_at = datetime.now(timezone.utc).isoformat()
            except Exception as exc:
                log.exception("Task %s failed: %s", task.id, exc)
                if task.retries < task.max_retries:
                    task.retries += 1
                    task.status = TaskStatus.QUEUED
                    await self._queue.enqueue(task)
                    await self._broadcaster.broadcast(
                        {"event": "task_retry", "task": task.to_dict()}
                    )
                    self._queue.task_done()
                    return
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                task.finished_at = datetime.now(timezone.utc).isoformat()

            self._queue.task_done()
            await self._broadcaster.broadcast(
                {"event": "task_updated", "task": task.to_dict()}
            )

    async def _dispatch(self, task: Task) -> str:
        agent_cls = self._agent_registry.get(task.agent)
        if not agent_cls:
            return f"[No agent registered for '{task.agent}'] Goal: {task.goal}"

        agent = agent_cls()
        loop = asyncio.get_event_loop()

        if asyncio.iscoroutinefunction(agent.execute_task):
            return await agent.execute_task(task)
        return await loop.run_in_executor(None, agent.execute_task, task)
