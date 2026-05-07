from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    from server.persona_manager import get_active_persona, load_personas, resolve_persona_name
except ImportError:
    from persona_manager import get_active_persona, load_personas, resolve_persona_name

try:
    from server.persona_memory import get_memory_path
except ImportError:
    from persona_memory import get_memory_path

try:
    from server.skills.obsidian_sync_skill import get_obsidian_vault_dir
except ImportError:
    from obsidian_sync_skill import get_obsidian_vault_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _persona_registry() -> dict[str, dict[str, Any]]:
    try:
        registry = load_personas()
    except Exception:
        return {}
    return registry if isinstance(registry, dict) else {}


def _resolve_persona_id(persona_id: str | None) -> str | None:
    if not str(persona_id or "").strip():
        return None
    resolved = resolve_persona_name(str(persona_id))
    if resolved:
        return resolved
    registry = _persona_registry()
    normalized = str(persona_id or "").strip().lower()
    if normalized in registry:
        return normalized
    return None


def _iter_memory_entries(persona_id: str) -> list[dict[str, Any]]:
    persona_dir = get_memory_path(persona_id)
    if not persona_dir.exists():
        return []

    entries: list[dict[str, Any]] = []
    for path in sorted(persona_dir.glob("*.jsonl")):
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not raw_line.strip():
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue

            if "content" in payload and "role" in payload:
                entries.append(
                    {
                        "role": str(payload.get("role") or ""),
                        "content": str(payload.get("content") or "").strip(),
                        "ts": str(payload.get("timestamp") or payload.get("ts") or ""),
                    }
                )
            elif "text" in payload:
                entries.append(
                    {
                        "role": "assistant",
                        "content": str(payload.get("text") or "").strip(),
                        "ts": str(payload.get("ts") or ""),
                    }
                )
    entries = [item for item in entries if item["content"]]
    entries.sort(key=lambda item: str(item.get("ts") or ""), reverse=True)
    return entries


def _obsidian_note_stats(persona_id: str) -> tuple[int, str | None]:
    vault_dir = get_obsidian_vault_dir()
    if vault_dir is None:
        return 0, None
    root = Path(vault_dir).expanduser().resolve(strict=False)
    registry = _persona_registry()
    persona = registry.get(persona_id) or {}
    folder = Path(str(persona.get("obsidian_folder") or f"personas/{persona_id}"))
    note_dir = (root / folder).resolve(strict=False)
    try:
        note_dir.relative_to(root)
    except ValueError:
        return 0, None
    if not note_dir.exists():
        return 0, None

    notes = sorted(
        note_dir.rglob("*.md"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not notes:
        return 0, None
    return len(notes), notes[0].stem


def get_persona_memory(persona_id: str, limit: int = 5) -> dict[str, Any]:
    resolved_id = _resolve_persona_id(persona_id)
    if not resolved_id:
        raise KeyError(str(persona_id or ""))

    registry = _persona_registry()
    persona = registry.get(resolved_id) or {}
    entries = _iter_memory_entries(resolved_id)
    note_count, last_note = _obsidian_note_stats(resolved_id)
    recent_messages = entries[: max(1, min(int(limit or 5), 20))]
    return {
        "persona_id": resolved_id,
        "persona_name": str(persona.get("name") or resolved_id.title()),
        "recent_messages": recent_messages,
        "last_active": str(recent_messages[0]["ts"]) if recent_messages else None,
        "message_count": len(entries),
        "obsidian_note_count": note_count,
        "last_obsidian_note": last_note,
    }


def get_all_agents_summary() -> dict[str, Any]:
    registry = _persona_registry()
    agents = []
    for persona_id in registry.keys():
        snapshot = get_persona_memory(persona_id, limit=5)
        agents.append(
            {
                "persona_id": snapshot["persona_id"],
                "persona_name": snapshot["persona_name"],
                "last_active": snapshot["last_active"],
                "message_count": snapshot["message_count"],
                "last_obsidian_note": snapshot["last_obsidian_note"],
                "obsidian_note_count": snapshot["obsidian_note_count"],
            }
        )
    agents.sort(key=lambda item: str(item.get("persona_id") or ""))
    try:
        active = get_active_persona()
    except Exception:
        active = {"id": "jarvis"}
    return {
        "agents": agents,
        "active_persona": str(active.get("id") or "jarvis"),
        "generated_at": _now_iso(),
    }


def format_persona_memory_text(snapshot: dict[str, Any]) -> str:
    recent = snapshot.get("recent_messages") or []
    if not recent:
        return f"{snapshot.get('persona_name')}: henuz konusma gecmisi yok"
    lines = [f"{snapshot.get('persona_name')} - son mesajlar"]
    for index, item in enumerate(recent, start=1):
        lines.append(f"{index}. [{item.get('role')}] {item.get('content')}")
    return "\n".join(lines)


def format_agents_summary_text(summary: dict[str, Any]) -> str:
    lines = [
        f"Aktif persona: {summary.get('active_persona')}",
        "",
    ]
    for item in summary.get("agents") or []:
        note = item.get("last_obsidian_note") or "not yok"
        last_active = item.get("last_active") or "henuz aktif degil"
        lines.append(
            f"- {item.get('persona_name')}: last_active={last_active} | notes={item.get('obsidian_note_count')} | last_note={note}"
        )
    return "\n".join(lines).strip()


__all__ = [
    "format_agents_summary_text",
    "format_persona_memory_text",
    "get_all_agents_summary",
    "get_persona_memory",
]
