from __future__ import annotations

import json
import os
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
TASK_QUEUE_STATE_FILE = Path(
    os.getenv("JARVIS_ORCHESTRATOR_STATE_FILE", DATA_DIR / "task_queue.json")
)
LIVE_EVENTS_FILE = Path(
    os.getenv("JARVIS_ORCHESTRATOR_EVENTS_FILE", DATA_DIR / "live_events.jsonl")
)
DESKTOP_ASSISTANT_FILE = ROOT / "server" / "logs" / "desktop_assistant.json"
VOICE_RUNTIME_EVENTS_FILE = ROOT / "server" / "logs" / "voice_runtime_events.jsonl"

TASK_EVENT_NAMES = {
    "task_created",
    "task_started",
    "task_updated",
    "task_confirmed",
    "task_retry",
}

_DEFAULT_RUNTIME_STATE: dict[str, Any] = {
    "phase": "idle",
    "text": "Jarvis hazir.",
    "agent": "voice",
    "latestPreview": "",
    "updated_at": 0.0,
    "runtime": {
        "status": "offline",
        "detail": "voice runtime inactive",
        "source": "unknown",
        "mode": "",
        "wake_mode": "",
        "stt_backend": "",
        "tts_backend": "",
    },
    "voice": {
        "last_heard": "",
        "last_response": "",
        "heard_at": 0.0,
        "response_at": 0.0,
        "turn_count": 0,
    },
}


def _clone_default_runtime_state() -> dict[str, Any]:
    return json.loads(json.dumps(_DEFAULT_RUNTIME_STATE))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _read_recent_lines(path: Path, limit: int) -> list[str]:
    if limit <= 0 or not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return list(deque(handle, maxlen=limit))
    except Exception:
        return []


def summarize_live_event(payload: dict[str, Any]) -> str:
    event_name = str(payload.get("event") or "").strip().lower()
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}

    if event_name in TASK_EVENT_NAMES:
        task_id = str(task.get("id") or "?")
        agent = str(task.get("agent") or "agent")
        status = str(task.get("status") or "")

        if event_name == "task_created":
            goal = str(task.get("goal") or "").strip()
            if goal:
                return f"{task_id} queued for {agent}: {goal[:72]}"
            return f"{task_id} queued for {agent}"
        if event_name == "task_started":
            return f"{task_id} started by {agent}"
        if event_name == "task_retry":
            retries = int(task.get("retries") or 0)
            return f"{task_id} retry {retries} for {agent}"
        if status == "done":
            return f"{task_id} done by {agent}"
        if status == "failed":
            error = str(task.get("error") or "").strip()
            if error:
                return f"{task_id} failed by {agent}: {error[:72]}"
            return f"{task_id} failed by {agent}"
        if status:
            return f"{task_id} updated to {status} by {agent}"
        return f"{task_id} updated by {agent}"

    if event_name == "runtime_state":
        phase = str(payload.get("phase") or "idle")
        runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
        voice = payload.get("voice") if isinstance(payload.get("voice"), dict) else {}
        heard = str(voice.get("last_heard") or "").strip()
        detail = str(runtime.get("detail") or "").strip()
        if heard:
            return f"voice {phase}: {heard[:72]}"
        if detail:
            return f"voice {phase}: {detail[:72]}"
        return f"voice {phase}"

    return str(payload.get("message") or event_name or "live_event")


def normalize_live_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_name = str(payload.get("event") or "").strip() or "unknown"
    normalized: dict[str, Any] = {
        "event": event_name,
        "timestamp": str(payload.get("timestamp") or _iso_now()),
        "message": str(payload.get("message") or summarize_live_event(payload)),
    }

    if isinstance(payload.get("task"), dict):
        normalized["task"] = payload["task"]
    if isinstance(payload.get("runtime"), dict):
        normalized["runtime"] = payload["runtime"]
    if isinstance(payload.get("voice"), dict):
        normalized["voice"] = payload["voice"]

    for key in ("phase", "text", "latestPreview", "updated_at", "source", "agent", "replayed"):
        if key in payload:
            normalized[key] = payload[key]

    return normalized


