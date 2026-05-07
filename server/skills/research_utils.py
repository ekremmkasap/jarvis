"""
research_utils.py — Shared utilities for the autonomous research agent.
Handles state file I/O, credential redaction, and Telegram message formatting.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

WATCH_LIST_PATH = Path("state/research/watch_list.json")
BRIEF_HISTORY_PATH = Path("state/research/daily_brief_history.json")
MAX_BRIEF_HISTORY = 30

_SENSITIVE_PATTERNS = re.compile(
    r"(token|key|secret|password|credential|auth|bearer)",
    re.IGNORECASE,
)


# ── Watch List ────────────────────────────────────────────────────────────────

def load_watch_list() -> list:
    """Load Instagram watch list from state file."""
    try:
        if WATCH_LIST_PATH.exists():
            return json.loads(WATCH_LIST_PATH.read_text(encoding="utf-8"))
        return []
    except Exception as e:
        logger.error("watch_list load error: %s", type(e).__name__)
        return []


def save_watch_list(accounts: list) -> bool:
    """Persist Instagram watch list to state file."""
    try:
        WATCH_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        WATCH_LIST_PATH.write_text(
            json.dumps(accounts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except Exception as e:
        logger.error("watch_list save error: %s", type(e).__name__)
        return False


# ── Brief History ─────────────────────────────────────────────────────────────

def load_brief_history() -> list:
    """Load daily brief history (last MAX_BRIEF_HISTORY entries)."""
    try:
        if BRIEF_HISTORY_PATH.exists():
            return json.loads(BRIEF_HISTORY_PATH.read_text(encoding="utf-8"))
        return []
    except Exception as e:
        logger.error("brief_history load error: %s", type(e).__name__)
        return []


def save_brief_history(history: list) -> bool:
    """Persist daily brief history, trimming to MAX_BRIEF_HISTORY."""
    try:
        BRIEF_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        trimmed = history[-MAX_BRIEF_HISTORY:]
        BRIEF_HISTORY_PATH.write_text(
            json.dumps(trimmed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except Exception as e:
        logger.error("brief_history save error: %s", type(e).__name__)
        return False


# ── Security ──────────────────────────────────────────────────────────────────

def redact_credentials(text: str) -> str:
    """Replace credential-like values in text with [REDACTED]."""
    lines = text.splitlines()
    redacted = []
    for line in lines:
        if _SENSITIVE_PATTERNS.search(line):
            line = re.sub(r"=\S+", "=[REDACTED]", line)
        redacted.append(line)
    return "\n".join(redacted)


# ── Message Formatting ────────────────────────────────────────────────────────

def build_telegram_message(items: list, soul_tone: str = "") -> str:
    """
    Format research items into a Telegram message string.

    Args:
        items: list of ResearchItem dicts (source, title, url, summary)
        soul_tone: optional prefix from soul.md Araştırma Brief Prefix section

    Returns:
        Formatted string, max ~3800 chars (Telegram limit is 4096).
    """
    sections = {}
    for item in items:
        src = item.get("source", "other")
        sections.setdefault(src, []).append(item)

    source_labels = {
        "github": "🐙 GitHub Trending",
        "reddit": "🟠 Reddit",
        "twitter": "🐦 X / Twitter",
        "instagram": "📸 Instagram",
    }

    lines = []
    if soul_tone:
        lines.append(soul_tone)
        lines.append("")

    lines.append("📋 *Günlük Araştırma Briefingi*")
    lines.append("")

    for src, src_items in sections.items():
        label = source_labels.get(src, f"📌 {src.title()}")
        lines.append(f"*{label}*")
        for item in src_items[:5]:
            title = item.get("title", "")[:80]
            url = item.get("url", "")
            if url:
                lines.append(f"• [{title}]({url})")
            else:
                lines.append(f"• {title}")
        lines.append("")

    message = "\n".join(lines).strip()
    # Telegram limit guard
    if len(message) > 3800:
        message = message[:3797] + "..."
    return message
