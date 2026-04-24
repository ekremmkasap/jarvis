from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml


log = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "persona_capabilities.yaml"

ACTION_SHELL_SAFE = "shell.safe"
ACTION_SHELL_FULL = "shell.full"
ACTION_PC_LOW = "pc.low_risk"
ACTION_PC_MEDIUM = "pc.medium_risk"
ACTION_PC_HIGH = "pc.high_risk"
ACTION_OPENCLAW_HELPER = "openclaw.helper"
ACTION_OPENCLAW_DELIVER = "openclaw.deliver"
ACTION_OPERATOR_HIGH = "operator.high_risk"

KNOWN_ACTION_CLASSES = frozenset(
    {
        ACTION_SHELL_SAFE,
        ACTION_SHELL_FULL,
        ACTION_PC_LOW,
        ACTION_PC_MEDIUM,
        ACTION_PC_HIGH,
        ACTION_OPENCLAW_HELPER,
        ACTION_OPENCLAW_DELIVER,
        ACTION_OPERATOR_HIGH,
    }
)

VALID_DECISIONS = ("allow", "require_approval", "deny")

DEFAULT_MATRIX: dict[str, dict[str, str]] = {
    "default": {
        ACTION_SHELL_SAFE: "allow",
        ACTION_SHELL_FULL: "require_approval",
        ACTION_PC_LOW: "allow",
        ACTION_PC_MEDIUM: "require_approval",
        ACTION_PC_HIGH: "require_approval",
        ACTION_OPENCLAW_HELPER: "require_approval",
        ACTION_OPENCLAW_DELIVER: "require_approval",
        ACTION_OPERATOR_HIGH: "require_approval",
    }
}


def _normalize_persona(persona_id: str | None) -> str:
    return str(persona_id or "").strip().lower() or "default"


def _coerce_decision(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if text in VALID_DECISIONS:
        return text
    return None


def load_matrix(path: Path | None = None) -> dict[str, dict[str, str]]:
    target = path or CONFIG_PATH
    matrix: dict[str, dict[str, str]] = {
        "default": dict(DEFAULT_MATRIX["default"]),
    }
    if not target.exists():
        return matrix
    try:
        payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        log.warning("persona_capabilities yaml okunamadi (%s): %s", target.name, exc)
        return matrix

    raw = payload.get("persona_capabilities") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        return matrix

    for persona_id, rules in raw.items():
        if not isinstance(rules, dict):
            continue
        key = _normalize_persona(persona_id)
        cleaned: dict[str, str] = {}
        for action_class, decision in rules.items():
            action_key = str(action_class or "").strip().lower()
            if action_key not in KNOWN_ACTION_CLASSES:
                continue
            coerced = _coerce_decision(decision)
            if coerced is None:
                continue
            cleaned[action_key] = coerced
        if cleaned:
            matrix[key] = cleaned
    return matrix


_MATRIX_CACHE: dict[str, dict[str, str]] | None = None


def _get_matrix() -> dict[str, dict[str, str]]:
    global _MATRIX_CACHE
    if _MATRIX_CACHE is None:
        _MATRIX_CACHE = load_matrix()
    return _MATRIX_CACHE


def reload_matrix() -> dict[str, dict[str, str]]:
    global _MATRIX_CACHE
    _MATRIX_CACHE = load_matrix()
    return _MATRIX_CACHE


def resolve_capability(persona_id: str | None, action_class: str) -> str:
    key = _normalize_persona(persona_id)
    action_key = str(action_class or "").strip().lower()
    if action_key not in KNOWN_ACTION_CLASSES:
        return "allow"

    matrix = _get_matrix()
    persona_rules = matrix.get(key) if isinstance(matrix.get(key), dict) else None
    if persona_rules and action_key in persona_rules:
        return persona_rules[action_key]

    default_rules = matrix.get("default") if isinstance(matrix.get("default"), dict) else None
    if default_rules and action_key in default_rules:
        return default_rules[action_key]

    baseline = DEFAULT_MATRIX["default"].get(action_key)
    return baseline or "allow"


__all__ = [
    "ACTION_OPENCLAW_DELIVER",
    "ACTION_OPENCLAW_HELPER",
    "ACTION_OPERATOR_HIGH",
    "ACTION_PC_HIGH",
    "ACTION_PC_LOW",
    "ACTION_PC_MEDIUM",
    "ACTION_SHELL_FULL",
    "ACTION_SHELL_SAFE",
    "CONFIG_PATH",
    "DEFAULT_MATRIX",
    "KNOWN_ACTION_CLASSES",
    "VALID_DECISIONS",
    "load_matrix",
    "reload_matrix",
    "resolve_capability",
]
