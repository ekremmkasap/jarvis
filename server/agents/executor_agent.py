from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.agents.tool_registry import ToolRegistry


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "executor_agent.log"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("agent.executor")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == LOG_FILE for handler in logger.handlers):
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
    return logger


class ExecutorAgent:
    """Executes a single planner step through registered tools."""

    # Step type timeouts (seconds)
    STEP_TIMEOUTS = {
        "read": 5.0,
        "write": 10.0,
        "api": 15.0,
        "process": 20.0,
        "default": 30.0,
    }

    # Max parallel steps to execute concurrently
    MAX_PARALLEL_STEPS = 3

    def __init__(self, tool_registry: ToolRegistry, logger: logging.Logger | None = None) -> None:
        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError("tool_registry must be ToolRegistry")
        self.tool_registry = tool_registry
        self.logger = logger or _build_logger()

    def execute_step(self, step: dict[str, Any], run_id: str = "") -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        safe_run_id = str(run_id or "default")

        try:
            action = str(step.get("action") or "").strip().lower()
            if not action:
                raise ValueError("step.action is required")

            payload = step.get("params")
            if payload is None:
                payload = {}
            if not isinstance(payload, dict):
                raise TypeError("step.params must be an object")

            if not self.tool_registry.has(action):
                raise KeyError(f"tool_not_registered:{action}")

            result = self.tool_registry.execute(action, payload)
            if not isinstance(result, dict):
                result = {"result": result}

            output = {
                "ok": True,
                "run_id": safe_run_id,
                "action": action,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "result": result,
                "error": None,
            }
            self.logger.info("step_executed run_id=%s action=%s", safe_run_id, action)
            return output
        except Exception as exc:
            output = {
                "ok": False,
                "run_id": safe_run_id,
                "action": str(step.get("action") or "").strip().lower(),
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "result": None,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }
            self.logger.error(
                "step_failed run_id=%s action=%s error=%s",
                safe_run_id,
                output["action"],
                str(exc),
            )
            return output

    def _get_step_timeout(self, step: dict[str, Any]) -> float:
        """Get timeout for a step based on its action type."""
        action = str(step.get("action") or "").strip().lower()
        # Extract prefix (e.g., "read_file" -> "read")
        prefix = action.split("_")[0] if "_" in action else action
        return self.STEP_TIMEOUTS.get(prefix, self.STEP_TIMEOUTS["default"])

    async def _execute_step_async(self, step: dict[str, Any], run_id: str = "") -> dict[str, Any]:
        """Execute a single step asynchronously with timeout."""
        timeout = self._get_step_timeout(step)
        try:
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, self.execute_step, step, run_id),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            started_at = datetime.now(timezone.utc)
            safe_run_id = str(run_id or "default")
            output = {
                "ok": False,
                "run_id": safe_run_id,
                "action": str(step.get("action") or "").strip().lower(),
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "result": None,
                "error": {
                    "type": "TimeoutError",
                    "message": f"step timed out after {timeout}s",
                },
            }
            self.logger.error(
                "step_timeout run_id=%s action=%s timeout=%s",
                safe_run_id,
                output["action"],
                timeout,
            )
            return output

    async def execute_plan_async(
        self,
        plan: list[dict[str, Any]],
        run_id: str = "",
        chunk_size: int | None = None,
    ) -> dict[str, Any]:
        """Execute a list of independent steps in parallel (chunked by MAX_PARALLEL_STEPS)."""
        safe_run_id = str(run_id or "default")
        if not isinstance(plan, list):
            raise TypeError("plan must be a list of steps")

        if not plan:
            return {
                "ok": True,
                "run_id": safe_run_id,
                "results": [],
                "total_steps": 0,
                "parallel_chunks": 0,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
            }

        started_at = datetime.now(timezone.utc)
        chunk_size = chunk_size or self.MAX_PARALLEL_STEPS
        results = []
        has_error = False

        # Process steps in chunks
        for i in range(0, len(plan), chunk_size):
            chunk = plan[i : i + chunk_size]
            tasks = [
                self._execute_step_async(step, run_id=safe_run_id)
                for step in chunk
            ]
            chunk_results = await asyncio.gather(*tasks)
            results.extend(chunk_results)

            # Check if any step failed
            if any(not r.get("ok", False) for r in chunk_results):
                has_error = True
                # Continue processing remaining steps even if one fails
                self.logger.warning(
                    "chunk_processing_continued_after_error run_id=%s chunk=%d",
                    safe_run_id,
                    i // chunk_size + 1,
                )

        output = {
            "ok": not has_error,
            "run_id": safe_run_id,
            "results": results,
            "total_steps": len(plan),
            "parallel_chunks": (len(plan) + chunk_size - 1) // chunk_size,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error": None if not has_error else {"type": "StepFailed", "message": "one or more steps failed"},
        }
        self.logger.info(
            "plan_executed run_id=%s total_steps=%d chunks=%d ok=%s",
            safe_run_id,
            len(plan),
            output["parallel_chunks"],
            output["ok"],
        )
        return output


def execute_step(
    step: dict[str, Any],
    *,
    tool_registry: ToolRegistry,
    run_id: str = "",
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    return ExecutorAgent(tool_registry=tool_registry, logger=logger).execute_step(step, run_id=run_id)


def execute_plan(
    plan: list[dict[str, Any]],
    *,
    tool_registry: ToolRegistry,
    run_id: str = "",
    logger: logging.Logger | None = None,
    chunk_size: int | None = None,
) -> dict[str, Any]:
    """Execute a plan of independent steps in parallel (synchronous wrapper)."""
    agent = ExecutorAgent(tool_registry=tool_registry, logger=logger)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(agent.execute_plan_async(plan, run_id=run_id, chunk_size=chunk_size))
    finally:
        loop.close()
