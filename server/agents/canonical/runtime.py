from __future__ import annotations

import asyncio
from typing import Any

from . import CANONICAL_AGENTS
from .constants import CANONICAL_AGENT_IDS, CANONICAL_AGENT_KEYWORDS


def match_canonical_agent(text: str) -> str | None:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return None
    for agent_id, keywords in CANONICAL_AGENT_KEYWORDS.items():
        if keywords and any(keyword in lowered for keyword in keywords):
            return agent_id
    return None


def run_canonical_agent_sync(agent_name: str, task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    agent_id = str(agent_name or "").strip()
    agent = CANONICAL_AGENTS.get(agent_id)
    if agent is None:
        raise KeyError(agent_id)
    return asyncio.run(agent.run(task, context or {}))


def handle_agent_request(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    if not isinstance(body, dict):
        return {"ok": False, "error": "JSON object body is required."}, 400
    agent_name = str(body.get("agent") or "").strip()
    task = str(body.get("task") or "").strip()
    context = body.get("context") or {}
    if not agent_name:
        return {"ok": False, "error": "agent is required"}, 400
    if agent_name not in CANONICAL_AGENT_IDS:
        return {"ok": False, "error": f"unknown agent: {agent_name}"}, 404
    if not task:
        return {"ok": False, "error": "task is required"}, 400
    if not isinstance(context, dict):
        return {"ok": False, "error": "context must be an object"}, 400
    result = run_canonical_agent_sync(agent_name, task, context)
    return result, 200


def dispatch_keyword_routed_agent(text: str, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]] | None:
    agent_id = match_canonical_agent(text)
    if not agent_id:
        return None
    result = run_canonical_agent_sync(agent_id, text, context or {})
    return agent_id, result


def format_canonical_result(agent_id: str, result: dict[str, Any]) -> str:
    status = str(result.get("status") or "error").strip().lower()
    if status != "ok":
        error = str(result.get("error") or "Unknown error").strip()
        return f"[CANONICAL/{agent_id}] error: {error}"

    if agent_id == "planner":
        steps = result.get("steps") or []
        titles = [str(item.get("title") or "").strip() for item in steps if isinstance(item, dict)]
        return f"[CANONICAL/planner] {len(steps)} steps, priority={result.get('priority')}, complexity={result.get('estimated_complexity')}: {', '.join(filter(None, titles[:3]))}"
    if agent_id == "repo_analyst":
        warnings = result.get("warnings") or []
        return f"[CANONICAL/repo_analyst] health={result.get('health_score')} changed={len(result.get('changed_files') or [])} warnings={len(warnings)}"
    if agent_id == "developer":
        files_changed = result.get("files_changed") or []
        return f"[CANONICAL/developer] status={result.get('status')} files={', '.join(str(item) for item in files_changed[:3])}"
    if agent_id == "reviewer":
        counts = result.get("severity_counts") or {}
        return f"[CANONICAL/reviewer] verdict={result.get('overall_verdict')} critical={counts.get('critical', 0)} major={counts.get('major', 0)} minor={counts.get('minor', 0)}"
    if agent_id == "debug":
        return f"[CANONICAL/debug] {result.get('error_type')}: {result.get('likely_cause')}"
    if agent_id == "release":
        highlights = result.get("highlights") or []
        return f"[CANONICAL/release] suggested={result.get('suggested_version')} highlights={'; '.join(str(item) for item in highlights[:2])}"
    if agent_id == "docs":
        return f"[CANONICAL/docs] type={result.get('doc_type')} target={result.get('target_file_suggestion')}"
    if agent_id == "voice_narrator":
        return str(result.get("tts_text") or "").strip()
    if agent_id == "mission_control":
        stuck = result.get("stuck_tasks") or []
        return f"[CANONICAL/mission_control] health={result.get('overall_health')} stuck={len(stuck)}"
    return f"[CANONICAL/{agent_id}] status=ok"
