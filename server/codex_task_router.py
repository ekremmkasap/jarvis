from __future__ import annotations

from typing import Iterable


SLOT_ORDER = ["atlas", "forge", "nexus", "shield", "spark"]
ALL_AGENTS = SLOT_ORDER.copy()

SLOT_RULES: list[tuple[list[str], str]] = [
    (["plan", "koordine", "koordin", "yonet", "yönet", "mimari", "strateji"], "atlas"),
    (["bridge", "bridge.py", "server", "api", "skill", "router", "telegram", "backend"], "forge"),
    (["voice", "ses", "tts", "stt", "hologram", "desktop"], "nexus"),
    (["security", "guvenlik", "güvenlik", "audit", "secret", "redact", "policy", "zafiyet"], "shield"),
    (["ui", "frontend", "web", "dashboard", "landing", "tasarim", "tasarım"], "spark"),
]

SLOT_CONTEXT: dict[str, str] = {
    "atlas": "Mimari koordinasyon, planlama ve task breakdown tarafina odaklan.",
    "forge": "Backend, bridge, server, API ve skill implementasyonuna odaklan.",
    "nexus": "Voice stack, TTS/STT, desktop runtime ve hologram akisina odaklan.",
    "shield": "Guvenlik, secret redaction, policy ve audit risklerine odaklan.",
    "spark": "Web UI, frontend, dashboard ve kullanici deneyimine odaklan.",
}


def _normalize_task(task: str) -> str:
    return str(task or "").strip().lower()


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


def split_task(task: str, agents: list[str]) -> dict[str, str]:
    normalized_agents = normalize_slots(agents)
    if len(normalized_agents) == 1:
        return {normalized_agents[0]: str(task or "").strip()}

    slices: dict[str, str] = {}
    for agent in normalized_agents:
        context = SLOT_CONTEXT.get(agent, "Bu gorevi kendi uzmanlik alanin icin ele al.")
        slices[agent] = f"{context}\n\nAna gorev: {str(task or '').strip()}"
    return slices
