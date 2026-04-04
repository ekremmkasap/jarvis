from __future__ import annotations

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


def execute_step(
    step: dict[str, Any],
    *,
    tool_registry: ToolRegistry,
    run_id: str = "",
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    return ExecutorAgent(tool_registry=tool_registry, logger=logger).execute_step(step, run_id=run_id)
