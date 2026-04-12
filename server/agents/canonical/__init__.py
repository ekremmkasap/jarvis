from __future__ import annotations

from .base import CanonicalAgent
from .developer import DeveloperAgent
from .planner import PlannerAgent
from .repo_analyst import RepoAnalystAgent


CANONICAL_AGENTS = {
    "planner": PlannerAgent(),
    "repo_analyst": RepoAnalystAgent(),
    "developer": DeveloperAgent(),
}


__all__ = [
    "CANONICAL_AGENTS",
    "CanonicalAgent",
    "DeveloperAgent",
    "PlannerAgent",
    "RepoAnalystAgent",
]

