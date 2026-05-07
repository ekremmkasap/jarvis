from __future__ import annotations

from typing import Any, Callable


ToolFn = Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """Minimal registry for executor-callable tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        key = str(name or "").strip().lower()
        if not key:
            raise ValueError("tool name is required")
        if not callable(fn):
            raise TypeError("tool function must be callable")
        self._tools[key] = fn

    def has(self, name: str) -> bool:
        return str(name or "").strip().lower() in self._tools

    def execute(self, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        key = str(name or "").strip().lower()
        if key not in self._tools:
            raise KeyError(f"tool_not_found:{key}")
        body = payload if isinstance(payload, dict) else {}
        return self._tools[key](body)

