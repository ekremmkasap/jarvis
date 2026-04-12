from __future__ import annotations

from .base import CanonicalAgent
from .debug_agent import DebugAgent
from .developer import DeveloperAgent
from .docs_agent import DocsAgent
from .release_agent import ReleaseAgent
from .planner import PlannerAgent
from .repo_analyst import RepoAnalystAgent
from .reviewer import ReviewerAgent
from .voice_narrator import VoiceNarratorAgent


CANONICAL_AGENTS = {
    "planner": PlannerAgent(),
    "repo_analyst": RepoAnalystAgent(),
    "developer": DeveloperAgent(),
    "reviewer": ReviewerAgent(),
    "debug": DebugAgent(),
    "release": ReleaseAgent(),
    "docs": DocsAgent(),
    "voice_narrator": VoiceNarratorAgent(),
}


__all__ = [
    "CANONICAL_AGENTS",
    "CanonicalAgent",
    "DebugAgent",
    "DeveloperAgent",
    "DocsAgent",
    "PlannerAgent",
    "ReleaseAgent",
    "RepoAnalystAgent",
    "ReviewerAgent",
    "VoiceNarratorAgent",
]
