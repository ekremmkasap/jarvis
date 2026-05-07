from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    from server.skills.obsidian_sync_skill import get_obsidian_vault_dir
except ImportError:
    from obsidian_sync_skill import get_obsidian_vault_dir

try:
    from server.skills.persona_obsidian_skill import (
        parse_note_file,
        render_note_markdown,
        write_persona_note,
    )
except ImportError:
    from persona_obsidian_skill import parse_note_file, render_note_markdown, write_persona_note


def _slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "note"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_obsidian_root() -> Path | None:
    vault_dir = get_obsidian_vault_dir()
    if vault_dir is None:
        return None
    root = Path(vault_dir).expanduser().resolve(strict=False)
    if not root.exists():
        return None
    return root


def _custom_note_path(relative_folder: str, title: str) -> tuple[Path | None, Path | None]:
    root = _resolve_obsidian_root()
    if root is None:
        return None, None

    folder = Path(relative_folder.replace("\\", "/"))
    if folder.is_absolute():
        raise RuntimeError("relative_folder relatif olmali")

    target_dir = (root / folder).resolve(strict=False)
    try:
        target_dir.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Obsidian hedef klasoru vault disina cikiyor") from exc

    stamp = _now().strftime("%Y-%m-%d-%H%M%S")
    return target_dir / f"{stamp}-{_slugify(title)}.md", root


def _write_custom_note(
    relative_folder: str,
    persona_id: str,
    title: str,
    body: str,
    tags: list[str],
) -> dict[str, Any] | None:
    target, vault_root = _custom_note_path(relative_folder, title)
    if target is None or vault_root is None:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_note_markdown(persona_id, title, body, created_at=_now(), tags=tags),
        encoding="utf-8",
    )
    parsed = parse_note_file(target, vault_dir=vault_root)
    parsed["ok"] = True
    return parsed


def auto_write_research(
    persona_id: str,
    query: str,
    result: str,
    *,
    title: str | None = None,
    source_type: str = "research",
) -> dict[str, Any] | None:
    clean_query = str(query or "").strip()
    clean_result = str(result or "").strip()
    if not clean_query or not clean_result:
        raise ValueError("query and result are required")

    note_title = str(title or clean_query[:80]).strip() or "arastirma-notu"
    note_body = (
        "## Sorgu\n"
        f"{clean_query}\n\n"
        "## Sonuc\n"
        f"{clean_result}\n"
    )
    note = write_persona_note(
        persona_id,
        note_title,
        note_body,
        created_at=_now(),
        tags=["auto", source_type, str(persona_id or "").strip() or "jarvis"],
    )
    if note is None:
        return None
    note["ok"] = True
    return note


def auto_write_pc_action(
    command: str,
    result: str,
    *,
    args: str | None = None,
    persona_id: str = "sabrican",
) -> dict[str, Any] | None:
    clean_command = str(command or "").strip()
    clean_result = str(result or "").strip()
    if not clean_command or not clean_result:
        raise ValueError("command and result are required")
    note_title = clean_command if not args else f"{clean_command} {args}"
    body = (
        f"## Komut\n{clean_command}\n\n"
        f"## Arguman\n{str(args or '-').strip()}\n\n"
        f"## Sonuc\n{clean_result}\n"
    )
    return _write_custom_note(
        "personas/sabrican/actions",
        persona_id,
        note_title,
        body,
        ["auto", "pc_action", "sabrican"],
    )


__all__ = [
    "auto_write_pc_action",
    "auto_write_research",
]
