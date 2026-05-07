from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT_DIR / "server" / "logs" / "agent_os_status.json"
TOOL_DECAY_SECONDS = int(os.environ.get("AGENT_OS_TOOL_DECAY_SECONDS", "10"))

_DEFAULT_AGENTS = {
    "jarvis": "idle",
    "claude": "idle",
    "ollama": "idle",
    "research": "idle",
    "guard": "idle",
}


def _default_status() -> dict[str, Any]:
    return {
        "mode": "agent_os",
        "status": "idle",
        "current_job": None,
        "tool_job": None,
        "updated_at": datetime.now().isoformat(),
        "agents": dict(_DEFAULT_AGENTS),
        "jobs": [],
        "stats": {},
    }


def load_visual_status() -> dict[str, Any]:
    if STATUS_PATH.exists():
        try:
            data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("agents", {})
                for key, value in _DEFAULT_AGENTS.items():
                    data["agents"].setdefault(key, value)
                data.setdefault("current_job", None)
                data.setdefault("tool_job", None)
                data.setdefault("last_tool_job", None)
                data.setdefault("jobs", [])
                data.setdefault("stats", {})
                data.setdefault("mode", "agent_os")
                return data
        except Exception:
            pass
    return _default_status()


def write_visual_status(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data or {})
    payload.setdefault("agents", {})
    for key, value in _DEFAULT_AGENTS.items():
        payload["agents"].setdefault(key, value)
    payload.setdefault("current_job", None)
    payload.setdefault("tool_job", None)
    payload.setdefault("last_tool_job", None)
    payload.setdefault("jobs", [])
    payload.setdefault("stats", {})
    payload.setdefault("mode", "agent_os")
    payload["updated_at"] = datetime.now().isoformat()
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def apply_visual_decay(status: dict[str, Any], decay_seconds: int = TOOL_DECAY_SECONDS) -> dict[str, Any]:
    payload = dict(status or {})
    last_tool_job = payload.get("last_tool_job") if isinstance(payload.get("last_tool_job"), dict) else {}
    tool_job = payload.get("tool_job") if isinstance(payload.get("tool_job"), dict) else {}
    current_job = payload.get("current_job") if isinstance(payload.get("current_job"), dict) else {}
    if tool_job:
        return payload
    if str(last_tool_job.get("source") or "") != "tool_execution":
        return payload
    finished_at = _parse_iso(last_tool_job.get("finished_at"))
    if finished_at is None:
        return payload
    age_seconds = (datetime.now() - finished_at).total_seconds()
    if age_seconds < max(1, int(decay_seconds)):
        return payload
    if current_job and str(current_job.get("source") or "").strip() != "tool_execution":
        return payload

    changed = False
    if payload.get("status") != "idle":
        payload["status"] = "idle"
        changed = True
    if current_job:
        payload["current_job"] = None
        changed = True
    agents = payload.get("agents") if isinstance(payload.get("agents"), dict) else {}
    for node, default_state in _DEFAULT_AGENTS.items():
        if agents.get(node) != default_state:
            agents[node] = default_state
            changed = True
    payload["agents"] = agents
    if changed:
        payload["tool_overlay_decayed_at"] = datetime.now().isoformat()
    return payload


def get_visual_status(decay_seconds: int = TOOL_DECAY_SECONDS) -> dict[str, Any]:
    status = load_visual_status()
    decayed = apply_visual_decay(status, decay_seconds=decay_seconds)
    if decayed != status:
        return write_visual_status(decayed)
    return decayed


def _tool_name(tool_execution: dict[str, Any] | None) -> str:
    return str((tool_execution or {}).get("tool") or "-").strip() or "-"


def _tool_status(tool_execution: dict[str, Any] | None) -> str:
    tool = _tool_name(tool_execution)
    if tool == "-":
        return "-"
    return "ok" if bool((tool_execution or {}).get("ok")) else "error"


def _fallback_label(tool_execution: dict[str, Any] | None) -> str:
    tool = _tool_name(tool_execution)
    if tool == "-":
        return "-"
    return "yes" if bool((tool_execution or {}).get("fallback_used")) else "no"


def _tool_mode(tool_execution: dict[str, Any] | None) -> str:
    return str((tool_execution or {}).get("mode") or "-").strip() or "-"


def _tool_node(tool_execution: dict[str, Any] | None) -> str:
    tool = _tool_name(tool_execution)
    if tool == "claude":
        return "claude"
    if tool in {"mcp", "jarvis_simulation"}:
        return "research"
    if tool in {"codex", "openhands", "aider", "cline"}:
        return "ollama"
    return "jarvis"


