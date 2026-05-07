from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import yaml

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PERSONA_CONFIG_PATH = ROOT / "config" / "agents.yaml"
STATE_DIR = ROOT / "state"
ACTIVE_AGENT_PATH = STATE_DIR / "active_agent.json"
AGENT_WORLD_PATH = STATE_DIR / "agent_world.json"
AGENT_MEMORY_DIR = STATE_DIR / "agent_memory"
ACTIVE_LANE_POLICY: dict[str, Any] = {
    "max_active": 3,
    "lanes": ["telegram", "web", "voice"],
}

DEFAULT_JARVIS_PERSONA: dict[str, Any] = {
    "id": "jarvis",
    "name": "Jarvis",
    "color": "#00d4ff",
    "voice": "AhmetNeural",
    "role": "Ana Sistem / Koordinator",
    "skills": ["general", "routing", "coordination"],
    "greeting": "Merhaba Ekrem, ben Jarvis. Nasil yardimci olabilirim?",
}

DEFAULT_PERSONAS: dict[str, dict[str, Any]] = {
    "sabri": {
        "name": "Sabri",
        "color": "#e74c3c",
        "voice": "AhmetNeural",
        "role": "Reklam Ajansi",
        "skills": ["reklam", "brief", "creative"],
    },
    "luna": {
        "name": "Luna",
        "color": "#9b59b6",
        "voice": "EmelNeural",
        "role": "Cyber / OSINT",
        "skills": ["cyber", "osint", "pentest"],
    },
    "buse": {
        "name": "Buse",
        "color": "#ff69b4",
        "voice": "EmelNeural",
        "role": "Sosyal Medya",
        "skills": ["sosyal_medya", "instagram", "icerik"],
    },
    "deniz": {
        "name": "Deniz",
        "color": "#1abc9c",
        "voice": "AhmetNeural",
        "role": "E-ticaret",
        "skills": ["e_ticaret", "trendyol", "pazaryeri"],
    },
    "eren": {
        "name": "Eren",
        "color": "#ff8c00",
        "voice": "AhmetNeural",
        "role": "YouTube / Video Analitik",
        "skills": ["youtube", "video", "kanal_analiz"],
    },
    "mert": {
        "name": "Mert",
        "color": "#ffdd00",
        "voice": "AhmetNeural",
        "role": "Derin Arastirma",
        "skills": ["arastirma", "rakip", "trend"],
    },
    "zeynep": {
        "name": "Zeynep",
        "color": "#34495e",
        "voice": "EmelNeural",
        "role": "Guvenlik / KVKK",
        "skills": ["guvenlik", "kvkk", "audit"],
    },
    "seda": {
        "name": "Seda",
        "color": "#00ff88",
        "voice": "AhmetNeural",
        "role": "Kod / Debug / PR",
        "skills": ["code_review", "implementer"],
        "visibility": "internal",
        "requires_flag": "JARVIS_DEV_MODE",
    },
    "sabrican": {
        "name": "Sabrican",
        "color": "#95a5a6",
        "voice": "AhmetNeural",
        "role": "Deploy / Ops",
        "skills": ["deploy", "ops", "openclaw_helper", "octogent_helper"],
        "visibility": "internal",
        "requires_flag": "JARVIS_ADMIN_MODE",
    },
}

DEFAULT_CODEX_SLOT_MAP = {
    "sabri": "atlas",
    "luna": "shield",
    "buse": "spark",
    "deniz": "nexus",
    "eren": "spark",
    "mert": "nexus",
    "zeynep": "shield",
    "seda": "forge",
    "sabrican": "nexus",
}

_TRUE_ENV_VALUES = {"1", "true", "yes", "on", "enabled", "aktif"}

_TRANSLATION = str.maketrans({"\u0131": "i", "\u0130": "i"})

