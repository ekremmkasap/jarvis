from __future__ import annotations

from .base import CanonicalAgent
from .debug_agent import DebugAgent
from .developer import DeveloperAgent
from .planner import PlannerAgent
from .repo_analyst import RepoAnalystAgent
from .reviewer import ReviewerAgent


CANONICAL_AGENTS = {
    "planner": PlannerAgent(),
    "repo_analyst": RepoAnalystAgent(),
    "developer": DeveloperAgent(),
    "reviewer": ReviewerAgent(),
    "debug": DebugAgent(),
}


__all__ = [
    "CANONICAL_AGENTS",
    "CanonicalAgent",
    "DebugAgent",
    "DeveloperAgent",
    "PlannerAgent",
    "RepoAnalystAgent",
    "ReviewerAgent",
]
