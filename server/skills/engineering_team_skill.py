"""Engineering team skill — Seda (forge) + Sabrican (nexus) Codex slot koordinasyonu."""
from __future__ import annotations

from typing import Any

try:
    from skills.swarm_skill import swarm_run  # type: ignore
except Exception:
    from server.skills.swarm_skill import swarm_run  # type: ignore


def run_engineering_team(goal: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    personas = context.get("personas") or ["seda", "sabrican"]
    result = swarm_run(goal, personas=personas)
    header = f"ENGINEERING TEAM ({', '.join(personas)}) — hedef: {goal[:80]}"
    return f"{header}\n{result}"
