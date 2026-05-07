from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT_DIR / "server" / "config" / "external_tools_registry.json"

_PRIMARY_TOOL_MAP: dict[str, tuple[str, ...]] = {
    "aider": ("aider", "cline", "claw_code"),
    "cline": ("cline", "aider", "claude_code_new_features"),
    "codex": ("octogent", "codex_subagents", "claude_code_mirror", "claude_code_new_features"),
    "claude": ("octogent", "claude_code_mirror", "claude_code_new_features", "hooks_mastery"),
    "jarvis_simulation": ("octogent", "swarms", "crewai", "paperclip"),
    "mcp": ("mcp_youtube_transcript", "youtube_mcp_server", "youtube_transcript_api"),
    "openhands": ("openhands", "devika", "claude_code_mirror"),
}

_REPO_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hooks_mastery": ("hook", "hooks", "pretooluse", "posttooluse", "sessionstart"),
    "codex_subagents": ("subagent", "subagents", "agent", "worker", "uzman"),
    "paperclip": ("company", "governance", "org", "organizasyon", "quota", "budget"),
    "spec_kit": ("spec", "plan", "tasks", "workflow", "roadmap", "implement"),
    "prompts_chat": ("prompt", "prompts", "system prompt"),
    "awesome_agent_skills": ("skill", "skills", "capability", "capabilities"),
    "claude_skills": ("skill", "marketing", "growth", "autoresearch", "review"),
    "slavingia_skills": ("mvp", "pricing", "first customer", "validate", "idea"),
    "claw_router": ("route", "router", "routing", "model sec", "provider"),
    "octogent": ("octogent", "tentacle", "todo", "parallel", "terminal", "worktree", "claude code"),
    "swarms": ("swarm", "multi agent", "orchestrate", "orchestration"),
    "crewai": ("crew", "team", "research", "review", "role"),
    "cline": ("ui", "editor", "interactive", "vscode", "cline"),
    "aider": ("fix", "refactor", "rename", "patch", "pair"),
    "openhands": ("sandbox", "autonomous", "full project", "insaat", "openhands"),
    "devika": ("research", "web", "planlama", "planner", "devika"),
    "claude_code_mirror": ("runtime", "architecture", "claude code", "bridge", "tool"),
    "claude_code_new_features": ("parallel", "continuation", "session", "new feature", "cheatsheet"),
    "claw_code": ("execution", "runtime", "claw code"),
    "cli_anything": ("desktop", "computer", "gui", "cli", "automation"),
    "mcp_youtube_transcript": ("youtube", "transcript", "subtitle", "captions"),
    "youtube_mcp_server": ("youtube", "mcp", "ingest", "transcript"),
    "youtube_transcript_api": ("youtube", "transcript", "fallback", "subtitle"),
}


def _normalize(text: str = "") -> str:
    return str(text or "").strip().lower()


def _tokenize(text: str = "") -> list[str]:
    return [token for token in re.split(r"[\s,/_\-:.]+", _normalize(text)) if token]


def _blob(entry: dict[str, Any]) -> str:
    parts = [
        entry.get("id", ""),
        entry.get("label", ""),
        entry.get("repo", ""),
        entry.get("path", ""),
        entry.get("category", ""),
        entry.get("tier", ""),
        entry.get("status", ""),
        entry.get("why", ""),
        entry.get("jarvis_use", ""),
    ]
    return " ".join(str(part or "") for part in parts).lower()


@lru_cache(maxsize=1)
def load_external_repo_entries() -> tuple[dict[str, Any], ...]:
    if not REGISTRY_PATH.exists():
        return tuple()
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    items = payload.get("tools") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return tuple()
    return tuple(item for item in items if isinstance(item, dict))


def get_external_repo_entry(repo_id: str) -> dict[str, Any] | None:
    lookup = _normalize(repo_id)
    for entry in load_external_repo_entries():
        if _normalize(str(entry.get("id") or "")) == lookup:
            return dict(entry)
    return None


def list_external_repos(query: str = "", limit: int = 10) -> list[dict[str, Any]]:
    entries = [dict(item) for item in load_external_repo_entries()]
    if not query:
        return entries[: max(1, int(limit))]

    normalized_query = _normalize(query)
    tokens = _tokenize(query)
    scored: list[tuple[int, dict[str, Any]]] = []

    for entry in entries:
        score = 0
        haystack = _blob(entry)
        entry_id = _normalize(str(entry.get("id") or ""))
        entry_label = _normalize(str(entry.get("label") or ""))
        if normalized_query == entry_id:
            score += 12
        if normalized_query == entry_label:
            score += 10
        if normalized_query and normalized_query in haystack:
            score += 6
        for token in tokens:
            if token in haystack:
                score += 2
        if score > 0:
            entry["score"] = score
            scored.append((score, entry))

    scored.sort(key=lambda item: (-item[0], str(item[1].get("label") or "")))
    return [item for _, item in scored[: max(1, int(limit))]]


