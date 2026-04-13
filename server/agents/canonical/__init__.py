from __future__ import annotations

from .base import CanonicalAgent
from .constants import CANONICAL_AGENT_IDS, CANONICAL_AGENT_KEYWORDS
from .debug_agent import DebugAgent
from .developer import DeveloperAgent
from .docs_agent import DocsAgent
from .mission_control import MissionControlAgent
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
    "mission_control": MissionControlAgent(),
}


__all__ = [
    "CANONICAL_AGENTS",
    "CANONICAL_AGENT_IDS",
    "CANONICAL_AGENT_KEYWORDS",
    "CanonicalAgent",
    "DebugAgent",
    "DeveloperAgent",
    "DocsAgent",
    "MissionControlAgent",
    "PlannerAgent",
    "ReleaseAgent",
    "RepoAnalystAgent",
    "ReviewerAgent",
    "VoiceNarratorAgent",
]
