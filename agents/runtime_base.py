from __future__ import annotations

"""Runtime base agent for orchestrator-driven execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import logging
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@dataclass
class TaskInput:
    id: str
    goal: str
    agent: str
    context: dict[str, Any]
    dry_run: bool = False


class RuntimeAgent(ABC):
    """Base for all orchestrator-dispatched agents."""

    name: str = "base"
    description: str = ""
    risk_level: str = "low"
    model_chain: str = "default"

    def __init__(self):
        self.log = logging.getLogger(f"agent.{self.name}")

    def _get_router(self):
        try:
            from server.model_router import build_model_router
            return build_model_router(ROOT, "http://127.0.0.1:11434", 120)
        except Exception as e:
            self.log.warning("Model router unavailable: %s", e)
            return None

    def llm_call(self, prompt: str, system: Optional[str] = None, max_tokens: int = 2048) -> str:
        router = self._get_router()
        if not router:
            return self.fallback_response(prompt)

        messages = [{"role": "user", "content": prompt}]
        response, trace = router.chat(
            route_name=self.model_chain,
            primary_model="qwen3:8b",
            fallback_model=None,
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            num_ctx=8192,
        )
        if trace.get("ok"):
            self.log.debug(
                "LLM success via %s", trace.get("selected_candidate")
            )
            return response

        self.log.warning("LLM call failed: %s", trace.get("error"))
        return self.fallback_response(prompt)

    def fallback_response(self, prompt: str) -> str:
        return (
            f"[{self.name}] LLM unavailable — cannot process goal: "
            f"{prompt[:200]}"
        )

    @abstractmethod
    def execute_task(self, task) -> str:
        """Execute the task. Return result as string."""
        ...