def summarize_external_repo_stats() -> dict[str, Any]:
    entries = list(load_external_repo_entries())
    stats: dict[str, Any] = {
        "total": len(entries),
        "by_tier": {},
        "by_status": {},
    }
    for entry in entries:
        tier = str(entry.get("tier") or "unknown").strip() or "unknown"
        status = str(entry.get("status") or "unknown").strip() or "unknown"
        stats["by_tier"][tier] = int(stats["by_tier"].get(tier, 0)) + 1
        stats["by_status"][status] = int(stats["by_status"].get(status, 0)) + 1
    return stats


def recommend_external_repos(
    goal: str,
    *,
    primary_tool: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    entries = [dict(item) for item in load_external_repo_entries()]
    tokens = _tokenize(goal)
    tool_key = _normalize(primary_tool)
    tool_bias = _PRIMARY_TOOL_MAP.get(tool_key, ())
    scored: list[tuple[int, dict[str, Any]]] = []

    for entry in entries:
        repo_id = str(entry.get("id") or "").strip()
        score = 0
        if repo_id in tool_bias:
            score += 8
        for keyword in _REPO_KEYWORDS.get(repo_id, ()):
            keyword_norm = _normalize(keyword)
            if keyword_norm and keyword_norm in _normalize(goal):
                score += 4
        entry_blob = _blob(entry)
        for token in tokens:
            if token in entry_blob:
                score += 1
        if score > 0:
            entry["score"] = score
            scored.append((score, entry))

    if not scored and tool_bias:
        for repo_id in tool_bias:
            entry = get_external_repo_entry(repo_id)
            if entry is not None:
                entry["score"] = 1
                scored.append((1, entry))

    scored.sort(key=lambda item: (-item[0], str(item[1].get("label") or "")))
    return [item for _, item in scored[: max(1, int(limit))]]


def build_external_repo_report(query: str = "", limit: int = 8) -> str:
    query = str(query or "").strip()
    if query:
        entries = list_external_repos(query, limit=limit)
        lines = [f"EXTERNAL REPO ARAMA: {query}", ""]
        if not entries:
            lines.append("Eslesen repo yok.")
            return "\n".join(lines)
        lines.append(f"Sonuc: {len(entries)}")
        for index, entry in enumerate(entries, start=1):
            lines.extend(
                [
                    "",
                    f"{index}. {entry.get('label', '-')}",
                    f"   id: {entry.get('id', '-')}",
                    f"   repo: {entry.get('repo', '-')}",
                    f"   path: {entry.get('path', '-')}",
                    f"   kategori: {entry.get('category', '-')}",
                    f"   tier/status: {entry.get('tier', '-')} / {entry.get('status', '-')}",
                    f"   jarvis_use: {entry.get('jarvis_use', '-')}",
                ]
            )
        return "\n".join(lines)

    stats = summarize_external_repo_stats()
    entries = list_external_repos(limit=limit)
    lines = [
        "EXTERNAL REPO HAVUZU",
        "",
        f"Toplam repo: {stats['total']}",
        f"Tier: {', '.join(f'{key}={value}' for key, value in sorted(stats['by_tier'].items())) or '-'}",
        f"Status: {', '.join(f'{key}={value}' for key, value in sorted(stats['by_status'].items())) or '-'}",
        "",
        "One cikanlar:",
    ]
    for entry in entries:
        lines.append(
            f"- {entry.get('label', '-')} [{entry.get('status', '-')}] -> {entry.get('path', '-')}"
        )
    lines.extend(
        [
            "",
            "Detay: /repo openhands",
            "Oneri: /repo-oner youtube transcript cek",
        ]
    )
    return "\n".join(lines)


def build_external_repo_recommendation_report(goal: str, limit: int = 5) -> str:
    goal = str(goal or "").strip()
    if not goal:
        return "Kullanim: /repo-oner [gorev]"

    try:
        from tool_router import route_task
    except Exception:
        from server.services.tool_router import route_task

    decision = route_task(goal)
    primary_tool = str(decision.get("tool") or "").strip()
    repos = recommend_external_repos(goal, primary_tool=primary_tool, limit=limit)

    lines = [
        "REPO ONERI",
        f"Gorev: {goal[:160]}",
        f"Primary tool: {decision.get('label', '-')} ({primary_tool or '-'})",
        f"Gerekce: {decision.get('reason', '-')}",
        "",
    ]
    if not repos:
        lines.append("Bu gorev icin ek repo onerisi bulunamadi.")
        return "\n".join(lines)

    lines.append("Onerilen repolar:")
    for entry in repos:
        lines.extend(
            [
                f"- {entry.get('label', '-')} [{entry.get('status', '-')}]",
                f"  path: {entry.get('path', '-')}",
                f"  jarvis_use: {entry.get('jarvis_use', '-')}",
            ]
        )
    return "\n".join(lines)
