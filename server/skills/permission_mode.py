from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "logs"  # server/logs/
STATE_FILE = DATA_DIR / "permission_mode.json"
AUDIT_FILE = DATA_DIR / "permission_audit.jsonl"

VALID_MODES = {"strict", "auto", "danger"}
MODE_ALIASES = {
    "off": "strict",
    "strict": "strict",
    "on": "auto",
    "auto": "auto",
    "danger": "danger",
}
DEFAULT_MODE = MODE_ALIASES.get(
    os.environ.get("JARVIS_PERMISSION_MODE", "auto").strip().lower(),
    "auto",
)

SAFE_PREFIXES = [
    "cat",
    "cd",
    "dir",
    "echo",
    "git clone",
    "git diff",
    "git log",
    "git pull",
    "git status",
    "ipconfig",
    "ls",
    "mkdir",
    "node",
    "npm init",
    "npm install",
    "ollama",
    "ping",
    "pip install",
    "ps",
    "pwd",
    "python",
    "python3",
    "tasklist",
    "type",
    "uv pip install",
    "where",
    "which",
]

BLOCKED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"rm\s+-rf\s+/",
        r"\brd\s+/s\s+/q\b",
        r"\bdel\s+/f\s+/s\s+/q\b",
        r"remove-item\s+.+-recurse.+-force",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bmkfs\b",
        r"\bdd\s+",
        r"\bformat\s+[a-z]:",
        r"\.env\b",
        r"\bssh\b",
        r"\bscp\b",
    ]
]

SEGMENT_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||\||;)\s*")
RISKY_SHELL_TOKENS_RE = re.compile(r"(?:^|\s)(?:>|>>|<|2>|2>>|\$\(|`)")

_LOCK = threading.RLock()


def normalize_mode(mode: str | None) -> str:
    normalized = MODE_ALIASES.get(str(mode or "").strip().lower(), "")
    if normalized not in VALID_MODES:
        raise ValueError(f"Invalid permission mode: {mode}")
    return normalized


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def describe_mode(mode: str) -> str:
    mode = MODE_ALIASES.get(mode, mode)
    if mode == "strict":
        return "No command executes automatically."
    if mode == "auto":
        return "Only allow-listed command segments run automatically."
    if mode == "danger":
        return "All non-blocked commands run automatically."
    return "Unknown mode."


def _state_template(mode: str = DEFAULT_MODE) -> dict[str, Any]:
    return {
        "mode": mode,
        "description": describe_mode(mode),
        "updated_at": None,
        "updated_by": "default",
    }


def _write_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _audit(event: str, payload: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"event": event, "timestamp": _now(), **payload}
    with AUDIT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_mode_state() -> dict[str, Any]:
    with _LOCK:
        if not STATE_FILE.exists():
            state = _state_template()
            _write_state(state)
            return state
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            mode = normalize_mode(raw.get("mode", DEFAULT_MODE))
            return {
                "mode": mode,
                "description": describe_mode(mode),
                "updated_at": raw.get("updated_at"),
                "updated_by": raw.get("updated_by", "unknown"),
            }
        except Exception:
            state = _state_template()
            _write_state(state)
            return state


def get_mode() -> str:
    return get_mode_state()["mode"]


def set_mode(mode: str, actor: str = "system") -> dict[str, Any]:
    normalized = normalize_mode(mode)
    with _LOCK:
        previous = get_mode_state()
        state = {
            "mode": normalized,
            "description": describe_mode(normalized),
            "updated_at": _now(),
            "updated_by": actor,
        }
        _write_state(state)
        _audit(
            "mode_changed",
            {
                "previous_mode": previous["mode"],
                "mode": normalized,
                "updated_by": actor,
            },
        )
        return state


def _normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", str(command or "").strip()).lower()


def _command_segments(command: str) -> list[str]:
    return [segment.strip() for segment in SEGMENT_SPLIT_RE.split(command) if segment.strip()]


def _is_blocked(command: str) -> bool:
    return any(pattern.search(command) for pattern in BLOCKED_PATTERNS)


def _segment_is_safe(segment: str) -> bool:
    normalized = _normalize_command(segment)
    if not normalized:
        return False
    if RISKY_SHELL_TOKENS_RE.search(segment):
        return False
    for prefix in SAFE_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix + " "):
            return True
    return False


def evaluate_command(command: str, surface: str = "safe", mode: str | None = None) -> dict[str, Any]:
    normalized_surface = "danger" if surface == "danger" else "safe"
    resolved_mode = normalize_mode(mode) if mode else get_mode()
    cmd = str(command or "").strip()

    if not cmd:
        decision = {
            "allowed": False,
            "status": "empty",
            "mode": resolved_mode,
            "surface": normalized_surface,
            "command": cmd,
            "reason": "empty_command",
            "message": "Command is empty.",
        }
        _audit("command_checked", decision)
        return decision

    if len(cmd) > 500:
        decision = {
            "allowed": False,
            "status": "blocked",
            "mode": resolved_mode,
            "surface": normalized_surface,
            "command": cmd[:80] + "...",
            "reason": "command_too_long",
            "message": f"Command exceeds 500 chars ({len(cmd)}). Possible injection.",
        }
        _audit("command_checked", decision)
        return decision

    if _is_blocked(cmd):
        decision = {
            "allowed": False,
            "status": "blocked",
            "mode": resolved_mode,
            "surface": normalized_surface,
            "command": cmd,
            "reason": "blocked_pattern",
            "message": "Blocked dangerous command pattern.",
        }
        _audit("command_checked", decision)
        return decision

    if resolved_mode == "danger":
        decision = {
            "allowed": True,
            "status": "allowed",
            "mode": resolved_mode,
            "surface": normalized_surface,
            "command": cmd,
            "reason": "danger_mode",
            "message": "Command allowed in danger mode.",
        }
        _audit("command_checked", decision)
        return decision

    if normalized_surface == "danger":
        decision = {
            "allowed": False,
            "status": "approval_required",
            "mode": resolved_mode,
            "surface": normalized_surface,
            "command": cmd,
            "reason": "danger_surface_requires_danger_mode",
            "message": "Advanced commands require danger mode. Use /bypass danger first.",
        }
        _audit("command_checked", decision)
        return decision

    if resolved_mode == "strict":
        decision = {
            "allowed": False,
            "status": "approval_required",
            "mode": resolved_mode,
            "surface": normalized_surface,
            "command": cmd,
            "reason": "strict_mode",
            "message": "Strict mode is active. Switch to /bypass auto or /bypass danger.",
        }
        _audit("command_checked", decision)
        return decision

    segments = _command_segments(cmd)
    if segments and all(_segment_is_safe(segment) for segment in segments):
        decision = {
            "allowed": True,
            "status": "allowed",
            "mode": resolved_mode,
            "surface": normalized_surface,
            "command": cmd,
            "reason": "auto_allow_list",
            "message": "Command allowed by auto mode allow-list.",
        }
        _audit("command_checked", decision)
        return decision

    decision = {
        "allowed": False,
        "status": "approval_required",
        "mode": resolved_mode,
        "surface": normalized_surface,
        "command": cmd,
        "reason": "not_auto_approved",
        "message": "Command is not on the auto-approve list. Use /bypass danger to run it.",
    }
    _audit("command_checked", decision)
    return decision
