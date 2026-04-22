"""Per-persona digital brain — read/write API over JARVIS-Brain/personas/<id>/.

Layout (built by scripts/build_persona_brain_skeleton.py):
    personas/<id>/
        00-Identity.md        canonical identity, regenerated from agents.yaml
        01-Daily-Log.md       append-only daily decisions
        02-Knowledge/         domain notes (user-authored)
        03-Projects/          active projects
        04-Memory/            conversation summaries (YYYY-MM-DD.md)
        05-Skills-Refs/       skill invocation index

Reuses path-safety helpers from server.skills.persona_obsidian_skill to avoid
duplicating normalize/traversal logic.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:  # pragma: no cover - import guard for packaged vs. flat layout
    from server.skills.persona_obsidian_skill import (
        VAULT_NOT_CONFIGURED_MESSAGE,
        UnsafeNotePathError,
        VaultUnavailableError,
        _is_relative_to,
        _normalize_persona_id,
        _split_frontmatter,
    )
except ImportError:  # pragma: no cover
    from skills.persona_obsidian_skill import (  # type: ignore[no-redef]
        VAULT_NOT_CONFIGURED_MESSAGE,
        UnsafeNotePathError,
        VaultUnavailableError,
        _is_relative_to,
        _normalize_persona_id,
        _split_frontmatter,
    )

DEFAULT_BRAIN_VAULT = Path("C:/Users/sergen/Desktop/JARVIS-Brain")


def _resolve_brain_vault(vault_dir: str | Path | None = None) -> Path:
    """Locate the brain vault root.

    Precedence:
      1. explicit vault_dir argument
      2. JARVIS_BRAIN_VAULT env var (brain-specific)
      3. OBSIDIAN_VAULT_PATH env var (shared obsidian vault)
      4. DEFAULT_BRAIN_VAULT fallback
    """
    if vault_dir is not None:
        candidate = Path(vault_dir).expanduser()
    else:
        raw = (
            os.environ.get("JARVIS_BRAIN_VAULT")
            or os.environ.get("OBSIDIAN_VAULT_PATH")
            or os.environ.get("OBSIDIAN_VAULT_DIR")
            or os.environ.get("OBSIDIAN_PATH")
        )
        candidate = Path(raw).expanduser() if raw else DEFAULT_BRAIN_VAULT
    resolved = candidate.resolve(strict=False)
    if not resolved.exists() or not resolved.is_dir():
        raise VaultUnavailableError(f"brain vault path not available: {resolved}")
    return resolved


class PersonaBrainError(RuntimeError):
    """Base for brain-specific errors."""


class BrainNotInitializedError(PersonaBrainError):
    """Persona folder does not exist in vault — run the skeleton builder."""


SUBDIRS = ("02-Knowledge", "03-Projects", "04-Memory", "05-Skills-Refs")
IDENTITY_FILE = "00-Identity.md"
DAILY_LOG_FILE = "01-Daily-Log.md"
MEMORY_DIR = "04-Memory"
KNOWLEDGE_DIR = "02-Knowledge"
PROJECTS_DIR = "03-Projects"
SKILLS_DIR = "05-Skills-Refs"

MAX_CONTENT_CHARS = 8000
MAX_TOPIC_LEN = 120


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_ts(dt: datetime | None = None) -> str:
    return (dt or _now_utc()).strftime("%Y-%m-%d %H:%M UTC")


def _safe_topic(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("topic is required")
    text = re.sub(r"\s+", " ", text)
    if len(text) > MAX_TOPIC_LEN:
        text = text[:MAX_TOPIC_LEN].rstrip() + "…"
    return text


def _safe_content(value: str) -> str:
    text = str(value or "").rstrip()
    if not text:
        raise ValueError("content is required")
    if len(text) > MAX_CONTENT_CHARS:
        text = text[:MAX_CONTENT_CHARS] + "\n\n_(truncated)_"
    return text


@dataclass
class BrainSnapshot:
    persona_id: str
    identity: dict[str, Any]
    daily_log_tail: list[str]
    project_count: int
    knowledge_count: int
    memory_days: int
    last_memory_file: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "identity": self.identity,
            "daily_log_tail": self.daily_log_tail,
            "project_count": self.project_count,
            "knowledge_count": self.knowledge_count,
            "memory_days": self.memory_days,
            "last_memory_file": self.last_memory_file,
        }


class PersonaBrain:
    """Per-persona brain accessor anchored to vault/<personas_root>/<id>/."""

    def __init__(
        self,
        persona_id: str,
        *,
        vault_dir: str | Path | None = None,
        personas_root: str = "personas",
    ) -> None:
        self.persona_id = _normalize_persona_id(persona_id)
        self.vault_root = _resolve_brain_vault(vault_dir)
        brain_root = (self.vault_root / personas_root / self.persona_id).resolve(strict=False)
        if not _is_relative_to(brain_root, self.vault_root):
            raise UnsafeNotePathError(f"persona brain path escapes vault: {brain_root}")
        self.brain_root = brain_root
        if not self.brain_root.exists() or not self.brain_root.is_dir():
            raise BrainNotInitializedError(
                f"brain folder missing for persona '{self.persona_id}'. "
                "Run scripts/build_persona_brain_skeleton.py first."
            )

    # ---------- identity ----------

    def identity(self) -> dict[str, Any]:
        path = self.brain_root / IDENTITY_FILE
        if not path.exists():
            raise BrainNotInitializedError(f"{IDENTITY_FILE} missing for {self.persona_id}")
        frontmatter, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        return {
            "persona_id": self.persona_id,
            "frontmatter": frontmatter,
            "body_preview": body.strip().splitlines()[:30],
        }

    # ---------- daily log ----------

    def read_daily_log(self, *, tail: int = 20) -> list[str]:
        path = self.brain_root / DAILY_LOG_FILE
        if not path.exists():
            return []
        lines = [ln.rstrip() for ln in path.read_text(encoding="utf-8").splitlines()]
        if tail <= 0:
            return lines
        return lines[-tail:]

    def append_daily_log(self, entry: str, *, timestamp: datetime | None = None) -> Path:
        text = _safe_content(entry)
        path = self.brain_root / DAILY_LOG_FILE
        block = f"\n### {_format_ts(timestamp)}\n{text}\n"
        if path.exists():
            with path.open("a", encoding="utf-8") as f:
                f.write(block)
        else:
            path.write_text(f"# {self.persona_id} — Günlük Log\n{block}", encoding="utf-8")
        return path

    # ---------- memory (daily file) ----------

    def write_memory(
        self,
        topic: str,
        content: str,
        *,
        channel: str = "unknown",
        timestamp: datetime | None = None,
    ) -> Path:
        clean_topic = _safe_topic(topic)
        clean_content = _safe_content(content)
        ts = timestamp or _now_utc()
        day = ts.strftime("%Y-%m-%d")
        mem_dir = self.brain_root / MEMORY_DIR
        mem_dir.mkdir(exist_ok=True)
        day_file = (mem_dir / f"{day}.md").resolve(strict=False)
        if not _is_relative_to(day_file, self.brain_root):
            raise UnsafeNotePathError(f"memory file escapes brain: {day_file}")
        header_needed = not day_file.exists()
        block_lines = [
            "",
            f"## {ts.strftime('%H:%M UTC')} — {clean_topic}",
            f"_channel: {channel}_",
            "",
            clean_content,
            "",
        ]
        if header_needed:
            preamble = f"# {self.persona_id} — Memory {day}\n"
            day_file.write_text(preamble + "\n".join(block_lines), encoding="utf-8")
        else:
            with day_file.open("a", encoding="utf-8") as f:
                f.write("\n".join(block_lines))
        return day_file

    def list_memory_days(self) -> list[str]:
        mem_dir = self.brain_root / MEMORY_DIR
        if not mem_dir.is_dir():
            return []
        days = []
        for p in mem_dir.iterdir():
            if p.is_file() and p.suffix == ".md" and re.match(r"^\d{4}-\d{2}-\d{2}$", p.stem):
                days.append(p.stem)
        return sorted(days)

    # ---------- knowledge / projects ----------

    def list_projects(self) -> list[dict[str, Any]]:
        projects_dir = self.brain_root / PROJECTS_DIR
        if not projects_dir.is_dir():
            return []
        out: list[dict[str, Any]] = []
        for p in sorted(projects_dir.iterdir()):
            if p.is_file() and p.suffix == ".md" and p.name != "README.md":
                out.append({
                    "name": p.stem,
                    "path": str(p.relative_to(self.brain_root)),
                    "size": p.stat().st_size,
                })
        return out

    def search_knowledge(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        term = str(query or "").strip().lower()
        if not term:
            return []
        knowledge_dir = self.brain_root / KNOWLEDGE_DIR
        if not knowledge_dir.is_dir():
            return []
        results: list[dict[str, Any]] = []
        for path in sorted(knowledge_dir.rglob("*.md")):
            if path.name == "README.md":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            hits = []
            for i, line in enumerate(text.splitlines(), start=1):
                if term in line.lower():
                    hits.append({"line_no": i, "line": line.strip()[:200]})
                if len(hits) >= 3:
                    break
            if hits:
                results.append({
                    "path": str(path.relative_to(self.brain_root)),
                    "matches": hits,
                })
            if len(results) >= limit:
                break
        return results

    # ---------- snapshot ----------

    def snapshot(self, *, daily_tail: int = 10) -> BrainSnapshot:
        days = self.list_memory_days()
        projects = self.list_projects()
        knowledge_dir = self.brain_root / KNOWLEDGE_DIR
        knowledge_count = 0
        if knowledge_dir.is_dir():
            for path in knowledge_dir.rglob("*.md"):
                if path.name != "README.md":
                    knowledge_count += 1
        return BrainSnapshot(
            persona_id=self.persona_id,
            identity=self.identity(),
            daily_log_tail=self.read_daily_log(tail=daily_tail),
            project_count=len(projects),
            knowledge_count=knowledge_count,
            memory_days=len(days),
            last_memory_file=days[-1] if days else None,
        )


def brain_available(persona_id: str, *, vault_dir: str | Path | None = None) -> bool:
    """Cheap check — returns False on any brain-layer error."""
    try:
        PersonaBrain(persona_id, vault_dir=vault_dir)
        return True
    except (VaultUnavailableError, BrainNotInitializedError, UnsafeNotePathError, ValueError):
        return False


def iter_available_personas(*, vault_dir: str | Path | None = None) -> Iterable[str]:
    """List persona ids that have a brain folder on disk."""
    try:
        root = _resolve_brain_vault(vault_dir)
    except VaultUnavailableError:
        return []
    personas_dir = root / "personas"
    if not personas_dir.is_dir():
        return []
    return sorted(p.name for p in personas_dir.iterdir() if p.is_dir())


__all__ = [
    "PersonaBrain",
    "BrainSnapshot",
    "PersonaBrainError",
    "BrainNotInitializedError",
    "VaultUnavailableError",
    "UnsafeNotePathError",
    "brain_available",
    "iter_available_personas",
    "VAULT_NOT_CONFIGURED_MESSAGE",
]
