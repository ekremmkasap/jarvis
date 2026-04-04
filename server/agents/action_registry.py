from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class ActionRegistry:
    allowed_actions: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_actions(cls, actions: Iterable[str]) -> "ActionRegistry":
        normalized = {str(action).strip().lower() for action in actions if str(action).strip()}
        return cls(allowed_actions=frozenset(normalized))

    def is_allowed(self, action: str) -> bool:
        return str(action).strip().lower() in self.allowed_actions

    def require_allowed(self, action: str) -> None:
        normalized = str(action).strip().lower()
        if normalized not in self.allowed_actions:
            raise ValueError(f"Action is not registered: {normalized}")


DEFAULT_ACTION_REGISTRY = ActionRegistry.from_actions(
    [
        "analyze",
        "design",
        "implement",
        "test",
        "review",
        "document",
        "verify",
    ]
)

