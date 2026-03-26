from __future__ import annotations

import logging
from typing import Type

log = logging.getLogger(__name__)

# ── Legacy GitHub workflow agents (existing) ─────────────────
try:
    from agents.base import BaseAgent
    from agents.ci_triager.agent import CITriagerAgent
    from agents.git_summarizer.agent import GitSummarizerAgent
    from agents.issue_router.agent import IssueRouterAgent
    from agents.pr_reviewer.agent import PRReviewerAgent
    _LEGACY: dict[str, type] = {
        "git_summarizer": GitSummarizerAgent,
        "pr_reviewer": PRReviewerAgent,
        "ci_triager": CITriagerAgent,
        "issue_router": IssueRouterAgent,
    }
except ImportError as e:
    log.debug("Legacy agents not loaded: %s", e)
    _LEGACY = {}

# ── Runtime orchestrator agents (v2) ─────────────────────────
try:
    from agents.planner_agent import PlannerAgent
    from agents.repo_analyst_agent import RepoAnalystAgent
    from agents.developer_agent import DeveloperAgent
    from agents.reviewer_agent import ReviewerAgent
    from agents.debug_agent import DebugAgent
    from agents.release_agent import ReleaseAgent
    from agents.docs_agent import DocsAgent
    from agents.voice_narrator_agent import VoiceNarratorAgent
    from agents.mission_control_agent import MissionControlAgent
    _RUNTIME: dict[str, type] = {
        "planner": PlannerAgent,
        "repo_analyst": RepoAnalystAgent,
        "developer": DeveloperAgent,
        "reviewer": ReviewerAgent,
        "debug": DebugAgent,
        "release": ReleaseAgent,
        "docs": DocsAgent,
        "voice_narrator": VoiceNarratorAgent,
        "mission_control": MissionControlAgent,
    }
except ImportError as e:
    log.warning("Runtime agents import error: %s", e)
    _RUNTIME = {}

REGISTRY: dict[str, type] = {**_LEGACY, **_RUNTIME}


def get_agent(agent_name: str):
    try:
        return REGISTRY[agent_name]()
    except KeyError as exc:
        raise KeyError(
            f"Unknown agent: {agent_name!r}. Available: {list(REGISTRY.keys())}"
        ) from exc


def list_agents() -> list[dict]:
    return [{"name": k, "class": v.__name__} for k, v in REGISTRY.items()]
