from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WIKI_DIR = ROOT / "wiki"
INDEX_PATH = WIKI_DIR / "index.md"
LOG_PATH = WIKI_DIR / "log.md"
HOT_PATH = WIKI_DIR / "hot.md"
HOT_HEADER = "# Jarvis Wiki - Sicak Onbellek"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "wiki-not"


def _limit_words(text: str, max_words: int = 500) -> str:
    words = str(text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).strip() + " ..."


def _read_text(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return fallback


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _update_index(slug: str, title: str) -> None:
    existing = _read_text(
        INDEX_PATH,
        "# Jarvis Wiki - Ana Navigasyon\n\n## Auto Pages\n",
    )
    entry = f"- [[{slug}]] - {title}"
    if entry in existing:
        return
    if "## Auto Pages" not in existing:
        existing = existing.rstrip() + "\n\n## Auto Pages\n"
    updated = existing.rstrip() + f"\n{entry}\n"
    _write_text(INDEX_PATH, updated)


def _append_log(slug: str, title: str, source: str) -> None:
    existing = _read_text(
        LOG_PATH,
        "# Jarvis Wiki - Islem Gecmisi\n\n| Tarih | Kaynak | Olusturulan Sayfalar | Not |\n|-------|--------|----------------------|-----|\n",
    ).rstrip()
    row = f"| {_today()} | {source} | {slug} | {title} |"
    updated = existing + "\n" + row + "\n"
    _write_text(LOG_PATH, updated)


def update_hot_md(summary: str) -> None:
    existing = _read_text(HOT_PATH, f"{HOT_HEADER}\n")
    clean_summary = _limit_words(summary, max_words=500).strip() or "-"

    body = existing
    if body.startswith(HOT_HEADER):
        body = body[len(HOT_HEADER) :].lstrip()
    body = re.sub(
        r"## Son Otomatik Guncelleme - .*?(?=\n## |\Z)",
        "",
        body,
        count=1,
        flags=re.DOTALL,
    ).strip()

    parts = [
        HOT_HEADER,
        "",
        f"## Son Otomatik Guncelleme - {_today()}",
        clean_summary,
    ]
    if body:
        parts.extend(["", body])
    _write_text(HOT_PATH, "\n".join(parts).rstrip() + "\n")


def write_wiki_page(
    title: str,
    content: str,
    linked_personas: list[str] | None = None,
    *,
    source: str = "intent",
) -> dict[str, Any]:
    clean_title = str(title or "").strip()
    clean_content = str(content or "").strip()
    if not clean_title or not clean_content:
        raise ValueError("title and content are required")

    slug = _slugify(clean_title)
    target = WIKI_DIR / f"{slug}.md"
    persona_line = ", ".join(
        str(item).strip() for item in (linked_personas or []) if str(item).strip()
    )
    body_parts = [f"# {clean_title}", "", clean_content]
    if persona_line:
        body_parts.extend(["", f"Linked personas: {persona_line}"])
    body_parts.extend(["", f"Source: {source}", f"Updated at: {_now_iso()}", ""])
    _write_text(target, "\n".join(body_parts))

    _update_index(slug, clean_title)
    _append_log(slug, clean_title, source)
    update_hot_md(clean_content)
    return {
        "ok": True,
        "slug": slug,
        "path": str(Path("wiki") / f"{slug}.md").replace("\\", "/"),
        "title": clean_title,
        "linked_personas": [
            str(item).strip() for item in (linked_personas or []) if str(item).strip()
        ],
    }


__all__ = [
    "update_hot_md",
    "write_wiki_page",
]