def append_live_event(payload: dict[str, Any], events_file: Path | None = None) -> dict[str, Any]:
    target = events_file or LIVE_EVENTS_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_live_event(payload)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(normalized, ensure_ascii=False) + "\n")
    return normalized


def read_recent_live_events(limit: int = 20, events_file: Path | None = None) -> list[dict[str, Any]]:
    target = events_file or LIVE_EVENTS_FILE
    events: list[dict[str, Any]] = []
    for line in _read_recent_lines(target, limit):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def read_latest_voice_runtime_event(
    events_file: Path | None = None,
) -> dict[str, Any] | None:
    target = events_file or VOICE_RUNTIME_EVENTS_FILE
    lines = _read_recent_lines(target, 1)
    if not lines:
        return None
    try:
        payload = json.loads(lines[-1])
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def load_runtime_snapshot(runtime_file: Path | None = None) -> dict[str, Any]:
    target = runtime_file or DESKTOP_ASSISTANT_FILE
    payload = _read_json(target, {})
    merged = _clone_default_runtime_state()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"runtime", "voice"}:
                continue
            merged[key] = value
        if isinstance(payload.get("runtime"), dict):
            merged["runtime"].update(payload["runtime"])
        if isinstance(payload.get("voice"), dict):
            merged["voice"].update(payload["voice"])
    return merged


def load_task_queue_snapshot(state_file: Path | None = None) -> dict[str, Any]:
    target = state_file or TASK_QUEUE_STATE_FILE
    payload = _read_json(target, {})
    tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    if not isinstance(tasks, list):
        tasks = []

    status_counts = {
        "pending": 0,
        "queued": 0,
        "running": 0,
        "done": 0,
        "failed": 0,
        "blocked": 0,
        "awaiting_confirmation": 0,
    }
    queued_by_priority = {
        "critical": 0,
        "high": 0,
        "normal": 0,
        "low": 0,
    }

    oldest_queued_at: str | None = None
    newest_queued_at: str | None = None

    for raw_task in tasks:
        if not isinstance(raw_task, dict):
            continue

        status = str(raw_task.get("status") or "queued")
        if status not in status_counts:
            status = "queued"
        status_counts[status] += 1

        if status == "queued":
            priority = str(raw_task.get("priority") or "normal")
            if priority not in queued_by_priority:
                priority = "normal"
            queued_by_priority[priority] += 1

            created_at = str(raw_task.get("created_at") or "")
            if created_at:
                if oldest_queued_at is None or created_at < oldest_queued_at:
                    oldest_queued_at = created_at
                if newest_queued_at is None or created_at > newest_queued_at:
                    newest_queued_at = created_at

    return {
        "state_file": str(target),
        "total_tasks": len([task for task in tasks if isinstance(task, dict)]),
        "queued_tasks": status_counts["queued"],
        "running_tasks": status_counts["running"],
        "awaiting_confirmation_tasks": status_counts["awaiting_confirmation"],
        "done_tasks": status_counts["done"],
        "failed_tasks": status_counts["failed"],
        "blocked_tasks": status_counts["blocked"],
        "pending_tasks": status_counts["pending"],
        "status_counts": status_counts,
        "queued_by_priority": queued_by_priority,
        "oldest_queued_at": oldest_queued_at,
        "newest_queued_at": newest_queued_at,
        "last_queue_order": int(payload.get("last_order", 0)) if isinstance(payload, dict) else 0,
    }


def build_live_event_counts(
    limit: int = 100,
    events_file: Path | None = None,
) -> dict[str, int]:
    counter = Counter(
        str(event.get("event") or "unknown")
        for event in read_recent_live_events(limit=limit, events_file=events_file)
    )
    return dict(counter)
