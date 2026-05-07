from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from server.agents.action_registry import ActionRegistry, DEFAULT_ACTION_REGISTRY


LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "task_planner_agent.log"


class PlannerError(Exception):
    """Base planner error."""


class InvalidPlanError(PlannerError):
    """Raised when the generated plan has invalid steps."""


@dataclass(frozen=True)
class PlanStep:
    action: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {"action": self.action, "description": self.description}


@dataclass(frozen=True)
class PlanResult:
    ok: bool
    steps: list[PlanStep]
    error: str | None = None


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("jarvis.task_planner_agent")
    if logger.handlers:
        return logger
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


class TaskPlannerAgent:
    def __init__(self, action_registry: ActionRegistry | None = None) -> None:
        self._registry = action_registry or DEFAULT_ACTION_REGISTRY
        self._log = _build_logger()

    def plan(
        self,
        goal: str,
        *,
        max_steps: int = 7,
        requested_actions: Iterable[str] | None = None,
    ) -> PlanResult:
        try:
            clean_goal = str(goal or "").strip()
            if not clean_goal:
                raise PlannerError("Goal cannot be empty.")
            if max_steps <= 0:
                raise PlannerError("max_steps must be positive.")

            steps = self._generate_steps(clean_goal, max_steps=max_steps, requested_actions=requested_actions)
            self._validate_steps(steps)
            self._log.info("plan_success goal=%s step_count=%d", clean_goal[:120], len(steps))
            return PlanResult(ok=True, steps=steps)
        except PlannerError as exc:
            self._log.warning("plan_error goal=%s error=%s", str(goal)[:120], str(exc))
            return PlanResult(ok=False, steps=[], error=str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            self._log.exception("plan_unexpected_error goal=%s", str(goal)[:120])
            return PlanResult(ok=False, steps=[], error=f"Unexpected planner error: {exc}")

    def _generate_steps(
        self,
        goal: str,
        *,
        max_steps: int,
        requested_actions: Iterable[str] | None,
    ) -> list[PlanStep]:
        if requested_actions is not None:
            actions = [str(action).strip().lower() for action in requested_actions if str(action).strip()]
            if not actions:
                raise PlannerError("requested_actions was provided but empty.")
            return [
                PlanStep(action=action, description=f"{action.capitalize()} for goal: {goal}")
                for action in actions[:max_steps]
            ]

        goal_lower = goal.lower()
        actions: list[str] = ["analyze", "design", "implement", "test", "review", "document", "verify"]

        if "quick" in goal_lower or "hotfix" in goal_lower:
            actions = ["analyze", "implement", "test", "verify"]
        elif "docs" in goal_lower or "documentation" in goal_lower:
            actions = ["analyze", "design", "document", "review", "verify"]

        limited = actions[: min(max_steps, 7)]
        return [PlanStep(action=action, description=f"{action.capitalize()} step for: {goal}") for action in limited]

    def _validate_steps(self, steps: list[PlanStep]) -> None:
        if not steps:
            raise InvalidPlanError("Generated plan has no steps.")
        if len(steps) > 7:
            raise InvalidPlanError("Generated plan exceeds the 7-step limit.")
        for step in steps:
            if not step.description.strip():
                raise InvalidPlanError(f"Step description is empty for action '{step.action}'.")
            if not self._registry.is_allowed(step.action):
                raise InvalidPlanError(f"Unregistered action in plan: {step.action}")


def plan(
    goal: str,
    *,
    max_steps: int = 7,
    requested_actions: Iterable[str] | None = None,
    action_registry: ActionRegistry | None = None,
) -> PlanResult:
    return TaskPlannerAgent(action_registry=action_registry).plan(
        goal,
        max_steps=max_steps,
        requested_actions=requested_actions,
    )