_SWITCH_PHRASES = (
    "ile konus",
    "yi cagir",
    "e gec",
    "a gec",
    "ya gec",
    "ye gec",
    "cagir",
    "sor",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.translate(_TRANSLATION)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _memory_file(persona_id: str) -> Path:
    return AGENT_MEMORY_DIR / persona_id / "memory.jsonl"


def _default_active_payload() -> dict[str, Any]:
    return {
        "id": DEFAULT_JARVIS_PERSONA["id"],
        "name": DEFAULT_JARVIS_PERSONA["name"],
        "color": DEFAULT_JARVIS_PERSONA["color"],
        "voice": DEFAULT_JARVIS_PERSONA["voice"],
        "activated_at": None,
    }


def _default_world_payload() -> dict[str, Any]:
    return {
        "last_active": "jarvis",
        "last_activated_at": None,
        "last_active_by_lane": {},
        "history": [],
        "personas": {},
    }


def _normalize_lane(value: Any) -> str | None:
    lane = _normalize_text(value)
    if lane in ACTIVE_LANE_POLICY["lanes"]:
        return lane
    return None


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=str(path.parent),
        suffix=".tmp",
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
    except Exception as exc:
        log.warning("Persona state okunamadi (%s): %s", path.name, exc)
    return json.loads(json.dumps(fallback))


def _build_greeting(name: str, role: str) -> str:
    return f"Merhaba Ekrem, ben {name}. {role} konusunda yardimci olabilirim."


def _build_prompt(name: str, role: str, skills: list[str]) -> str:
    skill_text = ", ".join(skills) if skills else "genel yardim"
    return (
        f"Sen {name}'sin. Jarvis'in icindeki ayri bir dijital ajansin. "
        f"Rolun: {role}. Uzmanlik alanlarin: {skill_text}. "
        "Ekrem ile sadece Turkce konus. Kisa, net ama kisilikli cevap ver. "
        f"Gerekli oldugunda kendini {name} olarak tanit ve sadece kendi uzmanlik alanina gore dusun."
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict) and item:
            items.append(json.loads(json.dumps(item)))
    return items


def _flag_enabled(flag_name: str | None) -> bool:
    if not flag_name:
        return False
    value = os.getenv(str(flag_name).strip(), "")
    return str(value).strip().lower() in _TRUE_ENV_VALUES


def _is_internal_persona(persona: dict[str, Any]) -> bool:
    return str(persona.get("visibility") or "public").strip().lower() == "internal"


def _persona_is_available(
    persona: dict[str, Any], *, include_internal: bool = False
) -> bool:
    if not _is_internal_persona(persona):
        return True
    if include_internal:
        return True
    return _flag_enabled(str(persona.get("requires_flag") or ""))


def _persona_aliases(raw: dict[str, Any], persona_id: str) -> list[str]:
    aliases: list[str] = []
    candidates: list[Any] = [persona_id, raw.get("id"), raw.get("name")]
    triggers = raw.get("triggers")
    if isinstance(triggers, list):
        candidates.extend(triggers)

    seen: set[str] = set()
    for candidate in candidates:
        text = str(candidate or "").strip()
        normalized = _normalize_text(text)
        if not text or not normalized or normalized in seen:
            continue
        aliases.append(text)
        seen.add(normalized)
    return aliases


def _build_runtime_payload(
    persona: dict[str, Any], *, activated_at: str | None = None
) -> dict[str, Any]:
    payload = dict(persona)
    payload["activated_at"] = activated_at
    payload["lane_policy"] = json.loads(json.dumps(ACTIVE_LANE_POLICY))
    return payload


def _merge_persona(persona_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name") or persona_id.title()).strip() or persona_id.title()
    role = str(raw.get("role") or "Genel Yardim").strip() or "Genel Yardim"
    skills = _string_list(raw.get("skills"))
    color = str(raw.get("color") or "#00d4ff").strip() or "#00d4ff"
    voice = str(raw.get("voice") or "AhmetNeural").strip() or "AhmetNeural"
    greeting = str(raw.get("greeting") or _build_greeting(name, role)).strip()
    prompt = str(raw.get("system_prompt") or raw.get("prompt") or "").strip()
    sub_agents = _string_list(raw.get("sub_agents"))
    handoff_targets = _string_list(raw.get("handoff_targets"))
    codex_subagents = _string_list(raw.get("codex_subagents"))
    skill_surfaces = _string_list(raw.get("skill_surfaces"))
    secondary_runtimes = _dict_list(raw.get("secondary_runtimes"))
    visibility = (
        str(raw.get("visibility") or "public").strip().lower() or "public"
    )
    requires_flag = str(raw.get("requires_flag") or "").strip()
    codex_slot = (
        str(raw.get("codex_slot") or DEFAULT_CODEX_SLOT_MAP.get(persona_id) or "")
        .strip()
        .lower()
    )
    domain_limits = (
        json.loads(json.dumps(raw.get("domain_limits")))
        if isinstance(raw.get("domain_limits"), dict)
        else {}
    )
    llm_profile = (
        json.loads(json.dumps(raw.get("llm_profile")))
        if isinstance(raw.get("llm_profile"), dict)
        else {}
    )
    persona: dict[str, Any] = {
        "id": persona_id,
        "name": name,
        "color": color,
        "voice": voice,
        "role": role,
        "skills": [str(item).strip() for item in skills if str(item).strip()],
        "greeting": greeting,
        "prompt": prompt or _build_prompt(name, role, skills),
        "system_prompt": prompt or _build_prompt(name, role, skills),
        "sub_agents": [str(item).strip() for item in sub_agents if str(item).strip()],
        "handoff_targets": [
            str(item).strip() for item in handoff_targets if str(item).strip()
        ],
        "codex_subagents": [
            str(item).strip() for item in codex_subagents if str(item).strip()
        ],
        "skill_surfaces": [
            str(item).strip() for item in skill_surfaces if str(item).strip()
        ],
        "codex_slot": codex_slot,
        "visibility": visibility,
        "requires_flag": requires_flag,
        "secondary_runtimes": secondary_runtimes,
        "domain_limits": domain_limits,
        "llm_profile": llm_profile,
        "obsidian_folder": str(
            raw.get("obsidian_folder") or f"personas/{persona_id}"
        ).strip()
        or f"personas/{persona_id}",
    }
    persona["triggers"] = _persona_aliases(raw, persona_id)
    return persona


def _build_active_entry(
    persona: dict[str, Any], *, activated_at: str | None = None
) -> dict[str, Any]:
    return {
        "id": str(persona.get("id") or "jarvis"),
        "name": str(persona.get("name") or "Jarvis"),
        "color": str(persona.get("color") or "#00d4ff"),
        "voice": str(persona.get("voice") or "AhmetNeural"),
        "llm_profile": (
            json.loads(json.dumps(persona.get("llm_profile")))
            if isinstance(persona.get("llm_profile"), dict)
            else {}
        ),
        "activated_at": activated_at,
    }


def _coerce_active_entry(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return dict(_default_active_payload())
    persona_id = (
        str(payload.get("id") or payload.get("active") or "jarvis").strip().lower()
    )
    persona = _persona_by_id(persona_id or "jarvis")
    return _build_active_entry(persona, activated_at=payload.get("activated_at"))


def _default_active_state() -> dict[str, Any]:
    return {
        "version": 2,
        "updated_at": None,
        "default": dict(_default_active_payload()),
        "lanes": {},
    }


def _read_active_state() -> dict[str, Any]:
    payload = _read_json(ACTIVE_AGENT_PATH, _default_active_payload())
    state = _default_active_state()
    if not isinstance(payload, dict):
        return state

    default_payload = (
        payload.get("default") if isinstance(payload.get("default"), dict) else payload
    )
    state["default"] = _coerce_active_entry(default_payload)
    state["updated_at"] = payload.get("updated_at")

    lanes_payload = (
        payload.get("lanes") if isinstance(payload.get("lanes"), dict) else {}
    )
    lanes: dict[str, dict[str, Any]] = {}
    for lane_name, lane_payload in lanes_payload.items():
        normalized_lane = _normalize_lane(lane_name)
        if not normalized_lane:
            continue
        lanes[normalized_lane] = _coerce_active_entry(lane_payload)
    state["lanes"] = lanes
    return state


def _write_active_state(state: dict[str, Any]) -> None:
    payload = {
        "version": 2,
        "updated_at": state.get("updated_at"),
        "default": _coerce_active_entry(state.get("default")),
        "lanes": {},
    }
    lanes_payload = state.get("lanes") if isinstance(state.get("lanes"), dict) else {}
    for lane_name, lane_state in lanes_payload.items():
        normalized_lane = _normalize_lane(lane_name)
        if not normalized_lane:
            continue
        payload["lanes"][normalized_lane] = _coerce_active_entry(lane_state)
    _atomic_write_json(ACTIVE_AGENT_PATH, payload)


def load_personas() -> dict[str, dict[str, Any]]:
    raw_personas: dict[str, Any] = {}
    try:
        payload = yaml.safe_load(PERSONA_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict) and isinstance(payload.get("personas"), dict):
            raw_personas = payload["personas"]
    except Exception as exc:
        log.warning(
            "agents.yaml persona bolumu okunamadi, fallback kullaniliyor: %s", exc
        )

    personas: dict[str, dict[str, Any]] = {}
    for persona_id, defaults in DEFAULT_PERSONAS.items():
        merged = dict(defaults)
        override = raw_personas.get(persona_id)
        if isinstance(override, dict):
            merged.update(override)
        personas[persona_id] = _merge_persona(persona_id, merged)
    return personas


def list_personas(include_internal: bool = False) -> list[dict[str, Any]]:
    personas = load_personas()
    visible: list[dict[str, Any]] = []
    for persona_id in DEFAULT_PERSONAS.keys():
        persona = personas[persona_id]
        if _persona_is_available(persona, include_internal=include_internal):
            visible.append(persona)
    return visible


def _persona_by_id(persona_id: str) -> dict[str, Any]:
    key = str(persona_id or "").strip().lower()
    if key == "jarvis":
        return dict(DEFAULT_JARVIS_PERSONA)
    return load_personas().get(key, dict(DEFAULT_JARVIS_PERSONA))


def resolve_persona_name(value: str, include_internal: bool = False) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    if normalized == "jarvis":
        return "jarvis"

    for persona in list_personas(include_internal=include_internal):
        aliases = {
            _normalize_text(alias)
            for alias in _persona_aliases(persona, str(persona["id"]))
        }
        if normalized in aliases:
            return str(persona["id"])
    return None


def get_active_persona(lane: str | None = None) -> dict[str, Any]:
    active_state = _read_active_state()
    normalized_lane = _normalize_lane(lane)
    lane_state = (
        active_state.get("lanes") if isinstance(active_state.get("lanes"), dict) else {}
    )
    payload = lane_state.get(normalized_lane) if normalized_lane else None
    if not isinstance(payload, dict):
        payload = (
            active_state.get("default")
            if isinstance(active_state.get("default"), dict)
            else _default_active_payload()
        )
    persona_id = (
        str(payload.get("id") or payload.get("active") or "jarvis").strip().lower()
        or "jarvis"
    )
    persona = _persona_by_id(persona_id)
    result = _build_runtime_payload(persona, activated_at=payload.get("activated_at"))
    if normalized_lane:
        result["lane"] = normalized_lane
    return result


def switch_persona(name: str, lane: str | None = None) -> dict[str, Any]:
    persona_id = resolve_persona_name(name)
    if not persona_id:
        available = ", ".join(persona["name"] for persona in list_personas())
        return {
            "ok": False,
            "error": f"Bu isimde bir ajan tanimlamadim. Mevcut ajanlar: {available}",
        }

    normalized_lane = _normalize_lane(lane)
    current = get_active_persona(normalized_lane)
    persona = _persona_by_id(persona_id)
    activated_at = _now_iso()
    active_payload = _build_active_entry(persona, activated_at=activated_at)
    active_state = _read_active_state()
    active_state["default"] = active_payload
    active_state["updated_at"] = activated_at
    if normalized_lane:
        lane_state = active_state.setdefault("lanes", {})
        if isinstance(lane_state, dict):
            lane_state[normalized_lane] = active_payload
    _write_active_state(active_state)

    world = _read_json(AGENT_WORLD_PATH, _default_world_payload())
    personas = world.setdefault("personas", {})
    persona_entry = personas.setdefault(
        persona_id, {"activations": 0, "last_activated_at": None}
    )
    persona_entry["activations"] = int(persona_entry.get("activations") or 0) + 1
    persona_entry["last_activated_at"] = activated_at
    persona_entry["name"] = persona["name"]
    persona_entry["role"] = persona["role"]
    world["last_active"] = persona_id
    world["last_activated_at"] = activated_at
    if normalized_lane:
        last_active_by_lane = world.setdefault("last_active_by_lane", {})
        if isinstance(last_active_by_lane, dict):
            last_active_by_lane[normalized_lane] = {
                "persona": persona_id,
                "activated_at": activated_at,
            }
    history = world.setdefault("history", [])
    history.append(
        {
            "persona": persona_id,
            "name": persona["name"],
            "role": persona["role"],
            "activated_at": activated_at,
            "previous": current.get("id", "jarvis"),
            "lane": normalized_lane,
        }
    )
    world["history"] = history[-100:]
    _atomic_write_json(AGENT_WORLD_PATH, world)

    result = _build_runtime_payload(persona, activated_at=activated_at)
    result.update(
        {
            "ok": True,
            "previous": current.get("id", "jarvis"),
            "already_active": current.get("id") == persona_id,
        }
    )
    if normalized_lane:
        result["lane"] = normalized_lane
    return result


def remember(persona_id: str, text: str) -> dict[str, Any]:
    key = resolve_persona_name(persona_id) or _normalize_text(persona_id)
    entry = {"ts": _now_iso(), "persona": key, "text": str(text or "").strip()}
    memory_file = _memory_file(key)
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    with memory_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def recall(persona_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
    key = resolve_persona_name(persona_id) or _normalize_text(persona_id)
    memory_file = _memory_file(key)
    if not memory_file.exists():
        return []

    normalized_query = _normalize_text(query)
    query_terms = [term for term in normalized_query.split() if term]
    matches: list[tuple[int, dict[str, Any]]] = []
    for line in memory_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        text = str(entry.get("text") or "")
        haystack = _normalize_text(text)
        if not query_terms:
            score = 1
        else:
            score = sum(1 for term in query_terms if term in haystack)
        if score > 0:
            matches.append((score, entry))

    matches.sort(key=lambda item: (item[0], str(item[1].get("ts") or "")), reverse=True)
    return [entry for _, entry in matches[: max(int(top_k or 0), 0) or 5]]


def detect_switch_from_text(text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    if not any(phrase in normalized for phrase in _SWITCH_PHRASES):
        return None

    if re.search(r"\bjarvis\b", normalized):
        return "jarvis"

    for persona in list_personas():
        aliases = {
            _normalize_text(alias)
            for alias in _persona_aliases(persona, str(persona["id"]))
        }
        if any(
            alias and re.search(rf"\b{re.escape(alias)}\b", normalized)
            for alias in aliases
        ):
            return str(persona["id"])
    return None
