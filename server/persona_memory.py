from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
AGENT_MEMORY_DIR = ROOT / "state" / "agent_memory"
ALLOWED_ROLES = {"user", "assistant", "system"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_persona_id(persona_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "-", str(persona_id or "").strip().lower())
    normalized = normalized.strip("-")
    if not normalized:
        raise ValueError("persona_id is required")
    return normalized


def _normalize_chat_id(chat_id: Any) -> str:
    value = str(chat_id or "").strip()
    if not value:
        raise ValueError("chat_id is required")
    return value


def get_memory_path(persona_id: str) -> Path:
    return AGENT_MEMORY_DIR / _normalize_persona_id(persona_id)


def conversation_path(persona_id: str, chat_id: Any) -> Path:
    normalized_chat_id = _normalize_chat_id(chat_id)
    return get_memory_path(persona_id) / f"conversation_{normalized_chat_id}.jsonl"


def append_turn(
    persona_id: str,
    chat_id: Any,
    role: str,
    content: str,
    *,
    source: str = "",
    timestamp: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_role = str(role or "").strip().lower()
    if normalized_role not in ALLOWED_ROLES:
        raise ValueError(f"unsupported role: {role}")

    clean_content = str(content or "").strip()
    if not clean_content:
        raise ValueError("content is required")

    entry: dict[str, Any] = {
        "timestamp": str(timestamp or _now_iso()),
        "chat_id": _normalize_chat_id(chat_id),
        "persona_id": _normalize_persona_id(persona_id),
        "role": normalized_role,
        "content": clean_content,
    }
    if str(source or "").strip():
        entry["source"] = str(source).strip()
    if isinstance(metadata, dict) and metadata:
        entry["metadata"] = dict(metadata)

    target = conversation_path(persona_id, chat_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def load_turns(persona_id: str, chat_id: Any) -> list[dict[str, Any]]:
    target = conversation_path(persona_id, chat_id)
    if not target.exists():
        return []

    turns: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        role = str(payload.get("role") or "").strip().lower()
        content = str(payload.get("content") or "").strip()
        if role not in ALLOWED_ROLES or not content:
            continue
        turns.append(payload)
    return turns


def get_history(
    persona_id: str, chat_id: Any, *, limit: int | None = None
) -> list[dict[str, str]]:
    turns = load_turns(persona_id, chat_id)
    if limit is not None and limit > 0:
        turns = turns[-limit:]
    return [
        {"role": str(turn["role"]), "content": str(turn["content"])} for turn in turns
    ]


def list_conversations(persona_id: str) -> list[str]:
    persona_dir = get_memory_path(persona_id)
    if not persona_dir.exists():
        return []

    conversation_ids: list[str] = []
    for path in sorted(persona_dir.glob("conversation_*.jsonl")):
        match = re.fullmatch(r"conversation_(.+)\.jsonl", path.name)
        if match:
            conversation_ids.append(match.group(1))
    return conversation_ids


__all__ = [
    "AGENT_MEMORY_DIR",
    "ALLOWED_ROLES",
    "append_turn",
    "conversation_path",
    "get_memory_path",
    "get_history",
    "list_conversations",
    "load_turns",
]
