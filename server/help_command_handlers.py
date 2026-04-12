from __future__ import annotations

from collections import OrderedDict
from typing import Any


def registry_help(args: str = "", context: dict[str, Any] | None = None) -> str:
    del args
    registry = (context or {}).get("registry")
    if registry is None:
        return "Komutlar:\n[genel] /yardim"

    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for entry in registry.list_commands():
        category = str(entry.category or "general")
        grouped.setdefault(category, [])
        grouped[category].append(entry.command)

    lines = ["Komutlar:"]
    for category, commands in grouped.items():
        unique_commands = []
        seen: set[str] = set()
        for command in commands:
            if command not in seen:
                unique_commands.append(command)
                seen.add(command)
        lines.append(f"[{category}] " + ", ".join(unique_commands))

    return _truncate_help("\n".join(lines))


def _truncate_help(text: str, limit: int = 400) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)].rstrip() + "..."
