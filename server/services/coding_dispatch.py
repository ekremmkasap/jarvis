from __future__ import annotations

import unicodedata
from typing import Any

try:
    from codex_task_router import get_fallback_chain
except Exception:  # pragma: no cover
    from server.codex_task_router import get_fallback_chain  # type: ignore


CODING_COMMANDS = ("/kod", "/code", "/jcoder")
CODING_INTENT_PHRASES = (
    "kod yaz",
    "kodla",
    "implement et",
    "uygula",
    "feature ekle",
    "test ekle",
    "refactor et",
    "refaktor et",
    "patch hazirla",
    "patchle",
    "bug fix",
    "fix et",
    "dosyayi degistir",
    "dosya degistir",
    "endpoint ekle",
    "handler ekle",
    "skill yaz",
    "repoyu guncelle",
)
CODING_VERBS = (
    "duzelt",
    "fix",
    "guncelle",
    "implement",
    "ekle",
    "refactor",
    "patch",
    "yaz",
)
CODING_NOUNS = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    "bridge",
    "api",
    "router",
    "endpoint",
    "handler",
    "skill",
    "test",
    "feature",
    "bug",
    "repo",
    "kod",
    "dosya",
    "commit",
    "pr",
)
SECURITY_KEYWORDS = ("security", "audit", "guvenlik", "zafiyet", "redact", "secret")
VIDEO_KEYWORDS = (
    "ui",
    "frontend",
    "landing",
    "dashboard",
    "render",
    "hologram",
    "web",
    "page",
    "css",
)
OPS_KEYWORDS = ("deploy", "docker", "ci", "cd", "infra", "ops", "k8s", "kubernetes")
MANAGER_KEYWORDS = ("plan", "mimari", "architecture", "roadmap", "incele", "review")

PERSONA_ROLE_HINTS = {
    "seda": "backend",
    "mert": "manager",
    "buse": "video",
    "eren": "video",
    "luna": "security",
    "sabrican": "overflow",
    "sabri": "manager",
    "jarvis": "backend",
}


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.split())


def is_coding_request(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if normalized.startswith(CODING_COMMANDS):
        return True
    if any(phrase in normalized for phrase in CODING_INTENT_PHRASES):
        return True
    return any(verb in normalized for verb in CODING_VERBS) and any(
        noun in normalized for noun in CODING_NOUNS
    )


def infer_coding_role(task_text: str, persona_id: str = "") -> str:
    normalized = _normalize_text(task_text)
    if any(keyword in normalized for keyword in SECURITY_KEYWORDS):
        return "security"
    if any(keyword in normalized for keyword in VIDEO_KEYWORDS):
        return "video"
    if any(keyword in normalized for keyword in OPS_KEYWORDS):
        return "overflow"
    if any(keyword in normalized for keyword in MANAGER_KEYWORDS):
        return "manager"
    return PERSONA_ROLE_HINTS.get(_normalize_text(persona_id), "backend")


def preferred_slot_for_role(role: str) -> str | None:
    chain = get_fallback_chain(role)
    return chain[0] if chain else None


def build_coding_task_payload(
    task_text: str,
    *,
    persona: dict[str, Any] | None = None,
    source: str = "unknown",
    role: str = "backend",
) -> str:
    persona_data = persona if isinstance(persona, dict) else {}
    persona_id = str(persona_data.get("id") or "jarvis").strip() or "jarvis"
    persona_name = str(persona_data.get("name") or persona_id).strip() or persona_id
    persona_role = str(persona_data.get("role") or "").strip()
    lines = [
        "Jarvis coding execution request.",
        f"Source: {source}",
        f"Persona: {persona_name} ({persona_id})",
        f"Persona role: {persona_role or '-'}",
        f"Preferred codex role: {role}",
        "Operator intent: implement and validate changes in the local repository.",
        "Output contract: list changed files, summarize behavior changes, report test results, state residual risks.",
        "Guardrails: no merge, no publish, no destructive filesystem operations, no credential exposure.",
        "",
        "Task:",
        str(task_text or "").strip(),
    ]
    return "\n".join(lines).strip()


def dispatch_coding_task(
    task_text: str,
    *,
    persona: dict[str, Any] | None = None,
    source: str = "unknown",
    priority: int = 5,
    requested_slot: str | None = None,
    explicit_role: str | None = None,
) -> dict[str, Any]:
    clean_task = str(task_text or "").strip()
    persona_data = persona if isinstance(persona, dict) else {}
    persona_id = str(persona_data.get("id") or "jarvis").strip() or "jarvis"
    role = str(explicit_role or infer_coding_role(clean_task, persona_id)).strip().lower()
    preferred_slot = str(requested_slot or preferred_slot_for_role(role) or "").strip().lower() or None
    dispatch_text = build_coding_task_payload(
        clean_task,
        persona=persona_data,
        source=source,
        role=role,
    )

    try:
        from codex_orchestrator import dispatch_job
    except Exception:  # pragma: no cover
        from server.codex_orchestrator import dispatch_job  # type: ignore

    result = dispatch_job(
        dispatch_text,
        role=role,
        priority=int(priority or 5),
        requested_slots=[preferred_slot] if preferred_slot else None,
    )
    payload = dict(result or {})
    payload["role"] = role
    payload["persona_id"] = persona_id
    payload["persona_name"] = str(persona_data.get("name") or persona_id).strip() or persona_id
    payload["source"] = source
    payload["requested_slot"] = preferred_slot
    payload["dispatch_task"] = dispatch_text
    return payload


def format_coding_dispatch_message(result: dict[str, Any]) -> str:
    payload = result if isinstance(result, dict) else {}
    if not payload.get("ok"):
        return str(payload.get("error") or "Kod gorevi baslatilamadi.").strip()

    job_id = str(payload.get("job_id") or "-").strip() or "-"
    status = str(payload.get("status") or "queued").strip() or "queued"
    role = str(payload.get("role") or "backend").strip() or "backend"
    selected_slots = payload.get("selected_slots") or []
    slot_text = (
        ", ".join(str(slot).upper() for slot in selected_slots if str(slot).strip())
        or str(payload.get("requested_slot") or "BEKLEMEDE").upper()
    )
    persona_name = str(payload.get("persona_name") or "Jarvis").strip() or "Jarvis"
    message = str(payload.get("message") or "").strip()
    lines = [
        f"Kod gorevi alindi: {job_id}",
        f"Durum: {status}",
        f"Role: {role}",
        f"Slot: {slot_text}",
        f"Persona: {persona_name}",
    ]
    if message:
        lines.append(message)
    return "\n".join(lines).strip()
