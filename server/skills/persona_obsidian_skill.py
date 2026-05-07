from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from server.persona_manager import load_personas, resolve_persona_name
except ImportError:
    from persona_manager import load_personas, resolve_persona_name

try:
    from server.skills.obsidian_sync_skill import get_obsidian_vault_dir
except ImportError:
    from obsidian_sync_skill import get_obsidian_vault_dir


class PersonaObsidianError(RuntimeError):
    pass


class VaultUnavailableError(PersonaObsidianError):
    pass


class UnsafeNotePathError(PersonaObsidianError):
    pass


VAULT_NOT_CONFIGURED_MESSAGE = "OBSIDIAN_VAULT_PATH ayarli degil"


def _sanitize_note_title(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("..", " ")
    text = text.replace("/", " ")
    text = text.replace("\\", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .-_")


def _normalize_persona_id(persona_id: str) -> str:
    resolved = resolve_persona_name(str(persona_id or "")) or str(persona_id or "")
    normalized = re.sub(r"[^a-z0-9_-]+", "-", str(resolved).strip().lower())
    normalized = normalized.strip("-")
    if not normalized:
        raise ValueError("persona_id is required")
    return normalized


def _slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "note"


def _coerce_datetime(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _load_persona_profile(persona_id: str) -> dict[str, Any]:
    normalized_persona_id = _normalize_persona_id(persona_id)
    try:
        personas = load_personas()
    except Exception:
        personas = {}
    profile = (
        personas.get(normalized_persona_id) if isinstance(personas, dict) else None
    )
    if isinstance(profile, dict):
        return dict(profile)
    return {
        "id": normalized_persona_id,
        "obsidian_folder": f"personas/{normalized_persona_id}",
    }


def _resolve_vault_dir(vault_dir: str | Path | None = None) -> Path:
    candidate = (
        Path(vault_dir).expanduser()
        if vault_dir is not None
        else get_obsidian_vault_dir()
    )
    if candidate is None:
        raise VaultUnavailableError(VAULT_NOT_CONFIGURED_MESSAGE)
    resolved = candidate.expanduser().resolve(strict=False)
    if not resolved.exists() or not resolved.is_dir():
        raise VaultUnavailableError(f"Obsidian vault path is not available: {resolved}")
    return resolved


def _resolve_vault_dir_gracefully(vault_dir: str | Path | None = None) -> Path | None:
    try:
        return _resolve_vault_dir(vault_dir)
    except VaultUnavailableError:
        if vault_dir is None:
            return None
        raise


def persona_note_dir(persona_id: str, *, vault_dir: str | Path | None = None) -> Path:
    normalized_persona_id = _normalize_persona_id(persona_id)
    vault_root = _resolve_vault_dir(vault_dir)
    profile = _load_persona_profile(normalized_persona_id)
    raw_folder = str(
        profile.get("obsidian_folder") or f"personas/{normalized_persona_id}"
    ).strip()
    folder = Path(raw_folder.replace("\\", "/"))
    if folder.is_absolute():
        raise UnsafeNotePathError(f"Persona note folder must be relative: {folder}")

    note_root = (vault_root / folder).resolve(strict=False)
    if not _is_relative_to(note_root, vault_root):
        raise UnsafeNotePathError(f"Persona note folder escapes vault root: {folder}")
    return note_root


def build_note_path(
    persona_id: str,
    title: str,
    *,
    created_at: str | datetime | None = None,
    vault_dir: str | Path | None = None,
) -> Path:
    clean_title = _sanitize_note_title(title)
    if not clean_title:
        raise ValueError("title is required")
    created = _coerce_datetime(created_at)
    stamp = created.strftime("%Y-%m-%d")
    slug = _slugify(clean_title)
    base_path = persona_note_dir(persona_id, vault_dir=vault_dir) / f"{stamp}-{slug}.md"
    candidate = base_path
    suffix = 2
    while candidate.exists():
        candidate = base_path.with_name(f"{stamp}-{slug}-{suffix}.md")
        suffix += 1
    return candidate


def render_note_markdown(
    persona_id: str,
    title: str,
    body: str,
    *,
    created_at: str | datetime | None = None,
    tags: list[str] | None = None,
) -> str:
    clean_title = _sanitize_note_title(title)
    clean_body = str(body or "").strip()
    if not clean_title:
        raise ValueError("title is required")
    if not clean_body:
        raise ValueError("body is required")

    normalized_persona_id = _normalize_persona_id(persona_id)
    created = _coerce_datetime(created_at).isoformat().replace("+00:00", "Z")
    clean_tags = [
        str(tag).strip() for tag in (tags or ["persona", "jarvis"]) if str(tag).strip()
    ]
    tag_text = ", ".join(clean_tags)
    lines = [
        "---",
        f"persona_id: {normalized_persona_id}",
        f"title: {clean_title}",
        f"created_at: {created}",
        f"tags: [{tag_text}]",
        "---",
        "",
        f"# {clean_title}",
        "",
        clean_body,
        "",
    ]
    return "\n".join(lines)


def _split_frontmatter(content: str) -> tuple[dict[str, str], str]:
    text = str(content or "")
    if not text.startswith("---\n"):
        return {}, text.strip()

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text.strip()

    header_block = parts[0].removeprefix("---\n")
    metadata: dict[str, str] = {}
    for line in header_block.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        metadata[key.strip()] = value.strip()
    return metadata, parts[1].strip()


def _parse_tags(raw_tags: str) -> list[str]:
    text = str(raw_tags or "").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text:
        return []
    return [item.strip().strip("\"'") for item in text.split(",") if item.strip()]


def parse_note_file(
    path: str | Path, *, vault_dir: str | Path | None = None
) -> dict[str, Any]:
    note_path = Path(path)
    content = note_path.read_text(encoding="utf-8")
    metadata, body = _split_frontmatter(content)
    vault_root = _resolve_vault_dir(vault_dir) if vault_dir is not None else None
    resolved_path = note_path.resolve(strict=False)
    relative_path = (
        resolved_path.relative_to(vault_root).as_posix()
        if vault_root is not None and _is_relative_to(resolved_path, vault_root)
        else note_path.as_posix()
    )
    return {
        "persona_id": metadata.get("persona_id") or note_path.parent.name,
        "path": relative_path,
        "title": metadata.get("title") or note_path.stem,
        "created_at": metadata.get("created_at")
        or datetime.fromtimestamp(note_path.stat().st_mtime, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "tags": _parse_tags(metadata.get("tags", "")),
        "body": body,
    }


def write_persona_note(
    persona_id: str,
    title: str,
    content: str | None = None,
    *,
    body: str | None = None,
    tags: list[str] | None = None,
    created_at: str | datetime | None = None,
    vault_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    vault_root = _resolve_vault_dir_gracefully(vault_dir)
    if vault_root is None:
        return None
    clean_body = str(content if content is not None else body or "").strip()
    note_path = build_note_path(
        persona_id,
        title,
        created_at=created_at,
        vault_dir=vault_root,
    )
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        render_note_markdown(
            persona_id,
            title,
            clean_body,
            created_at=created_at,
            tags=tags,
        ),
        encoding="utf-8",
    )
    return parse_note_file(note_path, vault_dir=vault_root)


def _body_without_heading(title: str, content: str) -> str:
    body = str(content or "").strip()
    expected_heading = f"# {_sanitize_note_title(title)}"
    if body.startswith(expected_heading):
        body = body[len(expected_heading) :].lstrip()
    return body


def read_persona_notes(
    persona_id: str,
    limit: int = 5,
    *,
    vault_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    if int(limit or 0) <= 0:
        return []
    vault_root = _resolve_vault_dir_gracefully(vault_dir)
    if vault_root is None:
        return []
    note_root = persona_note_dir(persona_id, vault_dir=vault_root)
    if not note_root.exists():
        return []

    notes: list[dict[str, Any]] = []
    note_paths = sorted(
        note_root.glob("*.md"),
        key=lambda current_path: current_path.stat().st_mtime,
        reverse=True,
    )
    for path in note_paths[: int(limit)]:
        note = parse_note_file(path, vault_dir=vault_root)
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        notes.append(
            {
                "title": str(note.get("title") or path.stem),
                "content": _body_without_heading(
                    str(note.get("title") or path.stem),
                    str(note.get("body") or ""),
                ),
                "date": modified_at.strftime("%Y-%m-%d"),
                "path": str(note.get("path") or ""),
            }
        )
    return notes


def get_persona_context(
    persona_id: str,
    *,
    limit: int = 5,
    vault_dir: str | Path | None = None,
) -> str:
    notes = read_persona_notes(persona_id, limit=limit, vault_dir=vault_dir)
    if not notes:
        return ""
    blocks = [
        f"[Not: {note['title']} ({note['date']})]\n{str(note['content'])[:300].strip()}"
        for note in notes
    ]
    return "\n\n".join(block for block in blocks if block.strip())


def recall_persona_notes(
    persona_id: str,
    query: str,
    *,
    top_k: int = 5,
    vault_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    try:
        vault_root = _resolve_vault_dir(vault_dir)
    except VaultUnavailableError:
        return []
    note_root = persona_note_dir(persona_id, vault_dir=vault_root)
    if not note_root.exists():
        return []

    query_terms = [
        _slugify(term) for term in str(query or "").split() if _slugify(term)
    ]
    matches: list[dict[str, Any]] = []
    for path in note_root.rglob("*.md"):
        note = parse_note_file(path, vault_dir=vault_root)
        haystack = _slugify(
            " ".join(
                [
                    str(note.get("title") or ""),
                    " ".join(note.get("tags") or []),
                    str(note.get("body") or ""),
                ]
            )
        )
        if query_terms:
            score = sum(1 for term in query_terms if term and term in haystack)
            if score <= 0:
                continue
        else:
            score = 1
        note["score"] = score
        matches.append(note)

    matches.sort(
        key=lambda item: (
            int(item.get("score") or 0),
            str(item.get("created_at") or ""),
            str(item.get("path") or ""),
        ),
        reverse=True,
    )
    return matches[:top_k]


def save_note(persona_id: str, title: str, content: str, **kwargs: Any):
    return write_persona_note(persona_id, title, content, **kwargs)


def recall_notes(persona_id: str, query: str, **kwargs: Any):
    return recall_persona_notes(persona_id, query, **kwargs)


__all__ = [
    "PersonaObsidianError",
    "UnsafeNotePathError",
    "VaultUnavailableError",
    "build_note_path",
    "get_persona_context",
    "parse_note_file",
    "persona_note_dir",
    "read_persona_notes",
    "recall_persona_notes",
    "recall_notes",
    "render_note_markdown",
    "save_note",
    "write_persona_note",
]
