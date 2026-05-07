from __future__ import annotations

from copy import deepcopy
from typing import Any

OPENCLAW_RESEARCH_DATE = "2026-04-14"

OPENCLAW_SOURCE_MAP: list[dict[str, str]] = [
    {
        "id": "repo",
        "title": "openclaw/openclaw",
        "url": "https://github.com/openclaw/openclaw",
        "focus": "core repo structure: docs, skills, src, apps, packages",
    },
    {
        "id": "channels",
        "title": "Supported channels",
        "url": "https://open-claw.bot/docs/channels/",
        "focus": "gateway-backed multi-channel delivery",
    },
    {
        "id": "skills_cli",
        "title": "Manage OpenClaw Skills",
        "url": "https://open-claw.bot/docs/cli/skills/",
        "focus": "skills search/install/list/check flow",
    },
    {
        "id": "skills_config",
        "title": "Skills config",
        "url": "https://open-claw.bot/docs/tools/skills-config/",
        "focus": "skills object, extraDirs, watch mode",
    },
    {
        "id": "subagents",
        "title": "OpenClaw Sub-Agents",
        "url": "https://open-claw.bot/docs/tools/subagents/",
        "focus": "background tasks, isolated sessions, allowAgents",
    },
    {
        "id": "multi_agent",
        "title": "Multi-agent routing",
        "url": "https://open-claw.bot/docs/concepts/multi-agent/",
        "focus": "isolated agents, bindings, auth profile copy guidance",
    },
    {
        "id": "memory_search",
        "title": "Memory search",
        "url": "https://open-claw.bot/docs/concepts/memory-search/",
        "focus": "hybrid retrieval, local or hosted providers",
    },
    {
        "id": "background_process",
        "title": "Background exec/process",
        "url": "https://open-claw.bot/docs/gateway/background-process/",
        "focus": "long-running task sessions and polling",
    },
]

OPENCLAW_FEATURE_FAMILIES: dict[str, dict[str, Any]] = {
    "channels": {
        "summary": "Gateway can route one assistant across 20+ chat channels.",
        "sabri_angle": "Design channel-first campaign and brand interaction ideas.",
        "local_skill": "openclaw_channel_mapper",
    },
    "skills": {
        "summary": "Skills can be loaded from workspace folders and managed with CLI install/list/check commands.",
        "sabri_angle": "Curate lightweight skill packs for experiments and offers.",
        "local_skill": "openclaw_skill_curator",
    },
    "subagents": {
        "summary": "Sub-agents run as isolated background sessions and can be allowed to spawn across agent ids.",
        "sabri_angle": "Turn rough ideas into role-separated agent blueprints.",
        "local_skill": "openclaw_agent_designer",
    },
    "memory": {
        "summary": "Memory search supports hybrid retrieval and local providers such as Ollama.",
        "sabri_angle": "Shape persistent idea banks and campaign memory loops.",
        "local_skill": "openclaw_memory_designer",
    },
}

CHANNEL_RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "community": {
        "channel": "discord",
        "why": "best fit for community loops, reactions, and public feedback collection",
    },
    "operator": {
        "channel": "telegram",
        "why": "fast owner notifications and direct response workflow",
    },
    "internal": {
        "channel": "slack",
        "why": "good for workspace coordination and slash-command driven ops",
    },
    "consumer": {
        "channel": "whatsapp",
        "why": "best fit for high-frequency consumer messaging and follow-ups",
    },
}


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def list_openclaw_sources() -> list[dict[str, str]]:
    return deepcopy(OPENCLAW_SOURCE_MAP)


def research_openclaw_repos(query: str = "") -> dict[str, Any]:
    normalized_query = _normalize(query)
    focus_areas: list[str] = []

    if any(token in normalized_query for token in ("channel", "telegram", "discord", "whatsapp", "slack")):
        focus_areas.extend(["channels", "multi_agent"])
    if any(token in normalized_query for token in ("skill", "plugin", "workflow", "tool")):
        focus_areas.extend(["skills", "subagents"])
    if any(token in normalized_query for token in ("memory", "context", "knowledge")):
        focus_areas.append("memory")
    if any(token in normalized_query for token in ("agent", "subagent", "team", "persona")):
        focus_areas.extend(["subagents", "multi_agent"])

    if not focus_areas:
        focus_areas = ["channels", "skills", "subagents", "memory"]

    deduped_focus: list[str] = []
    for item in focus_areas:
        if item not in deduped_focus:
            deduped_focus.append(item)

    return {
        "ok": True,
        "query": normalized_query or "general",
        "researched_at": OPENCLAW_RESEARCH_DATE,
        "sources": list_openclaw_sources(),
        "focus_areas": deduped_focus,
        "feature_families": {
            key: deepcopy(OPENCLAW_FEATURE_FAMILIES[key])
            for key in deduped_focus
            if key in OPENCLAW_FEATURE_FAMILIES
        },
        "takeaways": [
            "Use separate agent workspaces and agent dirs when splitting personas.",
            "Keep skill packs small and inspectable before wider rollout.",
            "Prefer background sub-agents for long research or content runs.",
        ],
    }