def _agent_node(agent_id: str) -> str:
    key = str(agent_id or "").strip().lower()
    if key == "security":
        return "guard"
    if key == "video":
        return "research"
    if key == "backend":
        return "ollama"
    return "jarvis"


def _set_nodes(status: dict[str, Any], values: dict[str, str]) -> None:
    agents = status.setdefault("agents", {})
    for node, state in values.items():
        if node in _DEFAULT_AGENTS:
            agents[node] = state


def _reset_tool_overlay_nodes(status: dict[str, Any]) -> None:
    agents = status.setdefault("agents", {})
    for node in _DEFAULT_AGENTS:
        agents[node] = "idle"


def sync_tool_job_start(
    *,
    task_id: str,
    task_type: str,
    agent_id: str,
    agent_name: str,
    task_text: str,
    tool_execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = load_visual_status()
    tool_node = _tool_node(tool_execution)
    agent_node = _agent_node(agent_id)
    job = {
        "id": str(task_id or "-").strip() or "-",
        "type": str(task_type or "-").strip() or "-",
        "agent_id": str(agent_id or "-").strip() or "-",
        "agent_name": str(agent_name or "-").strip() or "-",
        "task": str(task_text or "").strip()[:180],
        "tool": _tool_name(tool_execution),
        "tool_status": _tool_status(tool_execution),
        "fallback_used": _fallback_label(tool_execution),
        "mode": _tool_mode(tool_execution),
        "source": "tool_execution",
        "started_at": datetime.now().isoformat(),
    }
    status["tool_job"] = job
    current_job = status.get("current_job")
    if not (isinstance(current_job, dict) and str(current_job.get("source") or "") not in {"", "tool_execution"}):
        _reset_tool_overlay_nodes(status)
    if not isinstance(current_job, dict) or str(current_job.get("source") or "tool_execution") == "tool_execution":
        status["current_job"] = dict(job)
    _set_nodes(
        status,
        {
            "jarvis": "thinking",
            tool_node: "running",
            agent_node: "running",
        },
    )
    status["status"] = "running"
    return write_visual_status(status)


def sync_tool_job_result(
    *,
    task_id: str,
    task_type: str,
    agent_id: str,
    agent_name: str,
    task_text: str,
    tool_execution: dict[str, Any] | None = None,
    summary: str = "",
    success: bool = True,
) -> dict[str, Any]:
    status = load_visual_status()
    tool_node = _tool_node(tool_execution)
    agent_node = _agent_node(agent_id)
    result_state = "done" if success else "blocked"
    active_tool_job = status.get("tool_job") if isinstance(status.get("tool_job"), dict) else {}
    active_tool_id = str(active_tool_job.get("id") or "").strip()
    is_active_completion = bool(active_tool_id and active_tool_id == str(task_id or "").strip())
    job = {
        "id": str(task_id or "-").strip() or "-",
        "type": str(task_type or "-").strip() or "-",
        "agent_id": str(agent_id or "-").strip() or "-",
        "agent_name": str(agent_name or "-").strip() or "-",
        "task": str(task_text or "").strip()[:180],
        "tool": _tool_name(tool_execution),
        "tool_status": _tool_status(tool_execution),
        "fallback_used": _fallback_label(tool_execution),
        "mode": _tool_mode(tool_execution),
        "source": "tool_execution",
        "summary": str(summary or "").strip()[:240],
        "finished_at": datetime.now().isoformat(),
        "success": bool(success),
    }
    jobs = status.get("jobs") if isinstance(status.get("jobs"), list) else []
    jobs.append(
        {
            "id": job["id"],
            "type": job["type"],
            "status": "done" if success else "failed",
            "agent": job["agent_id"],
            "tool": job["tool"],
            "finished_at": job["finished_at"],
        }
    )
    status["jobs"] = jobs[-20:]
    if is_active_completion:
        status["tool_job"] = None
        current_job = status.get("current_job")
        if isinstance(current_job, dict) and str(current_job.get("source") or "") == "tool_execution" and str(current_job.get("id") or "").strip() == job["id"]:
            status["current_job"] = None
        _reset_tool_overlay_nodes(status)
        _set_nodes(
            status,
            {
                "jarvis": result_state,
                tool_node: result_state,
                agent_node: result_state,
            },
        )
        status["status"] = result_state
    status["last_tool_job"] = job
    return write_visual_status(status)
