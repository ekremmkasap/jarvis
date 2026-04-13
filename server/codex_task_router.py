from __future__ import annotations

from typing import Iterable

try:
    from account_manager import get_account_manager
except Exception:
    from server.account_manager import get_account_manager  # type: ignore


SLOT_ORDER = ["atlas", "forge", "nexus", "shield", "spark"]
ALL_AGENTS = SLOT_ORDER.copy()
SLOT_ROLES = {
    "atlas": "manager",
    "forge": "backend",
    "nexus": "overflow",
    "shield": "security",
    "spark": "voice",
}
ROLE_AFFINITY = {
    "backend": ["forge", "nexus"],
    "security": ["shield", "nexus"],
    "voice": ["spark", "nexus"],
    "video": ["spark", "nexus"],
    "core": ["atlas", "forge"],
    "manager": ["atlas"],
    "overflow": ["nexus"],
    "any": ["atlas", "forge", "nexus", "shield", "spark"],
}
ROLE_KEYWORDS: list[tuple[list[str], str]] = [
    (["backend", "bridge", "server", "api", "skill", "router", "telegram"], "backend"),
    (["security", "audit", "secret", "redact", "policy", "guvenlik", "güvenlik"], "security"),
    (["voice", "ses", "tts", "stt", "hologram", "desktop"], "voice"),
    (["video", "visual", "render", "ui", "frontend", "web", "dashboard"], "video"),
    (["overflow", "reserve", "backup"], "overflow"),
    (["core", "manager", "plan", "koordine", "koordin", "yonet", "mimari", "strateji"], "manager"),
]

SLOT_RULES: list[tuple[list[str], str]] = [
    (["plan", "koordine", "koordin", "yonet", "mimari", "strateji"], "atlas"),
    (["bridge", "bridge.py", "server", "api", "skill", "router", "telegram", "backend"], "forge"),
    (["overflow", "reserve", "backup", "archived"], "nexus"),
    (["security", "guvenlik", "güvenlik", "audit", "secret", "redact", "policy", "zafiyet"], "shield"),
    (["voice", "ses", "tts", "stt", "hologram", "desktop", "video", "visual", "render", "ui", "frontend", "web", "dashboard", "landing", "tasarim"], "spark"),
]

SLOT_CONTEXT: dict[str, str] = {
    "atlas": "Mimari koordinasyon, planlama ve task breakdown tarafina odaklan.",
    "forge": "Backend, bridge, server, API ve skill implementasyonuna odaklan.",
    "nexus": "Overflow, reserve capacity ve failover tasklerini ele al.",
    "shield": "Guvenlik, secret redaction, policy ve audit risklerine odaklan.",
    "spark": "Voice, video, visual surfaces ve operator-facing frontend akislarina odaklan.",
}


class SlotExhaustedError(RuntimeError):
    pass


def _normalize_task(task: str) -> str:
    return str(task or "").strip().lower()


def _normalize_role(role: str | None) -> str:
    normalized = str(role or "").strip().lower()
    if normalized in ROLE_AFFINITY:
        return normalized
    if normalized in {"ops", "server", "api"}:
        return "backend"
    if normalized in {"sec", "audit"}:
        return "security"
    if normalized in {"ui", "frontend", "web", "visual"}:
        return "video"
    if normalized in {"reserve", "backup"}:
        return "overflow"
    return "any"


def _infer_role_from_text(text: str) -> str:
    normalized = _normalize_task(text)
    if not normalized:
        return "any"
    for keywords, role in ROLE_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return role
    return "any"


def normalize_slots(slots: Iterable[str] | None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for slot in slots or []:
        slot_name = str(slot or "").strip().lower()
        if not slot_name or slot_name in seen:
            continue
        seen.add(slot_name)
        ordered.append(slot_name)

    return sorted(
        ordered,
        key=lambda slot_name: SLOT_ORDER.index(slot_name) if slot_name in SLOT_ORDER else len(SLOT_ORDER),
    )


def _dedupe_preserve_order(values: Iterable[str] | None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        normalized = str(value or "").strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def route_keywords(task: str) -> list[str]:
    lower = _normalize_task(task)
    if not lower:
        return ["atlas"]

    matched: list[str] = []
    for keywords, slot in SLOT_RULES:
        if any(keyword in lower for keyword in keywords):
            matched.append(slot)

    return normalize_slots(matched) or ["atlas"]


def route(task: str) -> list[str]:
    return route_keywords(task)


def get_fallback_chain(role: str) -> list[str]:
    normalized_role = _normalize_role(role)
    return _dedupe_preserve_order(ROLE_AFFINITY.get(normalized_role) or ROLE_AFFINITY["any"])


class CodexTaskRouter:
    def __init__(self) -> None:
        self.account_manager = get_account_manager()

    def get_fallback_chain(self, role: str) -> list[str]:
        return get_fallback_chain(role)

    def route_task(self, task: dict) -> str:
        payload = task if isinstance(task, dict) else {}
        role = payload.get("role") or payload.get("type") or _infer_role_from_text(
            str(payload.get("description") or payload.get("task") or "")
        )
        affinity = self.get_fallback_chain(str(role or "any"))
        available = [slot for slot in affinity if self.account_manager.is_slot_available(slot)]
        if available:
            return available[0]
        if self.account_manager.is_slot_available("nexus"):
            return "nexus"
        raise SlotExhaustedError(f"No available Codex slot for role '{role or 'any'}'")


def route_task(task: dict) -> str:
    return CodexTaskRouter().route_task(task)


def split_task(task: str, agents: list[str]) -> dict[str, str]:
    normalized_agents = normalize_slots(agents)
    if len(normalized_agents) == 1:
        return {normalized_agents[0]: str(task or "").strip()}

    slices: dict[str, str] = {}
    for agent in normalized_agents:
        context = SLOT_CONTEXT.get(agent, "Bu gorevi kendi uzmanlik alanin icin ele al.")
        slices[agent] = f"{context}\n\nAna gorev: {str(task or '').strip()}"
    return slices
