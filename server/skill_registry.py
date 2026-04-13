from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


# bridge.py legacy handle_command chain currently contains 81 elif branches.
@dataclass
class SkillEntry:
    command: str
    handler: Callable
    description: str
    aliases: list[str] = field(default_factory=list)
    requires_args: bool = False
    min_args: int = 0
    category: str = "general"


class SkillRegistry:
    def __init__(self):
        self._registry: dict[str, SkillEntry] = {}

    def register(self, entry: SkillEntry):
        self._registry[entry.command] = entry
        for alias in entry.aliases:
            self._registry[alias] = entry

    def dispatch(self, command: str, args: str = "", context: Optional[dict] = None) -> str:
        entry = self._registry.get(command)
        if not entry:
            return f"Bilinmeyen komut: {command}"

        try:
            import asyncio
            import inspect

            if inspect.iscoroutinefunction(entry.handler):
                result = asyncio.run(entry.handler(args, context or {}))
            else:
                result = entry.handler(args, context or {})
            return str(result)[:400]
        except Exception as exc:
            return f"Hata ({command}): {exc}"

    def list_commands(self, category: Optional[str] = None) -> list[SkillEntry]:
        seen: set[str] = set()
        result: list[SkillEntry] = []
        for _, entry in self._registry.items():
            if entry.command in seen:
                continue
            if category is None or entry.category == category:
                result.append(entry)
                seen.add(entry.command)
        return result

    def get_help(self, command: str) -> str:
        entry = self._registry.get(command)
        if not entry:
            return f"{command}: bilinmiyor"
        return f"{entry.command}: {entry.description}"