def curate_openclaw_skill_pack(goal: str = "") -> dict[str, Any]:
    normalized_goal = _normalize(goal)
    primary_mode = "creative_lab"
    recommended_channels = ["telegram", "discord"]

    if any(token in normalized_goal for token in ("landing", "offer", "campaign", "brand")):
        primary_mode = "growth_lab"
        recommended_channels = ["telegram", "discord", "whatsapp"]
    elif any(token in normalized_goal for token in ("internal", "team", "workflow", "ops")):
        primary_mode = "operator_lab"
        recommended_channels = ["telegram", "slack"]

    skills = [
        {
            "id": "repo_scout",
            "purpose": "track repo/docs changes and capture new capability areas",
        },
        {
            "id": "skill_curator",
            "purpose": "assemble a small skill pack using CLI search/install/check flow",
        },
        {
            "id": "agent_designer",
            "purpose": "split ideation, execution, and review into separate agent roles",
        },
        {
            "id": "memory_designer",
            "purpose": "persist winning prompts, offers, and campaign notes with memory search",
        },
    ]

    return {
        "ok": True,
        "goal": normalized_goal or "general",
        "primary_mode": primary_mode,
        "recommended_channels": recommended_channels,
        "recommended_skills": skills,
        "activation_steps": [
            "search or inspect target skills with the OpenClaw skills CLI",
            "load workspace skill directories in skills.extraDirs",
            "enable watch mode only for actively iterated local skills",
            "keep memory search local unless a hosted provider is clearly needed",
        ],
    }


def design_openclaw_channel_strategy(goal: str = "") -> dict[str, Any]:
    normalized_goal = _normalize(goal)
    mode = "operator"
    if any(token in normalized_goal for token in ("community", "fans", "audience", "feedback")):
        mode = "community"
    elif any(token in normalized_goal for token in ("customer", "sales", "lead", "consumer")):
        mode = "consumer"
    elif any(token in normalized_goal for token in ("internal", "workspace", "team")):
        mode = "internal"

    base = CHANNEL_RECOMMENDATIONS[mode]
    return {
        "ok": True,
        "goal": normalized_goal or "general",
        "primary_channel": base["channel"],
        "rationale": base["why"],
        "secondary_channels": ["telegram", "discord"] if base["channel"] != "telegram" else ["discord"],
        "binding_notes": [
            "keep high-context private flows on a dedicated agent binding",
            "do not reuse auth/session directories across unrelated personas",
            "copy auth profiles manually only when shared credentials are intentional",
        ],
    }


def design_openclaw_agent_blueprint(goal: str = "") -> dict[str, Any]:
    normalized_goal = _normalize(goal)
    return {
        "ok": True,
        "goal": normalized_goal or "general",
        "primary_agent": {
            "id": "sabri-lab",
            "role": "creative direction, positioning, offer framing",
        },
        "support_agents": [
            {
                "id": "repo-scout",
                "role": "scan repo/docs and summarize new opportunities",
            },
            {
                "id": "skill-curator",
                "role": "select the thinnest useful skill set for the current experiment",
            },
            {
                "id": "channel-mapper",
                "role": "match audience flows to the right OpenClaw channel bindings",
            },
        ],
        "subagent_policy": {
            "spawn_model": "background",
            "reason": "lets Sabri keep ideation moving while research/design tasks finish asynchronously",
            "cross_agent_note": "allowAgents should stay explicit instead of wildcard unless the workflow is trusted",
        },
        "handoff_notes": [
            "send code-heavy implementation to Seda",
            "send runtime/deploy work to Sabrican",
            "keep Sabri focused on framing, experimentation, and agent topology",
        ],
    }


def design_openclaw_memory_strategy(goal: str = "") -> dict[str, Any]:
    normalized_goal = _normalize(goal)
    return {
        "ok": True,
        "goal": normalized_goal or "general",
        "provider_preference": "ollama",
        "indexing_strategy": [
            "store campaign learnings as short markdown notes",
            "separate evergreen prompts from fast-expiring experiment notes",
            "prefer hybrid retrieval for fuzzy recall plus exact IDs",
        ],
        "risk_notes": [
            "large memory sets need decay or pruning to avoid stale recall",
            "shared auth does not imply shared memory isolation",
        ],
    }


def build_sabri_openclaw_upgrade(goal: str = "") -> dict[str, Any]:
    return {
        "ok": True,
        "research": research_openclaw_repos(goal),
        "skill_pack": curate_openclaw_skill_pack(goal),
        "channel_strategy": design_openclaw_channel_strategy(goal),
        "agent_blueprint": design_openclaw_agent_blueprint(goal),
        "memory_strategy": design_openclaw_memory_strategy(goal),
    }


__all__ = [
    "OPENCLAW_RESEARCH_DATE",
    "build_sabri_openclaw_upgrade",
    "curate_openclaw_skill_pack",
    "design_openclaw_agent_blueprint",
    "design_openclaw_channel_strategy",
    "design_openclaw_memory_strategy",
    "list_openclaw_sources",
    "research_openclaw_repos",
]
