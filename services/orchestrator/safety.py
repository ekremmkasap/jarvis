from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


DESTRUCTIVE_PATTERNS = [
    r"git\s+push\s+--force",
    r"git\s+reset\s+--hard",
    r"rm\s+-rf",
    r"DROP\s+TABLE",
    r"DELETE\s+FROM",
    r"merge.*main",
    r"merge.*master",
    r"rotate.*secret",
    r"delete.*file",
    r"format.*disk",
]

ALLOWED_AUTO_PATTERNS = [
    r"triage",
    r"summarize",
    r"review",
    r"analyze",
    r"draft",
    r"suggest",
    r"report",
    r"scan",
    r"check",
    r"update.*doc",
    r"update.*readme",
    r"update.*agents",
    r"changelog",
    r"release.*notes",
    r"daily.*summary",
    r"weekly.*digest",
]


@dataclass
class SafetyResult:
    blocked: bool
    requires_confirmation: bool
    reason: str
    risk_score: float  # 0.0 - 1.0


class SafetyViolation(Exception):
    pass


class SafetyPolicy:
    def __init__(self):
        self._destructive = [re.compile(p, re.IGNORECASE) for p in DESTRUCTIVE_PATTERNS]
        self._allowed = [re.compile(p, re.IGNORECASE) for p in ALLOWED_AUTO_PATTERNS]

    def check(self, goal: str, agent: str, context: dict[str, Any] = None) -> SafetyResult:
        context = context or {}

        # Check destructive patterns — require confirmation
        for pattern in self._destructive:
            if pattern.search(goal):
                return SafetyResult(
                    blocked=False,
                    requires_confirmation=True,
                    reason=f"Destructive operation detected: '{pattern.pattern}'",
                    risk_score=0.9,
                )

        # Explicitly allowed auto-operations
        for pattern in self._allowed:
            if pattern.search(goal):
                return SafetyResult(
                    blocked=False,
                    requires_confirmation=False,
                    reason="Routine operation — auto-approved",
                    risk_score=0.1,
                )

        # Protected branch merge
        if "merge" in goal.lower() and any(
            b in goal.lower() for b in ["main", "master", "prod", "release"]
        ):
            return SafetyResult(
                blocked=False,
                requires_confirmation=True,
                reason="Protected branch merge requires confirmation",
                risk_score=0.8,
            )

        # Shell execution
        if any(
            k in goal.lower()
            for k in ["execute", "run shell", "bash", "cmd", "powershell", "subprocess"]
        ):
            return SafetyResult(
                blocked=False,
                requires_confirmation=True,
                reason="Shell execution requires confirmation",
                risk_score=0.7,
            )

        # Default: allow
        return SafetyResult(
            blocked=False,
            requires_confirmation=False,
            reason="Standard task",
            risk_score=0.3,
        )
