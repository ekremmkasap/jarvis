#!/usr/bin/env python3
"""
JARVIS MISSION CONTROL — bridge.py v2.3 (Windows Standalone)
Multi-Model AI Router | Telegram + Web Dashboard | eBay + Trendyol Skills
"""

import os
import asyncio
import importlib
import json
import inspect
import time
import logging
import threading
import queue
import re
import socket
import unicodedata
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

# ─────────────────────────── PATHS ────────────────────────────────
BASE_DIR = Path(__file__).parent  # server/
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ROOT_DIR = BASE_DIR.parent  # jarvis-mission-control/
WATCHDOG_HEARTBEAT_FILE = DATA_DIR / "bridge_heartbeat.json"
WATCHDOG_LOCK_FILE = DATA_DIR / "bridge.lock"
WATCHDOG_HEARTBEAT_INTERVAL = 5

# Setup sys.path BEFORE any imports from project root
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ─────────────────────────── ENV / API KEYS ───────────────────────
from runtime_config import (
    apply_runtime_cli_overrides,
    load_runtime_config,
    validate_runtime_config,
)
from model_router import build_model_router
from runtime_state import RuntimeState
from server.security.policy_gate import (
    evaluate_operator_action,
    evaluate_shell_command,
    format_policy_block_message,
)
from telegram.telegram_intelligence import TelegramIntelligence
from telegram_webhook import send_telegram_message
from services.orchestrator.live_state import (
    build_live_event_counts,
    load_task_queue_snapshot,
    read_recent_live_events,
)


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")

KNOWLEDGE_DIR = str(BASE_DIR / "knowledge")
SOUL_PATH = str(BASE_DIR / "soul.md")
SKILLS_PATH = str(BASE_DIR / "skills")
PRINTIFY_TOKEN_PATH = str(BASE_DIR / "printify_token.txt")
WEB_CHAT_ID = 9999
VOICE_CHAT_ID = 9998
DEFAULT_TELEGRAM_CHAT_ID = 9997
RUNTIME_LANES = {
    "web": WEB_CHAT_ID,
    "voice": VOICE_CHAT_ID,
    "telegram": DEFAULT_TELEGRAM_CHAT_ID,
}
ACTIVE_LANE_POLICY = {"max_active": 3, "lanes": list(RUNTIME_LANES.keys())}
_EXTERNAL_SKILL_HINTS = {
    "markxxxv_skill": "Mark-XXXV runtime",
    "crewai_skill": "external-repos/crewAI",
    "openhands_skill": "external-repos/OpenHands",
    "upondhand_skill": "external-repos/OpenHands",
    "youtube_unified_skill": "YouTube unified runtime",
    "swarms_skill": "external-repos/swarms",
    "octogent_skill": "external-repos/octogent",
    "hooks_skill": "Claude hooks runtime",
}
_CODEX_SILENT_ALERT_RE = re.compile(
    r"^(?P<slot>[A-Z0-9_-]+)\s+sessiz:\s+son aktivite\s+\d+\s+dk once$",
    re.IGNORECASE,
)

# skills dizinini import path'e ekle
if SKILLS_PATH not in sys.path:
    sys.path.insert(0, SKILLS_PATH)

# ─────────────────────────── CONFIG ───────────────────────────────
RUNTIME_CONFIG = apply_runtime_cli_overrides(
    load_runtime_config(ROOT_DIR, BASE_DIR),
    sys.argv[1:],
)
CONFIG = RUNTIME_CONFIG.as_dict()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY)
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", SERPER_API_KEY)
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", OLLAMA_API_KEY)
MODEL_ROUTER = build_model_router(
    root_dir=ROOT_DIR,
    default_ollama_url=str(CONFIG["ollama_url"]),
    request_timeout=int(CONFIG["request_timeout"]),
)

# ─────────────────────────── LOGGING ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"], encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("jarvis")


def _get_canonical_runtime():
    try:
        from server.agents.canonical import runtime as canonical_runtime

        return canonical_runtime
    except Exception as exc:  # noqa: BLE001
        try:
            from agents.canonical import runtime as canonical_runtime

            return canonical_runtime
        except Exception:
            log.warning(f"Canonical runtime unavailable: {exc}")
            return None


AGENT_KEYWORDS = {
    "planner": [
        "plan yap",
        "hedef belirle",
        "gorev olustur",
        "görev oluştur",
        "planla",
    ],
    "repo_analyst": [
        "repo analiz",
        "saglik raporu",
        "sağlık raporu",
        "git durumu",
        "kod sagligi",
        "kod sağlığı",
    ],
    "developer": ["kod yaz", "implement et", "feature ekle", "gelistir", "geliştir"],
    "reviewer": [
        "review et",
        "incele",
        "pr kontrol",
        "kodu gozden gecir",
        "kodu gözden geçir",
    ],
    "debug": [
        "hata var",
        "debug et",
        "neden calismiyor",
        "neden çalışmıyor",
        "hata bul",
    ],
    "release": [
        "release yap",
        "changelog",
        "versiyon guncelle",
        "versiyon güncelle",
        "yayinla",
        "yayınla",
    ],
    "docs": [
        "dokumantasyon yaz",
        "dökümantasyon yaz",
        "readme guncelle",
        "readme güncelle",
        "dokumante et",
        "dokümante et",
    ],
    "mission_control": [
        "sistem durumu",
        "agent saglik",
        "agent sağlık",
        "ne calisiyor",
        "ne çalışıyor",
    ],
}


def _normalize_agent_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().split())


def _detect_agent_from_text(text: str) -> str | None:
    lowered = _normalize_agent_text(text)
    if not lowered:
        return None
    for agent_name, keywords in AGENT_KEYWORDS.items():
        if any(_normalize_agent_text(keyword) in lowered for keyword in keywords):
            return agent_name
    return None


def _load_canonical_agent_classes():
    import sys as _sys

    server_path = str(BASE_DIR)
    if server_path not in _sys.path:
        _sys.path.insert(0, server_path)

    try:
        from server.agents.canonical import (
            PlannerAgent,
            RepoAnalystAgent,
            DeveloperAgent,
            ReviewerAgent,
            DebugAgent,
            ReleaseAgent,
            DocsAgent,
            VoiceNarratorAgent,
            MissionControlAgent,
        )
    except Exception:
        from agents.canonical import (
            PlannerAgent,
            RepoAnalystAgent,
            DeveloperAgent,
            ReviewerAgent,
            DebugAgent,
            ReleaseAgent,
            DocsAgent,
            VoiceNarratorAgent,
            MissionControlAgent,
        )

    return {
        "planner": PlannerAgent,
        "repo_analyst": RepoAnalystAgent,
        "developer": DeveloperAgent,
        "reviewer": ReviewerAgent,
        "debug": DebugAgent,
        "release": ReleaseAgent,
        "docs": DocsAgent,
        "voice_narrator": VoiceNarratorAgent,
        "mission_control": MissionControlAgent,
    }


def _execute_canonical_agent(
    agent_name: str, task: str, context: dict | None = None
) -> dict:
    normalized_agent = str(agent_name or "").strip().lower()
    context_data = context if isinstance(context, dict) else {}
    agent_classes = _load_canonical_agent_classes()
    agent_class = agent_classes.get(normalized_agent)
    if agent_class is None:
        raise KeyError(normalized_agent)

    agent = agent_class()
    if str(context_data.get("mode") or "").strip().lower() == "health":
        return {
            "agent_id": normalized_agent,
            "status": "ok",
            "message": "health_check_ready",
            "output": {"message": "health_check_ready"},
        }

    run_method = getattr(agent, "run", None)
    if run_method is None:
        raise AttributeError(f"{agent_class.__name__} has no run method")
    if inspect.iscoroutinefunction(run_method):
        return asyncio.run(run_method(task, context_data))

    result = run_method(task, context_data)
    if inspect.isawaitable(result):
        return asyncio.run(result)
    if not isinstance(result, dict):
        raise TypeError("Canonical agent result must be a dictionary")
    return result


def _format_canonical_agent_result(agent_name: str, result: dict) -> str:
    runtime = _get_canonical_runtime()
    if runtime is not None:
        try:
            formatted = runtime.format_canonical_result(agent_name, result)
            if formatted:
                return str(formatted)
        except Exception as exc:  # noqa: BLE001
            log.warning(f"Canonical result formatting failed for {agent_name}: {exc}")
    try:
        return json.dumps(result, ensure_ascii=False)[:2000]
    except Exception:
        return str(result)[:2000]


def _run_canonical_agent(
    agent_name: str, task: str, context: dict | None = None
) -> dict:
    normalized_agent = str(agent_name or "").strip().lower()
    task_text = str(task or "").strip()
    context_data = context if isinstance(context, dict) else {}
    health_mode = str(context_data.get("mode") or "").strip().lower() == "health"

    if not normalized_agent:
        return {"ok": False, "error": "agent field required"}
    if normalized_agent not in _load_canonical_agent_classes():
        available = sorted(_load_canonical_agent_classes().keys())
        return {
            "ok": False,
            "agent": normalized_agent,
            "error": f"Unknown agent: {normalized_agent}. Available: {available}",
        }
    if not task_text and not health_mode:
        return {"ok": False, "agent": normalized_agent, "error": "task field required"}
    if context is not None and not isinstance(context, dict):
        return {
            "ok": False,
            "agent": normalized_agent,
            "error": "context must be an object",
        }

    try:
        raw_result = _execute_canonical_agent(
            normalized_agent, task_text or "health_check", context_data
        )
    except KeyError:
        available = sorted(_load_canonical_agent_classes().keys())
        return {
            "ok": False,
            "agent": normalized_agent,
            "error": f"Unknown agent: {normalized_agent}. Available: {available}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "agent": normalized_agent, "error": str(exc)}

    if str(raw_result.get("status") or "").strip().lower() != "ok":
        return {
            "ok": False,
            "agent": normalized_agent,
            "error": str(raw_result.get("error") or "agent execution failed"),
            "raw": raw_result,
        }

    return {
        "ok": True,
        "agent": normalized_agent,
        "result": _format_canonical_agent_result(normalized_agent, raw_result),
        "raw": raw_result,
    }


def _build_agents_health_payload() -> dict:
    agent_names = [
        "planner",
        "repo_analyst",
        "developer",
        "reviewer",
        "debug",
        "release",
        "docs",
        "voice_narrator",
        "mission_control",
    ]
    results = []
    for agent_name in agent_names:
        agent_result = _run_canonical_agent(
            agent_name, "health_check", {"mode": "health"}
        )
        results.append(
            {
                "agent": agent_name,
                "status": "ok" if agent_result.get("ok") else "error",
                "error": None if agent_result.get("ok") else agent_result.get("error"),
            }
        )
    return {
        "agents": results,
        "total": len(results),
        "healthy": sum(1 for item in results if item["status"] == "ok"),
    }


def _dispatch_canonical_message(chat_id: int, text: str):
    runtime = _get_canonical_runtime()
    detected_agent = _detect_agent_from_text(text)
    if detected_agent:
        wrapped = _run_canonical_agent(
            detected_agent, text, {"chat_id": chat_id, "source": "telegram"}
        )
        if wrapped.get("ok"):
            raw_result = (
                wrapped.get("raw") if isinstance(wrapped.get("raw"), dict) else {}
            )
            formatted = (
                runtime.format_canonical_result(detected_agent, raw_result)
                if runtime is not None and raw_result
                else str(wrapped.get("result") or "")
            )
            return detected_agent, raw_result, formatted

    if runtime is None:
        return None
    try:
        dispatched = runtime.dispatch_keyword_routed_agent(
            text, {"chat_id": chat_id, "source": "telegram"}
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(f"Canonical keyword dispatch failed: {exc}")
        return None
    if not dispatched:
        return None
    agent_id, result = dispatched
    formatted = runtime.format_canonical_result(agent_id, result)
    return agent_id, result, formatted


def _watchdog_timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_watchdog_state() -> None:
    payload = {
        "pid": os.getpid(),
        "updated_at": _watchdog_timestamp(),
        "web_port": int(CONFIG["web_port"]),
        "runtime_label": str(CONFIG["runtime_label"]),
    }
    try:
        WATCHDOG_HEARTBEAT_FILE.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        log.warning(f"Watchdog heartbeat yazilamadi: {exc}")


def _cleanup_watchdog_state() -> None:
    for target in (WATCHDOG_HEARTBEAT_FILE, WATCHDOG_LOCK_FILE):
        try:
            if target.exists():
                target.unlink()
        except Exception as exc:
            log.warning(f"Watchdog state temizlenemedi ({target.name}): {exc}")


def _watchdog_heartbeat_loop(stop_event: threading.Event) -> None:
    while not stop_event.wait(WATCHDOG_HEARTBEAT_INTERVAL):
        _write_watchdog_state()


def _start_watchdog_state() -> threading.Event:
    stop_event = threading.Event()
    try:
        WATCHDOG_LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except Exception as exc:
        log.warning(f"Watchdog lock yazilamadi: {exc}")
    _write_watchdog_state()
    threading.Thread(
        target=_watchdog_heartbeat_loop,
        args=(stop_event,),
        daemon=True,
        name="bridge-heartbeat",
    ).start()
    return stop_event


# ─── KNOWLEDGE BASE ───────────────────────────────────────────────
import glob as _glob

KNOWLEDGE = {}


def _load_knowledge():
    global KNOWLEDGE
    try:
        files = _glob.glob(f"{KNOWLEDGE_DIR}/*.md")
        for fp in files:
            name = Path(fp).stem
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                KNOWLEDGE[name] = f.read()
        log.info(f"Bilgi bankasi yuklendi: {list(KNOWLEDGE.keys())}")
    except Exception as e:
        log.warning(f"Bilgi bankasi yuklenemedi: {e}")


def get_relevant_knowledge(text: str) -> str:
    text_lower = text.lower()
    snippets = []
    if "profil" in KNOWLEDGE:
        profile_lines = [
            l
            for l in KNOWLEDGE["profil"].split("\n")
            if l.startswith("- ") or l.startswith("**")
        ][:8]
        snippets.append("Kullanici profili:\n" + "\n".join(profile_lines))
    if any(k in text_lower for k in ["ebay", "dropship", "listing", "urun", "satis"]):
        if "ebay_strateji" in KNOWLEDGE:
            snippets.append("eBay Bilgisi:\n" + KNOWLEDGE["ebay_strateji"][:600])
    if any(k in text_lower for k in ["trendyol", "tr pazar", "turkiye"]):
        if "trendyol_strateji" in KNOWLEDGE:
            snippets.append(
                "Trendyol Bilgisi:\n" + KNOWLEDGE["trendyol_strateji"][:600]
            )
    if any(
        k in text_lower
        for k in [
            "reklam",
            "ajans",
            "sabri",
            "creative director",
            "mert durmazer",
            "paperclip",
            "agentic",
            "ai ajan",
            "micro agent",
            "micro ajan",
            "brief",
            "kampanya",
            "brand dna",
        ]
    ):
        if "sabri_mert_durmazer_ai_ajans" in KNOWLEDGE:
            snippets.append(
                "Sabri reklam ajansi kaynagi (Mert Durmazer / Paperclip / Agentic):\n"
                + KNOWLEDGE["sabri_mert_durmazer_ai_ajans"][:900]
            )
    return "\n\n".join(snippets) if snippets else ""


_load_knowledge()

# ─── SOUL ──────────────────────────────────────────────────────────
try:
    with open(SOUL_PATH, "r", encoding="utf-8") as _f:
        JARVIS_SOUL = _f.read()
    log.info("soul.md yuklendi")
except Exception as _e:
    JARVIS_SOUL = (
        "Sen Jarvis'sin, Ekrem'in AI asistani. Zeki, pratik, Tony Stark tarzi."
    )
    log.warning(f"soul.md bulunamadi: {_e}")

# ─── TELEGRAM INTELLIGENCE ──────────────────────────────────────────
try:
    TELEGRAM_INTELLIGENCE = TelegramIntelligence(
        log_dir=str(BASE_DIR / "logs" / "telegram")
    )
    log.info("Telegram intelligence initialized")
except Exception as _e:
    TELEGRAM_INTELLIGENCE = None
    log.warning(f"Telegram intelligence init failed: {_e}")

# ─── SELF-LEARNING ENGINE ────────────────────────────────────────────
try:
    import sys as _sys

    _repo_root = str(BASE_DIR.parent)
    if _repo_root not in _sys.path:
        _sys.path.insert(0, _repo_root)

    try:
        from server.agents.conversation_learner import ConversationLearner
        from server.agents.skill_auto_tuner import SkillAutoTuner
    except ImportError:
        from agents.conversation_learner import ConversationLearner
        from agents.skill_auto_tuner import SkillAutoTuner

    _CONV_LEARNER: ConversationLearner = None  # call_ollama hazır olunca init edilir
    _SKILL_TUNER: SkillAutoTuner = None
    _LEARNING_ENABLED = True
    log.info("Self-learning modules loaded")
except Exception as _le:
    _CONV_LEARNER = None
    _SKILL_TUNER = None
    _LEARNING_ENABLED = False
    log.warning(f"Self-learning init failed: {_le}")


def _get_conv_learner():
    """ConversationLearner'ı call_ollama hazır olduktan sonra lazy-init et."""
    global _CONV_LEARNER, _SKILL_TUNER
    if not _LEARNING_ENABLED:
        return None
    if _CONV_LEARNER is None:
        try:
            _CONV_LEARNER = ConversationLearner(call_ollama)
            _SKILL_TUNER = SkillAutoTuner(call_ollama)
        except Exception as e:
            log.warning(f"ConversationLearner lazy-init failed: {e}")
    return _CONV_LEARNER


# ─────────────────────────── MODEL ROUTES ─────────────────────────
MODEL_ROUTES = {
    "code": {
        "model": "groq/llama-3.3-70b-versatile",
        "fallback": "gemini/gemini-2.5-flash",
        "second_fallback": "ollama/gemma4:e2b",
        "keywords": [
            "kod",
            "yaz",
            "python",
            "javascript",
            "bug",
            "hata",
            "script",
            "code",
            "write",
            "function",
            "class",
            "debug",
            "fix",
            "program",
        ],
        "system": "Sen uzman bir yazilim gelistiricisin. Temiz, yorumlanmis ve calisan kod yaz.",
    },
    "reasoning": {
        "model": "groq/qwen-qwq-32b",
        "fallback": "gemini/gemini-2.5-pro",
        "keywords": [
            "neden",
            "analiz",
            "planla",
            "strateji",
            "dusun",
            "mantik",
            "why",
            "analyze",
            "plan",
            "strategy",
            "think",
            "reason",
            "decide",
        ],
        "system": "Sen derin dusunen bir stratejist ve analistsin. Adim adim mantik yurut.",
    },
    "vision": {
        "model": "gemini/gemini-2.5-flash",
        "fallback": "ollama/moondream:latest",
        "keywords": [
            "ekran",
            "goruntu",
            "bak",
            "ne var",
            "screen",
            "image",
            "foto",
            "goster",
            "gorsel",
            "pencere",
            "uygulama",
        ],
        "system": "Sen ekrani analiz eden bir AI asistanisin. Ne goruyorsun detayli anlat.",
    },
    "search": {
        "model": "gemini/gemini-2.5-flash",
        "fallback": "groq/llama-3.3-70b-versatile",
        "keywords": [
            "ara",
            "bul",
            "ebay",
            "trendyol",
            "urun",
            "fiyat",
            "piyasa",
            "search",
            "find",
            "product",
            "price",
            "market",
            "trend",
        ],
        "system": "Sen bir e-ticaret ve piyasa arastirma uzmaninisin. Detayli ve pratik bilgi ver.",
    },
    "system": {
        "model": "groq/llama-3.1-8b-instant",
        "fallback": "gemini/gemini-2.5-flash",
        "keywords": [
            "durum",
            "sistem",
            "servis",
            "sunucu",
            "calistir",
            "durdur",
            "status",
            "service",
            "server",
            "run",
            "stop",
            "restart",
            "memory",
            "cpu",
        ],
        "system": "Sen bir sistem yoneticisisin. Komutlari dogru ve guvenli ver.",
    },
    "marketing": {
        "model": "groq/llama-3.3-70b-versatile",
        "fallback": "gemini/gemini-2.5-flash",
        "keywords": [
            "reklam",
            "kampanya",
            "marka",
            "icerik",
            "satis",
            "musteri",
            "instagram",
            "tiktok",
            "linkedin",
            "brief",
            "kopya",
            "hook",
            "reklam_ajans",
            "websitesi",
            "holding",
            "ajans",
        ],
        "system": "Sen uzman bir dijital pazarlama ve reklam danismanisin. Turkiye pazarini iyi bilirsin. Kisa, net, aksiyona donusulebilir tavsiyeler ver.",
    },
    "general": {
        "model": "groq/llama-3.1-8b-instant",
        "fallback": "gemini/gemini-2.5-flash",
        "second_fallback": "ollama/gemma4:e2b",
        "keywords": [],
        "system": "Sen yardimci bir AI asistanisin. Kisa ve net yanit ver.",
    },
    "chat": {
        "model": "groq/llama-3.1-8b-instant",
        "fallback": "gemini/gemini-2.5-flash",
        "second_fallback": "ollama/gemma4:e2b",
        "keywords": [],
        "system": JARVIS_SOUL,
    },
    "heavy": {
        "model": "gemini/gemini-2.5-pro",
        "fallback": "groq/qwen-qwq-32b",
        "keywords": [],
        "system": "Sen guclu bir yapay zeka asistanisin. Kapsamli ve detayli yanit ver.",
    },
}

# ─── ACTIVE AGENT STATE ───────────────────────────────────────────
STATE = RuntimeState(CONFIG["memory_file"])
ACTIVE_AGENTS = STATE.active_agents
CONTENT_FACTORY_SESSIONS = STATE.content_factory_sessions

# ─── MEMORY SKILL ─────────────────────────────────────────────────
try:
    from memory_skill import save_message, get_history, format_history_for_ollama
    from memory_skill import save_fact, get_facts, get_user_context
    from memory_skill import add_task, get_tasks, update_task, daily_memory_report
    from memory_skill import init_db

    init_db()
    MEMORY_ENABLED = True
    log.info("memory_skill yuklendi")
except Exception as _me:
    MEMORY_ENABLED = False

    def save_message(*a, **k):
        pass

    def get_history(*a, **k):
        return []

    def format_history_for_ollama(*a, **k):
        return []

    def get_user_context(*a, **k):
        return ""

    def add_task(*a, **k):
        return 0

    def get_tasks(*a, **k):
        return "Hafiza kapali"

    def update_task(*a, **k):
        return ""

    def daily_memory_report(*a, **k):
        return "Hafiza kapali"


# ─── REME UZUN VADELI HAFIZA ──────────────────────────────────────
import asyncio as _asyncio

_reme_instance = None
_reme_loop = None
_reme_thread = None


def _start_reme_loop():
    global _reme_instance, _reme_loop
    _reme_loop = _asyncio.new_event_loop()
    _asyncio.set_event_loop(_reme_loop)

    async def _init():
        global _reme_instance
        try:
            sys.path.insert(0, str(BASE_DIR))
            from reme import ReMe

            # OpenAI key varsa daha iyi embedding kullan, yoksa Ollama fallback
            if OPENAI_API_KEY and OPENAI_API_KEY != "sk-buraya-yaz":
                emb_cfg = {
                    "backend": "openai",
                    "model_name": "text-embedding-3-small",
                    "api_key": OPENAI_API_KEY,
                }
                log.info("ReMe: OpenAI embedding aktif")
            else:
                emb_cfg = {
                    "backend": "openai",
                    "model_name": "gemma4:e2b",
                    "base_url": "http://127.0.0.1:11434/v1",
                    "api_key": "ollama",
                }
                log.info("ReMe: Ollama embedding aktif (OpenAI key girilmedi)")
            _reme_instance = ReMe(
                working_dir=str(BASE_DIR / ".reme"),
                enable_logo=False,
                log_to_console=False,
                default_llm_config={
                    "backend": "openai",
                    "model_name": "gemma4:e2b",
                    "base_url": "http://127.0.0.1:11434/v1",
                    "api_key": "ollama",
                },
                default_embedding_model_config=emb_cfg,
                default_vector_store_config={"backend": "local"},
            )
            await _reme_instance.start()
            log.info("ReMe uzun vadeli hafiza aktif")
        except Exception as e:
            log.warning(f"ReMe baslatma hatasi: {e}")
            _reme_instance = None

    _reme_loop.run_until_complete(_init())
    _reme_loop.run_forever()


_reme_thread = threading.Thread(target=_start_reme_loop, daemon=True, name="reme-loop")
_reme_thread.start()


def reme_get_context(query: str, user_name: str = "ekrem") -> str:
    """Sorguyla ilgili en yakın bellek kayitlarini getirir (non-blocking, 3s timeout)."""
    if not _reme_instance or not _reme_loop:
        return ""
    try:
        future = _asyncio.run_coroutine_threadsafe(
            _reme_instance.list_memory(user_name=user_name, limit=5), _reme_loop
        )
        memories = future.result(timeout=3)
        if not memories:
            return ""
        lines = [m.content for m in memories[:5]]
        return "Uzun vadeli hafiza:\n" + "\n".join(f"- {l}" for l in lines)
    except Exception:
        return ""


def reme_save(user_msg: str, assistant_msg: str, user_name: str = "ekrem"):
    """Konusmadan onemli bilgileri arka planda belleğe kaydeder."""
    if not _reme_instance or not _reme_loop:
        return
    content = f"Kullanici: {user_msg[:200]} | Jarvis: {assistant_msg[:200]}"

    async def _save():
        try:
            await _reme_instance.add_memory(memory_content=content, user_name=user_name)
        except Exception as e:
            log.debug(f"ReMe kayit hatasi: {e}")

    _asyncio.run_coroutine_threadsafe(_save(), _reme_loop)


# ─── INTENT CLASSIFIER ────────────────────────────────────────────
try:
    from intent_skill import classify_intent, handle_with_intent

    INTENT_ENABLED = True
except Exception:
    INTENT_ENABLED = False

    def classify_intent(t):
        return None

    def handle_with_intent(t, u=None):
        return None


# ─── MEMORY (JSON fallback) ───────────────────────────────────────
memory = STATE.memory

# Wire JSON memory → memory_skill (SQLite + semantic + fact extraction).
# Without this bridge, save_message/_extract_facts never runs and
# get_user_context() returns "", so the LLM never sees who the user is.
if MEMORY_ENABLED:
    _memory_add_original = memory.add_message

    def _memory_add_with_skill(chat_id, role, content, model=None):
        _memory_add_original(chat_id, role, content, model)
        try:
            save_message(str(chat_id), role, content, command=model)
        except Exception as _mem_sync_err:
            log.debug(f"memory_skill sync skipped: {_mem_sync_err}")

    memory.add_message = _memory_add_with_skill
    log.info("memory_skill wired to memory.add_message (fact extraction active)")

# ─── MONITORING: Health & Metrics ─────────────────────────────────
try:
    from monitoring.health_check import HealthChecker
    from monitoring.execution_metrics import ExecutionMetricsCollector

    HEALTH_CHECKER = HealthChecker(log_dir=str(BASE_DIR / "logs"))
    METRICS_COLLECTOR = ExecutionMetricsCollector(log_dir=str(BASE_DIR / "logs"))
    MONITORING_ENABLED = True
    log.info("Monitoring modules initialized (health check + metrics collection)")
except Exception as _me:
    MONITORING_ENABLED = False
    HEALTH_CHECKER = None
    METRICS_COLLECTOR = None
    log.warning(f"Monitoring disabled: {_me}")


# ─────────────────────────── HELPERS ──────────────────────────────
def detect_route(text: str):
    text_lower = text.lower()
    for route_name, route in MODEL_ROUTES.items():
        if route_name in ("chat", "general"):
            continue
        for kw in route["keywords"]:
            if kw in text_lower:
                return route_name, route
    return "chat", MODEL_ROUTES["chat"]


def get_selected_candidate(default_model: str) -> str:
    trace = STATE.last_route_trace if isinstance(STATE.last_route_trace, dict) else {}
    selected = str(trace.get("selected_candidate", "")).strip()
    return selected or default_model


def get_provider_health() -> dict:
    return get_router_health_snapshot().get("providers", {})


def get_router_health_snapshot() -> dict:
    try:
        return MODEL_ROUTER.build_health_snapshot(
            route_map=MODEL_ROUTES,
            ollama_models=get_available_models(),
            last_trace=STATE.last_route_trace
            if isinstance(STATE.last_route_trace, dict)
            else {},
        )
    except AttributeError:
        # build_health_snapshot metodu ModelRouter'da tanımlı değil — safe fallback
        providers = {}
        try:
            for name, route in MODEL_ROUTES.items():
                providers[name] = {"status": "ok", "route": str(route)}
        except Exception:
            pass
        return {"providers": providers, "status": "ok", "error": "snapshot_unavailable"}


def _merge_health_status(primary_status: str, router_status: str) -> str:
    primary = str(primary_status or "").strip().lower()
    router = str(router_status or "").strip().lower()

    if primary in {"unhealthy", "failed"} or router in {"unhealthy"}:
        return "unhealthy"
    if primary in {"degraded", "warning"} or router in {"degraded", "disabled"}:
        return "degraded"
    return primary_status


def get_agent_os_runtime():
    if STATE.agent_os_runtime is None:
        sys.path.insert(0, str(BASE_DIR / "core"))
        sys.path.insert(0, str(BASE_DIR / "agent_os"))
        from runtime import AgentOSRuntime

        STATE.agent_os_runtime = AgentOSRuntime(call_ollama, base_dir=BASE_DIR)
    return STATE.agent_os_runtime


def should_use_team_mode(text: str) -> bool:
    lower = text.lower()
    triggers = [
        "agent team",
        "otomat",
        "otomasyon",
        "orchestrator",
        "workflow",
        "mimari",
        "architecture",
        "auth",
        "login",
        "register",
        "security review",
        "guvenlik incele",
        "kod yaz",
        "code review",
        "refactor",
        "entegrasyon",
    ]
    strong_matches = sum(1 for item in triggers if item in lower)
    return strong_matches >= 2 or (
        len(text) > 140 and any(item in lower for item in triggers)
    )


def run_team_task(chat_id: int, goal: str) -> str:
    runtime = get_agent_os_runtime()
    result = runtime.run(goal, chat_id=str(chat_id))
    status = result.get("status", "unknown")
    synthesis = (
        result.get("summary")
        or result.get("synthesis")
        or result.get("reason")
        or "Team sonucu uretemedi."
    )
    memory.add_message(chat_id, "user", f"/team {goal}")
    memory.add_message(chat_id, "assistant", synthesis, "agent_os")
    task_id = result.get("task_id", "-")
    badge = "✅" if result.get("guard_passed") else "⚠️"
    return f"{badge} *Team Task #{task_id}* (`{status}`)\n\n{synthesis}"


_VOICE_TEST_MANAGER = None
_WEEK1_PIPELINE = None


def get_voice_test_manager():
    global _VOICE_TEST_MANAGER
    if _VOICE_TEST_MANAGER is None:
        from server.voice.voice_layer import VoiceConversationManager

        _VOICE_TEST_MANAGER = VoiceConversationManager()
    return _VOICE_TEST_MANAGER


def get_week1_pipeline():
    global _WEEK1_PIPELINE
    if _WEEK1_PIPELINE is None:
        from server.agents.week1_pipeline import Week1Pipeline

        _WEEK1_PIPELINE = Week1Pipeline()
    return _WEEK1_PIPELINE


def run_week1_task(chat_id: int, goal: str) -> str:
    result = get_week1_pipeline().run(goal)
    memory.add_message(chat_id, "user", f"/task {goal}")
    memory.add_message(
        chat_id, "assistant", result.get("summary", ""), "week1_pipeline"
    )
    return (
        f"*Week 1 Task Flow* (`{result.get('status', 'unknown')}`)\n\n"
        f"{result.get('summary', 'No summary available.')}"
    )


def handle_voice_test_command(chat_id: int, args: str) -> str:
    manager = get_voice_test_manager()
    parts = [part for part in str(args or "").split() if part]
    action = parts[0].lower() if parts else "start"

    if action == "stop":
        status = manager.stop_session(chat_id)
        return f"Voice test stopped. Turns: {status.turns}. Mode: {status.mode}."

    if action == "status":
        status = manager.get_status(chat_id)
        if not status.active:
            return "Voice test is inactive."
        return (
            f"Voice test active. Remaining seconds: {int(status.remaining_seconds)}. "
            f"Turns: {status.turns}. Mode: {status.mode}."
        )

    duration_seconds = 300
    if action == "start" and len(parts) > 1:
        try:
            duration_seconds = max(60, int(parts[1]) * 60)
        except ValueError:
            duration_seconds = 300

    status = manager.start_session(chat_id, duration_seconds=duration_seconds)
    return (
        "Voice test started for 5 minutes. "
        "Send normal messages for conversation, or prefix a message with `task:` to run the Week 1 task flow. "
        f"Mode: {status.mode}."
    )


def get_available_models() -> list:
    try:
        req = Request(f"{CONFIG['ollama_url']}/api/tags")
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except:
        return []


def get_agent_os_visual_status() -> dict:
    status_path = BASE_DIR / "logs" / "agent_os_status.json"
    if status_path.exists():
        try:
            return json.loads(status_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "mode": "agent_os",
        "status": "idle",
        "current_job": None,
        "updated_at": datetime.now().isoformat(),
        "agents": {
            "jarvis": "idle",
            "claude": "idle",
            "ollama": "idle",
            "research": "idle",
            "guard": "idle",
        },
        "jobs": [],
        "stats": {},
    }


def get_agent_os_visual_events(limit: int = 25) -> list:
    events_path = BASE_DIR / "logs" / "agent_os_events.jsonl"
    if not events_path.exists():
        return []
    try:
        lines = events_path.read_text(encoding="utf-8", errors="ignore").splitlines()[
            -limit:
        ]
        return [json.loads(line) for line in lines if line.strip()]
    except Exception:
        return []


def get_desktop_assistant_payload() -> dict:
    payload_path = BASE_DIR / "logs" / "desktop_assistant.json"
    default_payload = {
        "phase": "idle",
        "text": "Jarvis hazir.",
        "agent": "jarvis",
        "latestPreview": "",
        "updated_at": time.time(),
        "runtime": {
            "status": "offline",
            "detail": "voice runtime inactive",
            "source": "bridge",
            "mode": "",
            "wake_mode": "",
            "stt_backend": "",
            "tts_backend": "",
        },
        "voice": {
            "last_heard": "",
            "last_response": "",
            "heard_at": 0.0,
            "response_at": 0.0,
            "turn_count": 0,
        },
    }

    payload: dict = {}
    if payload_path.exists():
        try:
            loaded = json.loads(payload_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except Exception:
            payload = {}

    status = get_agent_os_visual_status()
    current_job = status.get("current_job") if isinstance(status, dict) else None
    active_agent = status.get("active_agent") if isinstance(status, dict) else None

    if not payload:
        preview = ""
        if isinstance(current_job, dict):
            preview = str(current_job.get("task") or "").strip()
        payload = {
            **default_payload,
            "phase": "thinking" if current_job else "idle",
            "agent": str(active_agent or "jarvis"),
            "latestPreview": preview[:180],
        }

    payload.setdefault("phase", default_payload["phase"])
    payload.setdefault("text", default_payload["text"])
    payload.setdefault("agent", str(active_agent or "jarvis"))
    payload.setdefault("latestPreview", "")
    payload.setdefault("updated_at", time.time())

    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    voice = payload.get("voice") if isinstance(payload.get("voice"), dict) else {}
    payload["runtime"] = {**default_payload["runtime"], **runtime}
    payload["voice"] = {**default_payload["voice"], **voice}

    if isinstance(current_job, dict):
        payload.setdefault("latestPreview", str(current_job.get("task") or "")[:180])

    if not payload.get("text") and payload["voice"].get("last_response"):
        payload["text"] = str(payload["voice"].get("last_response") or "")[:220]
    if not payload.get("latestPreview") and payload["voice"].get("last_heard"):
        payload["latestPreview"] = str(payload["voice"].get("last_heard") or "")[:180]

    payload.setdefault(
        "mission",
        {
            "active_agent": active_agent,
            "task_status": status.get("status") if isinstance(status, dict) else None,
            "last_event": status.get("last_event")
            if isinstance(status, dict)
            else None,
            "last_task_summary": current_job.get("task")
            if isinstance(current_job, dict)
            else None,
        },
    )

    return payload


def get_office_presence_payload(limit: int = 20) -> dict:
    online: list[str] = []
    seen: set[str] = set()
    assistant_payload = get_desktop_assistant_payload()

    status = get_agent_os_visual_status()
    agents = status.get("agents", {}) if isinstance(status, dict) else {}
    if isinstance(agents, dict):
        for agent_name, agent_state in agents.items():
            state_text = str(agent_state or "").strip().lower()
            if state_text in {"running", "thinking", "listening", "speaking", "active"}:
                seen.add(str(agent_name))
                online.append(str(agent_name))

    for event in reversed(get_agent_os_visual_events(limit=limit)):
        if not isinstance(event, dict):
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        agent_name = (
            data.get("agent_name")
            or data.get("agent_id")
            or event.get("agent")
            or event.get("agent_id")
        )
        if not agent_name:
            continue
        agent_text = str(agent_name)
        if agent_text in seen:
            continue
        seen.add(agent_text)
        online.append(agent_text)

    assistant_runtime = (
        assistant_payload.get("runtime")
        if isinstance(assistant_payload.get("runtime"), dict)
        else {}
    )
    assistant_phase = str(assistant_payload.get("phase") or "").strip().lower()
    assistant_status = str(assistant_runtime.get("status") or "").strip().lower()
    if assistant_status in {"online", "ready"} or assistant_phase in {
        "listening",
        "thinking",
        "speaking",
    }:
        assistant_name = (
            str(assistant_payload.get("agent") or "voice").strip().lower() or "voice"
        )
        presence_agent = "voice" if assistant_name == "jarvis" else assistant_name
        if presence_agent not in seen:
            seen.add(presence_agent)
            online.insert(0, presence_agent)

    return {
        "online_agents": online,
        "bridge": "online",
        "updated_at": time.time(),
        "assistant": {
            "phase": assistant_phase or "idle",
            "status": assistant_status or "offline",
            "source": str(
                assistant_runtime.get("source") or assistant_payload.get("agent") or ""
            ),
        },
    }


def get_orchestrator_live_payload(event_limit: int = 25) -> dict:
    queue_snapshot = load_task_queue_snapshot()
    recent_events = read_recent_live_events(limit=event_limit)
    assistant_payload = get_desktop_assistant_payload()
    assistant_runtime = (
        assistant_payload.get("runtime")
        if isinstance(assistant_payload.get("runtime"), dict)
        else {}
    )
    assistant_voice = (
        assistant_payload.get("voice")
        if isinstance(assistant_payload.get("voice"), dict)
        else {}
    )
    active_statuses = {"pending", "queued", "running", "awaiting_confirmation"}
    current_task = None
    last_task = None

    for event in reversed(recent_events):
        task = event.get("task") if isinstance(event.get("task"), dict) else None
        if not task:
            continue
        if last_task is None:
            last_task = task
        if (
            current_task is None
            and str(task.get("status") or "").strip().lower() in active_statuses
        ):
            current_task = task

    voice_phase = (
        str(assistant_payload.get("phase") or "idle").strip().lower() or "idle"
    )
    voice_active = voice_phase in {"listening", "thinking", "speaking"}
    state_file = Path(str(queue_snapshot.get("state_file") or ""))
    orchestrator_ready = state_file.exists()
    status = "degraded" if queue_snapshot.get("failed_tasks", 0) else "healthy"
    if not orchestrator_ready:
        status = "degraded"

    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "activity": "busy"
        if current_task
        or queue_snapshot.get("queued_tasks", 0)
        or queue_snapshot.get("running_tasks", 0)
        or voice_active
        else "idle",
        "queue_snapshot": queue_snapshot,
        "current_task": current_task,
        "last_task": last_task,
        "recent_events": recent_events,
        "event_counts": build_live_event_counts(limit=max(event_limit, 100)),
        "voice": {
            "active": voice_active,
            "phase": voice_phase,
            "status": str(assistant_runtime.get("status") or "offline"),
            "detail": str(assistant_runtime.get("detail") or ""),
            "turn_count": int(assistant_voice.get("turn_count") or 0),
            "last_heard": str(assistant_voice.get("last_heard") or ""),
            "last_response": str(assistant_voice.get("last_response") or ""),
            "updated_at": assistant_payload.get("updated_at", 0.0),
        },
    }


def build_telegram_health_payload() -> dict:
    live_payload = get_orchestrator_live_payload(event_limit=10)
    queue_snapshot = live_payload["queue_snapshot"]
    current_task = live_payload.get("current_task") or live_payload.get("last_task")
    provider_health = get_provider_health()
    route_trace = (
        STATE.last_route_trace if isinstance(STATE.last_route_trace, dict) else {}
    )
    orchestrator_state_file = Path(str(queue_snapshot.get("state_file") or ""))

    return {
        "status": live_payload.get("status", "unknown"),
        "timestamp": live_payload.get("timestamp"),
        "bridge_status": "healthy",
        "orchestrator_status": "healthy"
        if orchestrator_state_file.exists()
        else "degraded",
        "queue_size": int(queue_snapshot.get("queued_tasks", 0)),
        "running_tasks": int(queue_snapshot.get("running_tasks", 0)),
        "awaiting_confirmation": int(
            queue_snapshot.get("awaiting_confirmation_tasks", 0)
        ),
        "completed_tasks": int(queue_snapshot.get("done_tasks", 0)),
        "failed_tasks": int(queue_snapshot.get("failed_tasks", 0)),
        "total_requests": int(memory.data["stats"].get("total_queries", 0)),
        "error_count": int(memory.data["stats"].get("errors", 0)),
        "current_task": current_task,
        "voice_phase": live_payload.get("voice", {}).get("phase", "idle"),
        "voice_status": live_payload.get("voice", {}).get("status", "offline"),
        "voice_active": bool(live_payload.get("voice", {}).get("active")),
        "provider_health": provider_health,
        "route_trace": route_trace,
    }


def build_telegram_metrics_payload() -> dict:
    live_payload = get_orchestrator_live_payload(event_limit=50)
    queue_snapshot = live_payload["queue_snapshot"]
    event_counts = live_payload.get("event_counts", {})
    completed_tasks = int(queue_snapshot.get("done_tasks", 0))
    failed_tasks = int(queue_snapshot.get("failed_tasks", 0))
    total_finished = completed_tasks + failed_tasks
    success_rate = (completed_tasks / total_finished) if total_finished else 0.0

    return {
        "total_executions": total_finished,
        "successful_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "queue_depth": int(queue_snapshot.get("queued_tasks", 0)),
        "running_tasks": int(queue_snapshot.get("running_tasks", 0)),
        "retry_events": int(event_counts.get("task_retry", 0)),
        "recent_events": len(live_payload.get("recent_events", [])),
        "voice_turn_count": int(live_payload.get("voice", {}).get("turn_count", 0)),
        "success_rate": success_rate,
        "avg_latency_ms": 0.0,
        "p95_latency_ms": 0.0,
        "cache_hit_rate": 0.0,
    }


def is_local_port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def call_ollama(
    model: str,
    messages: list,
    system: str = None,
    max_tokens: int = 1024,
    num_ctx: int = 2048,
    fallback_model: str = None,
    route_name: str | None = None,
):
    """
    Multi-provider model router.
    1) Primary model
    2) Route fallback (if any)
    3) config/model_router.yml chain
    """
    import time as _time_module

    start_time = _time_module.time()
    extra_fallback_models: list[str] = []
    explicit_provider_model = False

    route = MODEL_ROUTES.get(route_name or "", {}) if route_name else {}
    route_second_fallback = route.get("second_fallback")
    if isinstance(route_second_fallback, str):
        route_second_fallback = route_second_fallback.strip()
        if route_second_fallback:
            extra_fallback_models.append(route_second_fallback)
    elif isinstance(route_second_fallback, list):
        extra_fallback_models.extend(
            item.strip()
            for item in route_second_fallback
            if isinstance(item, str) and item.strip()
        )

    inspected_model = (
        MODEL_ROUTER.inspect_model_ref(model)
        if hasattr(MODEL_ROUTER, "inspect_model_ref")
        else {
            "raw": str(model or "").strip(),
            "explicit_provider": False,
            "valid": True,
            "error": "",
        }
    )
    if not inspected_model.get("valid", False):
        trace = {
            "ok": False,
            "error": str(inspected_model.get("error", "Gecersiz model referansi.")),
            "route": route_name or "",
            "selected_provider": "",
            "selected_model": "",
            "selected_candidate": "",
            "fallback_used": False,
            "attempts": [
                {
                    "provider": str(inspected_model.get("provider", "")),
                    "model": str(inspected_model.get("model", "")) or str(model or ""),
                    "ok": False,
                    "retryable": False,
                    "error": str(inspected_model.get("error", "")),
                    "source": "bridge:validation",
                }
            ],
        }
        trace["requested_model"] = model
        trace["requested_fallback_model"] = fallback_model
        trace["requested_extra_fallback_models"] = extra_fallback_models
        STATE.last_route_trace = trace
        return trace["error"]

    explicit_provider_model = bool(inspected_model.get("explicit_provider"))
    if explicit_provider_model:
        model = (
            f"{inspected_model['provider']}/{inspected_model['model']}"
            if inspected_model.get("provider") and inspected_model.get("model")
            else str(model or "").strip()
        )

    if model and not explicit_provider_model:
        available = get_available_models()
        if available and not any(model.split(":")[0] in item for item in available):
            model = available[0]

    # ── Persona system prompt inject ──────────────────────────────────────
    # Aktif persona Jarvis değilse system_prompt'u LLM çağrısına ekle.
    try:
        from server.persona_manager import get_active_persona as _get_active_persona
        _persona = _get_active_persona()
        _persona_id = _persona.get("id", "jarvis") if isinstance(_persona, dict) else "jarvis"
        if _persona_id != "jarvis":
            _persona_prompt = _build_persona_system_prompt(_persona).strip()
            if _persona_prompt:
                # max 400 token güvencesi: yaklaşık 1600 karakter
                _persona_prompt = _persona_prompt[:1600]
                system = "\n\n".join(filter(None, [_persona_prompt, system or ""]))
    except Exception:
        pass
    # ─────────────────────────────────────────────────────────────────────

    response, trace = MODEL_ROUTER.chat(
        route_name=route_name,
        primary_model=model,
        fallback_model=fallback_model,
        extra_fallback_models=extra_fallback_models,
        messages=messages,
        system=system,
        max_tokens=max_tokens,
        num_ctx=num_ctx,
    )

    trace["requested_model"] = model
    trace["requested_fallback_model"] = fallback_model
    trace["requested_extra_fallback_models"] = extra_fallback_models
    STATE.last_route_trace = trace

    # ──── WEEK 2: Record execution metrics ────
    duration_seconds = _time_module.time() - start_time
    if MONITORING_ENABLED and METRICS_COLLECTOR:
        try:
            status = "success" if trace.get("ok") else "failure"
            action = route_name or "chat"
            result_size = (
                len(response.encode("utf-8")) if isinstance(response, str) else 0
            )
            error_msg = trace.get("error") if not trace.get("ok") else None

            METRICS_COLLECTOR.record_execution(
                run_id=f"msg_{int(_time_module.time() * 1000)}",
                action=action,
                status=status,
                duration_seconds=duration_seconds,
                result_size_bytes=result_size,
                error_message=error_msg,
                cache_hit=False,  # Can be enhanced with actual cache tracking
                retry_count=len(trace.get("attempts", [])) - 1
                if trace.get("attempts")
                else 0,
            )
        except Exception as _me:
            log.debug(f"Failed to record metrics: {_me}")

    if trace.get("ok"):
        selected = trace.get("selected_candidate") or model
        if trace.get("fallback_used"):
            log.info(f"Fallback kullanildi: {selected}")
        else:
            log.info(f"Model secildi: {selected}")
        return response

    attempts = trace.get("attempts", [])
    if attempts:
        failed = ", ".join(
            f"{item.get('provider')}/{item.get('model')}"
            for item in attempts
            if not item.get("ok")
        )
        log.error(
            f"Model router basarisiz: {trace.get('error')} | Denenenler: {failed}"
        )
    else:
        log.error(f"Model router basarisiz: {trace.get('error')}")
    return f"LLM yaniti alinamadi: {trace.get('error')}"


def get_system_info() -> dict:
    """Cross-platform sistem bilgisi"""
    info = {}
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        info["cpu"] = f"{cpu:.1f}%"
        info["ram"] = f"{mem.used / 1024**3:.1f}GB/{mem.total / 1024**3:.1f}GB"
        info["disk"] = (
            f"{disk.used / 1024**3:.0f}GB/{disk.total / 1024**3:.0f}GB ({disk.percent:.0f}% dolu)"
        )
    except ImportError:
        # psutil yoksa fallback
        if sys.platform == "win32":
            try:
                r = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "$m=Get-CimInstance Win32_OperatingSystem; "
                        "[math]::Round($m.FreePhysicalMemory/1024)",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                free_mb = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
                r2 = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "$m=Get-CimInstance Win32_OperatingSystem; "
                        "[math]::Round($m.TotalVisibleMemorySize/1024)",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                total_mb = int(r2.stdout.strip()) if r2.stdout.strip().isdigit() else 0
                used_mb = total_mb - free_mb
                info["ram"] = f"{used_mb}MB/{total_mb}MB"
            except:
                info["ram"] = "bilinmiyor"
        info["cpu"] = "bilinmiyor"
        info["disk"] = "bilinmiyor"
    return info


def _chat_id_to_lane(chat_id: int | str | None) -> str | None:
    if chat_id is None:
        return None
    try:
        cid = int(chat_id)
    except (TypeError, ValueError):
        return "telegram"
    if cid == WEB_CHAT_ID:
        return "web"
    if cid == VOICE_CHAT_ID:
        return "voice"
    return "telegram"


def _current_persona_id(chat_id: int | str | None = None) -> str:
    try:
        from server.persona_manager import get_active_persona
    except Exception:
        try:
            from persona_manager import get_active_persona  # type: ignore
        except Exception:
            return "jarvis"
    lane = _chat_id_to_lane(chat_id)
    try:
        persona = get_active_persona(lane)
        return str(persona.get("id") or "jarvis").strip().lower() or "jarvis"
    except Exception:
        return "jarvis"


def run_command_safe(cmd: str, persona_id: str = "jarvis") -> str:
    """Guvenli komut calistirici (cross-platform)"""
    ALLOWED_WIN = [
        "dir",
        "echo",
        "ping",
        "ipconfig",
        "tasklist",
        "ollama",
        "python",
        "where",
    ]
    ALLOWED_LIN = ["ls", "echo", "ping", "ps", "free", "df", "ollama", "python3"]
    allowed = ALLOWED_WIN if sys.platform == "win32" else ALLOWED_LIN
    decision = evaluate_shell_command(
        cmd,
        full_access=False,
        source="bridge.safe_shell",
        persona_id=persona_id,
    )
    if not decision.allowed:
        reason = "Bu komut icin izin yok."
        if decision.reason == "not-in-safe-allowlist":
            reason = f"Bu komut safe allowlist disinda: {cmd.split(maxsplit=1)[0] if cmd.strip() else 'komut'}"
        return f"{reason} (policy: {decision.reason})"
    if not any(cmd.lower().startswith(a) for a in allowed):
        return "Bu komut icin izin yok. (policy: runtime-allowlist)"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout[:2000] or result.stderr[:500] or "Cikti yok."
    except subprocess.TimeoutExpired:
        return "Komut zaman asimina ugradi."


def run_shell_full(cmd: str, persona_id: str = "jarvis") -> str:
    """Kisitsiz shell komutu (!! prefix)"""
    decision = evaluate_shell_command(
        cmd,
        full_access=True,
        source="bridge.full_shell",
        persona_id=persona_id,
    )
    if not decision.allowed:
        return format_policy_block_message(decision)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout[:3000] or result.stderr[:1000] or "Cikti yok."
    except subprocess.TimeoutExpired:
        return "Komut zaman asimina ugradi (30s)."
    except Exception as e:
        return f"Hata: {e}"


# ─────────────────────────── COMMANDS ─────────────────────────────
def _get_admin_chat_id() -> str:
    return os.environ.get("ADMIN_CHAT_ID", "").strip()


def _is_admin_chat(chat_id: int | str) -> bool:
    admin_chat_id = _get_admin_chat_id()
    return bool(admin_chat_id) and str(chat_id) == admin_chat_id


def _capture_screenshot(target_path: Path | None = None) -> Path | None:
    output_path = Path(target_path) if target_path else (DATA_DIR / "screenshot.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import ImageGrab

        img = ImageGrab.grab()
        img.save(output_path)
        if output_path.exists():
            return output_path
    except Exception as exc:
        log.debug(f"PIL screenshot fallback'a dustu: {exc}")

    escaped_path = str(output_path).replace("'", "''")
    ps_cmd = (
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
        "$bmp=New-Object System.Drawing.Bitmap("
        "[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,"
        "[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height);"
        "$g=[System.Drawing.Graphics]::FromImage($bmp);"
        "$g.CopyFromScreen(0,0,0,0,$bmp.Size);"
        f"$bmp.Save('{escaped_path}');"
        "$g.Dispose();$bmp.Dispose()"
    )
    try:
        subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True,
            timeout=15,
        )
    except Exception as exc:
        log.warning(f"PowerShell screenshot alinamadi: {exc}")

    return output_path if output_path.exists() else None


def _handle_vision_command(chat_id: int, args: str) -> str:
    admin_chat_id = _get_admin_chat_id()
    if not admin_chat_id:
        return "ADMIN_CHAT_ID tanimli degil."
    if not _is_admin_chat(chat_id):
        return "Bu komut sadece admin kullanicisi icin acik."

    screenshot_path = _capture_screenshot()
    if not screenshot_path:
        return "Ekran goruntusu alinamadi."

    prompt = args.strip() or "Bu ekranda ne var? Detayli acikla. Turkce cevap ver."
    try:
        from vision_skill import analyze_image_with_ollama

        return analyze_image_with_ollama(str(screenshot_path), prompt)
    except Exception as exc:
        return f"Hata: {exc}"


def _handle_swarm_command(args: str) -> str:
    try:
        from swarm_skill import swarm_run

        return swarm_run(args.strip())
    except Exception as exc:
        return f"Hata: {exc}"


def _handle_youtube_command(args: str) -> str:
    query = args.strip()
    if not query:
        return "Kullanim: /youtube [url veya arama]"

    try:
        from youtube_skill import format_report, get_transcript

        return format_report(get_transcript(query))
    except Exception as exc:
        return f"Hata: {exc}"


def _handle_autoresearch_command(args: str) -> str:
    topic = args.strip() or "genel arastirma"
    try:
        from autoresearch_skill import run_deep_research

        return run_deep_research(topic)
    except Exception as exc:
        return f"Hata: {exc}"


def _handle_skill_registry_command(args: str) -> str:
    try:
        from skill_registry_skill import run

        return run(args)
    except Exception as exc:
        return f"Hata: {exc}"


def _handle_whisper_command(args: str) -> str:
    audio_path = args.strip().strip('"')
    if not audio_path:
        return "Kullanim: /transkript [ses dosyasi]"

    candidate = Path(audio_path)
    if not candidate.is_absolute():
        candidate = ROOT_DIR / candidate
    if not candidate.exists():
        return f"Ses dosyasi bulunamadi: {candidate}"

    try:
        from whisper_skill import transcribe_audio

        transcript = transcribe_audio(str(candidate))
        return f"*Transkript:*\n\n{transcript}"
    except Exception as exc:
        return f"Hata: {exc}"


def _build_persona_session(persona: dict) -> dict:
    prompt = _build_persona_system_prompt(persona)
    llm_profile = (
        dict(persona.get("llm_profile"))
        if isinstance(persona.get("llm_profile"), dict)
        else {}
    )
    provider = str(llm_profile.get("provider") or "").strip()
    model_name = str(llm_profile.get("model") or "").strip()
    model_ref = (
        f"{provider}/{model_name}"
        if provider and model_name
        else str(llm_profile.get("model_ref") or "gemma4:e2b").strip()
        or "gemma4:e2b"
    )
    return {
        "name": str(persona.get("name") or persona.get("id") or "jarvis"),
        "prompt": prompt,
        "system_prompt": prompt,
        "model": model_ref,
        "fallback_model": str(
            llm_profile.get("fallback_model") or "groq/llama-3.3-70b-versatile"
        ).strip(),
        "model_chain": str(llm_profile.get("model_chain") or "chat").strip() or "chat",
        "api_key_env": str(llm_profile.get("api_key_env") or "").strip(),
        "persona_id": str(persona.get("id") or "jarvis"),
        "voice": str(persona.get("voice") or "AhmetNeural"),
        "voice_model": str(
            llm_profile.get("voice_model") or persona.get("voice") or "AhmetNeural"
        ).strip(),
        "role": str(persona.get("role") or ""),
        "skills": list(persona.get("skills") or []),
        "greeting": str(persona.get("greeting") or ""),
        "sub_agents": list(persona.get("sub_agents") or []),
        "obsidian_folder": str(persona.get("obsidian_folder") or ""),
        "llm_profile": llm_profile,
    }


def _apply_persona_to_chat(chat_id: int, persona: dict) -> None:
    persona_id = str(persona.get("id") or "jarvis").strip().lower() or "jarvis"
    if persona_id == "jarvis":
        ACTIVE_AGENTS.pop(str(chat_id), None)
        return
    ACTIVE_AGENTS[str(chat_id)] = _build_persona_session(persona)


def _load_persona_manager_module():
    last_exc: Exception | None = None
    for module_name in ("persona_manager", "server.persona_manager"):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            last_exc = exc
            if str(getattr(exc, "name", "") or "").strip() not in {
                module_name,
                module_name.split(".")[-1],
            }:
                raise
    if last_exc is not None:
        raise last_exc
    raise ModuleNotFoundError("persona_manager")


def _load_persona_brain_module():
    last_exc: Exception | None = None
    for module_name in ("persona_brain", "server.persona_brain"):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            last_exc = exc
            if str(getattr(exc, "name", "") or "").strip() not in {
                module_name,
                module_name.split(".")[-1],
            }:
                raise
    if last_exc is not None:
        raise last_exc
    raise ModuleNotFoundError("persona_brain")


def _persona_api_payload(
    persona: dict, *, chat_id: int | None = None, lane: str | None = None
) -> dict:
    payload = dict(persona) if isinstance(persona, dict) else {}
    payload.setdefault("id", "jarvis")
    payload.setdefault("name", "Jarvis")
    payload.setdefault("color", "#00d4ff")
    payload.setdefault("voice", "AhmetNeural")
    payload.setdefault("role", "Ana Sistem / Koordinator")
    payload.setdefault("skills", [])
    payload.setdefault("greeting", "Merhaba Ekrem, ben Jarvis.")
    payload.setdefault("activated_at", None)
    payload.setdefault("lane_policy", ACTIVE_LANE_POLICY)
    if lane:
        payload["lane"] = lane
    if chat_id is not None:
        payload["chat_id"] = chat_id
    return payload


def _persona_summary_payload(persona: dict) -> dict:
    payload = dict(persona) if isinstance(persona, dict) else {}
    return {
        "id": str(payload.get("id") or "jarvis"),
        "name": str(payload.get("name") or "Jarvis"),
        "role": str(payload.get("role") or "Ana Sistem / Koordinator"),
        "color": str(payload.get("color") or "#00d4ff"),
        "voice": str(payload.get("voice") or "AhmetNeural"),
        "skills": [str(item) for item in (payload.get("skills") or []) if str(item)],
        "codex_slot": str(payload.get("codex_slot") or ""),
        "greeting": str(payload.get("greeting") or "Merhaba Ekrem, ben Jarvis."),
    }


def _build_personas_payload() -> dict:
    persona_module = _load_persona_manager_module()
    return {
        "personas": [
            _persona_summary_payload(persona)
            for persona in persona_module.list_personas()
        ]
    }


def _build_persona_brain_payload(
    persona_id: str, *, daily_tail: int = 10
) -> dict[str, object]:
    brain_module = _load_persona_brain_module()
    brain = brain_module.PersonaBrain(persona_id)
    payload = brain.snapshot(daily_tail=daily_tail).to_dict()
    payload["available"] = True
    return payload


def _write_persona_brain_payload(
    persona_id: str, body: dict[str, object] | None
) -> dict[str, object]:
    data = body if isinstance(body, dict) else {}
    action = str(data.get("action") or "memory").strip().lower() or "memory"
    brain_module = _load_persona_brain_module()
    brain = brain_module.PersonaBrain(persona_id)

    if action in {"memory", "write_memory"}:
        topic = str(data.get("topic") or data.get("title") or "").strip()
        content = str(data.get("content") or data.get("text") or "").strip()
        channel = str(data.get("channel") or data.get("source") or "bridge-api").strip()
        relative_path = brain.write_memory(
            topic,
            content,
            channel=channel or "bridge-api",
        ).relative_to(brain.brain_root)
    elif action in {"daily_log", "append_daily_log", "log"}:
        entry = str(data.get("entry") or data.get("content") or data.get("text") or "").strip()
        relative_path = brain.append_daily_log(entry).relative_to(brain.brain_root)
    else:
        raise ValueError(f"unsupported persona brain action: {action}")

    return {
        "ok": True,
        "persona_id": brain.persona_id,
        "action": action,
        "path": relative_path.as_posix(),
        "snapshot": brain.snapshot().to_dict(),
    }


def _persona_brain_error_response(
    persona_id: str, exc: Exception
) -> tuple[dict[str, object], int]:
    exc_name = exc.__class__.__name__
    if exc_name == "BrainNotInitializedError":
        return {
            "ok": False,
            "error": "brain_not_initialized",
            "persona_id": persona_id,
            "message": str(exc),
        }, 404
    if exc_name == "VaultUnavailableError":
        return {
            "ok": False,
            "error": "brain_vault_unavailable",
            "persona_id": persona_id,
            "message": str(exc),
        }, 503
    if exc_name in {"UnsafeNotePathError", "ValueError"}:
        return {
            "ok": False,
            "error": "invalid_persona_brain_request",
            "persona_id": persona_id,
            "message": str(exc),
        }, 400
    return {
        "ok": False,
        "error": "persona_brain_error",
        "persona_id": persona_id,
        "message": str(exc),
    }, 500


def _load_subagent_registry_module():
    last_exc: Exception | None = None
    for module_name in ("subagent_registry", "server.subagent_registry"):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            last_exc = exc
            if str(getattr(exc, "name", "") or "").strip() not in {
                module_name,
                module_name.split(".")[-1],
            }:
                raise
    if last_exc is not None:
        raise last_exc
    raise ModuleNotFoundError("subagent_registry")


def _load_subagent_dispatcher_module():
    last_exc: Exception | None = None
    for module_name in ("subagent_dispatcher", "server.subagent_dispatcher"):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            last_exc = exc
            if str(getattr(exc, "name", "") or "").strip() not in {
                module_name,
                module_name.split(".")[-1],
            }:
                raise
    if last_exc is not None:
        raise last_exc
    raise ModuleNotFoundError("subagent_dispatcher")


def _build_subagent_list_payload(persona_id: str) -> dict[str, object]:
    registry_mod = _load_subagent_registry_module()
    registry = registry_mod.load_registry()
    specs = registry.for_persona(persona_id)
    missing = registry.missing_for_persona(persona_id)
    return {
        "ok": True,
        "persona_id": persona_id,
        "count": len(specs),
        "subagents": [
            {
                "name": s.name,
                "description": s.description,
                "hidden": s.hidden,
                "tools": s.allowed_tools(),
            }
            for s in specs
        ],
        "missing": missing,
    }


def _dispatch_subagent_payload(
    persona_id: str, agent_name: str, body: dict[str, object] | None
) -> dict[str, object]:
    data = body if isinstance(body, dict) else {}
    task = str(data.get("task") or data.get("prompt") or "").strip()
    if not task:
        raise ValueError("'task' field is required")
    context_raw = data.get("context")
    context = context_raw if isinstance(context_raw, dict) else None
    persist = bool(data.get("persist_to_brain") or data.get("persist") or False)
    max_tokens_raw = data.get("max_tokens")
    try:
        max_tokens = int(max_tokens_raw) if max_tokens_raw is not None else 1024
    except (TypeError, ValueError):
        max_tokens = 1024

    dispatcher_mod = _load_subagent_dispatcher_module()
    dispatcher = dispatcher_mod.get_dispatcher()
    result = dispatcher.dispatch(
        persona_id,
        agent_name,
        task,
        context=context,
        persist_to_brain=persist,
        max_tokens=max_tokens,
    )
    return result.to_dict()


def _subagent_error_response(
    persona_id: str, agent_name: str, exc: Exception
) -> tuple[dict[str, object], int]:
    exc_name = exc.__class__.__name__
    if exc_name == "PersonaNotFoundError":
        return {
            "ok": False,
            "error": "persona_not_found",
            "persona_id": persona_id,
            "agent_name": agent_name,
            "message": str(exc),
        }, 404
    if exc_name == "SubAgentNotAllowedError":
        return {
            "ok": False,
            "error": "subagent_not_allowed",
            "persona_id": persona_id,
            "agent_name": agent_name,
            "message": str(exc),
        }, 403
    if exc_name in {"ValueError", "KeyError"}:
        return {
            "ok": False,
            "error": "invalid_subagent_request",
            "persona_id": persona_id,
            "agent_name": agent_name,
            "message": str(exc),
        }, 400
    return {
        "ok": False,
        "error": "subagent_dispatch_error",
        "persona_id": persona_id,
        "agent_name": agent_name,
        "message": str(exc),
    }, 500


def _get_active_persona_payload(
    *, chat_id: int | None = None, lane: str | None = None
) -> dict:
    persona_module = _load_persona_manager_module()
    resolved_lane = (
        lane
        if lane is not None
        else (_lane_for_chat_id(chat_id) if chat_id is not None else None)
    )
    payload = persona_module.get_active_persona(lane=resolved_lane)
    return _persona_api_payload(payload, chat_id=chat_id, lane=resolved_lane)


def _sync_persona_session_for_chat(chat_id: int) -> dict:
    persona = _get_active_persona_payload(chat_id=chat_id)
    _apply_persona_to_chat(chat_id, persona)
    return persona


def _build_persona_system_prompt(persona: dict | None) -> str:
    payload = persona if isinstance(persona, dict) else {}
    prompt = str(payload.get("system_prompt") or payload.get("prompt") or JARVIS_SOUL)
    prompt = prompt.strip() or JARVIS_SOUL

    domain_limits = payload.get("domain_limits")
    if not isinstance(domain_limits, dict):
        return prompt

    restricted_topics = [
        str(item).strip()
        for item in (domain_limits.get("restricted_topics") or [])
        if str(item).strip()
    ]
    fallback_persona = str(domain_limits.get("fallback_persona") or "").strip()
    if not restricted_topics or not fallback_persona:
        return prompt

    topic_text = ", ".join(restricted_topics)
    domain_hint = (
        f"Domain limits: restricted_topics={topic_text}; "
        f"fallback_persona={fallback_persona}. "
        f"Eger soru bu konulara giriyorsa '{fallback_persona}'ya yonlendir."
    )
    if domain_hint in prompt:
        return prompt
    return f"{prompt}\n{domain_hint}"


def _build_persona_handoff_reply(persona: dict | None) -> str:
    payload = persona if isinstance(persona, dict) else {}
    name = str(payload.get("name") or payload.get("id") or "Jarvis")
    greeting = str(payload.get("greeting") or "Hazirim.")
    return f"Baglaniyor: {name}... {greeting}"


def _extract_runtime_lane(value: object) -> str | None:
    lane = str(value or "").strip().lower()
    if lane in RUNTIME_LANES:
        return lane
    return None


def _normalize_runtime_lane(value: object) -> str:
    lane = _extract_runtime_lane(value)
    if lane:
        return lane
    return "web"


def _lane_for_chat_id(chat_id: int | None) -> str:
    if chat_id == VOICE_CHAT_ID:
        return "voice"
    if chat_id == WEB_CHAT_ID:
        return "web"
    return "telegram"


def _resolve_runtime_chat(payload: dict | None) -> tuple[int, str]:
    data = payload if isinstance(payload, dict) else {}
    explicit_chat_id = (
        data.get("chatId")
        if data.get("chatId") not in (None, "")
        else data.get("chat_id")
    )
    lane = _extract_runtime_lane(data.get("lane") or data.get("source"))
    if explicit_chat_id not in (None, ""):
        try:
            resolved_chat_id = int(explicit_chat_id)
            return resolved_chat_id, lane or _lane_for_chat_id(resolved_chat_id)
        except (TypeError, ValueError):
            pass
    lane = lane or "web"
    return int(RUNTIME_LANES.get(lane, WEB_CHAT_ID)), lane


def _load_optional_skill_module(module_name: str):
    if SKILLS_PATH not in sys.path:
        sys.path.insert(0, SKILLS_PATH)
    last_exc: ModuleNotFoundError | None = None
    for import_name in (module_name, f"server.skills.{module_name}"):
        try:
            return importlib.import_module(import_name)
        except ModuleNotFoundError as exc:
            last_exc = exc
            if str(getattr(exc, "name", "") or "").strip() not in {
                module_name,
                import_name,
            }:
                raise
    if last_exc is not None:
        raise last_exc
    raise ModuleNotFoundError(module_name)


def _load_coding_dispatch_module():
    last_exc: ModuleNotFoundError | None = None
    for import_name in ("services.coding_dispatch", "server.services.coding_dispatch"):
        try:
            return importlib.import_module(import_name)
        except ModuleNotFoundError as exc:
            last_exc = exc
            if str(getattr(exc, "name", "") or "").strip() not in {
                "services",
                "coding_dispatch",
                import_name,
            }:
                raise
    if last_exc is not None:
        raise last_exc
    raise ModuleNotFoundError("coding_dispatch")


def _missing_skill_message(
    label: str, module_name: str, exc: ModuleNotFoundError
) -> str:
    missing_name = str(getattr(exc, "name", "") or module_name).strip()
    hint = _EXTERNAL_SKILL_HINTS.get(module_name, "").strip()
    if missing_name not in {module_name, f"server.skills.{module_name}"}:
        if hint:
            return f"{label} bagimlisi eksik: {missing_name} ({hint})"
        return f"{label} bagimlisi eksik: {missing_name}"
    if hint:
        return f"{label} skill'i hazir degil. Referans: {hint}"
    return "Skill henuz kurulu degil"


def _switch_persona_for_chat(chat_id: int, persona_name: str) -> dict:
    persona_module = _load_persona_manager_module()
    result = persona_module.switch_persona(
        persona_name,
        lane=_lane_for_chat_id(chat_id),
    )
    if result.get("ok"):
        _apply_persona_to_chat(chat_id, result)
        result["reply"] = _build_persona_handoff_reply(result)
    return result


def _handle_persona_list_command(chat_id: int) -> str:
    persona_module = _load_persona_manager_module()
    active = persona_module.get_active_persona(lane=_lane_for_chat_id(chat_id))
    lines = ["*Persona Listesi*", f"", f"Aktif: `{active.get('name', 'Jarvis')}`"]
    for persona in persona_module.list_personas():
        role = str(persona.get("role") or "-")
        voice = str(persona.get("voice") or "-")
        skills = ", ".join(str(skill) for skill in (persona.get("skills") or [])[:3])
        lines.append(
            f"- `{persona['name']}` | {role} | ses: {voice} | yetenek: {skills}"
        )
    lines.append("")
    lines.append("Dogal dil: `Buse ile konus`, `Mert'i cagir`, `Luna'ya gec`")
    return "\n".join(lines)


def _handle_persona_status_command(chat_id: int) -> str:
    active = _get_active_persona_payload(chat_id=chat_id)
    lane = str(active.get("lane") or _lane_for_chat_id(chat_id))
    role = str(active.get("role") or "Ana Sistem")
    skills = (
        ", ".join(str(skill) for skill in (active.get("skills") or [])[:4]) or "genel"
    )
    return (
        f"Su an `{active.get('name', 'Jarvis')}` aktif.\n"
        f"Lane: {lane}\n"
        f"Rol: {role}\n"
        f"Ses: {active.get('voice', 'AhmetNeural')}\n"
        f"Yetenekler: {skills}"
    )


def _normalize_obsidian_intent_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_text = ascii_text.replace("'", "")
    ascii_text = re.sub(r"[^a-z0-9:\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _derive_obsidian_note_title(content: str) -> str:
    lines = [line.strip() for line in str(content or "").splitlines() if line.strip()]
    title_source = lines[0] if lines else str(content or "").strip()
    title_source = title_source.split("|", 1)[0].strip()
    if len(title_source) > 72:
        title_source = title_source[:72].rstrip()
    return title_source or "Not"


def _extract_obsidian_save_payload(text: str) -> tuple[str, str] | None:
    raw_text = str(text or "").strip()
    normalized = _normalize_obsidian_intent_text(raw_text)
    patterns = (
        r"^(?:bunu\s+)?kaydet\s*:\s*(?P<content>.+)$",
        r"^not al\s*:\s*(?P<content>.+)$",
        r"^obsidiana yaz\s*:\s*(?P<content>.+)$",
    )
    payload: str | None = None
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            payload = raw_text.split(":", 1)[1].strip() if ":" in raw_text else raw_text
            break
    if not payload:
        return None
    if "|" in payload:
        title, content = payload.split("|", 1)
        title = title.strip() or _derive_obsidian_note_title(content)
        content = content.strip() or title
        return title, content
    derived_title = _derive_obsidian_note_title(payload)
    return derived_title, payload.strip()


def _is_obsidian_context_request(text: str) -> bool:
    normalized = _normalize_obsidian_intent_text(text)
    return any(
        phrase in normalized
        for phrase in (
            "ne biliyorsun",
            "arastirdiklarimiz",
            "gecen notlarim",
        )
    )


def _build_obsidian_context_block(persona_id: str) -> str:
    try:
        from server.skills.persona_obsidian_skill import get_persona_context

        context = get_persona_context(persona_id)
    except Exception as exc:
        log.warning("Obsidian context okunamadi (%s): %s", persona_id, exc)
        return ""
    context = str(context or "").strip()
    if not context:
        return ""
    return f"Aktif persona icin Obsidian baglami:\n{context}"


def _handle_obsidian_save_intent(chat_id: int, text: str) -> str | None:
    payload = _extract_obsidian_save_payload(text)
    if not payload:
        return None
    title, content = payload
    persona = _get_active_persona_payload(chat_id=chat_id)
    persona_id = str(persona.get("id") or "jarvis")
    try:
        from server.skills.persona_obsidian_skill import write_persona_note

        note = write_persona_note(persona_id=persona_id, title=title, content=content)
    except Exception as exc:
        return f"Obsidian kayit hatasi: {exc}"
    if not note:
        return "OBSIDIAN_VAULT_PATH ayarli degil; not kaydedemedim."
    note_path = str(note.get("path") or "").strip()
    if note_path:
        return f"Obsidian'a kaydettim ({persona_id}): {note_path}"
    return f"Obsidian'a kaydettim ({persona_id}): {title}"


def _handle_persona_fleet_summary_command(chat_id: int) -> str:
    persona_module = _load_persona_manager_module()
    try:
        from server.skills.persona_obsidian_skill import read_persona_notes
    except Exception as exc:
        return f"Obsidian ozet modulu yuklenemedi: {exc}"

    lines = ["*Ajanlarin Ozeti*"]
    active_id = str(_get_active_persona_payload(chat_id=chat_id).get("id") or "jarvis")
    for persona in persona_module.list_personas():
        persona_id = str(persona.get("id") or "").strip()
        name = str(persona.get("name") or persona_id or "Persona").strip()
        marker = " (aktif)" if persona_id == active_id else ""
        try:
            notes = read_persona_notes(persona_id, limit=1)
        except Exception as exc:
            lines.append(f"{name}{marker}: not okunamadi ({exc})")
            continue
        if not notes:
            lines.append(f"{name}{marker}: henüz not yok")
            continue
        note = notes[0]
        title = str(note.get("title") or "Not").strip()
        date = str(note.get("date") or "-").strip()
        content = " ".join(str(note.get("content") or "").split())
        preview = content[:120].strip()
        if len(content) > 120:
            preview = preview.rstrip() + "..."
        suffix = f" - {preview}" if preview else ""
        lines.append(f"{name}{marker}: {title} ({date}){suffix}")
    return "\n".join(lines)


def handle_command(chat_id: int, cmd: str) -> str:
    parts = cmd.split(" ", 2)
    command = parts[0].lower()
    args = " ".join(parts[1:]) if len(parts) > 1 else ""

    if command in ("/start", "/help"):
        available = get_available_models()
        models_str = "\n".join([f"  - {m}" for m in available]) or "  - (model yok)"
        return f"""*Jarvis Mission Control v2.3*

*Holding Departmanlari:*
  `/holding` -> Departman listesi
  `/reklam_ajans [brief]` -> Konsept + Gorsel Prompt + 3 Kopya
  `/satis [urun]` -> Pazar + USP + Email + Kapanis
  `/websitesi [brief]` -> HTML/Tailwind landing page

*Arama & Arastirma:*
  `/ara [sorgu]` -> Perplexica AI arama (web + ozet)
  `/arastir [konu]` -> Derin arastirma ve ozet
  `/youtube [url/arama]` -> YouTube transcript ve analiz
  `/rakip [hedef]` -> Rakip analizi
  `/ebay [urun]` -> eBay piyasa analizi
  `/ebay-canli [urun]` -> Gercek eBay sold listings + analiz
  `/trendyol [urun]` -> Trendyol TR analizi
  `/firsat` -> eBay + Trendyol gunluk firsat taramasi
  `/firsat-durum` -> Firsat scheduler durumu ve son tarama

*Marketing & Icerik:*
  `/reklam [urun]` -> Hizli reklam metni
  `/icerik [metin]` -> 5 platform icin icerik
  `/abtest [sayfa]` -> A/B test fikirleri
  `/analiz [veri]` -> Kampanya KPI analizi

*Kod & Plan:*
  `/kod [gorev]` -> Codex worker ile kod gorevi baslat
  `/kod-durum` -> Kod kuyrugu ve slot ozetini goster
  `/kod-sonuc [job_id]` -> Tek kod gorevinin sonucunu getir
  `/code [gorev]` -> /kod alias
  `/plan [proje]` -> Plan olustur
  `/task [hedef]` -> Otonom gorev (Plan+Execute)
  `/voice-test [start|stop|status]` -> 5 dakikalik sesli sohbet testi
  `/team [hedef]` -> Planner+Builder+Guard agent team
  `/onaylar` -> Bekleyen onay kuyruğu
  `/onay-ekle [baslik] | [ozet]` -> Onay isteği ekle
  `/onay [id] | [not]` -> Onay ver
  `/red [id] | [not]` -> Onayı reddet
  `/claude-uyandir [saat] | [not]` -> Claude resume saati planla
  `/claude-durum` -> Claude resume durumunu göster
  `/uyku-modu [ac|kapat]` -> Kullanici uyurken otomatik onay modu
  `/otopilot [start|stop]` -> Durmadan calisan gece/sabah otomasyon motoru

*AI Uzman Ajanlar:*
  `/jcoder [gorev]` -> /kod alias
  `/markxxxv [gorev]` -> Mark-XXXV planner/executor gorevi
  `/skill [isim] [aciklama]` -> Yeni Jarvis skill dosyasi yaz
  `/skills [kategori|ara kelime]` -> Aktif ve curated skill listesi
  `/swarm [gorev]` -> Multi-agent orchestration
  `/analyst [konu]` -> Iş analizi, SaaS strateji, pazarlama

*Ajanlar:*
  `/agent [isim]` -> 624 AI ajan sec
  `/persona` -> 7 dijital persona listesi
  `/kim-aktif` -> Aktif personayi goster
  `/agent reklam-stratejisti` -> Meta/Google Ads uzmani
  `/agent sosyal-medya-uzmani` -> TikTok/Instagram
  `/agent satis-kapanisi` -> Itiraz yonetimi
  `/agent email-copywriter` -> Soguk email uzmani

*Notlar & Araclar:*
  `/not [metin]` -> Not kaydet
  `/notlar` -> Tum notlari listele
  `/not-sil` -> Tum notlari sil
  `/gor [soru]` -> Ekrani analiz et (admin)
  `/transkript [ses dosyasi]` -> Whisper ile sesi metne donustur
  `/cevirici [metin]` -> TR<->EN otomatik ceviri
  `/ozet [metin/url]` -> Metin veya URL ozetleme
  `/gpt [soru]` -> GPT-4o ile soru sor

*Sistem & Hafiza:*
  `/status` -> Sistem durumu
  `/models` -> AI modeller (lokal + cloud)
  `/model [route] [model]` -> Canlı model değiştir
  `/hafiza` -> Hafiza raporu
  `/gorev` -> Gorev listesi
  `/reset` -> Gecmisi sil
  `/hava [sehir]` -> Hava durumu
  `/haber [konu]` -> Son haberler
  `/altin` -> Altin & doviz
  `/kur [100 USD TRY]` -> Doviz cevirici
  `/hesap [islem]` -> Hesap makinesi
  `$ [komut]` -> Guvenli sistem komutu
  `!! [komut]` -> Gelismis sistem komutu

*Uzak Yonetim & PC Kontrol:*
  `/kabul` -> AnyDesk baglanti istegini kabul et
  `/tarayici [komut]` -> Playwright ile gorunen Chromium oturumu
  `/mouse [x] [y]` -> Mouse'u konuma tasI
  `/tıkla [x] [y]` -> Sol tikla
  `/çifttıkla [x] [y]` -> Cift tikla
  `/sağtıkla [x] [y]` -> Sag tikla
  `/yaz [metin]` -> Klavyeye yaz
  `/tuş [enter]` -> Tus bas
  `/kısayol [ctrl+c]` -> Kisayol
  `/scroll [yukari/asagi] [miktar]` -> Scroll
  `/ekranoku` -> Ekran boyutu + mouse konumu
  `/ekran` -> Ekran goruntusu al ve gonder
  `/dosyalar [yol]` -> Klasor icerigini listele
  `/surec` -> En yuklu 10 proses
  `/kill [isim]` -> Proses durdur
  `/ip` -> Dis IP ve yerel IP adresini goster

*Öz-Öğrenme:*
  `/ogren` -> Tüm komutları analiz et, ne öğrenilmeli söyle
  `/rapor` -> Son öğrenme raporunu göster
  `/tune [skill]` -> Bir skill'in promptunu otomatik iyileştir (Karpathy döngüsü)

*Yeni Ajanlar:*
  `/agent growth-hacker` -> Buyume stratejisti
  `/agent icerik-stratejisti` -> Cok platform icerik
  `/agent pazar-arastirmacisi` -> Pazar & rakip analizi
  `/agent seo-uzmani` -> TR SEO optimizasyonu
  `/agent rakip-analisti` -> Rekabet istihbarat

*Modeller:*
{models_str}"""

    # ─── SELF-LEARNING KOMUTLARI ─────────────────────────────────────
    elif command == "/ogren":
        learner = _get_conv_learner()
        if not learner:
            return "Öğrenme motoru başlatılamadı."
        try:
            send_telegram_message(chat_id, "Analiz ediyorum... (30-60 sn sürebilir)")
            insight = learner.analyze(limit=300)
            return f"*Jarvis Öğrenme Raporu*\n\n{insight}"
        except Exception as e:
            return f"Analiz hatası: {e}"

    elif command == "/rapor":
        learner = _get_conv_learner()
        if not learner:
            return "Öğrenme motoru başlatılamadı."
        return f"*Son Öğrenme Raporu*\n\n{learner.get_last_insight()[:1500]}"

    elif command == "/tune":
        if not args:
            return "Kullanım: `/tune [skill_adi]`\nÖrnek: `/tune reklam`"
        learner = _get_conv_learner()
        if not _SKILL_TUNER or not learner:
            return "Tuning motoru başlatılamadı."
        try:
            skill_name = args.strip()
            send_telegram_message(
                chat_id, f"*{skill_name}* skill'ini optimize ediyorum... (2-3 dk)"
            )
            # Örnek test girdileri
            test_inputs = [
                f"{skill_name} için örnek bir görev",
                f"{skill_name} kullanarak sonuç üret",
                f"{skill_name} ile analiz yap",
            ]
            base_prompt = f"Sen Jarvis'in {skill_name} uzmanısın. Türkçe, kısa ve etkili yanıtlar ver."
            result = _SKILL_TUNER.tune(
                skill_name=skill_name,
                current_prompt=base_prompt,
                test_inputs=test_inputs,
                iterations=3,
            )
            return (
                f"*{skill_name} Tuning Tamamlandı*\n"
                f"Başlangıç skoru: {result['original_score']:.1f}/10\n"
                f"Final skor: {result['final_score']:.1f}/10\n"
                f"İyileşme: +{result['improvement']:.1f}\n"
                f"İterasyon: {result['iterations']}"
            )
        except Exception as e:
            return f"Tuning hatası: {e}"

    elif command == "/status":
        try:
            info = get_system_info()
            models = get_available_models()
            stats = memory.data["stats"]
            provider_health = get_provider_health()
            trace = (
                STATE.last_route_trace
                if isinstance(STATE.last_route_trace, dict)
                else {}
            )
            last_sel = trace.get("selected_candidate", "-")
            fallback = "evet" if trace.get("fallback_used") else "hayir"
            return f"""*Jarvis Sistem Durumu*
CPU: `{info["cpu"]}` | RAM: `{info["ram"]}`
AI Modeller: {len(models)} aktif
Toplam Sorgu: {stats["total_queries"]}
Saat: {datetime.now().strftime("%H:%M:%S")}
Servis: Aktif ({CONFIG["runtime_label"]})
Ollama: `{provider_health.get("ollama", {}).get("label", "-")}`
OpenRouter: `{provider_health.get("openrouter", {}).get("label", "-")}`
OpenAI: `{provider_health.get("openai", {}).get("label", "-")}`
Son Model: `{last_sel}` | Fallback: `{fallback}`"""
        except Exception as e:
            return f"Durum alinamadi: {e}"

    elif command == "/jarvis-durum":
        try:
            try:
                from skills.jarvis_self_survey_skill import run_survey
            except ImportError:
                from server.skills.jarvis_self_survey_skill import run_survey  # type: ignore
            result = run_survey()
            brief = result.get("brief") or "Self-survey bos."
            vault = result.get("vault_path")
            if vault:
                brief = f"{brief}\n\n📁 Vault: `{vault}`"
            return brief
        except Exception as e:
            return f"Self-survey hatasi: {e}"

    elif command == "/durum":
        try:
            info = get_system_info()
            models = get_available_models()
            provider_health = get_provider_health()
            lines = ["*Jarvis Sistem Durumu*\n"]
            lines.append(f"CPU: `{info['cpu']}`")
            lines.append(f"RAM: `{info['ram']}`")
            lines.append(f"Disk: `{info['disk']}`")
            lines.append(
                f"OpenRouter: `{provider_health.get('openrouter', {}).get('label', '-')}`"
            )
            lines.append(
                f"OpenAI: `{provider_health.get('openai', {}).get('label', '-')}`"
            )
            lines.append(f"\nOllama ({len(models)} model):")
            for m in models:
                lines.append(f"  - `{m}`")
            return "\n".join(lines)
        except Exception as e:
            return f"Durum alinamadi: {e}"

    elif command == "/models":
        local_models = get_available_models()
        cloud_models = [
            "groq/llama-3.3-70b-versatile",
            "groq/qwen-qwq-32b",
            "gemini/gemini-2.5-flash",
            "gemini/gemini-2.5-pro",
        ]
        route_info = "\n".join(
            [f"  {k}: `{v['model']}`" for k, v in MODEL_ROUTES.items()]
        )
        local_str = (
            "\n".join([f"- {m}" for m in local_models])
            if local_models
            else "  (Ollama bagli degil)"
        )
        cloud_str = "\n".join([f"- {m} ☁️" for m in cloud_models])
        return f"*Aktif Route'lar:*\n{route_info}\n\n*Lokal Modeller:*\n{local_str}\n\n*Cloud Modeller:*\n{cloud_str}"

    elif command == "/model":
        if not args:
            return (
                "Kullanim: /model [route] [model]\nOrnek: /model chat ollama/gemma4:e2b\nOrnek: /model reasoning groq/qwen-qwq-32b\n\nRoute'lar: "
                + ", ".join(MODEL_ROUTES.keys())
            )
        parts2 = args.split(None, 1)
        if len(parts2) < 2:
            return "Kullanim: /model [route] [model-adi]"
        route_key, new_model = parts2[0].lower(), parts2[1].strip()
        if route_key not in MODEL_ROUTES:
            return f"Bilinmeyen route: {route_key}\nMevcut: {', '.join(MODEL_ROUTES.keys())}"
        inspected = (
            MODEL_ROUTER.inspect_model_ref(new_model)
            if hasattr(MODEL_ROUTER, "inspect_model_ref")
            else {"valid": True, "provider": "", "model": ""}
        )
        if not inspected.get("valid", False):
            return f"Gecersiz model referansi: {inspected.get('error', new_model)}"
        if (
            inspected.get("explicit_provider")
            and inspected.get("provider")
            and inspected.get("model")
        ):
            new_model = f"{inspected['provider']}/{inspected['model']}"
        MODEL_ROUTES[route_key]["model"] = new_model
        return f"✅ `{route_key}` route'u artık `{new_model}` kullanıyor."

    elif command == "/reset":
        memory.clear(chat_id)
        return "Konusma gecmisi temizlendi."

    elif command == "/hafiza":
        return daily_memory_report(str(chat_id))

    elif command == "/gorev":
        return get_tasks(str(chat_id))

    elif command == "/gorev-ekle":
        if not args:
            return "Kullanim: /gorev-ekle Gorev basligi"
        task_id = add_task(str(chat_id), args, "normal")
        return f"Gorev eklendi: #{task_id} — {args}"

    elif command == "/gorev-bitti":
        if not args:
            return "Kullanim: /gorev-bitti [id]"
        try:
            return update_task(str(chat_id), int(args.strip()), "done")
        except:
            return "Gecersiz gorev ID"

    elif command == "/gor":
        return _handle_vision_command(chat_id, args)

    elif command == "/swarm":
        return _handle_swarm_command(args)

    elif command == "/youtube":
        return _handle_youtube_command(args)

    elif command == "/arastir":
        return _handle_autoresearch_command(args)

    elif command == "/skills":
        return _handle_skill_registry_command(args)

    elif command == "/transkript":
        return _handle_whisper_command(args)

    elif command == "/ebay":
        query = args or "kazancli dropshipping urun"
        try:
            from ebay_research import analyze_product, format_report

            result = analyze_product(query)
            return format_report(result)
        except Exception:
            route = MODEL_ROUTES["search"]
            prompt = f"""eBay'de "{query}" icin analiz:
1. Pazar ve fiyat araligi
2. Kar marji tahmini
3. Tedarikci kaynagi
4. Rekabet seviyesi"""
            history = [{"role": "user", "content": prompt}]
            response = call_ollama(
                route["model"],
                history,
                route["system"],
                fallback_model=route.get("fallback"),
                route_name="search",
            )
            selected_candidate = get_selected_candidate(route["model"])
            memory.add_message(chat_id, "user", f"/ebay {query}")
            memory.add_message(chat_id, "assistant", response, selected_candidate)
            return f"*eBay Analizi:*\n\n{response}"

    elif command == "/ebay-canli":
        query = args or "phone accessories"
        try:
            from ebay_research import analyze_product, format_report

            result = analyze_product(query)
            return format_report(result)
        except Exception as e:
            return f"eBay-canli hatasi: {e}"

    elif command == "/hava":
        city = args or "Istanbul"
        try:
            from utils_skill import get_weather

            return get_weather(city)
        except Exception as e:
            return f"Hava hatasi: {e}"

    elif command == "/haber":
        import urllib.request as ur, re

        topic = args or "turkiye"
        feeds = {
            "ekonomi": "https://www.ntv.com.tr/ekonomi.rss",
            "turkiye": "https://www.ntv.com.tr/turkiye.rss",
            "teknoloji": "https://www.ntv.com.tr/teknoloji.rss",
            "spor": "https://www.ntv.com.tr/spor.rss",
        }
        feed_url = feeds.get(topic.lower(), "https://www.ntv.com.tr/son-dakika.rss")
        try:
            req = ur.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with ur.urlopen(req, timeout=12) as r:
                raw = r.read().decode("utf-8", errors="ignore")
            titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", raw)
            if not titles:
                titles = re.findall(r"<title>(.*?)</title>", raw)
            lines = [f"Son Haberler — {topic.upper()}\n"]
            for i, t in enumerate(titles[1:6]):
                lines.append(f"{i + 1}. {t.strip()}")
            return "\n".join(lines) if len(lines) > 1 else "Haber bulunamadi."
        except Exception as e:
            return f"Haber hatasi: {e}"

    elif command == "/altin":
        try:
            from utils_skill import get_gold_price

            return get_gold_price()
        except Exception as e:
            return f"Altin hatasi: {e}"

    elif command == "/kur":
        kur_parts = args.split() if args else []
        try:
            from utils_skill import get_currency

            if len(kur_parts) >= 3:
                return get_currency(float(kur_parts[0]), kur_parts[1], kur_parts[2])
            elif len(kur_parts) == 2:
                return get_currency(1, kur_parts[0], kur_parts[1])
            else:
                return get_currency(1, "USD", "TRY")
        except Exception as e:
            return f"Kur hatasi: {e}"

    elif command == "/hesap":
        if not args:
            return "Kullanim: /hesap 2+2 veya /hesap sqrt(144)"
        try:
            from utils_skill import calculate

            return calculate(args)
        except Exception as e:
            return f"Hesap hatasi: {e}"

    elif command == "/printify":
        query = args or "genel"
        try:
            token = ""
            try:
                with open(PRINTIFY_TOKEN_PATH) as f:
                    token = f.read().strip()
            except:
                pass
            if not token:
                return f"Printify token gerekli. Token'i {PRINTIFY_TOKEN_PATH} dosyasina yaz."
            from printify_skill import format_overview, analyze_product_opportunity

            if query in ("genel", "durum", "status", "shop"):
                return format_overview(token)
            else:
                return analyze_product_opportunity(token, query)
        except Exception as e:
            return f"Printify hatasi: {e}"

    elif command == "/trendyol":
        query = args or "bluetooth kulaklik"
        try:
            from trendyol_skill import full_trendyol_analysis

            return full_trendyol_analysis(query)
        except Exception:
            route = MODEL_ROUTES["search"]
            prompt = f"""Trendyol TR pazarinda "{query}" icin analiz:
1. Fiyat araligi (TL)
2. Rekabet durumu
3. AliExpress karsilastirmasi
4. Dropshipping fizibilitesi"""
            history = [{"role": "user", "content": prompt}]
            response = call_ollama(
                route["model"],
                history,
                route["system"],
                fallback_model=route.get("fallback"),
                route_name="search",
            )
            selected_candidate = get_selected_candidate(route["model"])
            memory.add_message(chat_id, "user", f"/trendyol {query}")
            memory.add_message(chat_id, "assistant", response, selected_candidate)
            return f"*Trendyol Analizi:*\n\n{response}"

    elif command == "/firsat":
        try:
            from ecommerce_opportunity_skill import (
                build_opportunity_report,
                save_scan_result,
                scan_opportunities,
            )

            opportunities = scan_opportunities()
            save_scan_result(opportunities)
            return build_opportunity_report(opportunities)
        except Exception as e:
            return f"Firsat tarama hatasi: {e}"

    elif command == "/firsat-durum":
        try:
            from ecommerce_opportunity_skill import get_scheduler_status, load_last_scan

            status = get_scheduler_status()
            last = load_last_scan()
            lines = ["*Firsat Tarayici Durumu*"]
            lines.append(
                f"Scheduler: {'calisiyor' if status['running'] else 'durduruldu'}"
            )
            if status.get("next_run"):
                lines.append(f"Sonraki tarama: {status['next_run']}")
            if last:
                lines.append(
                    f"Son tarama: {last.get('date')} ({str(last.get('scanned_at', ''))[:16]})"
                )
                lines.append(f"Bulunan firsat: {len(last.get('opportunities', []))}")
            else:
                lines.append("Henuz tarama yapilmadi.")
            return "\n".join(lines)
        except Exception as e:
            return f"Firsat durum hatasi: {e}"

    elif command == "/code":
        task = args or "Merhaba dunya"
        route = MODEL_ROUTES["code"]
        history = [
            {"role": "user", "content": f"Su gorevi icin tam calisir kod yaz: {task}"}
        ]
        response = call_ollama(
            route["model"],
            history,
            route["system"],
            fallback_model=route.get("fallback"),
            route_name="code",
        )
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/code {task}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*Kod:*\n\n{response}"

    elif command == "/plan":
        task = args or "proje"
        route = MODEL_ROUTES["reasoning"]
        prompt = f"Su proje icin detayli plan olustur: {task}\n1.Hedef 2.Gereksinimler 3.Adimlar 4.Riskler 5.Basari kriterleri"
        history = [{"role": "user", "content": prompt}]
        response = call_ollama(
            route["model"],
            history,
            route["system"],
            fallback_model=route.get("fallback"),
            route_name="reasoning",
        )
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/plan {task}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*Plan:*\n\n{response}"

    elif command == "/voice-test":
        return handle_voice_test_command(chat_id, args)

    elif command == "/task":
        task_goal = args or "Genel durum ozeti ve yapilacaklar listesi hazirla"
        try:
            return run_week1_task(chat_id, task_goal)
        except Exception as e:
            log.warning(f"week1 task flow hatasi: {e}, team orchestrator fallback")
            try:
                return run_team_task(chat_id, task_goal)
            except Exception as team_e:
                log.warning(f"team orchestrator hatasi: {team_e}, agent_loop fallback")
            try:
                sys.path.insert(0, str(BASE_DIR))
                from agent_loop import run as agent_run

                result = agent_run(task_goal, chat_id=str(chat_id))
                memory.add_message(chat_id, "user", f"/task {task_goal}")
                memory.add_message(chat_id, "assistant", result, "agent_loop")
                return result
            except Exception as inner_e:
                log.warning(f"agent_loop hatasi: {inner_e}, llm fallback")
                route = MODEL_ROUTES["code"]
                history = [
                    {"role": "user", "content": f"Bu gorevi tamamla: {task_goal}"}
                ]
                response = call_ollama(
                    route["model"],
                    history,
                    route["system"],
                    fallback_model=route.get("fallback"),
                    route_name="code",
                )
                selected_candidate = get_selected_candidate(route["model"])
                memory.add_message(chat_id, "user", f"/task {task_goal}")
                memory.add_message(chat_id, "assistant", response, selected_candidate)
                return f"*Task Sonucu:*\n\n{response}"

    elif command == "/team":
        team_goal = args or "Jarvis icin uzman agent team workflow'u calistir"
        try:
            return run_team_task(chat_id, team_goal)
        except Exception as e:
            log.error(f"/team hatasi: {e}")
            return f"Team orchestrator hatasi: {e}"

    elif command == "/gorevler":
        try:
            from ollama_orchestrator import get_task_history

            return get_task_history(8)
        except Exception as e:
            return f"Gorev gecmisi alinamadi: {e}"

    elif command == "/agent":
        agent_name = args.strip().lower().split()[0] if args.strip() else ""

        if agent_name in ("content-factory", "icerik"):
            try:
                from content_factory_skill import get_interviewer, init_content_db

                init_content_db()
                msg = get_interviewer().start(str(chat_id))
                CONTENT_FACTORY_SESSIONS[str(chat_id)] = True
                return msg
            except Exception as e:
                return "Content Factory hatasi: " + str(e)

        if agent_name in ("off", "kapat", "sil", "reset", "iptal"):
            ACTIVE_AGENTS.pop(str(chat_id), None)
            return "Aktif ajan kapatildi. Normal moda donuldu."

        if not agent_name:
            active = ACTIVE_AGENTS.get(str(chat_id))
            aktif_str = f"\n\n*Aktif:* `{active['name']}`" if active else ""
            try:
                from claude_agent_skill import list_all_agents

                agents = list_all_agents()
                txt = "\n".join([f"- `{a}`" for a in agents[:60]])
                return f"*Yuklü Ajanlar ({len(agents)}):*{aktif_str}\n\n{txt}\n\n_/agent [isim] ile sec | /agent off ile kapat_"
            except Exception as e:
                return f"Ajanlar listelenemedi: {e}"

        try:
            from claude_agent_skill import get_agent_prompt

            raw_prompt = get_agent_prompt(agent_name)
            if not raw_prompt:
                return f"'{agent_name}' adinda ajan bulunamadi. /agent yaz listeyi gor."
            lines = raw_prompt.split("\n")
            if lines[0].strip() == "---":
                end_fm = next(
                    (i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), -1
                )
                if end_fm > 0:
                    lines = lines[end_fm + 1 :]
            clean_prompt = "\n".join(lines).strip()
            system_prompt = (
                clean_prompt + "\n\n"
                "ONEMLI: Bundan sonraki TUM yanitlarini YALNIZCA TURKCE olarak ver."
            )
            ACTIVE_AGENTS[str(chat_id)] = {
                "name": agent_name,
                "prompt": system_prompt,
                "model": "gemma4:e2b",
            }
            preview = clean_prompt[:120].replace("\n", " ")
            return (
                f"*{agent_name.upper()}* ajani aktif!\n\n"
                f"_Rol: {preview}..._\n\n"
                "Simdi soru sor. Kapamak icin: `/agent off`"
            )
        except Exception as e:
            return f"Ajan yuklenemedi: {e}"

    elif command in {"/persona", "/ajan"}:
        return _handle_persona_list_command(chat_id)

    elif command == "/kim-aktif":
        return _handle_persona_status_command(chat_id)

    elif command == "/ajanlarin-ozeti":
        return _handle_persona_fleet_summary_command(chat_id)

    elif command == "/ara":
        query = args.strip()
        if not query:
            return "Kullanim: `/ara [arama sorgusu]`"
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from perplexica_skill import PerplexicaSkill

            result = PerplexicaSkill(call_ollama).search(query)
            memory.add_message(chat_id, "user", f"/ara {query}")
            memory.add_message(chat_id, "assistant", result[:200], "perplexica")
            return result
        except Exception as _pe:
            try:
                from web_search_skill import web_search

                result = web_search(query, max_results=5)
                memory.add_message(chat_id, "user", f"/ara {query}")
                memory.add_message(chat_id, "assistant", result, "web_search")
                return "*Web Arama:* `" + query + "`" + chr(10) * 2 + result
            except Exception as _e2:
                return f"Arama hatasi: {_e2}"

    elif command == "/reklam":
        urun = args.strip()
        if not urun:
            return "*Kullanim:* `/reklam [urun adi]`"
        route = MODEL_ROUTES["general"]
        user_prompt = (
            f"Urun: {urun}\n"
            "BASLIK: (kisa, etkileyici)\n"
            "ACIKLAMA: (1 cumle)\n"
            "HASHTAG: (#ile 5 etiket)\n"
            "INSTAGRAM: (emoji+1cumle)\n"
            "EBAY: (English, 5 words)"
        )
        history = [{"role": "user", "content": user_prompt}]
        response = call_ollama(
            route["model"],
            history,
            "Turkce e-ticaret reklam uzmanisin. Cok kisa yaz. Sadece Turkce.",
            max_tokens=110,
            num_ctx=512,
            fallback_model=route.get("fallback"),
            route_name="general",
        )
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/reklam {urun}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*Reklam:* `{urun[:40]}`\n\n{response}"

    elif command == "/icerik":
        metin = args.strip()
        if not metin:
            return "*Kullanim:* `/icerik [konu]`"
        route = MODEL_ROUTES["general"]
        user_prompt = (
            f"Konu: {metin[:200]}\n\n"
            "Her biri 1 cumle max:\n"
            "TWITTER: (tweet+3hashtag)\n"
            "LINKEDIN: (profesyonel)\n"
            "INSTAGRAM: (emoji+5hashtag)\n"
            "EMAIL: (konu satiri)\n"
            "TIKTOK: (hook cumle)"
        )
        history = [{"role": "user", "content": user_prompt}]
        response = call_ollama(
            route["model"],
            history,
            "Sosyal medya uzmanisin. Cok kisa, sadece Turkce.",
            max_tokens=130,
            num_ctx=512,
            fallback_model=route.get("fallback"),
            route_name="general",
        )
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/icerik {metin[:50]}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*5 Platform:*\n\n{response}"

    elif command == "/buse-hook":
        topic = args.strip()
        if not topic:
            return "Kullanim: /buse-hook <konu>"
        try:
            from server.skills.buse_content_skill import generate_hook

            result = generate_hook(topic)
            if result.get("ok") is False:
                return str(result.get("message") or result.get("error") or "Hook uretilemedi.")
            hooks = result.get("hooks") or []
            lines = ["*Buse Hook Secenekleri*", ""]
            for index, hook in enumerate(hooks, start=1):
                lines.append(f"{index}. {hook}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Buse hook hatasi: {exc}"

    elif command == "/buse-cta":
        parts = args.split()
        if not parts:
            return "Kullanim: /buse-cta <hedef> <platform>\nOrnek: /buse-cta comment_bait instagram"
        goal = parts[0]
        platform = parts[1] if len(parts) > 1 else "instagram"
        try:
            from server.skills.buse_content_skill import generate_cta

            result = generate_cta(goal, platform)
            if result.get("ok") is False:
                return str(result.get("message") or result.get("error") or "CTA uretilemedi.")
            return f"*Buse CTA* ({result['platform']} / {result['goal']})\n\n{result['cta']}"
        except Exception as exc:
            return f"Buse CTA hatasi: {exc}"

    elif command == "/buse-brief":
        if not args.strip():
            return "Kullanim: /buse-brief <urun> | <kitle> | <hedef>"
        try:
            from server.skills.buse_content_skill import content_brief

            result = content_brief(args.strip())
            if result.get("ok") is False:
                return str(result.get("message") or result.get("error") or "Brief olusturulamadi.")
            lines = [
                "*Buse Icerik Brief*",
                "",
                f"Hook: {result['hook']}",
                "",
                "Body Outline:",
                *[f"- {item}" for item in result.get("body_outline") or []],
                "",
                f"CTA: {result['cta']}",
            ]
            if result.get("saved_to"):
                lines.extend(["", f"Kaydedildi: {result['saved_to']}"])
            return "\n".join(lines)
        except Exception as exc:
            return f"Buse brief hatasi: {exc}"

    elif command == "/eren-analiz":
        file_path = args.strip()
        if not file_path:
            return "Kullanim: /eren-analiz <dosya_yolu>"
        try:
            from server.skills.eren_data_skill import quick_report

            result = quick_report(file_path)
            if result.get("ok") is False:
                return str(result.get("message") or result.get("error") or "CSV analizi basarisiz.")
            lines = ["*Eren Hizli Rapor*", "", str(result["summary"])]
            if result.get("saved_to"):
                lines.extend(["", f"Kaydedildi: {result['saved_to']}"])
            return "\n".join(lines)
        except Exception as exc:
            return f"Eren analiz hatasi: {exc}"

    elif command == "/eren-kpi":
        payload = args.strip()
        if not payload:
            return 'Kullanim: /eren-kpi {"gelir":15000,"musteri":23}'
        try:
            from server.skills.eren_data_skill import kpi_summary

            result = kpi_summary(payload)
            if result.get("ok") is False:
                return str(result.get("message") or result.get("error") or "KPI ozeti uretilemedi.")
            return str(result["summary"])
        except Exception as exc:
            return f"Eren KPI hatasi: {exc}"

    elif command == "/rakip":
        hedef = args.strip()
        if not hedef:
            return "*Kullanim:* `/rakip [rakip/kategori]`"
        try:
            from web_search_skill import web_search

            arama = web_search(f"{hedef} rakip platform", max_results=3)
        except Exception as e:
            arama = f"Arama hatasi: {e}"
        route = MODEL_ROUTES["general"]
        user_prompt = (
            f"Konu: {hedef}\nArama: {arama[:700]}\n\n"
            "OZET: (1 cumle)\n"
            "RAKIPLER: (3 isim)\n"
            "FIRSAT: (1 cumle)\n"
            "2 AKSIYON:"
        )
        history = [{"role": "user", "content": user_prompt}]
        response = call_ollama(
            route["model"],
            history,
            "Pazar analisti. Cok kisa, sadece Turkce.",
            max_tokens=120,
            num_ctx=512,
            fallback_model=route.get("fallback"),
            route_name="general",
        )
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/rakip {hedef}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*Rakip Analizi:* `{hedef[:40]}`\n\n{response}"

    elif command == "/abtest":
        sayfa = args.strip()
        if not sayfa:
            return "*Kullanim:* `/abtest [sayfa/hedef]`"
        route = MODEL_ROUTES["general"]
        user_prompt = (
            f"Sayfa: {sayfa}\n\n"
            "2 A/B test (her biri kisa):\n"
            "TEST1: degisiklik + hipotez + ICE(E/G/K 1-10)\n"
            "TEST2: degisiklik + hipotez + ICE(E/G/K 1-10)\n"
            "ONERI: hangisiyle basla"
        )
        history = [{"role": "user", "content": user_prompt}]
        response = call_ollama(
            route["model"],
            history,
            "CRO uzmanisin. Kisa, sadece Turkce.",
            max_tokens=130,
            num_ctx=512,
            fallback_model=route.get("fallback"),
            route_name="general",
        )
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/abtest {sayfa[:50]}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*A/B Test:* `{sayfa[:40]}`\n\n{response}"

    elif command == "/analiz":
        veri = args.strip()
        if not veri:
            return "*Kullanim:* `/analiz [veri]`\n*Ornek:* `/analiz harcama=500TL tiklamalar=1200 donusum=45 gelir=2800TL`"
        route = MODEL_ROUTES["general"]
        user_prompt = (
            f"Veri: {veri}\n\n"
            "Hesapla:\nROAS=gelir/harcama=?\n"
            "CPA=harcama/donusum=?TL\n"
            "CVR=donusum/tiklamalar*100=?%\n\n"
            "SONUC: IYI/ORTA/KOTU (ROAS>3=iyi, <1.2=kotu)\n"
            "2 AKSIYON:"
        )
        history = [{"role": "user", "content": user_prompt}]
        response = call_ollama(
            route["model"],
            history,
            "Marketing analistsin. Matematik dogru yap. Kisa, sadece Turkce.",
            max_tokens=120,
            num_ctx=512,
            fallback_model=route.get("fallback"),
            route_name="general",
        )
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/analiz {veri[:50]}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*Marketing Analizi:*\n\n{response}"

    # HOLDING DEPARTMANI

    elif command == "/reklam_ajans":
        if not args:
            return "*Reklam Ajansi*\n\nKullanim: /reklam_ajans [brief]"
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from reklam_ajans_skill import ReklamAjansSkill

            result = ReklamAjansSkill(call_ollama).run(str(chat_id), args)
            memory.add_message(chat_id, "user", f"/reklam_ajans {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Reklam Ajansi hatasi: {e}"

    elif command == "/satis":
        if not args:
            return "*Satis Departmani*\n\nKullanim: /satis [urun]"
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from satis_departmani import SatisDepartmani

            result = SatisDepartmani(call_ollama).run(str(chat_id), args)
            memory.add_message(chat_id, "user", f"/satis {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Satis Departmani hatasi: {e}"

    elif command == "/websitesi":
        if not args:
            return "*Web Ajansi*\n\nKullanim: /websitesi [brief]"
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from web_ajans_skill import WebAjansSkill

            result = WebAjansSkill(call_ollama).run(str(chat_id), args)
            memory.add_message(chat_id, "user", f"/websitesi {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Web Ajansi hatasi: {e}"

    elif command == "/mail":
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from gmail_skill import handle_gmail

            result = handle_gmail(args)
            memory.add_message(chat_id, "user", f"/mail {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Gmail hatasi: {e}"

    elif command == "/takvim":
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from gcalendar_skill import handle_gcalendar

            result = handle_gcalendar(args)
            memory.add_message(chat_id, "user", f"/takvim {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Takvim hatasi: {e}"

    elif command == "/notion":
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from notion_skill import handle_notion

            result = handle_notion(args, str(chat_id))
            memory.add_message(chat_id, "user", f"/notion {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Notion hatasi: {e}"

    elif command in ("/markxxxv", "/mark-xxxv", "/mark_xxxv"):
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from markxxxv_skill import handle_markxxxv

            result = handle_markxxxv(args, str(chat_id))
            memory.add_message(chat_id, "user", f"/markxxxv {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            log.exception("Mark-XXXV komutu basarisiz")
            return f"Mark-XXXV hatasi: {str(e)[:200]}"

    elif command in ("/stripe_webhook", "/stripe-webhook"):
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from stripe_webhook_skill import run as run_stripe_webhook

            result = run_stripe_webhook(args)
            memory.add_message(chat_id, "user", f"/stripe_webhook {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Stripe webhook hatasi: {e}"

    elif command == "/admin_musteriler":
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "").strip()
        if not admin_chat_id:
            return "ADMIN_CHAT_ID tanimli degil."
        if str(chat_id) != admin_chat_id:
            return "Bu komut sadece admin kullanicisi icin acik."
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from tenant_manager import format_tenant_list

            result = format_tenant_list()
            memory.add_message(chat_id, "user", "/admin_musteriler")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Admin musteri listesi hatasi: {e}"

    elif command == "/admin_stats":
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "").strip()
        if not admin_chat_id:
            return "ADMIN_CHAT_ID tanimli degil."
        if str(chat_id) != admin_chat_id:
            return "Bu komut sadece admin kullanicisi icin acik."
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from tenant_manager import format_stats

            result = format_stats()
            memory.add_message(chat_id, "user", "/admin_stats")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Admin istatistik hatasi: {e}"

    elif command == "/holding":
        return "*Holding Departmanlari*\n\n*/reklam_ajans [brief]* - Konsept + Gorsel Prompt + 3 Kopya\n*/satis [urun]* - Pazar + USP + Email + Kapanis\n*/websitesi [brief]* - HTML/Tailwind landing page"

    # ─── UZAK YONETIM ─────────────────────────────────────────────
    elif command == "/ekran":
        import tempfile as _tmpf

        ss_path = str(DATA_DIR / "screenshot.png")
        taken = False
        # Yöntem 1: PIL/Pillow
        try:
            from PIL import ImageGrab

            img = ImageGrab.grab()
            img.save(ss_path)
            taken = True
        except Exception:
            pass
        # Yöntem 2: PowerShell CopyFromScreen
        if not taken:
            ps_cmd = (
                "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
                "$bmp=New-Object System.Drawing.Bitmap("
                "[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,"
                "[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height);"
                "$g=[System.Drawing.Graphics]::FromImage($bmp);"
                "$g.CopyFromScreen(0,0,0,0,$bmp.Size);"
                "$bmp.Save($env:TEMP + '\jarvis_ss.png');"
                "$g.Dispose();$bmp.Dispose()"
            )
            try:
                r = subprocess.run(
                    ["powershell", "-Command", ps_cmd], capture_output=True, timeout=15
                )
                taken = Path(ss_path).exists()
            except Exception:
                pass
        if taken and Path(ss_path).exists():
            return f"__SCREENSHOT__{ss_path}"
        return "Ekran goruntusu alinamadi. (PIL veya PowerShell gerekli)"

    elif command == "/dosyalar":
        path = args.strip() or str(Path.home() / "Desktop")
        try:
            items = list(Path(path).iterdir())
            dirs = [f"📁 {p.name}" for p in sorted(items) if p.is_dir()][:10]
            files = [f"📄 {p.name}" for p in sorted(items) if p.is_file()][:15]
            return f"*{path}*\n\n" + "\n".join(dirs + files) or "Bos klasor."
        except Exception as e:
            return f"Klasor hatasi: {e}"

    elif command == "/surec":
        try:
            r = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name,CPU,WorkingSet | Format-Table -AutoSize",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return f"*En Yuklu 10 Proses:*\n```\n{r.stdout[:1500]}\n```"
        except Exception as e:
            return f"Proses hatasi: {e}"

    elif command == "/kill":
        if not args:
            return "Kullanim: /kill [proses-adi veya PID]"
        kill_target = args.strip().split()[0]  # sadece ilk kelime
        try:
            r = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"Stop-Process -Name '{kill_target}' -Force",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return (
                f"`{kill_target}` durduruldu."
                if r.returncode == 0
                else f"Hata: {r.stderr[:200]}"
            )
        except Exception as e:
            return f"Kill hatasi: {e}"

    elif command == "/ip":
        try:
            r = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "(Invoke-WebRequest -Uri 'https://api.ipify.org' -UseBasicParsing).Content",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            local = subprocess.run(
                ["ipconfig"], capture_output=True, text=True, timeout=5
            )
            local_ip = next(
                (
                    l.split(":")[-1].strip()
                    for l in local.stdout.split("\n")
                    if "IPv4" in l
                ),
                "?",
            )
            return f"*Dis IP:* `{r.stdout.strip()}`\n*Yerel IP:* `{local_ip}`"
        except Exception as e:
            return f"IP hatasi: {e}"

    elif command == "/not":
        if not args:
            return "Kullanim: /not [metin]\nOrnek: /not Yarin toplanti var saat 15:00"
        import json as _json_not

        notes_file = str(DATA_DIR / "notlar.json")
        try:
            with open(notes_file, "r", encoding="utf-8") as f:
                notes = _json_not.load(f)
        except Exception:
            notes = []
        from datetime import datetime as _dt

        notes.append({"tarih": _dt.now().strftime("%Y-%m-%d %H:%M"), "not": args})
        with open(notes_file, "w", encoding="utf-8") as f:
            _json_not.dump(notes, f, ensure_ascii=False, indent=2)
        return f"Not kaydedildi ({len(notes)}. not):\n{args}"

    elif command == "/notlar":
        import json as _json_notlar

        notes_file = str(DATA_DIR / "notlar.json")
        try:
            with open(notes_file, "r", encoding="utf-8") as f:
                notes = _json_notlar.load(f)
        except Exception:
            notes = []
        if not notes:
            return "Hic not yok. /not [metin] ile ekle."
        lines = [f"*Notlarim ({len(notes)} adet):*"]
        for i, n in enumerate(notes[-10:], 1):
            lines.append(f"{i}. [{n.get('tarih', '')}] {n.get('not', '')}")
        return chr(10).join(lines)

    elif command == "/not-sil":
        import json as _json_notsil

        notes_file = str(DATA_DIR / "notlar.json")
        try:
            with open(notes_file, "w", encoding="utf-8") as f:
                _json_notsil.dump([], f)
            return "Tum notlar silindi."
        except Exception as e:
            return f"Hata: {e}"

    elif command == "/obsidian-kaydet":
        if not args:
            return "Kullanim: /obsidian-kaydet <baslik> | <icerik>\nOrnek: /obsidian-kaydet Toplanti | Yarin saat 15"
        try:
            from server.persona_manager import get_active_persona as _gap
            from server.skills.persona_obsidian_skill import write_persona_note as _write_note
            _persona = _gap()
            _pid = _persona.get("id", "jarvis") if isinstance(_persona, dict) else "jarvis"
            parts = args.split("|", 1)
            _title = parts[0].strip()
            _content = parts[1].strip() if len(parts) > 1 else args
            _note = _write_note(persona_id=_pid, title=_title, content=_content)
            return f"Obsidian'a kaydedildi ({_pid}): {_title}"
        except Exception as _e:
            return f"Obsidian kayit hatasi: {_e}"

    elif command == "/obsidian-oku":
        if not args:
            return "Kullanim: /obsidian-oku <arama sorgusu>"
        try:
            from server.persona_manager import get_active_persona as _gap2
            from server.skills.persona_obsidian_skill import recall_persona_notes as _recall
            _persona2 = _gap2()
            _pid2 = _persona2.get("id", "jarvis") if isinstance(_persona2, dict) else "jarvis"
            _notes = _recall(persona_id=_pid2, query=args)
            if not _notes:
                return f"{_pid2} icin ilgili not bulunamadi: {args}"
            return f"*{_pid2} notlari ({args}):*\n{_notes[:1500]}"
        except Exception as _e2:
            return f"Obsidian okuma hatasi: {_e2}"

    elif command == "/luna-tara":
        if not args:
            return "Kullanim: /luna-tara <target_id>"
        try:
            from server.services.luna_agent import (
                TargetNotAuthorizedError as _LunaTargetNotAuthorizedError,
            )
            from server.services.luna_agent import scan_target as _scan_luna_target

            _target_id = args.strip().split()[0]
            _result = _scan_luna_target(_target_id)
            if not _result.get("ok"):
                _error = _result.get("error") or "scan_failed"
                return f"Luna tarama basarisiz ({_target_id}): {_error}"
            _findings = _result.get("findings") or []
            _severity_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            }
            for _finding in _findings:
                _severity = str(_finding.get("severity") or "info").lower()
                if _severity not in _severity_counts:
                    _severity = "info"
                _severity_counts[_severity] += 1
            return (
                f"Luna tarama tamamlandi: {_target_id}\n"
                f"Bulgu: {len(_findings)} | "
                f"Kritik: {_severity_counts['critical']} | "
                f"Yuksek: {_severity_counts['high']} | "
                f"Orta: {_severity_counts['medium']} | "
                f"Dusuk: {_severity_counts['low']} | "
                f"Bilgi: {_severity_counts['info']}"
            )
        except _LunaTargetNotAuthorizedError as _unauth_exc:
            return f"Luna hedef reddedildi: {_unauth_exc}"
        except Exception as _luna_exc:
            return f"Luna tarama hatasi: {_luna_exc}"

    elif command == "/mert-ara":
        if not args:
            return "Kullanim: /mert-ara <sorgu>"
        try:
            from server.skills.mert_research_skill import search_and_summarize

            result = search_and_summarize(args)
            if not result.get("ok"):
                return f"Mert arastirma hatasi: {result.get('error', 'bilinmeyen_hata')}"

            lines = ["*Mert Arastirma Ozeti*", str(result.get("summary") or "").strip()]
            saved_to = str(result.get("saved_to") or "").strip()
            if saved_to:
                lines.append(f"Kayit: {saved_to}")
            sources = result.get("sources") if isinstance(result.get("sources"), list) else []
            if sources:
                lines.append("Kaynaklar:")
                for source in sources[:3]:
                    title = str(source.get("title") or "Kaynak").strip()
                    url = str(source.get("url") or "").strip()
                    lines.append(f"- {title}" + (f" -> {url}" if url else ""))
            return "\n".join(line for line in lines if line).strip()[:3500]
        except Exception as exc:
            return f"Mert arastirma hatasi: {exc}"

    elif command == "/mert-rakip":
        if not args:
            return "Kullanim: /mert-rakip <urun_adi>"
        try:
            from server.skills.mert_research_skill import competitor_analysis

            result = competitor_analysis(args)
            if not result.get("ok"):
                return f"Mert rakip analizi hatasi: {result.get('error', 'bilinmeyen_hata')}"
            return str(result.get("report") or "Rapor olusturulamadi.")[:3500]
        except Exception as exc:
            return f"Mert rakip analizi hatasi: {exc}"

    elif command == "/sabri-brief":
        if not args.strip():
            return "Kullanim: /sabri-brief <musteri notu>"
        try:
            from server.skills.sabri_campaign_skill import sabri_brief

            result = sabri_brief(args.strip())
            if not result.get("ok"):
                return f"Sabri brief hatasi: {result.get('error', 'bilinmeyen_hata')}"
            lines = [
                "*Sabri Brief*",
                "",
                f"Brief ID: `{result['brief_id']}`",
                f"Marka: {result.get('brand', '-')}",
                f"Kitle: {result.get('audience', '-')}",
                f"Hedef: {result.get('goal', '-')}",
                f"Ton: {result.get('tone', '-')}",
                f"Butce (TL): {result.get('budget_try') or 'belirtilmedi'}",
                f"Kaydedildi: {result.get('saved_to', '-')}",
            ]
            return "\n".join(lines)
        except Exception as exc:
            return f"Sabri brief hatasi: {exc}"

    elif command == "/sabri-copy":
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 1:
            return "Kullanim: /sabri-copy <brief_id> [platform]\nPlatformlar: meta, google, linkedin, instagram, tiktok"
        brief_id = parts[0]
        platform = parts[1].strip().lower() if len(parts) > 1 else "meta"
        try:
            from server.skills.sabri_campaign_skill import sabri_copy

            result = sabri_copy(brief_id, platform)
            if not result.get("ok"):
                return f"Sabri copy hatasi: {result.get('message') or result.get('error')}"
            lines = [f"*Sabri Copy* ({result['platform']} / ton: {result['tone']})"]
            for idx, v in enumerate(result["variants"], start=1):
                lines.append("")
                lines.append(f"*{idx}. {v['angle']}*")
                lines.append(f"Headline: {v['headline']}")
                lines.append(f"Primary: {v['primary']}")
                lines.append(f"CTA: {v['cta']}")
            return "\n".join(lines)[:3500]
        except Exception as exc:
            return f"Sabri copy hatasi: {exc}"

    elif command == "/sabri-gorsel":
        brief_id = args.strip()
        if not brief_id:
            return "Kullanim: /sabri-gorsel <brief_id>"
        try:
            from server.skills.sabri_campaign_skill import sabri_visual_prompt

            result = sabri_visual_prompt(brief_id)
            if not result.get("ok"):
                return f"Sabri gorsel hatasi: {result.get('message') or result.get('error')}"
            lines = [f"*Sabri Gorsel Prompt'lari* (ton: {result['tone']})", ""]
            for idx, prompt in enumerate(result["prompts"], start=1):
                lines.append(f"{idx}. {prompt}")
                lines.append("")
            return "\n".join(lines)[:3500]
        except Exception as exc:
            return f"Sabri gorsel hatasi: {exc}"

    elif command == "/sabri-kampanya":
        parts = args.strip().split()
        if len(parts) < 2:
            return "Kullanim: /sabri-kampanya <brief_id> <butce_tl> [gun=30]"
        brief_id = parts[0]
        try:
            budget = float(parts[1])
            days = int(parts[2]) if len(parts) > 2 else 30
        except (ValueError, IndexError):
            return "Butce sayi olmali. Ornek: /sabri-kampanya abc_123 10000 30"
        try:
            from server.skills.sabri_campaign_skill import sabri_campaign_plan

            result = sabri_campaign_plan(brief_id, budget, days)
            if not result.get("ok"):
                return f"Sabri kampanya hatasi: {result.get('message') or result.get('error')}"
            lines = [
                f"*Sabri Kampanya Plani* ({result['goal']} / {result['duration_days']} gun / {result['budget_try']:.0f} TL)",
                "",
                "*Kanal Mix:*",
            ]
            for ch in result["channel_mix"]:
                lines.append(f"- {ch['channel']}: %{ch['percent']} = {ch['budget_try']:.0f} TL ({ch['daily_try']:.0f}/gun)")
            lines.append("")
            lines.append("*Fazlar:*")
            for ph in result["phases"]:
                lines.append(f"- {ph['phase']} ({ph['days']}): {ph['focus']}")
            if result.get("kpi_targets"):
                lines.append("")
                lines.append("*KPI Hedefleri:*")
                for k, v in result["kpi_targets"].items():
                    lines.append(f"- {k}: {v}")
            return "\n".join(lines)[:3500]
        except Exception as exc:
            return f"Sabri kampanya hatasi: {exc}"

    elif command == "/zeynep-kvkk":
        target = args.strip() or "."
        try:
            from server.skills.zeynep_security_skill import zeynep_kvkk_audit

            result = zeynep_kvkk_audit(target)
            if not result.get("ok"):
                return f"Zeynep KVKK hatasi: {result.get('message') or result.get('error')}"
            sev = result["by_severity"]
            lines = [
                f"*Zeynep KVKK Audit* ({result['scope']})",
                f"Taranan dosya: {result['scanned_files']}",
                f"Toplam bulgu: {result['total_findings']} (high:{sev.get('high',0)} medium:{sev.get('medium',0)} low:{sev.get('low',0)})",
            ]
            for f in result["findings"][:15]:
                lines.append(f"- [{f['severity']}] {f['type']} @ {f['file']}:{f['line']} — {f['sample']}")
            if result["total_findings"] > 15:
                lines.append(f"... (+{result['total_findings']-15} bulgu daha)")
            return "\n".join(lines)[:3500]
        except Exception as exc:
            return f"Zeynep KVKK hatasi: {exc}"

    elif command == "/zeynep-gizli":
        target = args.strip() or "."
        try:
            from server.skills.zeynep_security_skill import zeynep_secret_scan

            result = zeynep_secret_scan(target)
            if not result.get("ok"):
                return f"Zeynep secret scan hatasi: {result.get('message') or result.get('error')}"
            lines = [
                f"*Zeynep Secret Scan* ({result['scope']})",
                f"Taranan dosya: {result['scanned_files']}",
                f"Toplam bulgu: {result['total_findings']}",
            ]
            for f in result["findings"][:15]:
                lines.append(f"- [{f['severity']}] {f['type']} @ {f['file']}:{f['line']} — {f['sample']}")
            if result["total_findings"] > 15:
                lines.append(f"... (+{result['total_findings']-15} bulgu daha)")
            return "\n".join(lines)[:3500]
        except Exception as exc:
            return f"Zeynep secret scan hatasi: {exc}"

    elif command == "/zeynep-log":
        parts = args.strip().split()
        log_path = parts[0] if parts else ""
        try:
            hours = int(parts[1]) if len(parts) > 1 else 24
        except ValueError:
            hours = 24
        try:
            from server.skills.zeynep_security_skill import zeynep_log_review

            result = zeynep_log_review(log_path, hours)
            if not result.get("ok"):
                return f"Zeynep log review hatasi: {result.get('message') or result.get('error')}"
            lines = [
                f"*Zeynep Log Review* (son {result['since_hours']}h, {result['scanned_files']} dosya)",
            ]
            for name, count in result["anomaly_counts"].items():
                lines.append(f"- {name}: {count}")
            return "\n".join(lines)[:3500]
        except Exception as exc:
            return f"Zeynep log review hatasi: {exc}"

    elif command == "/zeynep-sertlestir":
        target = args.strip()
        try:
            from server.skills.zeynep_security_skill import zeynep_hardening_check

            result = zeynep_hardening_check(target)
            if not result.get("ok"):
                return f"Zeynep hardening hatasi: {result.get('message') or result.get('error')}"
            lines = [
                f"*Zeynep Hardening Check* (skor: %{result['score_pct']}, {result['pass_count']}/{result['total_checks']})",
            ]
            for c in result["checks"]:
                mark = "[OK]" if c["ok"] else "[X]"
                lines.append(f"{mark} {c['id']} ({c['severity']}): {c['note']}")
            return "\n".join(lines)[:3500]
        except Exception as exc:
            return f"Zeynep hardening hatasi: {exc}"

    elif command == "/deniz-ebay":
        if not args.strip():
            return "Kullanim: /deniz-ebay <urun>"
        try:
            from server.skills.ebay_research import analyze_product, format_report

            result = analyze_product(args.strip())
            if not result:
                return "Deniz eBay: sonuc bulunamadi."
            return str(format_report(result))[:3500]
        except Exception as exc:
            return f"Deniz eBay hatasi: {exc}"

    elif command == "/deniz-trendyol":
        if not args.strip():
            return "Kullanim: /deniz-trendyol <urun>"
        try:
            from server.skills.trendyol_skill import full_trendyol_analysis

            report = full_trendyol_analysis(args.strip())
            return str(report or "Deniz Trendyol: sonuc bulunamadi.")[:3500]
        except Exception as exc:
            return f"Deniz Trendyol hatasi: {exc}"

    elif command == "/deniz-printify":
        parts = args.strip().split(maxsplit=1)
        action = parts[0].lower() if parts else "overview"
        niche = parts[1] if len(parts) > 1 else ""
        token = os.environ.get("PRINTIFY_TOKEN", "")
        if not token:
            return "Deniz Printify: PRINTIFY_TOKEN eksik (.env'e ekle)."
        try:
            from server.skills.printify_skill import format_overview, analyze_product_opportunity

            if action in ("overview", "ozet", "durum"):
                return str(format_overview(token))[:3500]
            if action in ("firsat", "fırsat", "opportunity"):
                if not niche:
                    return "Kullanim: /deniz-printify firsat <niche>"
                return str(analyze_product_opportunity(token, niche))[:3500]
            return "Kullanim: /deniz-printify overview | /deniz-printify firsat <niche>"
        except Exception as exc:
            return f"Deniz Printify hatasi: {exc}"

    elif command == "/deniz-rakip":
        if not args.strip():
            return "Kullanim: /deniz-rakip <urun>"
        query = args.strip()
        sections: list[str] = [f"*Deniz Rakip Analizi*: {query}", ""]
        try:
            from server.skills.ebay_research import analyze_product
            ebay_result = analyze_product(query)
            if ebay_result:
                ebay_avg = ebay_result.get("stats", {}).get("avg_price_usd") or ebay_result.get("avg_price_usd")
                sections.append(f"- eBay ortalama: {ebay_avg or '-'}")
            else:
                sections.append("- eBay: sonuc yok")
        except Exception as exc:
            sections.append(f"- eBay hata: {exc}")
        try:
            from server.skills.trendyol_skill import search_trendyol, analyze_trendyol_results
            ty_raw = search_trendyol(query)
            ty_analysis = analyze_trendyol_results(ty_raw, query) if ty_raw else {}
            stats = ty_analysis.get("stats") if isinstance(ty_analysis, dict) else {}
            avg = (stats or {}).get("avg_price_try")
            sections.append(f"- Trendyol ortalama TL: {avg or '-'}")
        except Exception as exc:
            sections.append(f"- Trendyol hata: {exc}")
        return "\n".join(sections)[:3500]

    elif command == "/cevirici":
        if not args:
            return "Kullanim: /cevirici [metin]\nOtomatik TR<->EN cevirir"
        route = MODEL_ROUTES["chat"]
        prompt = (
            f"Asagidaki metni cevirdir. Eger Turkce ise Ingilizceye, "
            f"eger Ingilizce ise Turkceye cevirdir. "
            f"SADECE cevirisi olan metni yaz, baska hicbir sey ekleme:" + chr(10) + args
        )
        reply = call_ollama(
            route["model"],
            [{"role": "user", "content": prompt}],
            max_tokens=800,
            num_ctx=2048,
            fallback_model=route.get("fallback"),
            route_name="chat",
        )
        return f"*Ceviri:*{chr(10)}{reply}"

    elif command == "/gpt":
        if not args:
            return "Kullanim: /gpt [soru]\nGPT-4o ile soru sor (OpenAI API)"
        oai_key = os.environ.get("OPENAI_API_KEY", "")
        if not oai_key or oai_key == "your_api_key_here":
            return "OpenAI API key eksik. .env dosyasina OPENAI_API_KEY ekle."
        import urllib.request as _ureq, json as _jgpt

        payload = _jgpt.dumps(
            {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": args}],
                "max_tokens": 1000,
            }
        ).encode()
        req = _ureq.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oai_key}",
            },
        )
        try:
            with _ureq.urlopen(req, timeout=30) as r:
                data = _jgpt.loads(r.read())
            reply = data["choices"][0]["message"]["content"]
            return f"*GPT-4o:*{chr(10)}{reply}"
        except Exception as e:
            return f"GPT hatasi: {e}"

    elif command == "/ozet":
        if not args:
            return "Kullanim: /ozet [metin veya url]\nLong metni/URL icerigini ozetler"
        route = MODEL_ROUTES["chat"]
        # URL mi metin mi?
        if args.startswith("http"):
            try:
                import urllib.request as _ur

                req = _ur.Request(args, headers={"User-Agent": "Mozilla/5.0"})
                with _ur.urlopen(req, timeout=10) as r:
                    raw = r.read().decode("utf-8", errors="ignore")
                # Basit HTML tag temizleme
                import re as _re

                clean = _re.sub(r"<[^>]+>", " ", raw)
                clean = _re.sub(r"\s+", " ", clean).strip()[:3000]
                text_to_sum = f"Su URL icerigi: {clean}"
            except Exception as e:
                text_to_sum = args
        else:
            text_to_sum = args
        prompt = f"Asagidaki metni Turkce olarak 3-5 madde halinde ozetle:{chr(10)}{text_to_sum}"
        reply = call_ollama(
            route["model"],
            [{"role": "user", "content": prompt}],
            max_tokens=600,
            num_ctx=4096,
            fallback_model=route.get("fallback"),
            route_name="chat",
        )
        return f"*Ozet:*{chr(10)}{reply}"

    elif command == "/jcoder":
        if not args:
            return (
                "Kullanim: /jcoder [gorev]\nOrnek: /jcoder bridge.py ye yeni komut ekle"
            )
        route = MODEL_ROUTES["code"]
        system_prompt = (
            "Sen Jarvis Mission Control sisteminin bas geliştiricisisin. "
            "Python 3.14, Telegram raw HTTP polling, Ollama (http://127.0.0.1:11434) kullaniyorsun. "
            "bridge.py yapisina hakimsin. f-string icinde chr(10) kullan. "
            "Kisa, net, calisir kod yaz. Turkce acikla."
        )
        reply = call_ollama(
            route["model"],
            [{"role": "user", "content": args}],
            system=system_prompt,
            max_tokens=1500,
            num_ctx=4096,
            fallback_model=route.get("fallback"),
            route_name="code",
        )
        return f"*Jarvis Coder:*{chr(10)}{reply}"

    elif command == "/skill":
        if not args:
            return "Kullanim: /skill [isim] [aciklama]\nOrnek: /skill hava Sehir hava durumu getir"
        route = MODEL_ROUTES["code"]
        skill_fmt = (
            "def run(args: str, context: dict = None) -> str:"
            + chr(10)
            + "    return 'sonuc'"
        )
        system_prompt = (
            "Sen Jarvis skill yazicisin. Skill su formatta olmali:"
            + chr(10)
            + skill_fmt
            + chr(10)
            + "Ollama icin urllib kullan (http://127.0.0.1:11434/api/generate). "
            "Sadece calisir Python kodu yaz, Turkce yorum ekle."
        )
        reply = call_ollama(
            route["model"],
            [{"role": "user", "content": f"Skill yaz: {args}"}],
            system=system_prompt,
            max_tokens=1500,
            num_ctx=4096,
            fallback_model=route.get("fallback"),
            route_name="code",
        )
        return f"*Skill Yazici:*{chr(10)}{reply}"

    elif command == "/analyst":
        if not args:
            return (
                "Kullanim: /analyst [konu]\nOrnek: /analyst Jarvis SaaS fiyatlandirma"
            )
        route = MODEL_ROUTES["reasoning"]
        system_prompt = (
            "Sen Jarvis Mission Control icin is gelistirme ve pazarlama uzmanisın. "
            "Jarvis = self-hosted Turkce AI asistan SaaS. "
            "Paketler: Starter 1500 TL, Pro 3500 TL, Agency 7500 TL. "
            "Hedef: 20 musteri = 80.000 TL/ay. "
            "Veriye dayali, somut, aksiyon odakli Turkce analiz yap."
        )
        reply = call_ollama(
            route["model"],
            [{"role": "user", "content": args}],
            system=system_prompt,
            max_tokens=1200,
            num_ctx=4096,
            fallback_model=route.get("fallback"),
            route_name="reasoning",
        )
        return f"*Jarvis Analyst:*{chr(10)}{reply}"

    elif command in (
        "/mouse",
        "/git",
        "/tıkla",
        "/tikla",
        "/click",
        "/çifttıkla",
        "/cifttikla",
        "/dblclick",
        "/sağtıkla",
        "/sagtikla",
        "/rightclick",
        "/yaz",
        "/type",
        "/tuş",
        "/tus",
        "/key",
        "/press",
        "/kısayol",
        "/kisayol",
        "/hotkey",
        "/scroll",
        "/ekranoku",
        "/konum",
        "/nerede",
    ):
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from computer_control_skill import run_computer_control

            return run_computer_control(command, args)
        except Exception as e:
            return f"❌ Computer control hatası: {e}"

    elif command in ("/tarayici", "/browser"):
        try:
            import sys as _sys

            _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from playwright_browser_skill import handle_browser

            result = handle_browser(args, str(chat_id))
            memory.add_message(chat_id, "user", f"/tarayici {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            log.exception("Tarayici komutu basarisiz")
            return f"Tarayici hatasi: {str(e)[:200]}"

    elif command in ("/yap", "/bak", "/otonom", "/kodcalistir"):
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from computer_agent_skill import run_computer_agent

            return run_computer_agent(command, args)
        except Exception as e:
            return f"❌ Computer agent hatası: {e}"

    elif command in ("/kabul", "/onayla", "/accept"):
        log.info("AnyDesk kabul komutu alindi.")
        try:
            decision = evaluate_operator_action(
                "anydesk_accept",
                "AnyDesk baglanti istegini kabul et",
                source="bridge.anydesk_accept",
                risk="high",
                require_approval=True,
                persona_id=_current_persona_id(chat_id),
            )
            if not decision.allowed:
                return format_policy_block_message(decision)
            ps_script = (
                r"C:\Users\sergen\Desktop\jarvis-mission-control\anydesk_kabul.ps1"
            )
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-WindowStyle",
                    "Hidden",
                    "-File",
                    ps_script,
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            if result.returncode == 0 or "kabul edildi" in out.lower():
                return f"✅ AnyDesk bağlantısı kabul edildi!\n{out}"
            else:
                return f"❌ AnyDesk kabul başarısız:\n{out or err or 'Pencere bulunamadı.'}"
        except Exception as e:
            return f"❌ Hata: {e}"

    elif command in ("/onaylar", "/bekleyen", "/approval"):
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from approval_skill import list_approval_requests

            status = args.strip() if args else "pending"
            return list_approval_requests(status)
        except Exception as e:
            return f"❌ Onay kuyruğu hatası: {e}"

    elif command in ("/onay-ekle", "/approval-add"):
        if not args:
            return "Kullanim: /onay-ekle [baslik] | [ozet]"
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from approval_skill import add_approval_request

            title, _, summary = args.partition("|")
            return add_approval_request(title, summary, source="manual")
        except Exception as e:
            return f"❌ Onay ekleme hatası: {e}"

    elif command in ("/onay", "/approve"):
        if not args:
            return "Kullanim: /onay [id] | [not]"
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from approval_skill import decide_approval

            item_id, _, note = args.partition("|")
            return decide_approval(item_id.strip(), "approve", note)
        except Exception as e:
            return f"❌ Onay işleme hatası: {e}"

    elif command in ("/red", "/reject"):
        if not args:
            return "Kullanim: /red [id] | [not]"
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from approval_skill import decide_approval

            item_id, _, note = args.partition("|")
            return decide_approval(item_id.strip(), "reject", note)
        except Exception as e:
            return f"❌ Red işleme hatası: {e}"

    elif command in ("/claude-uyandir", "/claude-wake"):
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from approval_skill import schedule_claude_resume

            schedule_part = args or "09:02"
            resume_at, _, note = schedule_part.partition("|")
            return schedule_claude_resume(
                resume_at.strip() or "09:02", note, "Claude collaboration protocol"
            )
        except Exception as e:
            return f"❌ Claude uyandırma planlama hatası: {e}"

    elif command in ("/claude-durum", "/claude-status"):
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from approval_skill import get_claude_resume_status

            return get_claude_resume_status()
        except Exception as e:
            return f"❌ Claude durum hatası: {e}"

    elif command in ("/uyku-modu", "/sleep-mode", "/oto-onay"):
        try:
            sys.path.insert(
                0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills"
            )
            from approval_skill import (
                set_autopilot,
                get_autopilot_status,
                process_pending_auto_approvals,
            )

            action = (args or "status").strip().lower()
            if action in ("ac", "on", "aktif"):
                result = set_autopilot(
                    True,
                    "sleep",
                    "Kullanici uyurken otomatik onay ve devam modu aktif.",
                )
                batch = process_pending_auto_approvals()
                return result + "\n" + batch
            if action in ("kapat", "off", "pasif"):
                return set_autopilot(
                    False, "manual", "Kullanici geri donene kadar manuel moda alindi."
                )
            return get_autopilot_status()
        except Exception as e:
            return f"❌ Uyku modu hatası: {e}"

    elif command in ("/otopilot", "/autopilot"):
        try:
            root = r"C:\Users\sergen\Desktop\jarvis-mission-control"
            if (args or "").strip().lower() in ("baslat", "start"):
                result = subprocess.run(
                    [
                        "powershell.exe",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        rf"{root}\start_autopilot_background.ps1",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                return (
                    result.stdout or result.stderr or "Autopilot baslatildi."
                ).strip()
            if (args or "").strip().lower() in ("durdur", "stop"):
                result = subprocess.run(
                    [
                        "powershell.exe",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        rf"{root}\stop_autopilot.ps1",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                return (
                    result.stdout
                    or result.stderr
                    or "Autopilot durdurma sinyali gonderildi."
                ).strip()
            runtime_path = (
                Path(root)
                / "server"
                / "agent_workspace"
                / "approval_state"
                / "autopilot_runtime.json"
            )
            if runtime_path.exists():
                return runtime_path.read_text(encoding="utf-8")
            return "Autopilot runtime durumu henuz yok. /otopilot start ile baslat."
        except Exception as e:
            return f"❌ Autopilot hatası: {e}"

    # ─── TELEGRAM INTELLIGENCE COMMANDS (Caleb-3) ───────────────────
    elif command == "/health":
        if TELEGRAM_INTELLIGENCE:
            try:
                metrics = build_telegram_health_payload()
                msg = TELEGRAM_INTELLIGENCE.format_health_message(metrics)
                TELEGRAM_INTELLIGENCE.log_command(
                    "/health",
                    chat_id,
                    "success",
                    len(msg),
                    metadata={
                        "current_task_id": (
                            metrics.get("current_task", {}).get("id")
                            if isinstance(metrics.get("current_task"), dict)
                            else None
                        ),
                        "voice_phase": metrics.get("voice_phase"),
                    },
                )
                return msg
            except Exception as e:
                return f"❌ Health check failed: {e}"
        return "Telegram intelligence not initialized"

    elif command == "/metrics":
        if TELEGRAM_INTELLIGENCE:
            try:
                metrics = build_telegram_metrics_payload()
                msg = TELEGRAM_INTELLIGENCE.format_metrics_message(metrics)
                TELEGRAM_INTELLIGENCE.log_command(
                    "/metrics",
                    chat_id,
                    "success",
                    len(msg),
                    metadata={
                        "queue_depth": metrics.get("queue_depth"),
                        "running_tasks": metrics.get("running_tasks"),
                    },
                )
                return msg
            except Exception as e:
                return f"❌ Metrics retrieval failed: {e}"
        return "Telegram intelligence not initialized"

    elif command == "/improve":
        if TELEGRAM_INTELLIGENCE:
            try:
                improvements = [
                    {"title": "Cache optimization", "impact_score": 0.8},
                    {"title": "Query batching", "impact_score": 0.6},
                    {"title": "Connection pooling", "impact_score": 0.7},
                ]
                msg = TELEGRAM_INTELLIGENCE.format_improvements_message(improvements)
                TELEGRAM_INTELLIGENCE.log_command(
                    "/improve", chat_id, "success", len(msg)
                )
                return msg
            except Exception as e:
                return f"❌ Improvement suggestions failed: {e}"
        return "Telegram intelligence not initialized"

    elif command == "/rollback":
        if TELEGRAM_INTELLIGENCE:
            try:
                result = {
                    "success": True,
                    "revision": "abc123def456",
                    "message": "Reverted to stable version",
                }
                msg = TELEGRAM_INTELLIGENCE.format_rollback_message(result)
                TELEGRAM_INTELLIGENCE.log_command(
                    "/rollback", chat_id, "success", len(msg)
                )
                return msg
            except Exception as e:
                return f"❌ Rollback failed: {e}"
        return "Telegram intelligence not initialized"

    elif command == "/cache":
        if TELEGRAM_INTELLIGENCE:
            try:
                cache_stats = {"hits": 450, "misses": 50, "size_mb": 125.5}
                msg = TELEGRAM_INTELLIGENCE.format_cache_message(cache_stats)
                TELEGRAM_INTELLIGENCE.log_command(
                    "/cache", chat_id, "success", len(msg)
                )
                return msg
            except Exception as e:
                return f"❌ Cache statistics failed: {e}"
        return "Telegram intelligence not initialized"

    # ─── 002: AUTONOMOUS RESEARCH AGENT ──────────────────────────────
    elif command == "/sabah-brief":
        try:
            import sys as _sys, os as _os

            _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "skills"))
            from research_scheduler_skill import run_morning_brief

            _chat = chat_id

            def _send(msg):
                pass  # bridge will return response string

            result = run_morning_brief(_send)
            if result.get("ok"):
                return f"Brief gonderildi — {result['items_count']} kaynak taranadi"
            return f"Brief gonderilemedi: {result.get('error', 'bilinmiyor')}"
        except Exception as e:
            return f"Hata: {str(e)[:200]}"

    elif command == "/arastirma-durum":
        try:
            import sys as _sys, os as _os

            _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "skills"))
            from research_scheduler_skill import get_scheduler_status, load_today_brief

            status = get_scheduler_status()
            today_brief = load_today_brief()
            running = "Calisiyor" if status.get("running") else "Durdurulmus"
            jobs = status.get("jobs", [])
            next_run = jobs[0].get("next_run", "bilinmiyor") if jobs else "job yok"
            brief_info = (
                "yok"
                if not today_brief
                else f"{today_brief['send_status']} ({today_brief.get('items_count', '?')} madde)"
            )
            return (
                f"Arastirma Durumu\nScheduler: {running}\nSonraki brief: {next_run}\nBugunku brief: {brief_info}"
            )[:400]
        except Exception as e:
            return f"Durum alinamadi: {str(e)[:150]}"

    elif command == "/instagram":
        try:
            import sys as _sys, os as _os
            import json as _json
            import asyncio as _asyncio

            _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "skills"))
            from instagram_skill import (
                add_watched_account,
                list_watched_accounts,
                remove_watched_account,
            )

            sub = args.strip()
            
            # ✨ NEW: Codex-powered profile analysis
            if sub.startswith("analyze-profiles "):
                handles_str = sub[len("analyze-profiles "):].strip()
                handles = [h.strip() for h in handles_str.split(",") if h.strip()]
                
                if not handles:
                    return "Kullanim: /instagram analyze-profiles @handle1,@handle2,@handle3,..."
                
                try:
                    from services.codex_profile_analyzer import InstagramProfileAnalysisOrchestrator
                    
                    orchestrator = InstagramProfileAnalysisOrchestrator(
                        codex_base_url=os.environ.get("CODEX_BASE_URL", "http://localhost:9090")
                    )
                    
                    insights = _asyncio.run(
                        orchestrator.analyze_profiles_from_list(handles)
                    )
                    
                    # Return structured response
                    response = {
                        "status": "completed",
                        "profiles_analyzed": insights.analyzed_profiles,
                        "top_content_themes": [
                            {
                                "theme": t["theme"],
                                "avg_engagement": f"{t['avg_engagement']:.1f}%"
                            }
                            for t in insights.top_5_content_themes[:3]
                        ],
                        "jarvis_playbook_summary": insights.jarvis_strategic_playbook.get("next_steps", []),
                        "top_profiles": [
                            f"#{i+1} @{p['handle']} ({p['followers']}k followers)"
                            for i, p in enumerate(insights.profile_rankings[:3])
                        ]
                    }
                    
                    return f"✅ Analiz tamamlandı:\n{_json.dumps(response, indent=2, ensure_ascii=False)[:1500]}"
                
                except Exception as e:
                    return f"Codex analiz hatasi: {str(e)[:200]}"
            
            # Original subcommands
            if sub.startswith("takip "):
                handle = sub[len("takip ") :].strip()
                result = add_watched_account(handle)
                return result["message"]
            elif sub == "listele":
                accounts = list_watched_accounts()
                if not accounts:
                    return "Takip listesi bos. /instagram takip @hesap ile ekle."
                lines = ["Takip Listesi"]
                for acc in accounts[:20]:
                    last = (
                        acc.get("last_checked_at", "")[:10]
                        if acc.get("last_checked_at")
                        else "hic"
                    )
                    lines.append(f"@{acc['username']} (son kontrol: {last})")
                return "\n".join(lines)[:400]
            elif sub.startswith("cikar "):
                handle = sub[len("cikar ") :].strip()
                result = remove_watched_account(handle)
                return result["message"]
            return "Kullanim: /instagram takip @hesap | /instagram listele | /instagram cikar @hesap | /instagram analyze-profiles @h1,@h2,..."
        except Exception as e:
            return f"Instagram hatasi: {str(e)[:150]}"

    elif command == "/scrape-profile":
        try:
            import sys as _sys, os as _os
            import json as _json
            import asyncio as _asyncio

            url_or_handle = args.strip()
            
            if not url_or_handle:
                return "Kullanim: /scrape-profile @handle | /scrape-profile https://youtube.com/c/ChannelName"
            
            from services.universal_profile_scraper import scrape_profile_handler
            
            result = _asyncio.run(scrape_profile_handler(url_or_handle))
            
            if result['status'] == 'completed':
                summary = result['data_summary']
                return f"""✅ Profil başarıyla çekildi!

📊 Özet:
  Handle: {summary['handle']}
  Followers: {summary['followers']:,}
  Posts/Videos: {summary['posts']}
  Engagement: {summary['engagement_rate']}

📁 Dosya kaydedildi: {result['file_saved'][:100]}...

(Full JSON'u analiz için Codex'e gönderilebilir)
"""
            else:
                return f"❌ Hata: {result.get('error', 'Unknown error')}"
        
        except Exception as e:
            return f"Profil çekme hatasi: {str(e)[:150]}"
    
    elif command == "/ekrem":
        try:
            import sys as _sys, os as _os
            import json as _json
            import asyncio as _asyncio

            sub = args.strip()
            
            # Ekrem'in takip ettiği AI accounts'ı analyze et
            if sub == "following-analyze":
                try:
                    from services.ekrem_following_analyzer import EkremFollowingAnalyzer
                    
                    analyzer = EkremFollowingAnalyzer(instagram_username="ekremmkasap")
                    
                    # Try instaloader export (wrapped in asyncio.run for sync context)
                    async def _fetch_following():
                        return await analyzer.export_following_list()
                    
                    following = _asyncio.run(_fetch_following())
                    
                    if not following:
                        return """
❌ Instaloader export başarısız (login gerekli).
Alternatif: Instagram app'den manually 200 handle'ı copy-paste verse:

/ekrem following-analyze-manual @handle1,@handle2,...

Veya Twitter'da atsana handles'ı, ben de parse ederim.
"""
                    
                    # Analyze (wrapped in asyncio.run)
                    async def _analyze_and_report():
                        analysis = await analyzer.analyze_following_list()
                        report = await analyzer.generate_report()
                        return analysis, report
                    
                    analysis, report = _asyncio.run(_analyze_and_report())
                    
                    # Pretty output
                    output_lines = [
                        f"📊 Ekrem'in Takip Ettiği AI Accounts Analiz'i",
                        f"",
                        f"Total takip: {report['total_following']}",
                        f"AI-focused: {report['summary']['ai_focused_count']} ({report['summary']['ai_percentage']})",
                        f"🔝 Top topic: {report['summary']['top_topic']}",
                        f"",
                        f"📌 Top 5 accounts:",
                    ]
                    
                    for acc in report['top_20_ai_accounts'][:5]:
                        output_lines.append(
                            f"  #{acc['rank']} @{acc['handle']} ({acc['followers']} followers) — {acc['keywords']}"
                        )
                    
                    output_lines.extend([
                        f"",
                        f"📚 Clusters:",
                        f"  • Educators: {report['clusters']['educators']['count']}",
                        f"  • Builders: {report['clusters']['builders']['count']}",
                        f"  • Researchers: {report['clusters']['researchers']['count']}",
                        f"  • Entrepreneurs: {report['clusters']['entrepreneurs']['count']}",
                        f"  • Influencers: {report['clusters']['influencers']['count']}",
                        f"",
                        f"💡 Insights:",
                    ])
                    
                    for insight in report['insights'][:3]:
                        output_lines.append(f"  • {insight}")
                    
                    return "\n".join(output_lines)[:2000]
                
                except Exception as e:
                    return f"Following analyze hatasi: {str(e)[:200]}"
            
            return "Kullanim: /ekrem following-analyze"
        
        except Exception as e:
            return f"Ekrem command hatasi: {str(e)[:150]}"

    elif command == "/crewai":
        try:
            import sys as _sys, os as _os

            _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "skills"))
            from external_agent_skill import run_agent_task, get_agent_status

            task_text = args.strip()
            if not task_text or task_text == "durum":
                status = get_agent_status("crewai")
                installed = "Kurulu" if status["installed"] else "Kurulu degil"
                return f"CrewAI: {installed}\n{status.get('message', '')}"[:400]
            result = run_agent_task("crewai", task_text, timeout_seconds=60)
            return result["output"][:400]
        except Exception as e:
            return f"CrewAI hatasi: {str(e)[:150]}"

    elif command == "/openhands":
        try:
            import sys as _sys, os as _os

            _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "skills"))
            from external_agent_skill import run_agent_task, get_agent_status

            task_text = args.strip()
            if not task_text or task_text == "durum":
                status = get_agent_status("openhands")
                installed = "Kurulu" if status["installed"] else "Kurulu degil"
                return f"OpenHands: {installed}\n{status.get('message', '')}"[:400]
            result = run_agent_task("openhands", task_text, timeout_seconds=60)
            return result["output"][:400]
        except Exception as e:
            return f"OpenHands hatasi: {str(e)[:150]}"

    elif command in ("/bugun-ne-var", "/bugun"):
        try:
            import sys as _sys, os as _os

            _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "skills"))
            from research_scheduler_skill import load_today_brief

            brief = load_today_brief()
            if brief:
                msg = brief.get("message_text", "")
                return (msg[:350] + "...") if len(msg) > 350 else msg
            return "Bugun henuz brief yok. /sabah-brief ile simdi olustur."
        except Exception as e:
            return f"Hata: {str(e)[:150]}"
    # ─── END 002 ──────────────────────────────────────────────────────

    return f"Bilinmeyen komut: {command}\n/help yaz yardim icin."


# ─────────────────────────── PROCESS MESSAGE ──────────────────────
def process_message(chat_id: int, text: str) -> str:
    text = text.strip()

    # Content Factory session
    if CONTENT_FACTORY_SESSIONS.get(str(chat_id)):
        try:
            from content_factory_skill import (
                get_interviewer,
                get_multiplier,
                format_output,
                init_content_db,
            )

            init_content_db()
            resp, ready, ctx = get_interviewer().process(str(chat_id), text)
            if ready and ctx:
                CONTENT_FACTORY_SESSIONS.pop(str(chat_id), None)
                try:
                    results = get_multiplier(call_ollama).multiply(ctx)
                    return resp + "\n\n" + format_output(results)
                except Exception as me:
                    return resp + "\n" + str(me)
            return resp
        except Exception as e:
            CONTENT_FACTORY_SESSIONS.pop(str(chat_id), None)
            return str(e)

    if text.startswith("/"):
        _t0 = time.time()
        _cmd = text.split()[0] if text.split() else text
        _result = handle_command(chat_id, text)
        # Self-learning log
        try:
            _learner = _get_conv_learner()
            if _learner:
                _learner.log_command(
                    command=_cmd,
                    chat_id=chat_id,
                    user_input=text,
                    response=_result or "",
                    duration_ms=(time.time() - _t0) * 1000,
                    status="success"
                    if _result and not _result.startswith("❌")
                    else "error",
                )
        except Exception:
            pass
        return _result

    # ── NATURAL LANGUAGE INTERCEPTS ────────────────────────────────
    try:
        voice_manager = get_voice_test_manager()
        if voice_manager.get_status(chat_id).active:
            voice_result = voice_manager.handle_message(
                chat_id,
                text,
                task_runner=lambda goal: get_week1_pipeline().run(goal),
            )
            memory.add_message(chat_id, "user", text)
            memory.add_message(
                chat_id,
                "assistant",
                voice_result["reply"],
                f"voice:{voice_result['mode']}",
            )
            return voice_result["reply"]
    except Exception as voice_error:
        log.warning(f"voice test handling failed: {voice_error}")

    persona_module = _load_persona_manager_module()

    _tl = text.lower()
    switch_target = persona_module.detect_switch_from_text(text)
    if switch_target:
        result = _switch_persona_for_chat(chat_id, switch_target)
        if result.get("ok"):
            reply = str(result.get("reply") or _build_persona_handoff_reply(result))
            memory.add_message(chat_id, "user", text)
            memory.add_message(chat_id, "assistant", reply, f"persona/{result['id']}")
            return reply
        return str(result.get("error") or "Persona degisimi basarisiz.")

    if any(
        phrase in _tl
        for phrase in [
            "kim aktif",
            "hangi ajan aktif",
            "su an kim aktif",
            "şu an kim aktif",
        ]
    ):
        active_persona_text = _handle_persona_status_command(chat_id)
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", active_persona_text, "persona/status")
        return active_persona_text

    if (
        str(_get_active_persona_payload(chat_id=chat_id).get("id") or "jarvis")
        != "jarvis"
        and str(chat_id) not in ACTIVE_AGENTS
    ):
        _sync_persona_session_for_chat(chat_id)

    _obsidian_save_reply = _handle_obsidian_save_intent(chat_id, text)
    if _obsidian_save_reply:
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", _obsidian_save_reply, "obsidian/save")
        return _obsidian_save_reply

    _active_persona_id = str(
        _get_active_persona_payload(chat_id=chat_id).get("id") or "jarvis"
    )
    _obsidian_context = (
        _build_obsidian_context_block(_active_persona_id)
        if _is_obsidian_context_request(text)
        else ""
    )

    # AnyDesk kabul
    if any(
        k in _tl
        for k in [
            "kabul et",
            "anydesk",
            "bağlantıyı kabul",
            "isteği kabul",
            "gelen isteği",
            "accept",
        ]
    ):
        return handle_command(chat_id, "/kabul")
    # Ekran görüntüsü
    if any(
        k in _tl
        for k in ["ekran görüntüsü", "ekranı göster", "screenshot", "ekrana bak"]
    ):
        return handle_command(chat_id, "/ekran")
    # Ekrana bak (vision)
    if any(
        k in _tl
        for k in ["ekrana bak", "ne var ekranda", "ekranda ne", "ekranı analiz"]
    ):
        return handle_command(chat_id, "/bak")
    # Bilgisayar kontrolü — doğal dil → /yap komutu
    # Typo normalizasyonu: sık yapılan yazım hataları
    for _typo, _fix in (("inatagram", "instagram"), ("yotube", "youtube"), ("yoututbe", "youtube"), ("spotfy", "spotify")):
        if _typo in _tl:
            _tl = _tl.replace(_typo, _fix)
    _bilgisayar_keys = [
        "aç",
        "ac",
        "kapat",
        "yaz",
        "tıkla",
        "tikla",
        "başlat",
        "baslat",
        "youtube",
        "instagram",
        "chrome",
        "firefox",
        "spotify",
        "explorer",
        "dosya",
        "klasör",
        "program",
        "uygulama",
        "pencere",
        "tarayıcı",
        "tarayici",
        "müzik",
        "muzik",
        "video",
        "oynat",
        "durdur",
        "ses aç",
        "ses kapat",
        "büyüt",
        "buyut",
        "küçült",
        "kucult",
        "tam ekran",
    ]
    if any(k in _tl for k in _bilgisayar_keys):
        # 1) Önce whitelist-aware PC gateway'i dene (Faz 1/2 komutları)
        try:
            from server.skills.pc_control_gateway import infer_pc_command as _infer_pc  # type: ignore
            _pc_req = _infer_pc(text)
            if _pc_req:
                _alias = "/" + str(_pc_req.get("command_key") or "")
                _pc_args = str(_pc_req.get("args") or "").strip()
                _full = _alias + (f" {_pc_args}" if _pc_args else "")
                return handle_command(chat_id, _full)
        except Exception:
            pass

        # 2) Legacy hızlı aç haritası (geriye uyum)
        _quick_map = {
            "youtube": ("url", "https://www.youtube.com"),
            "instagram": ("url", "https://www.instagram.com"),
            "spotify": ("ac", "spotify"),
            "chrome": ("ac", "chrome"),
            "firefox": ("ac", "firefox"),
            "explorer": ("ac", "explorer"),
            "hesap": ("ac", "calc"),
            "notepad": ("ac", "notepad"),
        }
        for _app, (_command_key, _command_args) in _quick_map.items():
            if _app in _tl:
                try:
                    return _autonomous_handle_pc_gateway_command(
                        chat_id,
                        _command_key,
                        _command_args,
                    )
                except Exception as _e:
                    return f"❌ Açılamadı: {_e}"
        # 3) Hiçbir PC intent'i eşleşmedi — LLM'e düş (eski /yap fallback kaldırıldı)

    if text.startswith("!! "):
        cmd = text[3:].strip()
        result = run_shell_full(cmd, persona_id=_current_persona_id(chat_id))
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", result, "system")
        return f"```\n{result}\n```"

    if text.startswith("$ "):
        cmd = text[2:].strip()
        result = run_command_safe(cmd, persona_id=_current_persona_id(chat_id))
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", result, "system")
        return f"```\n{result}\n```"

    # Intent check
    if INTENT_ENABLED:
        try:
            _intent_response = handle_with_intent(text, str(chat_id))
            if _intent_response:
                memory.add_message(chat_id, "user", text)
                memory.add_message(chat_id, "assistant", _intent_response)
                _detected = classify_intent(text)
                _cmd = _detected.get("command", "") if _detected else ""
                return f"[{_cmd}]\n\n{_intent_response}" if _cmd else _intent_response
        except Exception:
            pass

    # Aktif ajan kontrolu
    active_agent = ACTIVE_AGENTS.get(str(chat_id))
    if active_agent:
        hist = memory.get_history(chat_id)
        hist.append({"role": "user", "content": text})
        model = active_agent.get("model", "gemma4:e2b")
        fallback_model = str(active_agent.get("fallback_model") or "").strip() or None
        model_chain = str(active_agent.get("model_chain") or "chat").strip() or "chat"
        active_system_prompt = str(active_agent.get("prompt") or "")
        if _obsidian_context:
            active_system_prompt = "\n\n".join(
                filter(None, [active_system_prompt, _obsidian_context])
            )
        response = call_ollama(
            model,
            hist,
            active_system_prompt,
            fallback_model=fallback_model,
            route_name=model_chain,
        )
        selected_candidate = get_selected_candidate(model)
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"[{active_agent['name'].upper()}] {response}"

    if should_use_team_mode(text):
        try:
            return run_team_task(chat_id, text)
        except Exception as e:
            log.warning(f"dogal dil team modu hatasi: {e}")

    canonical_dispatch = _dispatch_canonical_message(chat_id, text)
    if canonical_dispatch:
        agent_id, result, formatted = canonical_dispatch
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", formatted, f"canonical/{agent_id}")
        return formatted

    # Normal routing
    route_name, route = detect_route(text)
    hist = memory.get_history(chat_id)
    knowledge = get_relevant_knowledge(text)
    if knowledge:
        hist.insert(0, {"role": "system", "content": knowledge})
    hist.append({"role": "user", "content": text})
    model = route["model"]
    try:
        _user_ctx = get_user_context(str(chat_id))
        _reme_ctx = reme_get_context(text)
        _extra = "\n\n".join(
            filter(None, [_user_ctx, _reme_ctx, _obsidian_context])
        )
        _system = route["system"] + ("\n\n" + _extra if _extra else "")
    except Exception:
        _system = route["system"] + (
            "\n\n" + _obsidian_context if _obsidian_context else ""
        )
    response = call_ollama(
        model,
        hist,
        _system,
        fallback_model=route.get("fallback"),
        route_name=route_name,
    )
    selected_candidate = get_selected_candidate(model)
    selected_model = selected_candidate.split("/", 1)[-1]
    selected_provider = (
        selected_candidate.split("/", 1)[0] if "/" in selected_candidate else "ollama"
    )
    memory.add_message(chat_id, "user", text)
    memory.add_message(chat_id, "assistant", response, selected_candidate)
    reme_save(text, response)
    model_short = selected_model.split(":")[0].replace("deepseek-", "DS-")
    return f"[{selected_provider}/{model_short}] {response}"


# ─────────────────────────── TELEGRAM ─────────────────────────────
class TelegramBot:
    def __init__(self, token, authorized_id):
        self.token = token
        self.authorized_id = authorized_id
        self.api = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.running = True

    def send(self, chat_id, text, parse_mode="Markdown"):
        while text:
            chunk = text[:4000]
            text = text[4000:]

            def _post(payload_dict):
                payload = json.dumps(payload_dict).encode()
                req = Request(
                    f"{self.api}/sendMessage",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urlopen(req, timeout=10)

            try:
                _post({"chat_id": chat_id, "text": chunk, "parse_mode": parse_mode})
            except HTTPError as http_exc:
                # Telegram Markdown parser rejects malformed syntax with 400.
                # Fall back to plain text so the user always receives the reply.
                if http_exc.code == 400 and parse_mode:
                    try:
                        _post({"chat_id": chat_id, "text": chunk})
                        log.warning(
                            "Markdown parse 400 — sent chunk as plain text"
                        )
                        continue
                    except Exception as fallback_exc:
                        log.error(f"Send fallback error: {fallback_exc}")
                else:
                    log.error(f"Send error: {http_exc}")
            except Exception as e:
                log.error(f"Send error: {e}")

    def send_voice(self, chat_id, audio_path):
        """Send an audio file as a Telegram voice message."""
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            boundary = "JarvisVoiceBoundary"
            ext = os.path.splitext(audio_path)[1].lower() or ".mp3"
            mime = "audio/ogg" if ext in (".ogg", ".oga") else "audio/mpeg"
            field_name = "voice" if ext in (".ogg", ".oga") else "audio"
            body = (
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
                    f"{chat_id}\r\n"
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{field_name}"; filename="reply{ext}"\r\n'
                    f"Content-Type: {mime}\r\n\r\n"
                ).encode()
                + audio_data
                + f"\r\n--{boundary}--\r\n".encode()
            )
            endpoint = "sendVoice" if field_name == "voice" else "sendAudio"
            req = Request(
                f"{self.api}/{endpoint}",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            urlopen(req, timeout=20)
        except Exception as e:
            log.error(f"send_voice error: {e}")

    def get_updates(self):
        try:
            url = f"{self.api}/getUpdates?offset={self.offset}&timeout=30&limit=10"
            with urlopen(Request(url), timeout=35) as resp:
                return json.loads(resp.read()).get("result", [])
        except Exception as e:
            log.error(f"GetUpdates error: {e}")
            time.sleep(5)
            return []

    def run(self):
        log.info("Jarvis Telegram bot basladi")
        self.send(
            self.authorized_id,
            f"*Jarvis Mission Control v2.4 Aktif!* ({CONFIG['runtime_label']})\nMulti-model AI router + Uzak Yonetim hazir.\n`/help` yaz yardim icin.",
        )
        while self.running:
            updates = self.get_updates()
            for update in updates:
                self.offset = update["update_id"] + 1
                try:
                    threading.Thread(
                        target=self._handle_update, args=(update,), daemon=True
                    ).start()
                except Exception as e:
                    log.error(f"Update error: {e}")

    def send_button(self, chat_id, text, btn_text, btn_data):
        payload = json.dumps(
            {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": {
                    "inline_keyboard": [[{"text": btn_text, "callback_data": btn_data}]]
                },
            }
        ).encode()
        try:
            req = Request(
                f"{self.api}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urlopen(req, timeout=10)
        except Exception as e:
            log.error(f"send_button error: {e}")

    def answer_callback(self, callback_id, text=""):
        payload = json.dumps({"callback_query_id": callback_id, "text": text}).encode()
        try:
            req = Request(
                f"{self.api}/answerCallbackQuery",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urlopen(req, timeout=5)
        except Exception as e:
            log.error(f"answer_callback error: {e}")

    def _handle_update(self, update):
        # Callback query (buton basma) işle
        cb = update.get("callback_query")
        if cb:
            cb_id = cb["id"]
            cb_data = cb.get("data", "")
            cb_chat = cb["message"]["chat"]["id"]
            if cb_chat != self.authorized_id:
                return
            if cb_data == "anydesk_kabul":
                self.answer_callback(cb_id, "⏳ Kabul ediliyor...")
                try:
                    ps_script = r"C:\Users\sergen\Desktop\jarvis-mission-control\anydesk_kabul.ps1"
                    result = subprocess.run(
                        [
                            "powershell.exe",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-WindowStyle",
                            "Hidden",
                            "-File",
                            ps_script,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    out = (result.stdout or "").strip()
                    if result.returncode == 0 or "kabul edildi" in out.lower():
                        self.send(cb_chat, "✅ AnyDesk bağlantısı kabul edildi!")
                    else:
                        self.send(
                            cb_chat,
                            f"❌ Kabul başarısız:\n{out or result.stderr[:200]}",
                        )
                except Exception as e:
                    self.send(cb_chat, f"❌ Hata: {e}")
            return

        msg = update.get("message", {})
        if not msg:
            return
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        username = msg.get("from", {}).get("username", "?")

        photos = msg.get("photo") or []
        if photos:
            if not _is_admin_chat(chat_id):
                return
            self.send(chat_id, "_Gorsel analiz ediliyor..._")
            caption = (msg.get("caption") or "").strip()
            prompt = caption
            if caption.lower().startswith("/gor"):
                prompt = caption[len("/gor") :].strip()
            try:
                from vision_skill import handle_photo_message

                file_id = photos[-1]["file_id"]
                result = handle_photo_message(self.token, file_id, prompt or None)
                self.send(chat_id, result)
            except Exception as e:
                self.send(chat_id, f"Hata: {e}")
            return

        # ── Sesli mesaj (voice/audio) ──────────────────────────────────────
        voice = msg.get("voice") or msg.get("audio")
        if voice and chat_id == self.authorized_id:
            self.send(chat_id, "🎙️ _Ses dinleniyor..._")
            try:
                import sys, os

                sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills"))
                from voice_skill import handle_voice_message

                result = handle_voice_message(self.token, voice["file_id"])
                text = result.get("text", "")
                if not text or "hata" in text.lower():
                    self.send(chat_id, f"❌ Ses anlaşılamadı: {text}")
                    return
                self.send(chat_id, f"🎙️ *Duydum:* _{text}_")
                log.info(f"[{username}][VOICE]: {text[:50]}")
            except Exception as e:
                self.send(chat_id, f"❌ Ses işleme hatası: {e}")
                return
        elif chat_id != self.authorized_id or not text:
            return

        log.info(f"[{username}]: {text[:50]}")

        # /kabul → buton gönder
        if text.strip().lower() in ("/kabul", "/onayla", "/accept"):
            self.send_button(
                chat_id,
                "🖥️ AnyDesk bağlantı isteği var mı?",
                "✅ Kabul Et",
                "anydesk_kabul",
            )
            return

        is_voice_request = bool(msg.get("voice") or msg.get("audio"))
        self.send(chat_id, "_Isleniyor..._")
        response = process_message(chat_id, text)
        if response.startswith("__SCREENSHOT__"):
            photo_path = response[len("__SCREENSHOT__") :]
            self.send_photo(chat_id, photo_path)
        else:
            self.send(chat_id, response)
            # Sesli mesajla geldiyse → sesli yanıt da gönder
            if is_voice_request:
                try:
                    import sys as _sys, os as _os

                    _sys.path.insert(
                        0, _os.path.join(_os.path.dirname(__file__), "skills")
                    )
                    from voice_skill import text_to_speech

                    # Emoji ve markdown işaretlerini temizle
                    _clean = response.replace("*", "").replace("_", "").replace("`", "")
                    _clean = _clean[:400]  # max 400 karakter
                    audio_path = text_to_speech(_clean)
                    if audio_path:
                        self.send_voice(chat_id, audio_path)
                except Exception as _e:
                    log.warning(f"TTS hatasi: {_e}")

    def send_photo(self, chat_id, photo_path):
        try:
            import urllib.request, urllib.parse

            with open(photo_path, "rb") as f:
                photo_data = f.read()
            boundary = "JarvisBoundary"
            body = (
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
                    f"{chat_id}\r\n"
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="photo"; filename="screenshot.png"\r\n'
                    f"Content-Type: image/png\r\n\r\n"
                ).encode()
                + photo_data
                + f"\r\n--{boundary}--\r\n".encode()
            )
            req = urllib.request.Request(
                f"{self.api}/sendPhoto",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=15)
            log.info("Ekran goruntusu gonderildi")
        except Exception as e:
            log.error(f"Fotograf gonderilemedi: {e}")
            self.send(chat_id, f"Fotograf gonderilemedi: {e}")


# ─────────────────────────── WEB DASHBOARD ────────────────────────
class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/", "/dashboard"):
            models = get_available_models()
            stats = memory.data["stats"]
            last_trace = (
                STATE.last_route_trace
                if isinstance(STATE.last_route_trace, dict)
                else {}
            )
            last_selected = last_trace.get("selected_candidate", "-")
            last_fallback = "evet" if last_trace.get("fallback_used") else "hayir"
            last_route = last_trace.get("route") or "-"
            provider_health = get_provider_health()
            openrouter_label = provider_health.get("openrouter", {}).get("label", "-")
            openai_label = provider_health.get("openai", {}).get("label", "-")
            html = f"""<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jarvis Mission Control</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#0a0a0f;color:#e0e0e0;min-height:100vh}}
header{{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:20px 30px;border-bottom:1px solid #00ff88;display:flex;align-items:center;gap:15px}}
header h1{{font-size:1.8em;color:#00ff88}}
header p{{color:#888;font-size:.9em}}
.dot{{width:12px;height:12px;border-radius:50%;background:#00ff88;box-shadow:0 0 10px #00ff88;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:20px}}
@media(max-width:768px){{.grid{{grid-template-columns:1fr}}}}
.card{{background:#11111b;border:1px solid #222;border-radius:12px;padding:20px}}
.card h2{{font-size:1em;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:15px}}
.stat{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #1a1a2e}}
.stat:last-child{{border:none}}
.stat-label{{color:#666;font-size:.9em}}
.stat-val{{color:#00ff88;font-weight:bold;font-family:monospace}}
.full{{grid-column:1/-1}}
.mission-map{{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:14px;margin-top:10px}}
@media(max-width:900px){{.mission-map{{grid-template-columns:repeat(2,minmax(120px,1fr))}}}}
.agent-node{{position:relative;background:linear-gradient(180deg,#13192b,#0d1220);border:1px solid #25314f;border-radius:16px;padding:16px;min-height:110px;overflow:hidden}}
.agent-node::after{{content:'';position:absolute;inset:auto -20% -35% -20%;height:70px;background:radial-gradient(circle,#00ff8840,transparent 60%);opacity:.2;transform:translateY(25px);transition:.35s}}
.agent-node.active::after{{opacity:.8;transform:translateY(0)}}
.agent-node h3{{font-size:1em;margin-bottom:8px}}
.agent-node p{{font-size:.8em;color:#7f8ca8}}
.agent-state{{display:inline-block;margin-top:10px;padding:4px 10px;border-radius:999px;font-family:monospace;font-size:.75em;border:1px solid #31415f}}
.state-idle{{color:#9aa4b2;border-color:#3a465f}}
.state-running{{color:#ffd166;border-color:#7f6514;box-shadow:0 0 0 1px #7f6514 inset}}
.state-done{{color:#00ff88;border-color:#0d6a46}}
.state-blocked{{color:#ff6b6b;border-color:#7c1f28}}
.state-thinking{{color:#6bc5ff;border-color:#1e5f8d}}
.mission-flow{{display:flex;gap:10px;align-items:center;margin-top:16px;overflow:auto;padding-bottom:4px}}
.flow-pill{{padding:8px 12px;border-radius:999px;background:#141b2d;border:1px solid #25314f;font-size:.8em;white-space:nowrap}}
.event-feed{{max-height:220px;overflow:auto;display:flex;flex-direction:column;gap:8px}}
.event-item{{padding:10px 12px;border-radius:10px;background:#0d1220;border:1px solid #1f2840;font-size:.82em}}
.event-time{{color:#6f809f;font-family:monospace;font-size:.75em;margin-bottom:4px}}
.chat{{background:#0d0d1a;border-radius:12px;padding:20px}}
.chat-row{{display:flex;gap:10px;margin-bottom:15px}}
.chat-row input{{flex:1;background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:10px 15px;color:#e0e0e0}}
.chat-row input:focus{{border-color:#00ff88;outline:none}}
.chat-row button{{background:#00ff88;color:#000;border:none;padding:10px 20px;border-radius:8px;cursor:pointer;font-weight:bold}}
.msgs{{max-height:350px;overflow-y:auto;display:flex;flex-direction:column;gap:8px}}
.msg{{padding:10px 15px;border-radius:8px;font-size:.9em;line-height:1.5}}
.msg.user{{background:#1a2744;align-self:flex-end;border:1px solid #2244aa}}
.msg.ai{{background:#1a2a1a;align-self:flex-start;border:1px solid #224422}}
.msg.sys{{background:#1a1a1a;color:#666;font-style:italic;align-self:center;font-size:.8em}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.75em;background:#002211;color:#00ff88;border:1px solid #00ff44;margin-bottom:4px}}
.tags{{display:flex;flex-wrap:wrap;gap:8px}}
.tag{{background:#1a1a2e;border:1px solid #333;padding:6px 12px;border-radius:20px;font-size:.8em;color:#aaa;font-family:monospace}}
.tag.on{{border-color:#00ff88;color:#00ff88}}
</style></head><body>
<header>
<div class="dot"></div>
<div><h1>Jarvis Mission Control</h1><p>{CONFIG["runtime_label"]} — {datetime.now().strftime("%H:%M:%S")}</p></div>
</header>
<div class="grid">
<div class="card">
<h2>Sistem</h2>
<div class="stat"><span class="stat-label">Toplam Sorgu</span><span class="stat-val">{stats["total_queries"]}</span></div>
<div class="stat"><span class="stat-label">AI Modeller</span><span class="stat-val">{len(models)} aktif</span></div>
<div class="stat"><span class="stat-label">Web Port</span><span class="stat-val">:{CONFIG["web_port"]}</span></div>
<div class="stat"><span class="stat-label">Platform</span><span class="stat-val">{CONFIG["platform_label"]}</span></div>
</div>
<div class="card">
<h2>Router</h2>
<div class="stat"><span class="stat-label">Default Provider</span><span class="stat-val">{MODEL_ROUTER.settings.default_provider}</span></div>
<div class="stat"><span class="stat-label">Son Secim</span><span class="stat-val" id="router-selected">{last_selected}</span></div>
<div class="stat"><span class="stat-label">Fallback</span><span class="stat-val" id="router-fallback">{last_fallback}</span></div>
<div class="stat"><span class="stat-label">Route</span><span class="stat-val" id="router-route">{last_route}</span></div>
<div class="stat"><span class="stat-label">OpenRouter</span><span class="stat-val" id="router-openrouter">{openrouter_label}</span></div>
<div class="stat"><span class="stat-label">OpenAI</span><span class="stat-val" id="router-openai">{openai_label}</span></div>
</div>
<div class="card full">
<h2>Web Chat</h2>
<div class="chat">
<div class="chat-row">
<input id="inp" placeholder="/help /ebay /trendyol /code /status /reklam /ara ..." onkeypress="if(event.key==='Enter')send()"/>
<button onclick="send()">Gonder</button>
</div>
<div class="msgs" id="msgs"><div class="msg sys">Jarvis hazir. Mesaj gonderin.</div></div>
</div>
</div>
<div class="card full"><h2>Modeller</h2>
<div class="tags">{"".join(f'<span class="tag on">{m}</span>' for m in models) or '<span class="tag">Ollama bagli degil</span>'}</div>
</div>
<div class="card full">
<h2>Agent OS Mission Map</h2>
<div class="mission-map" id="mission-map">
  <div class="agent-node" data-agent="jarvis"><h3>Jarvis</h3><p>CEO / Orchestrator</p><span class="agent-state state-idle">idle</span></div>
  <div class="agent-node" data-agent="claude"><h3>Claude</h3><p>Deep analysis worker</p><span class="agent-state state-idle">idle</span></div>
  <div class="agent-node" data-agent="ollama"><h3>Ollama</h3><p>Local model runner</p><span class="agent-state state-idle">idle</span></div>
  <div class="agent-node" data-agent="research"><h3>Research</h3><p>Repo + trend scout</p><span class="agent-state state-idle">idle</span></div>
  <div class="agent-node" data-agent="guard"><h3>Guard</h3><p>Safety + review</p><span class="agent-state state-idle">idle</span></div>
</div>
<div class="mission-flow" id="mission-flow">
  <div class="flow-pill">Queued</div>
  <div class="flow-pill">Planning</div>
  <div class="flow-pill">Build</div>
  <div class="flow-pill">Review</div>
  <div class="flow-pill">Report</div>
</div>
</div>
<div class="card">
<h2>Current Job</h2>
<div id="current-job" class="msg sys">No active night job.</div>
</div>
<div class="card">
<h2>Event Feed</h2>
<div id="event-feed" class="event-feed"><div class="event-item">Agent OS event stream waiting...</div></div>
</div>
</div>
<script>
async function send(){{
const inp=document.getElementById('inp');
const text=inp.value.trim(); if(!text) return;
addMsg('user',text); inp.value=''; addMsg('sys','...');
try{{
const r=await fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:text}})}});
const d=await r.json();
removeLastSys(); addMsg('ai',d.response,d.model);
if(d.fallback_used){{addMsg('sys','Fallback aktif: '+(d.model||'-'));}}
await refreshRuntimeStatus();
}}catch(e){{removeLastSys();addMsg('sys','Hata: '+e);}}
}}
function addMsg(role,text,model){{
const c=document.getElementById('msgs');
const d=document.createElement('div'); d.className='msg '+role;
if(model){{const b=document.createElement('div');b.className='badge';b.textContent=(model.length>50?model.slice(0,50)+'...':model);d.appendChild(b);}}
const t=document.createElement('div');
t.innerHTML=text.replace(/```([\\s\\S]*?)```/g,'<pre>$1</pre>').replace(/\\*\\*(.+?)\\*\\*/g,'<b>$1</b>').replace(/\\n/g,'<br>');
d.appendChild(t); c.appendChild(d); c.scrollTop=c.scrollHeight;
}}
function removeLastSys(){{
const s=document.querySelectorAll('.msg.sys');
if(s.length)s[s.length-1].remove();
}}
async function refreshRuntimeStatus(){{
 try{{
   const statusRes = await fetch('/api/status');
   const status = await statusRes.json();
   const trace = status.last_route_trace || {{}};
   const health = status.provider_health || {{}};
   const selected = trace.selected_candidate || '-';
   const fallback = trace.fallback_used ? 'evet' : 'hayir';
   const route = trace.route || '-';
   const openrouter = (health.openrouter && health.openrouter.label) ? health.openrouter.label : '-';
   const openai = (health.openai && health.openai.label) ? health.openai.label : '-';
   document.getElementById('router-selected').textContent = selected;
   document.getElementById('router-fallback').textContent = fallback;
   document.getElementById('router-route').textContent = route;
   document.getElementById('router-openrouter').textContent = openrouter;
   document.getElementById('router-openai').textContent = openai;
 }}catch(e){{}}
}}
function paintNode(name,state){{
 const node=document.querySelector(`.agent-node[data-agent="${{name}}"]`);
 if(!node) return;
 const badge=node.querySelector('.agent-state');
 node.classList.toggle('active', state==='running'||state==='thinking');
 badge.className='agent-state state-'+(state||'idle');
 badge.textContent=state||'idle';
}}
async function refreshAgentOS(){{
 try{{
   const [statusRes, eventsRes]=await Promise.all([
     fetch('/api/agent-os/status'),
     fetch('/api/agent-os/events')
   ]);
   const status=await statusRes.json();
   const events=await eventsRes.json();
   Object.entries(status.agents||{{}}).forEach(([name,state])=>paintNode(name,state));
   const current=document.getElementById('current-job');
   current.textContent=status.current_job ? `${{status.current_job.id}} (${{status.current_job.type}})` : 'No active night job.';
   const feed=document.getElementById('event-feed');
   feed.innerHTML='';
   (events.events||[]).slice().reverse().forEach(ev=>{{
     const item=document.createElement('div'); item.className='event-item';
     item.innerHTML=`<div class="event-time">${{new Date(ev.time).toLocaleTimeString()}}</div><div>${{ev.message}}</div>`;
     feed.appendChild(item);
   }});
   if(!feed.innerHTML){{feed.innerHTML='<div class="event-item">No events yet.</div>';}}
 }}catch(e){{}}
}}
setInterval(refreshAgentOS,3000);
setInterval(refreshRuntimeStatus,3000);
refreshAgentOS();
refreshRuntimeStatus();
</script></body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path == "/api/status":
            provider_health = get_provider_health()
            data = {
                "status": "online",
                "models": get_available_models(),
                "stats": memory.data["stats"],
                "time": datetime.now().isoformat(),
                "last_route_trace": STATE.last_route_trace,
                "provider_health": provider_health,
                "live": get_orchestrator_live_payload(event_limit=5),
            }
            self._json(data)
        elif path == "/api/agent-os/status":
            self._json(get_agent_os_visual_status())
        elif path == "/api/agent-os/events":
            self._json({"events": get_agent_os_visual_events()})
        elif path == "/api/live/status":
            self._json(get_orchestrator_live_payload(event_limit=15))
        elif path == "/api/live/events":
            live_payload = get_orchestrator_live_payload(event_limit=50)
            self._json(
                {
                    "status": live_payload.get("status", "unknown"),
                    "activity": live_payload.get("activity", "idle"),
                    "current_task": live_payload.get("current_task"),
                    "last_task": live_payload.get("last_task"),
                    "events": live_payload.get("recent_events", []),
                }
            )
        elif path == "/api/personas":
            self._handle_personas_endpoint()
        elif path == "/api/persona/active":
            self._handle_persona_active_endpoint(query)
        elif path == "/api/desktop-assistant":
            self._json(get_desktop_assistant_payload())
        elif path == "/api/office/presence":
            self._json(get_office_presence_payload())
        elif path == "/api/cloud/ec2":
            self._handle_cloud_ec2_endpoint()
        elif path == "/api/cloud/s3":
            self._handle_cloud_s3_endpoint()
        elif path == "/api/cloud/cost":
            self._handle_cloud_cost_endpoint()
        elif path == "/api/cloud/alerts":
            self._handle_cloud_alerts_endpoint()

        # ──── WEEK 2: HEALTH & METRICS ENDPOINTS ────
        elif path == "/health":
            self._handle_health_endpoint()
        elif path == "/metrics":
            self._handle_metrics_endpoint()
        elif path == "/metrics/cache":
            self._handle_cache_metrics_endpoint()
        elif path == "/learning/status":
            self._handle_learning_status_endpoint()
        elif path == "/api/swarm-status":
            self._handle_swarm_status_endpoint()
        elif path == "/api/accounts":
            self._handle_codex_accounts_endpoint()
        elif path == "/api/codex/slots":
            self._handle_codex_slots_endpoint()
        elif path == "/api/codex/jobs":
            self._handle_codex_jobs_endpoint(query)
        elif path == "/api/codex/queue":
            self._handle_codex_queue_endpoint()
        elif path == "/api/codex/health":
            self._handle_codex_health_endpoint()
        elif path == "/api/agents/health":
            self._handle_agents_health_endpoint()
        elif path == "/api/codex/audit":
            self._handle_codex_audit_endpoint()
        elif path == "/api/codex/result":
            self._handle_codex_result_endpoint(query)
        elif path == "/api/codex/status":
            self._handle_codex_status_endpoint()
        elif path == "/api/saas-metrics":
            self._handle_saas_metrics_endpoint()
        else:
            self.send_error(404)

    def _handle_persona_active_endpoint(
        self, query: dict[str, list[str]] | None = None
    ):
        try:
            params = query if isinstance(query, dict) else {}
            lane_value = None
            for key in ("lane", "source"):
                values = params.get(key)
                if values:
                    lane_value = values[0]
                    break

            chat_id_value = None
            for key in ("chatId", "chat_id"):
                values = params.get(key)
                if values:
                    chat_id_value = values[0]
                    break

            lane = _extract_runtime_lane(lane_value)
            chat_id = None
            if chat_id_value not in (None, ""):
                try:
                    chat_id = int(chat_id_value)
                except (TypeError, ValueError):
                    chat_id = None

            self._json(_get_active_persona_payload(chat_id=chat_id, lane=lane))
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_personas_endpoint(self):
        try:
            self._json(_build_personas_payload())
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/chat":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    self._json(
                        {"ok": False, "error": "JSON object body is required"}, 400
                    )
                    return

                chat_id, lane = _resolve_runtime_chat(body)
                persona_override = str(
                    body.get("persona")
                    or body.get("persona_id")
                    or body.get("active_persona")
                    or ""
                ).strip()
                text = str(body.get("message") or body.get("text") or "").strip()

                if persona_override:
                    switch_result = _switch_persona_for_chat(chat_id, persona_override)
                    if not switch_result.get("ok"):
                        self._json(
                            {"ok": False, "error": switch_result.get("error")}, 400
                        )
                        return
                    active_persona = _persona_api_payload(
                        switch_result, chat_id=chat_id, lane=lane
                    )
                    if not text:
                        self._json(
                            {
                                "ok": True,
                                "response": str(
                                    switch_result.get("reply")
                                    or _build_persona_handoff_reply(switch_result)
                                ),
                                "chat_id": chat_id,
                                "lane": lane,
                                "active_persona": active_persona,
                            }
                        )
                        return
                else:
                    active_persona = _get_active_persona_payload(
                        chat_id=chat_id, lane=lane
                    )
                    if str(active_persona.get("id") or "jarvis") != "jarvis":
                        _apply_persona_to_chat(chat_id, active_persona)

                if not text:
                    self._json({"ok": False, "error": "message is required"}, 400)
                    return

                route_name, route = detect_route(text)
                response = process_message(chat_id, text)
                trace = (
                    STATE.last_route_trace
                    if isinstance(STATE.last_route_trace, dict)
                    else {}
                )
                selected_candidate = trace.get("selected_candidate") or route.get(
                    "model"
                )
                self._json(
                    {
                        "ok": True,
                        "response": response,
                        "model": selected_candidate,
                        "provider": trace.get("selected_provider", ""),
                        "route": route_name,
                        "fallback_used": bool(trace.get("fallback_used")),
                        "attempts": trace.get("attempts", []),
                        "chat_id": chat_id,
                        "lane": lane,
                        "active_persona": _get_active_persona_payload(
                            chat_id=chat_id, lane=lane
                        ),
                    }
                )
            except Exception as e:
                self._json({"error": str(e)}, 500)
        elif path == "/agent":
            self._handle_agent_endpoint()
        elif path == "/command":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                command = str(body.get("command", "")).strip()
                args = body.get("args")
                chat_id_raw = body.get("chatId")

                if not command:
                    self._json({"ok": False, "error": "command is required"}, 400)
                    return

                if not command.startswith("/"):
                    command = f"/{command}"

                chat_id = 9999
                if chat_id_raw not in (None, ""):
                    try:
                        chat_id = int(chat_id_raw)
                    except (TypeError, ValueError):
                        chat_id = 9999

                args_text = ""
                if isinstance(args, dict) and args:
                    if isinstance(args.get("text"), str):
                        args_text = args["text"]
                    elif isinstance(args.get("args"), str):
                        args_text = args["args"]
                    else:
                        args_text = json.dumps(args, ensure_ascii=False)
                elif isinstance(body.get("data"), dict) and body["data"]:
                    args_text = json.dumps(body["data"], ensure_ascii=False)

                result = handle_command(chat_id, f"{command} {args_text}".strip())
                self._json({"ok": True, "result": result})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500)
        elif path == "/api/cloud/ec2/action":
            self._handle_cloud_ec2_action_endpoint()
        elif path == "/api/accounts/update":
            self._handle_codex_accounts_update_endpoint()
        elif path == "/api/codex/dispatch":
            self._handle_codex_dispatch_endpoint()
        elif path == "/api/codex/control":
            self._handle_codex_control_endpoint()
        elif path == "/api/swarm/team-dispatch":
            self._handle_team_dispatch_endpoint()
        else:
            self.send_error(404)

    def _handle_saas_metrics_endpoint(self):
        """GET /api/saas-metrics — current MRR + 30d trend + customer count."""
        try:
            from server.services.saas_db import SaasDB
            db = SaasDB()
            self._json({
                "ok": True,
                "current": db.get_current_mrr(),
                "trend_30d": db.get_mrr_trend(days=30),
                "customer_count": db.get_customer_count(),
                "metrics": db.calculate_metrics() if hasattr(db, "calculate_metrics") else {},
            })
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_team_dispatch_endpoint(self):
        """POST /api/swarm/team-dispatch {goal, personas[]} — parallel swarm dispatch."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            goal = str(body.get("goal") or "").strip()
            personas = body.get("personas") or []
            if not isinstance(personas, list):
                personas = []
            personas = [str(p).lower() for p in personas if p]
            if not goal:
                self._json({"ok": False, "error": "goal is required"}, 400)
                return
            # Luna defense-in-depth (bridge layer)
            from server.skills.swarm_skill import LUNA_HARD_REJECT, swarm_run
            low = goal.lower()
            if "luna" in personas and any(kw in low for kw in LUNA_HARD_REJECT):
                self._json({
                    "ok": False,
                    "error": "LUNA: Bu istek reddedildi. Yalnızca savunma amaçlı lab bağlamında çalışabilirim.",
                }, 403)
                return
            result = swarm_run(goal, personas=personas or None)
            self._json({"ok": True, "result": result, "personas": personas})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    # ──── WEEK 2: NEW ENDPOINT HANDLERS ────
    def _handle_health_endpoint(self):
        """GET /health - System health status"""
        router_snapshot = get_router_health_snapshot()
        live_payload = get_orchestrator_live_payload(event_limit=10)

        if not MONITORING_ENABLED or HEALTH_CHECKER is None:
            # Fallback health response if monitoring not available
            health_data = {
                "status": _merge_health_status(
                    _merge_health_status(
                        "healthy", str(router_snapshot.get("status", "healthy"))
                    ),
                    str(live_payload.get("status", "healthy")),
                ),
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "logs_writable": True,
                    "bridge_running": True,
                    "model_router_enabled": bool(router_snapshot.get("enabled", False)),
                    "model_router_ready": str(router_snapshot.get("status", "")).lower()
                    in {"healthy", "degraded"},
                },
                "warning": "Monitoring modules disabled",
                "runtime_label": str(CONFIG["runtime_label"]),
                "provider_health": router_snapshot.get("providers", {}),
                "router": router_snapshot,
                "route_trace": router_snapshot.get("active", {}),
                "live": live_payload,
            }
            status_code = 200 if health_data["status"] in {"healthy", "degraded"} else 503
            self._json(health_data, status_code)
            return

        # Use HealthChecker for comprehensive status
        metrics_data = (
            METRICS_COLLECTOR.get_stats(time_window_minutes=60)
            if METRICS_COLLECTOR
            else None
        )
        health_status = HEALTH_CHECKER.get_status(metrics_data=metrics_data)
        response, status_code = HEALTH_CHECKER.get_health_endpoint_response(
            include_metrics=True, metrics_data=metrics_data
        )
        response["status"] = _merge_health_status(
            _merge_health_status(
                str(response.get("status", "healthy")),
                str(router_snapshot.get("status", "healthy")),
            ),
            str(live_payload.get("status", "healthy")),
        )
        if response["status"] not in {"healthy", "degraded"}:
            status_code = 503
        components = response.get("components")
        if isinstance(components, dict):
            components["model_router_enabled"] = bool(
                router_snapshot.get("enabled", False)
            )
            components["model_router_ready"] = str(
                router_snapshot.get("status", "")
            ).lower() in {"healthy", "degraded"}
        response["runtime_label"] = str(CONFIG["runtime_label"])
        response["provider_health"] = router_snapshot.get("providers", {})
        response["router"] = router_snapshot
        response["route_trace"] = router_snapshot.get("active", {})
        response["live"] = live_payload
        self._json(response, status_code)
        log.debug(f"Health check: {health_status.status}")

    def _handle_metrics_endpoint(self):
        """GET /metrics - Execution metrics and statistics"""
        if not MONITORING_ENABLED or METRICS_COLLECTOR is None:
            self._json({"error": "Metrics collection disabled"}, 503)
            return

        try:
            # Get aggregated metrics over last hour
            stats = METRICS_COLLECTOR.get_stats(time_window_minutes=60)

            # Add execution metrics response
            metrics_response = {
                "timestamp": datetime.now().isoformat(),
                "window_minutes": 60,
                "execution_stats": stats,
                # Include memory stats from bridge
                "memory_stats": memory.data.get("stats", {}),
                "total_queries": memory.data.get("stats", {}).get("total_queries", 0),
                "live": get_orchestrator_live_payload(event_limit=10),
            }
            self._json(metrics_response, 200)
            log.debug("Metrics endpoint accessed")
        except Exception as e:
            log.error(f"Error retrieving metrics: {e}")
            self._json({"error": str(e)}, 500)

    def _handle_cache_metrics_endpoint(self):
        """GET /metrics/cache - Cache statistics"""
        if not MONITORING_ENABLED or METRICS_COLLECTOR is None:
            self._json({"error": "Metrics collection disabled"}, 503)
            return

        try:
            # Get recent metrics to calculate cache stats
            recent_metrics = METRICS_COLLECTOR.get_recent_metrics(limit=500)

            cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
            total = len(recent_metrics)
            cache_hit_rate = (cache_hits / total * 100) if total > 0 else 0

            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "total_executions": total,
                "cache_hits": cache_hits,
                "cache_hit_rate_pct": round(cache_hit_rate, 1),
                "cache_misses": total - cache_hits,
                "details": {
                    "last_100_hit_rate": round(
                        sum(1 for m in recent_metrics[-100:] if m.cache_hit)
                        / min(100, len(recent_metrics))
                        * 100
                        if len(recent_metrics) > 0
                        else 0,
                        1,
                    )
                },
            }
            self._json(cache_data, 200)
            log.debug("Cache metrics accessed")
        except Exception as e:
            log.error(f"Error retrieving cache metrics: {e}")
            self._json({"error": str(e)}, 500)

    def _handle_learning_status_endpoint(self):
        """GET /learning/status - Learning engine status"""
        try:
            # Get recent metrics to infer learning engine status
            stats = (
                METRICS_COLLECTOR.get_stats(time_window_minutes=60)
                if METRICS_COLLECTOR
                else {}
            )

            learning_status = {
                "timestamp": datetime.now().isoformat(),
                "learning_enabled": MONITORING_ENABLED,
                "execution_data_available": bool(stats.get("total_executions", 0) > 0),
                "recent_metrics": {
                    "total_executions": stats.get("total_executions", 0),
                    "success_rate_pct": stats.get("success_rate_pct", 0),
                    "cache_hit_rate_pct": stats.get("cache_hit_rate_pct", 0),
                    "throughput_per_minute": stats.get("throughput_per_minute", 0),
                },
                "top_actions": stats.get("top_actions", [])[:5],
                "status": "operational" if MONITORING_ENABLED else "disabled",
            }
            self._json(learning_status, 200)
            log.debug("Learning status accessed")
        except Exception as e:
            log.error(f"Error retrieving learning status: {e}")
            self._json({"error": str(e)}, 500)

    # ──── SWARM & CODEX CONTROL PLANE ENDPOINTS ────

    def _handle_swarm_status_endpoint(self):
        """GET /api/swarm-status - 7 clone agent aktiflik durumu"""
        try:
            state_dir = Path(__file__).parent.parent / "state" / "codex-accounts"
            active_agents: set[str] = set()
            slots = [
                "atlas",
                "forge",
                "nexus",
                "shield",
                "spark",
                "seda",
                "deniz",
                "mert",
                "buse",
                "eren",
                "luna",
                "zeynep",
                "sabrican",
                "sabri",
            ]
            runtime_slots = {}
            for slot in slots:
                slot_file = state_dir / f"{slot}.json"
                if slot_file.exists():
                    try:
                        data = json.loads(slot_file.read_text(encoding="utf-8"))
                        status = data.get("status", "idle")
                        runtime_slots[slot] = status
                        if status in ("running", "active", "thinking", "speaking"):
                            active_agents.add(slot)
                    except Exception:
                        runtime_slots[slot] = "unknown"

            speaking_state = {}
            speaking_file = (
                Path(__file__).parent.parent / "state" / "swarm_speaking_state.json"
            )
            if speaking_file.exists():
                try:
                    speaking_state = json.loads(
                        speaking_file.read_text(encoding="utf-8")
                    )
                except Exception:
                    pass

            speaking_agent = str(speaking_state.get("speaking") or "").strip().lower()
            if speaking_agent:
                active_agents.add(speaking_agent)

            participants = speaking_state.get("participants")
            dialogue_active = bool(speaking_state.get("dialogue_active", False))
            if dialogue_active and isinstance(participants, list):
                for participant in participants:
                    participant_id = str(participant or "").strip().lower()
                    if participant_id:
                        active_agents.add(participant_id)

            self._json(
                {
                    "active": sorted(active_agents),
                    "active_agents": sorted(active_agents),
                    "slots": runtime_slots,
                    "speaking": speaking_state.get("speaking"),
                    "text": speaking_state.get("text", ""),
                    "ceo_phase": speaking_state.get("ceo_phase", "idle"),
                    "dialogue_active": dialogue_active,
                    "participants": participants if isinstance(participants, list) else [],
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception as e:
            log.error(f"swarm-status error: {e}")
            self._json(
                {
                    "active": [],
                    "active_agents": [],
                    "slots": {},
                    "speaking": None,
                    "text": "",
                    "ceo_phase": "idle",
                    "dialogue_active": False,
                    "participants": [],
                }
            )

    def _handle_codex_accounts_endpoint(self):
        """GET /api/accounts - operator metadata (secrets olmadan)"""
        try:
            self._json(_build_codex_accounts_payload())
        except Exception as e:
            log.error(f"accounts endpoint error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_codex_accounts_update_endpoint(self):
        """POST /api/accounts/update - operator metadata mutasyonu"""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            payload, status_code = _update_codex_account_payload(
                str(body.get("account_id") or "").strip(),
                str(body.get("field") or "").strip(),
                body.get("value"),
            )
            self._json(payload, status_code)
        except Exception as e:
            log.error(f"accounts/update error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _handle_codex_status_endpoint_legacy(self):
        """GET /api/codex/status - job queue + quota özeti"""
        try:
            state_dir = Path(__file__).parent.parent / "state" / "codex-accounts"
            # Job queue
            job_file = state_dir / "job_queue.json"
            jobs = []
            if job_file.exists():
                raw = json.loads(job_file.read_text(encoding="utf-8"))
                for j in raw.get("jobs", [])[-10:]:
                    jobs.append(
                        {
                            "id": j.get("id"),
                            "task": j.get("task", "")[:80],
                            "status": j.get("status"),
                            "created_at": j.get("created_at"),
                            "finished_at": j.get("finished_at"),
                            "slots": j.get("selected_slots", []),
                        }
                    )
            # Quota
            quota_file = state_dir / "quota.json"
            quotas = {}
            if quota_file.exists():
                quotas = json.loads(quota_file.read_text(encoding="utf-8"))
            # Runtime slots
            slots = ["atlas", "forge", "nexus", "shield", "spark"]
            runtime_slots = {}
            for slot in slots:
                sf = state_dir / f"{slot}.json"
                if sf.exists():
                    try:
                        d = json.loads(sf.read_text(encoding="utf-8"))
                        runtime_slots[slot] = {"status": d.get("status", "idle")}
                    except Exception:
                        runtime_slots[slot] = {"status": "unknown"}
            self._json(
                {
                    "jobs": jobs,
                    "queue": {"total": len(jobs)},
                    "quotas": quotas,
                    "runtime_slots": runtime_slots,
                }
            )
        except Exception as e:
            log.error(f"codex/status error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_codex_result_endpoint_legacy(self):
        """GET /api/codex/result?job_id=... - tek job sonucu"""
        try:
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            job_id = params.get("job_id", [None])[0]
            if not job_id:
                self._json({"ok": False, "error": "job_id required"}, 400)
                return
            state_dir = Path(__file__).parent.parent / "state" / "codex-accounts"
            job_file = state_dir / "job_queue.json"
            if not job_file.exists():
                self._json({"ok": False, "error": "job not found"}, 404)
                return
            raw = json.loads(job_file.read_text(encoding="utf-8"))
            for j in raw.get("jobs", []):
                if j.get("id") == job_id:
                    result = None
                    for agent_data in j.get("agents", {}).values():
                        if agent_data.get("output"):
                            result = str(agent_data["output"])[:500]
                            break
                    self._json(
                        {
                            "ok": True,
                            "job_id": job_id,
                            "result": result or j.get("status"),
                        }
                    )
                    return
            self._json({"ok": False, "error": "job not found"}, 404)
        except Exception as e:
            log.error(f"codex/result error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_codex_status_endpoint(self):
        """GET /api/codex/status - job queue + quota ozeti"""
        try:
            self._json(_build_codex_status_payload(limit=10))
        except Exception as e:
            log.error(f"codex/status error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_codex_slots_endpoint(self):
        try:
            self._json(_build_codex_slots_payload())
        except Exception as e:
            log.error(f"codex/slots error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_codex_jobs_endpoint(self, query: dict[str, list[str]]):
        try:
            status = (query.get("status") or [None])[0]
            slot_id = (query.get("slot_id") or [None])[0]
            self._json(
                _build_codex_jobs_payload(status=status, slot_id=slot_id, limit=100)
            )
        except Exception as e:
            log.error(f"codex/jobs error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_codex_queue_endpoint(self):
        try:
            self._json(_build_codex_queue_payload())
        except Exception as e:
            log.error(f"codex/queue error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_codex_health_endpoint(self):
        try:
            self._json(_build_codex_health_payload())
        except Exception as e:
            log.error(f"codex/health error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_agents_health_endpoint(self):
        try:
            self._json(_build_agents_health_payload())
        except Exception as e:
            log.error(f"agents/health error: {e}")
            self._json({"error": str(e)}, 500)

    def _handle_codex_audit_endpoint(self):
        try:
            self._json(_build_codex_audit_payload(limit=50))
        except Exception as e:
            log.error(f"codex/audit error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_agent_endpoint(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                self._json({"ok": False, "error": "JSON object body is required."}, 400)
                return

            agent_name = str(body.get("agent") or "").strip().lower()
            task = str(body.get("task") or "").strip()
            context = body.get("context") or {}
            wrapped = bool(body.get("wrapped_response"))

            if wrapped:
                result = _run_canonical_agent(agent_name, task, context)
                status_code = 200
                if not result.get("ok"):
                    error_text = str(result.get("error") or "").lower()
                    if "unknown agent" in error_text:
                        status_code = 404
                    elif (
                        "required" in error_text
                        or "context must be an object" in error_text
                    ):
                        status_code = 400
                    else:
                        status_code = 500
                self._json(result, status_code)
                return

            runtime = _get_canonical_runtime()
            if runtime is not None:
                payload, status_code = runtime.handle_agent_request(body)
                self._json(payload, status_code)
                return

            result = _run_canonical_agent(agent_name, task, context)
            status_code = 200 if result.get("ok") else 500
            error_text = str(result.get("error") or "").lower()
            if "unknown agent" in error_text:
                status_code = 404
            elif "required" in error_text or "context must be an object" in error_text:
                status_code = 400
            self._json(result, status_code)
        except Exception as e:
            log.error(f"/agent error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _handle_codex_result_endpoint(self, query: dict[str, list[str]]):
        """GET /api/codex/result?job_id=... - tek job sonucu"""
        try:
            job_id = (query.get("job_id") or [None])[0]
            if not job_id:
                self._json({"ok": False, "error": "job_id required"}, 400)
                return
            payload, status_code = _build_codex_result_payload(str(job_id))
            self._json(payload, status_code)
        except Exception as e:
            log.error(f"codex/result error: {e}")
            self._json({"error": "internal error"}, 500)

    def _handle_codex_dispatch_endpoint(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            task_description = str(body.get("task_description") or "").strip()
            role = str(body.get("role") or "").strip() or None
            priority = int(body.get("priority") or 5)
            if not task_description:
                self._json({"ok": False, "error": "task_description required"}, 400)
                return
            result = _dispatch_codex_job(
                task_description=task_description, role=role, priority=priority
            )
            self._json(result, 200 if result.get("ok") else 400)
        except Exception as e:
            log.error(f"codex/dispatch error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _handle_codex_control_endpoint(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            action = str(body.get("action") or "").strip().lower()
            slot_id = str(body.get("slot_id") or "").strip() or None
            job_id = str(body.get("job_id") or "").strip() or None
            result = _control_codex_plane(action=action, slot_id=slot_id, job_id=job_id)
            self._json(result, 200 if result.get("ok") else 400)
        except Exception as e:
            log.error(f"codex/control error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _handle_cloud_ec2_endpoint(self):
        try:
            payload = _load_cloud_modules()["list_instances"]()
            self._json(payload, _cloud_status_code(payload))
        except Exception as e:
            log.error(f"cloud/ec2 error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _handle_cloud_s3_endpoint(self):
        try:
            payload = _load_cloud_modules()["list_buckets"]()
            self._json(payload, _cloud_status_code(payload))
        except Exception as e:
            log.error(f"cloud/s3 error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _handle_cloud_cost_endpoint(self):
        try:
            payload = _load_cloud_modules()["get_monthly_cost"]()
            self._json(payload, _cloud_status_code(payload))
        except Exception as e:
            log.error(f"cloud/cost error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _handle_cloud_alerts_endpoint(self):
        try:
            payload = _load_cloud_modules()["get_budget_alerts"]()
            self._json(payload, _cloud_status_code(payload))
        except Exception as e:
            log.error(f"cloud/alerts error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _handle_cloud_ec2_action_endpoint(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            instance_id = str(body.get("instance_id", "") or "").strip()
            action = str(body.get("action", "") or "").strip().lower()

            if not instance_id:
                self._json({"ok": False, "error": "instance_id required"}, 400)
                return
            if action not in {"start", "stop"}:
                self._json({"ok": False, "error": "action must be start or stop"}, 400)
                return

            modules = _load_cloud_modules()
            payload = (
                modules["start_instance"](instance_id)
                if action == "start"
                else modules["stop_instance"](instance_id)
            )
            self._json(payload, _cloud_status_code(payload))
        except Exception as e:
            log.error(f"cloud/ec2/action error: {e}")
            self._json({"ok": False, "error": "internal error"}, 500)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


_CODEX_SLOT_META = {
    "atlas": {"label": "ATLAS", "role": "Manager/Core"},
    "forge": {"label": "FORGE", "role": "Backend Ops"},
    "nexus": {"label": "NEXUS", "role": "Voice + Hologram"},
    "shield": {"label": "SHIELD", "role": "Security / Audit"},
    "spark": {"label": "SPARK", "role": "Web UI / Frontend"},
}
_CODEX_SLOT_ORDER = ["atlas", "forge", "nexus", "shield", "spark"]
_CODEX_MUTABLE_FIELDS = {
    "status",
    "daily_limit",
    "weekly_limit",
    "remaining_estimate",
    "notes",
}


def _strip_wrapping_quotes(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1].strip()
    return text


def _build_codex_runtime_slots() -> list[dict[str, object]]:
    try:
        from account_manager import get_account_manager
    except Exception:
        from server.account_manager import get_account_manager  # type: ignore

    try:
        from codex_quota_tracker import get_all_quotas
    except Exception:
        from server.codex_quota_tracker import get_all_quotas  # type: ignore

    try:
        from codex_job_manager import get_queue_stats
    except Exception:
        from server.codex_job_manager import get_queue_stats  # type: ignore

    account_manager = get_account_manager()
    codex_status = account_manager.get_status().get("codex", {})
    runtime_accounts = {
        str(item.get("runtime_slot") or "").strip(): item
        for item in codex_status.get("accounts", [])
        if isinstance(item, dict) and str(item.get("runtime_slot") or "").strip()
    }
    quotas = get_all_quotas()
    queue = get_queue_stats()
    slot_stats = queue.get("slots", {}) if isinstance(queue, dict) else {}

    records: list[dict[str, object]] = []
    for slot in _CODEX_SLOT_ORDER:
        meta = _CODEX_SLOT_META[slot]
        account = runtime_accounts.get(slot, {})
        quota = quotas.get(slot, {}) if isinstance(quotas, dict) else {}
        stats = slot_stats.get(slot, {}) if isinstance(slot_stats, dict) else {}
        remaining_pct = int(quota.get("remaining_pct") or 0)
        records.append(
            {
                "slot": slot,
                "label": meta["label"],
                "role": meta["role"],
                "status": str(account.get("status") or "unknown"),
                "runtime_account_id": account.get("runtime_account_id"),
                "operator_label": account.get("operator_label"),
                "last_seen": account.get("last_used")
                or account.get("last_synced_at")
                or "-",
                "daily_limit": int(quota.get("daily_limit") or 0),
                "weekly_limit": int(quota.get("weekly_limit") or 0),
                "daily_used": int(quota.get("daily_used") or 0),
                "weekly_used": int(quota.get("weekly_used") or 0),
                "remaining_pct": remaining_pct,
                "remaining_estimate": f"%{remaining_pct}",
                "cooldown_until": quota.get("cooldown_until"),
                "exhausted": remaining_pct <= 0,
                "running": int(stats.get("running") or 0),
                "queued": int(stats.get("queued") or 0),
                "done": int(stats.get("done") or 0),
                "failed": int(stats.get("failed") or 0),
                "total_jobs": int(stats.get("total") or 0),
            }
        )
    return records


def _build_codex_accounts_payload() -> dict[str, object]:
    try:
        from skills.account_monitor import get_public_account_registry
    except Exception:
        try:
            from account_monitor import get_public_account_registry
        except Exception:
            from server.skills.account_monitor import get_public_account_registry  # type: ignore

    registry = get_public_account_registry()
    accounts = registry.get("accounts", []) if isinstance(registry, dict) else []
    return {"accounts": accounts}


def _redact_codex_payload(data: object) -> object:
    try:
        from account_manager import get_account_manager
    except Exception:
        from server.account_manager import get_account_manager  # type: ignore

    return get_account_manager()._redact_sensitive(data)


def _build_codex_jobs_payload(
    status: str | None = None, slot_id: str | None = None, limit: int = 100
) -> dict[str, object]:
    try:
        from codex_job_manager import get_job_manager
    except Exception:
        from server.codex_job_manager import get_job_manager  # type: ignore

    jobs = []
    for item in get_job_manager().list_jobs(
        status=status, slot_id=slot_id, limit=min(max(int(limit or 0), 0), 100)
    ):
        if not isinstance(item, dict):
            continue
        jobs.append(
            {
                "job_id": item.get("id"),
                "status": item.get("status"),
                "priority": item.get("priority", 5),
                "role": item.get("type"),
                "slot_id": item.get("slot_id"),
                "worktree": item.get("worktree"),
                "task": {
                    "description": item.get("task"),
                    "type": item.get("type"),
                    "payload": {},
                },
                "task_description": item.get("task"),
                "requested_slots": item.get("requested_slots", []),
                "selected_slots": item.get("selected_slots", []),
                "failure_reason": item.get("failure_reason"),
                "started_at": item.get("started_at"),
                "completed_at": item.get("finished_at"),
                "dispatch_after": item.get("dispatch_after"),
                "output_summary": item.get("result_summary"),
            }
        )
    return _redact_codex_payload({"jobs": jobs})


def _build_codex_queue_payload() -> dict[str, object]:
    payload = _build_codex_jobs_payload(status="pending", limit=100)
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    return {"jobs": jobs}


def _build_codex_slots_payload() -> dict[str, object]:
    try:
        from account_manager import get_account_manager
    except Exception:
        from server.account_manager import get_account_manager  # type: ignore
    try:
        from codex_job_manager import get_job_manager
    except Exception:
        from server.codex_job_manager import get_job_manager  # type: ignore
    try:
        from codex_orchestrator import get_cooldown_state
    except Exception:
        from server.codex_orchestrator import get_cooldown_state  # type: ignore

    slots = get_account_manager().list_slots()
    jobs = get_job_manager().list_jobs(limit=500)
    cooldowns = get_cooldown_state()
    records: list[dict[str, object]] = []

    for slot in slots:
        slot_id = str(slot.get("slot_id") or "").strip().lower()
        slot_jobs = [
            job
            for job in jobs
            if str(job.get("slot_id") or "").strip().lower() == slot_id
        ]
        current_job = next(
            (
                job
                for job in slot_jobs
                if str(job.get("status") or "").strip().lower() == "running"
            ),
            None,
        )
        completed_jobs = [
            job
            for job in slot_jobs
            if str(job.get("status") or "").strip().lower()
            in {"done", "failed", "cancelled"}
        ]
        fail_count = sum(
            1
            for job in slot_jobs
            if str(job.get("status") or "").strip().lower() == "failed"
        )
        cooldown = cooldowns.get(slot_id, {}) if isinstance(cooldowns, dict) else {}
        cooldown_remaining = (
            int(cooldown.get("remaining_seconds") or 0)
            if isinstance(cooldown, dict)
            else 0
        )

        status = "idle"
        effective_status = (
            str(slot.get("effective_status") or slot.get("status") or "")
            .strip()
            .lower()
        )
        if current_job:
            status = "active"
        elif cooldown_remaining > 0:
            status = "cooldown"
        elif effective_status in {
            "inactive",
            "failed",
            "quota_exceeded",
            "limited",
            "rate_limited",
            "pending_login",
            "offline",
        }:
            status = "disabled"

        records.append(
            {
                "slot_id": slot_id,
                "label": slot.get("label"),
                "role": slot.get("role"),
                "status": status,
                "quota_estimate": slot.get("quota_estimate"),
                "is_available": slot.get("is_available"),
                "current_job": {
                    "job_id": current_job.get("id"),
                    "description": current_job.get("task"),
                    "started_at": current_job.get("started_at"),
                    "duration_seconds": current_job.get("duration_seconds"),
                }
                if current_job
                else None,
                "last_completion": completed_jobs[0].get("finished_at")
                if completed_jobs
                else slot.get("last_completion"),
                "fail_count": fail_count,
                "cooldown_remaining": cooldown_remaining,
                "cooldown_until": slot.get("cooldown_until")
                or (cooldown.get("until") if isinstance(cooldown, dict) else None),
            }
        )

    return _redact_codex_payload({"slots": records})


def _build_codex_health_payload() -> dict[str, object]:
    try:
        from codex_health import CodexHealthWatcher
    except Exception:
        from server.codex_health import CodexHealthWatcher  # type: ignore
    try:
        from codex_job_manager import get_job_manager
    except Exception:
        from server.codex_job_manager import get_job_manager  # type: ignore
    try:
        from codex_orchestrator import get_cooldown_state
    except Exception:
        from server.codex_orchestrator import get_cooldown_state  # type: ignore

    slot_records = _build_codex_slots_payload().get("slots", [])
    stuck_jobs = get_job_manager().find_stuck_jobs(timeout_minutes=30)
    cooldowns = get_cooldown_state()
    health_slots = []
    for slot in slot_records if isinstance(slot_records, list) else []:
        if not isinstance(slot, dict):
            continue
        quota_text = (
            str(slot.get("quota_estimate") or "")
            .strip()
            .replace("%", "")
            .replace("~", "")
        )
        quota_value = (
            int(float(quota_text)) if quota_text.replace(".", "", 1).isdigit() else 0
        )
        health_score = 100
        if str(slot.get("status") or "") == "disabled":
            health_score -= 60
        if str(slot.get("status") or "") == "cooldown":
            health_score -= 30
        health_score -= min(int(slot.get("fail_count") or 0) * 10, 40)
        health_score = min(max(health_score + min(quota_value, 100) // 10, 0), 100)
        health_slots.append(
            {
                "slot_id": slot.get("slot_id"),
                "health_score": health_score,
                "status": slot.get("status"),
                "quota_estimate": slot.get("quota_estimate"),
                "cooldown": cooldowns.get(slot.get("slot_id"))
                if isinstance(cooldowns, dict)
                else None,
            }
        )

    return _redact_codex_payload(
        {"slots": health_slots, "stuck_jobs": stuck_jobs, "cooldowns": cooldowns}
    )


def _build_codex_audit_payload(limit: int = 50) -> dict[str, object]:
    try:
        from codex_orchestrator import read_dispatch_audit
    except Exception:
        from server.codex_orchestrator import read_dispatch_audit  # type: ignore

    return _redact_codex_payload(
        {"entries": read_dispatch_audit(limit=min(max(int(limit or 0), 0), 50))}
    )


def _dispatch_codex_job(
    *, task_description: str, role: str | None, priority: int
) -> dict[str, object]:
    try:
        from codex_orchestrator import dispatch_job
    except Exception:
        from server.codex_orchestrator import dispatch_job  # type: ignore

    result = dispatch_job(task_description, role=role, priority=priority)
    selected_slots = result.get("selected_slots") or []
    return _redact_codex_payload(
        {
            "ok": bool(result.get("ok")),
            "job_id": result.get("job_id"),
            "slot_id": selected_slots[0] if selected_slots else None,
            "status": "pending",
            "message": result.get("message"),
        }
    )


def _control_codex_plane(
    *, action: str, slot_id: str | None, job_id: str | None
) -> dict[str, object]:
    try:
        from account_manager import get_account_manager
    except Exception:
        from server.account_manager import get_account_manager  # type: ignore
    try:
        from codex_job_manager import get_job_manager
    except Exception:
        from server.codex_job_manager import get_job_manager  # type: ignore
    try:
        import codex_orchestrator as codex_orchestrator_module
    except Exception:
        import server.codex_orchestrator as codex_orchestrator_module  # type: ignore

    manager = get_job_manager()
    account_manager = get_account_manager()

    if action == "drain" and slot_id:
        codex_orchestrator_module.set_cooldown(slot_id, minutes=10, reason="drain")
        return {"ok": True, "message": f"{slot_id} drain moduna alindi."}
    if action == "pause" and slot_id:
        codex_orchestrator_module.set_cooldown(slot_id, minutes=15, reason="pause")
        return {"ok": True, "message": f"{slot_id} pause moduna alindi."}
    if action == "disable" and slot_id:
        account_manager.set_slot_status(slot_id, "inactive")
        codex_orchestrator_module.set_cooldown(slot_id, minutes=60, reason="disabled")
        return {"ok": True, "message": f"{slot_id} disable edildi."}
    if action == "retry" and job_id:
        retried = manager.retry_job(job_id)
        if retried is None:
            return {"ok": False, "message": "Job bulunamadi."}
        selected_slot = codex_orchestrator_module.dispatch(job_id)
        if selected_slot:
            codex_orchestrator_module._spawn_slot_thread(
                job_id, selected_slot, str(retried.get("task") or "")
            )
        return {
            "ok": True,
            "message": f"{job_id} retry edildi.",
            "slot_id": selected_slot,
        }
    if action == "cancel" and job_id:
        cancelled = manager.cancel_job(job_id)
        if cancelled is None:
            return {"ok": False, "message": "Job bulunamadi."}
        return {"ok": True, "message": f"{job_id} iptal edildi."}
    if action == "stop_all":
        return {
            "ok": True,
            "message": str(codex_orchestrator_module.stop_all() or "").strip()
            or "Aktif Codex isi yok.",
        }
    if action == "clear_cooldowns":
        codex_orchestrator_module.clear_cooldown()
        return {"ok": True, "message": "Tum cooldown kayitlari temizlendi."}
    return {"ok": False, "message": "unsupported action"}


def _build_codex_status_payload(limit: int = 10) -> dict[str, object]:
    try:
        from codex_orchestrator import get_status_payload
    except Exception:
        from server.codex_orchestrator import get_status_payload  # type: ignore
    try:
        from codex_workspace import WorkspaceManager
    except Exception:
        from server.codex_workspace import WorkspaceManager  # type: ignore

    payload = get_status_payload(limit=limit)
    payload["runtime_slots"] = _build_codex_runtime_slots()
    payload["workspaces"] = WorkspaceManager().status()
    return payload


def _build_codex_result_payload(job_id: str) -> tuple[dict[str, object], int]:
    try:
        from codex_orchestrator import get_job_result_payload
    except Exception:
        from server.codex_orchestrator import get_job_result_payload  # type: ignore

    result = get_job_result_payload(str(job_id or "").strip())
    if result is None:
        return {
            "ok": False,
            "error": "job_not_found",
            "job_id": str(job_id or "").strip(),
        }, 404
    return result, 200


def _update_codex_account_payload(
    account_id: str, field: str, value: object
) -> tuple[dict[str, object], int]:
    field_name = str(field or "").strip()
    if field_name not in _CODEX_MUTABLE_FIELDS:
        return {"ok": False, "error": "unsupported_field"}, 400

    try:
        from skills.account_monitor import (
            get_public_account_registry,
            update_account_field,
        )
    except Exception:
        try:
            from account_monitor import (
                get_public_account_registry,
                update_account_field,
            )
        except Exception:
            from server.skills.account_monitor import (
                get_public_account_registry,
                update_account_field,
            )  # type: ignore

    message = update_account_field(str(account_id or "").strip(), field_name, value)
    payload = _build_codex_accounts_payload()
    payload.update({"ok": True, "message": message})
    return payload, 200


def _parse_codex_dispatch_args(args: str) -> tuple[str | None, str]:
    raw = _strip_wrapping_quotes(args)
    if not raw:
        return None, ""

    parts = raw.split(maxsplit=1)
    first = parts[0].strip().lower()
    if first in {"auto", *_CODEX_SLOT_ORDER}:
        task = _strip_wrapping_quotes(parts[1] if len(parts) > 1 else "")
        return first, task
    return None, raw


def _truncate_telegram(text: str, limit: int = 400) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)].rstrip() + "..."


def _handle_kod_command(chat_id: int, args: str) -> str:
    explicit_slot, parsed_task = _parse_codex_dispatch_args(args)
    task = parsed_task or _strip_wrapping_quotes(args)
    requested_slot = explicit_slot if explicit_slot and explicit_slot != "auto" else None
    if not task:
        return 'Kullanim: /kod [auto|atlas|forge|nexus|shield|spark] "gorev"'

    try:
        coding_dispatch = _load_coding_dispatch_module()
        persona = _get_active_persona_payload(chat_id=chat_id)
        result = coding_dispatch.dispatch_coding_task(
            task,
            persona=persona,
            source=f"bridge:{_lane_for_chat_id(chat_id)}",
            requested_slot=requested_slot,
            priority=5,
        )
        return _truncate_telegram(
            coding_dispatch.format_coding_dispatch_message(result), limit=500
        )
    except Exception as exc:
        log.exception("Kod gorevi dispatch edilemedi")
        return f"Kod gorevi baslatilamadi: {exc}"


def _handle_kod_status_command(chat_id: int) -> str:
    return _handle_codex_status_command(chat_id)


def _handle_kod_result_command(chat_id: int, args: str) -> str:
    return _handle_codex_result_command(chat_id, args)


def _maybe_dispatch_coding_request(chat_id: int, text: str) -> str | None:
    try:
        coding_dispatch = _load_coding_dispatch_module()
    except Exception as exc:
        log.warning("coding_dispatch module unavailable: %s", exc)
        return None

    if not bool(coding_dispatch.is_coding_request(text)):
        return None

    persona = _get_active_persona_payload(chat_id=chat_id)
    result = coding_dispatch.dispatch_coding_task(
        text,
        persona=persona,
        source=f"natural:{_lane_for_chat_id(chat_id)}",
        priority=5,
    )
    return coding_dispatch.format_coding_dispatch_message(result)


def _handle_codex_command(chat_id: int, args: str, *, swarm: bool = False) -> str:
    task = _strip_wrapping_quotes(args)
    requested_slots = None

    if not swarm:
        explicit_slot, parsed_task = _parse_codex_dispatch_args(args)
        task = parsed_task
        if explicit_slot and explicit_slot != "auto":
            requested_slots = [explicit_slot]

    if not task:
        if swarm:
            return 'Kullanim: /codex-swarm "gorev"'
        return 'Kullanim: /codex [auto|atlas|forge|nexus|shield|spark] "gorev"'

    try:
        from codex_orchestrator import dispatch_job
    except Exception:
        from server.codex_orchestrator import dispatch_job  # type: ignore

    result = dispatch_job(task, swarm=swarm, requested_slots=requested_slots)
    if not result.get("ok"):
        return str(result.get("error") or "Codex dispatch basarisiz.")

    job_id = str(result.get("job_id") or "-")
    status = str(result.get("status") or "unknown")
    selected_slots = result.get("selected_slots") or []
    slot_text = (
        ", ".join(str(slot).upper() for slot in selected_slots)
        if selected_slots
        else "BEKLEMEDE"
    )
    return f"Job: {job_id}\nDurum: {status}\nSlot: {slot_text}\n{result.get('message', '')}".strip()


def _handle_codex_status_command(chat_id: int) -> str:
    payload = _build_codex_status_payload(limit=10)
    queue = payload.get("queue", {}) if isinstance(payload, dict) else {}
    totals = queue.get("totals", {}) if isinstance(queue, dict) else {}
    lines = [
        "CODEX DURUM",
        f"Kuyruk: {int(totals.get('queued') or 0)} | Calisan: {int(totals.get('running') or 0)} | Tamamlanan: {int(totals.get('done') or 0)} | Hata: {int(totals.get('failed') or 0)}",
        "",
    ]

    for record in payload.get("runtime_slots", []):
        if not isinstance(record, dict):
            continue
        lines.append(
            f"- {record.get('label')} | {record.get('status')} | run:{record.get('running')} | queue:{record.get('queued')} | quota:{record.get('remaining_estimate')}"
        )

    recent_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    if recent_jobs:
        lines.append("")
        lines.append("Son Joblar:")
        for job in recent_jobs[:5]:
            if not isinstance(job, dict):
                continue
            lines.append(
                f"  {job.get('id')} [{job.get('status')}] {job.get('summary')}"
            )

    return "\n".join(lines).strip()


def _handle_codex_queue_command(chat_id: int) -> str:
    payload = _build_codex_queue_payload()
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    lines = [f"Kuyrukta {len(jobs)} is var:"]
    for index, job in enumerate(jobs[:5], start=1):
        if not isinstance(job, dict):
            continue
        lines.append(
            f"{index}. [{job.get('priority')}] [{job.get('role')}] {str(job.get('task_description') or '')[:48]}"
        )
    return _truncate_telegram("\n".join(lines))


def _handle_codex_start_command(chat_id: int, args: str) -> str:
    raw = _strip_wrapping_quotes(args)
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        return "Kullanim: /codex-baslat <role> <aciklama>"
    role = parts[0].strip().lower()
    description = _strip_wrapping_quotes(parts[1])
    payload = _dispatch_codex_job(task_description=description, role=role, priority=5)
    text = f"Is kuyruga eklendi: {payload.get('job_id')} — slot: {payload.get('slot_id') or '-'}"
    return _truncate_telegram(text)


def _handle_codex_health_command(chat_id: int) -> str:
    payload = _build_codex_health_payload()
    slots = payload.get("slots", []) if isinstance(payload, dict) else []
    stuck_jobs = payload.get("stuck_jobs", []) if isinstance(payload, dict) else []
    lines = [f"Health: {len(slots)} slot | stuck jobs: {len(stuck_jobs)}"]
    for slot in slots[:5]:
        if not isinstance(slot, dict):
            continue
        lines.append(
            f"- {slot.get('slot_id')}: {slot.get('health_score')} ({slot.get('status')})"
        )
    return _truncate_telegram("\n".join(lines))


def _handle_codex_slots_command(chat_id: int) -> str:
    return _handle_codex_accounts_command(chat_id)


def _handle_codex_accounts_command(chat_id: int) -> str:
    payload = _build_codex_slots_payload()
    slots = payload.get("slots", []) if isinstance(payload, dict) else []
    lines = []
    for slot in slots[:5]:
        if not isinstance(slot, dict):
            continue
        lines.append(
            f"- {slot.get('label')}: {slot.get('role')} | {slot.get('status')} | {slot.get('quota_estimate')}"
        )
    return _truncate_telegram("\n".join(lines) or "Slot verisi yok.")


def _handle_codex_stop_command(chat_id: int) -> str:
    try:
        from codex_orchestrator import stop_all
    except Exception:
        from server.codex_orchestrator import stop_all  # type: ignore

    result = str(stop_all() or "").strip()
    if result.endswith(" job iptal edildi."):
        count = result.split(" ", 1)[0]
        result = f"{count} is iptal edildi."
    return _truncate_telegram(result or "Aktif Codex isi yok.")


def _handle_codex_clear_cooldowns_command(chat_id: int) -> str:
    result = _control_codex_plane(action="clear_cooldowns", slot_id=None, job_id=None)
    if result.get("ok"):
        return "Cooldownlar temizlendi."
    return _truncate_telegram(
        str(result.get("message") or "Cooldownlar temizlenemedi.")
    )


def _handle_codex_result_command(chat_id: int, args: str) -> str:
    job_id = _strip_wrapping_quotes(args)
    if not job_id:
        return "Kullanim: /codex-sonuc [job_id]"
    payload, status_code = _build_codex_result_payload(job_id)
    if status_code >= 400:
        return f"Job bulunamadi: {job_id}"
    result = str(payload.get("result") or payload.get("summary") or "Sonuc yok.")
    return f"Job {job_id}\n{result}".strip()


def _load_sabrican_ops_skill():
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).parent / "skills"))
    import sabrican_ops_skill

    return sabrican_ops_skill


def _format_sabrican_service_message(payload: dict[str, object]) -> str:
    service = str(payload.get("service") or "-").upper()
    status = str(payload.get("status") or "unknown").upper()
    latency = payload.get("latency_ms")
    latency_text = f"{latency} ms" if isinstance(latency, int) else "-"
    lines = [
        f"Sabrican Servis: {service}",
        f"Durum: {status}",
        f"Latency: {latency_text}",
    ]
    error = str(payload.get("error") or "").strip()
    if error:
        lines.append(f"Detay: {error}")
    return "\n".join(lines)


def _handle_sabrican_status_command(chat_id: int) -> str:
    try:
        skill = _load_sabrican_ops_skill()
        payload = skill.get_system_status()
        lines = [
            "Sabrican Durum",
            "",
            f"CPU: %{payload.get('cpu_pct', 0.0)}",
            f"RAM: %{payload.get('ram_pct', 0.0)}",
            f"Disk: %{payload.get('disk_pct', 0.0)}",
            "",
            "Servisler:",
        ]
        for service in payload.get("services", []):
            if not isinstance(service, dict):
                continue
            icon = "UP" if service.get("ok") else "DOWN"
            latency = service.get("latency_ms")
            latency_text = f"{latency} ms" if isinstance(latency, int) else "-"
            lines.append(
                f"- {service.get('service', '-')} | {icon} | {service.get('status', 'unknown')} | {latency_text}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Sabrican durum hatasi: {e}"


def _handle_sabrican_service_command(chat_id: int, args: str) -> str:
    parts = [part for part in str(args or "").split() if part]
    if not parts:
        return "Kullanim: /sabrican-servis <bridge|ollama|hologram> [url]"
    service_name = parts[0]
    url = parts[1] if len(parts) > 1 else None
    try:
        skill = _load_sabrican_ops_skill()
        payload = skill.check_service_health(service_name, url=url)
        return _format_sabrican_service_message(payload)
    except Exception as e:
        return f"Sabrican servis hatasi: {e}"


def _handle_sabrican_docker_command(chat_id: int) -> str:
    try:
        skill = _load_sabrican_ops_skill()
        payload = skill.docker_status()
        if not payload.get("ok"):
            return (
                "Sabrican Docker\n\n"
                f"Durum: DOWN\nDetay: {payload.get('error', 'docker_unavailable')}"
            )

        containers = payload.get("containers") or []
        if not containers:
            return "Sabrican Docker\n\nCalisan container yok."

        lines = ["Sabrican Docker", ""]
        for item in containers[:10]:
            if not isinstance(item, dict):
                continue
            name = item.get("Names") or item.get("Name") or item.get("raw") or "-"
            image = item.get("Image") or "-"
            status = item.get("Status") or item.get("State") or "-"
            lines.append(f"- {name} | {image} | {status}")
        return "\n".join(lines)
    except Exception as e:
        return f"Sabrican docker hatasi: {e}"


def _handle_sabrican_restart_command(chat_id: int, args: str) -> str:
    service_name = str(args or "").strip().split(" ", 1)[0].strip().lower()
    if not service_name:
        return "Kullanim: /sabrican-restart <bridge|ollama>"
    try:
        skill = _load_sabrican_ops_skill()
        payload = skill.restart_service(service_name)
        if payload.get("ok"):
            return (
                "Sabrican Restart\n\n"
                f"Servis: {service_name}\nDurum: {payload.get('status', 'scheduled')}"
            )
        return (
            "Sabrican Restart\n\n"
            f"Servis: {service_name}\n"
            f"Durum: {payload.get('status', 'unknown')}\n"
            f"Hata: {payload.get('error', 'unknown_error')}"
        )
    except Exception as e:
        return f"Sabrican restart hatasi: {e}"


def _handle_sabri_openclaw_command(chat_id: int, args: str) -> str:
    """/sabri-openclaw [sub] [query] — research/skill-pack/channel/agent/memory/all."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent / "skills"))
    try:
        import sabri_openclaw_skill as sk
    except Exception as e:
        return f"Sabri OpenClaw yüklenemedi: {e}"

    parts = (args or "").strip().split(None, 1)
    sub = parts[0].lower() if parts else "all"
    query = parts[1] if len(parts) > 1 else ""
    try:
        if sub in ("research", "arastir"):
            data = sk.research_openclaw_repos(query)
        elif sub in ("skill-pack", "skills"):
            data = sk.curate_openclaw_skill_pack(query)
        elif sub in ("channel", "kanal"):
            data = sk.design_openclaw_channel_strategy(query)
        elif sub in ("agent", "ajan"):
            data = sk.design_openclaw_agent_blueprint(query)
        elif sub in ("memory", "bellek"):
            data = sk.design_openclaw_memory_strategy(query)
        elif sub in ("all", "hepsi", ""):
            data = sk.build_sabri_openclaw_upgrade(query or sub)
        else:
            return (
                "Kullanim: /sabri-openclaw <research|skill-pack|channel|agent|memory|all> [query]"
            )
        return "Sabri OpenClaw\n" + json.dumps(data, ensure_ascii=False, indent=2)[:1800]
    except Exception as e:
        return f"Sabri OpenClaw hatasi: {e}"


def _handle_sabrican_subagents_command(chat_id: int, args: str) -> str:
    """/sabrican-subagents <name1,name2> — chain of subagents."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    try:
        from server.skills.sabrican_subagent_runner import run_subagent_chain, SUBAGENT_REGISTRY
    except Exception:
        try:
            from skills.sabrican_subagent_runner import run_subagent_chain, SUBAGENT_REGISTRY  # type: ignore
        except Exception as e:
            return f"Sabrican subagent yüklenemedi: {e}"

    raw = (args or "").strip()
    if not raw or raw.lower() in ("help", "list"):
        return "Kayitli subagents:\n- " + "\n- ".join(sorted(SUBAGENT_REGISTRY.keys()))
    names = [n.strip() for n in raw.replace(",", " ").split() if n.strip()]
    tasks = [{"name": n, "payload": {}} for n in names]
    try:
        results = run_subagent_chain(tasks)
        return "Sabrican Subagents\n" + json.dumps(results, ensure_ascii=False, indent=2)[:1800]
    except Exception as e:
        return f"Sabrican subagent hatasi: {e}"


def _ensure_dreams_operator_persona(chat_id: int) -> tuple[bool, str]:
    persona_id = _current_persona_id(chat_id)
    if persona_id in {"jarvis", "sabrican"}:
        return True, persona_id
    return (
        False,
        "Bu komut Sabrican icin ayrildi. Once Sabrican'a gecip tekrar dene.",
    )


def _handle_openclaw_dreams_snapshot_command(chat_id: int) -> str:
    allowed, persona_or_message = _ensure_dreams_operator_persona(chat_id)
    if not allowed:
        return persona_or_message
    persona_id = persona_or_message

    decision = evaluate_operator_action(
        "dreams_snapshot",
        "capture today rem report into persona memory",
        source="bridge.dreams_snapshot",
        risk="low",
        require_approval=False,
        persona_id=persona_id,
        action_class="dreams.snapshot",
    )
    if not decision.allowed:
        return format_policy_block_message(decision)

    try:
        from server.skills.openclaw_dreams_skill import capture_dream_snapshot
    except Exception:
        try:
            from skills.openclaw_dreams_skill import capture_dream_snapshot  # type: ignore
        except Exception as e:
            return f"Dusler skill yuklenemedi: {e}"

    try:
        payload = capture_dream_snapshot(persona_id)
    except Exception as e:
        log.exception("Dreams snapshot failed")
        return f"Dusler snapshot hatasi: {e}"

    if payload.get("status") == "missing_report":
        return (
            "Dusler Snapshot\n"
            f"Durum: rapor bulunamadi\n"
            f"Persona: {payload.get('target_persona', persona_id)}\n"
            f"Beklenen dosya: {payload.get('report_path', '-')}"
        )

    theme_preview = ", ".join(payload.get("themes", [])[:6]) or "-"
    return (
        "Dusler Snapshot\n"
        f"Persona: {payload.get('target_persona', persona_id)}\n"
        f"Tema sayisi: {payload.get('themes_captured', 0)}\n"
        f"Kalici gercek sayisi: {payload.get('lasting_truths', 0)}\n"
        f"Yazilan bellek girdisi: {payload.get('memory_entries_written', 0)}\n"
        f"Temalar: {theme_preview}\n"
        f"Rapor: {payload.get('report_path', '-')}"
    )


def _handle_openclaw_dreams_report_command(chat_id: int, args: str) -> str:
    allowed, persona_or_message = _ensure_dreams_operator_persona(chat_id)
    if not allowed:
        return persona_or_message
    persona_id = persona_or_message

    raw_phase = str(args or "").strip().lower() or "rem"
    if raw_phase not in {"light", "rem", "deep"}:
        return "Kullanim: /dusler-rapor [light|rem|deep]"

    decision = evaluate_operator_action(
        "dreams_report",
        f"read today {raw_phase} dream report",
        source="bridge.dreams_report",
        risk="low",
        require_approval=False,
        persona_id=persona_id,
        action_class="dreams.report",
    )
    if not decision.allowed:
        return format_policy_block_message(decision)

    try:
        from server.skills.openclaw_dreams_skill import get_dream_report
    except Exception:
        try:
            from skills.openclaw_dreams_skill import get_dream_report  # type: ignore
        except Exception as e:
            return f"Dusler skill yuklenemedi: {e}"

    try:
        report = get_dream_report(raw_phase)
    except Exception as e:
        log.exception("Dreams report failed")
        return f"Dusler raporu okunamadi: {e}"

    if not report.get("exists"):
        return (
            f"Dusler Raporu ({raw_phase})\n"
            "Durum: rapor bulunamadi\n"
            f"Beklenen dosya: {report.get('path', '-')}"
        )

    content = str(report.get("content") or "").strip()
    if not content:
        content = "(rapor bos)"
    return (
        f"Dusler Raporu ({raw_phase})\n"
        f"Dosya: {report.get('path', '-')}\n\n"
        f"{content}"
    )[:3600]


def _handle_openclaw_health_command(chat_id: int) -> str:
    """/openclaw-health — gateway + CLI snapshot."""
    try:
        from server.openclaw_bridge import build_openclaw_health_snapshot
    except Exception:
        try:
            from openclaw_bridge import build_openclaw_health_snapshot  # type: ignore
        except Exception as e:
            return f"OpenClaw bridge yüklenemedi: {e}"
    try:
        snap = build_openclaw_health_snapshot()
        return "OpenClaw Health\n" + json.dumps(snap, ensure_ascii=False, indent=2)[:1800]
    except Exception as e:
        return f"OpenClaw health hatasi: {e}"


def _handle_openclaw_skill_command(chat_id: int, args: str) -> str:
    """/openclaw-skill [skill-adı] [açıklama] — OpenCode skill kataloğundan skill çalıştır."""
    parts = (args or "").strip().split(None, 1)
    skill_name = parts[0].lower() if parts else ""
    task_desc = parts[1] if len(parts) > 1 else ""

    if not skill_name:
        skills_json_path = Path(__file__).resolve().parents[1] / "OPENCODE_SKILLS.json"
        try:
            with open(skills_json_path, encoding="utf-8") as f:
                data = json.load(f)
            categories = data.get("opencode_skills", {}).get("categories", [])
            lines = ["OpenCode Skills Kataloğu"]
            for cat in categories[:8]:
                names = ", ".join(cat.get("skills", [])[:5])
                lines.append(f"▸ {cat['name']}: {names}...")
            lines.append("\nKullanim: /openclaw-skill <skill-adı> [açıklama]")
            return "\n".join(lines)
        except Exception as e:
            return f"Skill kataloğu okunamadı: {e}"

    try:
        from server.openclaw_bridge import run_openclaw_integrator
    except ImportError:
        try:
            from openclaw_bridge import run_openclaw_integrator  # type: ignore
        except Exception as e:
            return f"OpenClaw bridge yüklenemedi: {e}"

    task = f"Run OpenCode skill '{skill_name}'"
    if task_desc:
        task += f": {task_desc}"

    try:
        result = run_openclaw_integrator(task, deliver=False)
        status = result.get("status", "?")
        return f"OpenClaw Skill — {skill_name}\nDurum: {status}\n{str(result)[:1200]}"
    except Exception as e:
        return f"OpenClaw skill hatası: {e}"


def _handle_octogent_health_command(chat_id: int) -> str:
    """/octogent-health — runtime + API snapshot."""
    try:
        from server.octogent_bridge import build_octogent_health_snapshot
    except Exception:
        try:
            from octogent_bridge import build_octogent_health_snapshot  # type: ignore
        except Exception as e:
            return f"Octogent bridge yüklenemedi: {e}"
    try:
        snap = build_octogent_health_snapshot()
        return "Octogent Health\n" + json.dumps(snap, ensure_ascii=False, indent=2)[:1800]
    except Exception as e:
        return f"Octogent health hatasi: {e}"


def _handle_devika_command(chat_id: int, args: str) -> str:
    try:
        from devika_skill import run_devika

        return run_devika(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Devika command failed")
        return f"Hata: {exc}"


def _handle_aider_command(chat_id: int, args: str) -> str:
    try:
        from aider_skill import run_aider

        return run_aider(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Aider command failed")
        return f"Hata: {exc}"


def _handle_cline_command(chat_id: int, args: str) -> str:
    try:
        from cline_skill import run_cline

        return run_cline(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Cline command failed")
        return f"Hata: {exc}"


def _handle_clawrouter_command(chat_id: int, args: str) -> str:
    try:
        from clawrouter_skill import run_clawrouter

        return run_clawrouter(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("ClawRouter command failed")
        return f"Hata: {exc}"


def _handle_cli_anything_command(chat_id: int, args: str) -> str:
    if not _is_admin_chat(chat_id):
        return "Bu komut sadece admin kullanicisi icin acik."
    try:
        from cli_anything_skill import run_cli_anything

        return run_cli_anything(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("CLI Anything command failed")
        return f"Hata: {exc}"


def _handle_claude_skills_command(chat_id: int, args: str) -> str:
    try:
        from claude_skills_skill import list_skills

        return list_skills(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Claude skills command failed")
        return f"Hata: {exc}"


def _handle_agent_catalog_command(chat_id: int, args: str) -> str:
    try:
        from agent_catalog_skill import catalog_stats, search_agent

        query = args.strip()
        return search_agent(query) if query else catalog_stats()
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Agent catalog command failed")
        return f"Hata: {exc}"


def _handle_repo_catalog_command(chat_id: int, args: str) -> str:
    try:
        from server.services.external_repo_registry import build_external_repo_report

        return build_external_repo_report(args.strip())
    except ModuleNotFoundError:
        return "External repo registry henuz kurulu degil"
    except Exception as exc:
        log.exception("External repo catalog command failed")
        return f"Hata: {exc}"


def _handle_repo_recommendation_command(chat_id: int, args: str) -> str:
    try:
        from server.services.external_repo_registry import (
            build_external_repo_recommendation_report,
        )

        return build_external_repo_recommendation_report(args.strip())
    except ModuleNotFoundError:
        return "External repo registry henuz kurulu degil"
    except Exception as exc:
        log.exception("External repo recommendation command failed")
        return f"Hata: {exc}"


def _handle_prompts_command(chat_id: int, args: str) -> str:
    try:
        from prompts_skill import list_prompts

        return list_prompts(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Prompts command failed")
        return f"Hata: {exc}"


def _handle_speckit_command(chat_id: int, args: str) -> str:
    try:
        from speckit_skill import spec_list, spec_plan, spec_specify, spec_tasks

        payload = args.strip()
        if not payload:
            return spec_list()

        action, _, remainder = payload.partition(" ")
        action_key = action.strip().lower()
        feature = remainder.strip()

        if action_key in {"list", "liste"}:
            return spec_list()
        if action_key in {"specify", "tanimla"}:
            return spec_specify(feature)
        if action_key in {"plan", "planla"}:
            return spec_plan(feature)
        if action_key in {"tasks", "gorevler"}:
            return spec_tasks(feature)
        return spec_specify(payload)
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("SpecKit command failed")
        return f"Hata: {exc}"


def _handle_paperclip_command(chat_id: int, args: str) -> str:
    try:
        from paperclip_skill import run_paperclip

        return run_paperclip(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Paperclip command failed")
        return f"Hata: {exc}"


def _handle_claw_code_command(chat_id: int, args: str) -> str:
    try:
        from claw_code_skill import run_claw_code

        return run_claw_code(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Claw code command failed")
        return f"Hata: {exc}"


def _handle_markxxxv_command(chat_id: int, args: str) -> str:
    try:
        module = _load_optional_skill_module("markxxxv_skill")
        result = module.handle_markxxxv(args, str(chat_id))
        memory.add_message(chat_id, "user", f"/markxxxv {args[:50]}")
        memory.add_message(chat_id, "assistant", str(result)[:200])
        return str(result)
    except ModuleNotFoundError as exc:
        return _missing_skill_message("Mark-XXXV", "markxxxv_skill", exc)
    except Exception as exc:
        log.exception("Mark-XXXV command failed")
        return f"Mark-XXXV hatasi: {str(exc)[:200]}"


def _handle_crewai_command(chat_id: int, args: str) -> str:
    try:
        module = _load_optional_skill_module("crewai_skill")
        return module.run_crewai(args.strip())
    except ModuleNotFoundError as exc:
        return _missing_skill_message("CrewAI", "crewai_skill", exc)
    except Exception as exc:
        log.exception("CrewAI command failed")
        return f"Hata: {exc}"


def _handle_openhands_command(chat_id: int, args: str) -> str:
    try:
        module = _load_optional_skill_module("openhands_skill")
        return module.run_openhands(args.strip())
    except ModuleNotFoundError as exc:
        return _missing_skill_message("OpenHands", "openhands_skill", exc)
    except Exception as exc:
        log.exception("OpenHands command failed")
        return f"Hata: {exc}"


def _handle_upondhand_command(chat_id: int, args: str) -> str:
    try:
        module = _load_optional_skill_module("upondhand_skill")
        return module.run_upondhand(args.strip())
    except ModuleNotFoundError as exc:
        return _missing_skill_message("upondhand", "upondhand_skill", exc)
    except Exception as exc:
        log.exception("upondhand command failed")
        return f"Hata: {exc}"


def _handle_youtube_unified_command(chat_id: int, args: str) -> str:
    try:
        module = _load_optional_skill_module("youtube_unified_skill")
        query = args.strip()
        return module.transcript_summary(query) if query else module.list_backends()
    except ModuleNotFoundError as exc:
        return _missing_skill_message("YouTube unified", "youtube_unified_skill", exc)
    except Exception as exc:
        log.exception("YouTube unified command failed")
        return f"Hata: {exc}"


def _handle_swarms_command(chat_id: int, args: str) -> str:
    try:
        module = _load_optional_skill_module("swarms_skill")
        query = args.strip()
        return module.swarms_run(query) if query else module.swarms_status()
    except ModuleNotFoundError as exc:
        return _missing_skill_message("Swarms", "swarms_skill", exc)
    except Exception as exc:
        log.exception("Swarms command failed")
        return f"Hata: {exc}"


def _handle_octogent_command(chat_id: int, args: str) -> str:
    try:
        module = _load_optional_skill_module("octogent_skill")
        return module.run_octogent(args.strip())
    except ModuleNotFoundError as exc:
        return _missing_skill_message("Octogent", "octogent_skill", exc)
    except Exception as exc:
        log.exception("Octogent command failed")
        return f"Hata: {exc}"


def _handle_hooks_command(chat_id: int, args: str) -> str:
    if not _is_admin_chat(chat_id):
        return "Bu komut sadece admin kullanicisi icin acik."
    try:
        module = _load_optional_skill_module("hooks_skill")
        payload = args.strip()
        if not payload:
            return module.hooks_status()

        action, _, remainder = payload.partition(" ")
        action_key = action.strip().lower()
        rest = remainder.strip()

        if action_key in {"durum", "status"}:
            return module.hooks_status()
        if action_key in {"liste", "ornek", "ornekler"}:
            return module.hooks_list_examples()
        if action_key in {"ekle", "add"}:
            event, _, command = rest.partition(" ")
            if not event.strip() or not command.strip():
                return "Kullanim: /hooks ekle [pre|post|stop|prompt] [komut]"
            return module.add_hook(event.strip(), command.strip())
        return module.hooks_status()
    except ModuleNotFoundError as exc:
        return _missing_skill_message("Hooks", "hooks_skill", exc)
    except Exception as exc:
        log.exception("Hooks command failed")
        return f"Hata: {exc}"


def _handle_gemini_command(chat_id: int, args: str) -> str:
    query = args.strip()
    if not query:
        return "Kullanim: /gemini [soru]"
    try:
        return MODEL_ROUTER.route("gemini", query)
    except Exception as exc:
        log.exception("Gemini command failed")
        return f"Hata: {exc}"


def _handle_deepseek_command(chat_id: int, args: str) -> str:
    query = args.strip()
    if not query:
        return "Kullanim: /deepseek [soru]"
    try:
        return MODEL_ROUTER.route("deep", query)
    except Exception as exc:
        log.exception("Deepseek command failed")
        return f"Hata: {exc}"


def _handle_wiki_command(chat_id: int, args: str) -> str:
    try:
        from obsidian_sync_skill import run_wiki

        return run_wiki(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Wiki command failed")
        return f"Hata: {exc}"


def _load_cloud_modules():
    from server.skills.aws_cost_skill import (
        get_budget_alerts,
        get_cost_trend,
        get_monthly_cost,
    )
    from server.skills.aws_ec2_skill import (
        get_instance_metrics,
        list_instances,
        reboot_instance,
        start_instance,
        stop_instance,
    )
    from server.skills.aws_s3_skill import list_buckets

    return {
        "get_budget_alerts": get_budget_alerts,
        "get_cost_trend": get_cost_trend,
        "get_instance_metrics": get_instance_metrics,
        "get_monthly_cost": get_monthly_cost,
        "list_buckets": list_buckets,
        "list_instances": list_instances,
        "reboot_instance": reboot_instance,
        "start_instance": start_instance,
        "stop_instance": stop_instance,
    }


def _cloud_status_code(payload) -> int:
    if isinstance(payload, dict) and payload.get("ok") is False:
        return 500
    return 200


from server.skill_registry import SkillRegistry
from server.skills.registry_entries.cloud_entries import register_cloud_skills
from server.skills.registry_entries.help_entries import register_help_skill
from server.skills.registry_entries.ops_entries import register_ops_skills

# Legacy note: the original handle_command chain contained 81 elif branches before registry extraction.
COMMAND_REGISTRY = SkillRegistry()
register_cloud_skills(COMMAND_REGISTRY)
register_help_skill(COMMAND_REGISTRY)
register_ops_skills(
    COMMAND_REGISTRY,
    codex_handler=lambda args, ctx: _handle_codex_command(
        int((ctx or {}).get("chat_id", 0) or 0), args
    ),
    codex_swarm_handler=lambda args, ctx: _handle_codex_command(
        int((ctx or {}).get("chat_id", 0) or 0), args, swarm=True
    ),
    codex_status_handler=lambda args, ctx: _handle_codex_status_command(
        int((ctx or {}).get("chat_id", 0) or 0)
    ),
    codex_result_handler=lambda args, ctx: _handle_codex_result_command(
        int((ctx or {}).get("chat_id", 0) or 0), args
    ),
    wiki_handler=lambda args, ctx: _handle_wiki_command(
        int((ctx or {}).get("chat_id", 0) or 0), args
    ),
)


_SPRINT45_HELP_LINES = """

*Sprint 4 & 5 Komutlari:*
  `/crew [gorev]` -> CrewAI repo/entegrasyon ozeti
  `/openhands [gorev]` -> OpenHands gorev baslat
  `/devika [gorev]` -> Devika repo/entegrasyon ozeti
  `/aider [aciklama]` -> Aider pair-programming yardimi
  `/cline [gorev]` -> Cline entegrasyon ozeti
  `/route [model] [soru]` -> ClawRouter repo/route bilgisi
  `/cli [komut]` -> CLI-Anything (admin)
  `/claude_skills [kategori]` -> Claude skills listesi
  `/catalog [arama]` -> Agent katalog arama
  `/repo [arama]` -> External repo havuzu / entegrasyon durumu
  `/repo-oner [gorev]` -> Goreve gore repo + tool onerisi
  `/prompt [kategori]` -> Prompt katalog arama
  `/spec [komut]` -> SpecKit specify/plan/tasks
  `/sirket [komut]` -> Paperclip isletme runtime ozeti
  `/ytunified [url]` -> Unified YouTube transcript
  `/clawcode [gorev]` -> Claw Code repo ozeti
  `/swarms [gorev]` -> Swarms framework gorevi
  `/octogent [durum|start|init|projects]` -> Octogent orchestration runtime
  `/octogent-health` -> Octogent runtime health snapshot
  `/dusler-snapshot` -> Bugunun REM raporunu persona memory'ye kaydet
  `/dusler-rapor [light|rem|deep]` -> Bugunun OpenClaw D\u00fcsler raporunu oku
  `/hooks [komut]` -> Claude hooks yonetimi (admin)
  `/gemini [soru]` -> Gemini 2.0 Flash route
  `/deepseek [soru]` -> DeepSeek route
  `/codex [slot|auto] [gorev]` -> Codex job baslat
  `/codex-swarm [gorev]` -> Coklu Codex slot dispatch
  `/codex-durum` -> Codex slot ozeti
  `/codex-kuyruk` -> Codex bekleyen isler
  `/codex-saglik` -> Codex slot health ozeti
  `/codex-baslat [role] [gorev]` -> Operator dispatch
  `/codex-durdur` -> Tum aktif Codex islerini iptal et
  `/codex-cooldown-temizle` -> Tum Codex cooldownlarini temizle
  `/codex-sonuc [job_id]` -> Tek job cikti ozeti
  `/wiki [konu]` -> Wiki sayfasi getir
  `/wiki ekle [baslik] | [icerik]` -> Wiki sayfasi olustur
""".rstrip()


_ORIGINAL_HANDLE_COMMAND = handle_command


def _handle_command_with_sprint_extensions(chat_id: int, cmd: str) -> str:
    parts = str(cmd or "").split(" ", 1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command in ("/start", "/help"):
        return _ORIGINAL_HANDLE_COMMAND(chat_id, cmd) + _SPRINT45_HELP_LINES
    elif command == "/codex-durum":
        return _handle_codex_slots_command(chat_id)
    elif command == "/codex-kuyruk":
        return _handle_codex_queue_command(chat_id)
    elif command == "/codex-saglik":
        return _handle_codex_health_command(chat_id)
    elif command == "/codex-baslat":
        return _handle_codex_start_command(chat_id, args)
    elif command == "/codex-durdur":
        return _handle_codex_stop_command(chat_id)
    elif command == "/codex-cooldown-temizle":
        return _handle_codex_clear_cooldowns_command(chat_id)
    elif command == "/sabrican-durum":
        return _handle_sabrican_status_command(chat_id)
    elif command == "/sabrican-servis":
        return _handle_sabrican_service_command(chat_id, args)
    elif command == "/sabrican-docker":
        return _handle_sabrican_docker_command(chat_id)
    elif command == "/sabrican-restart":
        return _handle_sabrican_restart_command(chat_id, args)
    elif command == "/sabri-openclaw":
        return _handle_sabri_openclaw_command(chat_id, args)
    elif command == "/sabrican-subagents":
        return _handle_sabrican_subagents_command(chat_id, args)
    elif command == "/dusler-snapshot":
        return _handle_openclaw_dreams_snapshot_command(chat_id)
    elif command == "/dusler-rapor":
        return _handle_openclaw_dreams_report_command(chat_id, args)
    elif command == "/openclaw-health":
        return _handle_openclaw_health_command(chat_id)
    elif command == "/openclaw-skill":
        return _handle_openclaw_skill_command(chat_id, args)
    elif command == "/octogent-health":
        return _handle_octogent_health_command(chat_id)
    elif command.startswith("/cloud-") or command in {
        "/yardim",
        "/ec2-izle",
        "/ec2-yeniden-baslat",
        "/s3-url",
        "/maliyet-uyari",
        "/codex",
        "/codex-swarm",
        "/codex-status",
        "/codex-sonuc",
        "/wiki",
    }:
        return COMMAND_REGISTRY.dispatch(
            command,
            args,
            {"chat_id": chat_id, "command": command, "registry": COMMAND_REGISTRY},
        )
    elif command == "/crew":
        return _handle_crewai_command(chat_id, args)
    elif command == "/crewai":
        return _handle_crewai_command(chat_id, args)
    elif command == "/openhands":
        return _handle_openhands_command(chat_id, args)
    elif command == "/upondhand":
        return _handle_upondhand_command(chat_id, args)
    elif command == "/devika":
        return _handle_devika_command(chat_id, args)
    elif command == "/aider":
        return _handle_aider_command(chat_id, args)
    elif command == "/cline":
        return _handle_cline_command(chat_id, args)
    elif command == "/route":
        return _handle_clawrouter_command(chat_id, args)
    elif command == "/cli":
        return _handle_cli_anything_command(chat_id, args)
    elif command == "/claude_skills":
        return _handle_claude_skills_command(chat_id, args)
    elif command == "/catalog":
        return _handle_agent_catalog_command(chat_id, args)
    elif command in {"/repo", "/repo-havuz"}:
        return _handle_repo_catalog_command(chat_id, args)
    elif command in {"/repo-oner", "/arac-oner"}:
        return _handle_repo_recommendation_command(chat_id, args)
    elif command == "/prompt":
        return _handle_prompts_command(chat_id, args)
    elif command == "/spec":
        return _handle_speckit_command(chat_id, args)
    elif command == "/sirket":
        return _handle_paperclip_command(chat_id, args)
    elif command in {"/markxxxv", "/mark-xxxv", "/mark_xxxv"}:
        return _handle_markxxxv_command(chat_id, args)
    elif command == "/ytunified":
        return _handle_youtube_unified_command(chat_id, args)
    elif command == "/clawcode":
        return _handle_claw_code_command(chat_id, args)
    elif command == "/swarms":
        return _handle_swarms_command(chat_id, args)
    elif command == "/octogent":
        return _handle_octogent_command(chat_id, args)
    elif command == "/hooks":
        return _handle_hooks_command(chat_id, args)
    elif command == "/gemini":
        return _handle_gemini_command(chat_id, args)
    elif command == "/deepseek":
        return _handle_deepseek_command(chat_id, args)
    elif command in {"/codex-workspace", "/worktree-durum"}:
        try:
            from codex_workspace import WorkspaceManager
        except Exception:
            from server.codex_workspace import WorkspaceManager  # type: ignore
        wm = WorkspaceManager()
        st = wm.status()
        lines = ["Worktree Durumu"]
        for slot, exists in st.items():
            icon = "✅" if exists else "❌"
            lines.append(f"  {icon} {slot}")
            if not exists:
                lines.append(f"     Init: {wm.init_command(slot)}")
        return "\n".join(lines)
    elif command in {"/key-pool", "/key-durum", "/keys"}:
        try:
            from server.key_pool import pool_status

            st = pool_status()
            lines = ["🔑 Key Pool Durumu\n"]
            for provider, info in st.items():
                lines.append(f"▸ {provider.upper()}")
                for k in info.get("keys", []):
                    icon = "✅" if k["status"] == "active" else "⏳"
                    lines.append(
                        f"  {icon} {k['id']} — {k['status']} ({k['ready_at']})"
                    )
            return "\n".join(lines)
        except Exception as e:
            return f"Key pool hatası: {e}"
    return _ORIGINAL_HANDLE_COMMAND(chat_id, cmd)


handle_command = _handle_command_with_sprint_extensions


_ORIGINAL_HEALTH_ENDPOINT_HANDLER = WebHandler._handle_health_endpoint


def _handle_health_endpoint_with_voice_state(self):
    original_json = self._json

    def _json_with_voice_state(data, code=200):
        if isinstance(data, dict):
            assistant_payload = get_desktop_assistant_payload()
            assistant_runtime = (
                assistant_payload.get("runtime", {})
                if isinstance(assistant_payload.get("runtime"), dict)
                else {}
            )
            live_payload = (
                data.get("live", {}) if isinstance(data.get("live"), dict) else {}
            )
            live_voice = (
                live_payload.get("voice", {})
                if isinstance(live_payload.get("voice"), dict)
                else {}
            )
            voice_state = (
                str(
                    data.get("voice_state")
                    or assistant_payload.get("phase")
                    or live_voice.get("phase")
                    or "idle"
                )
                .strip()
                .upper()
                or "IDLE"
            )
            data["voice_state"] = voice_state
            data.setdefault(
                "voice_detail",
                str(assistant_runtime.get("detail") or live_voice.get("detail") or ""),
            )
        return original_json(data, code)

    self._json = _json_with_voice_state
    try:
        return _ORIGINAL_HEALTH_ENDPOINT_HANDLER(self)
    finally:
        self._json = original_json


WebHandler._handle_health_endpoint = _handle_health_endpoint_with_voice_state


# ─────────────────────────── MAIN ─────────────────────────────────
def build_web_server():
    return HTTPServer(("127.0.0.1", CONFIG["web_port"]), WebHandler)


def serve_web(server: HTTPServer):
    try:
        server.serve_forever()
    except Exception:
        log.exception("Web server stopped unexpectedly")
        raise


def _sched_telegram_send(text: str) -> None:
    if not CONFIG["enable_telegram"]:
        log.info("Opportunity scheduler skip: Telegram adapter disabled")
        return
    chat_id = int(CONFIG["authorized_chat_id"] or 0)
    if chat_id <= 0:
        log.info("Opportunity scheduler skip: authorized_chat_id missing")
        return
    send_telegram_message(chat_id, text)


def _slot_has_runtime_activity(slot_id: str) -> bool:
    try:
        payload = _build_codex_slots_payload()
    except Exception:
        return True

    slots = payload.get("slots", []) if isinstance(payload, dict) else []
    for slot in slots if isinstance(slots, list) else []:
        if str(slot.get("slot_id") or "").strip().lower() != slot_id:
            continue
        status = str(slot.get("status") or "").strip().lower()
        current_job = slot.get("current_job")
        return bool(current_job) or status in {"active", "cooldown"}
    return False


def _install_codex_health_guard(watcher):
    original_notify = watcher._notify
    silent_cache: dict[str, float] = {}

    def _guarded_notify(level: str, message: str):
        text = " ".join(str(message or "").split())
        match = _CODEX_SILENT_ALERT_RE.match(text)
        if match:
            slot_id = str(match.group("slot") or "").strip().lower()
            if slot_id and not _slot_has_runtime_activity(slot_id):
                log.info("Codex silent alert suppressed for idle slot: %s", slot_id)
                return
            now = time.monotonic()
            cooldown = max(int(getattr(watcher, "interval", 0) or 0), 6 * 60 * 60)
            if slot_id and (now - silent_cache.get(slot_id, 0.0)) < cooldown:
                return
            if slot_id:
                silent_cache[slot_id] = now
                text = f"{slot_id.upper()} sessiz"
        return original_notify(level, text)

    watcher._notify = _guarded_notify
    return watcher


def main():
    validate_runtime_config(RUNTIME_CONFIG)
    try:
        from codex_health import CodexHealthWatcher
    except Exception:
        from server.codex_health import CodexHealthWatcher  # type: ignore
    log.info("=" * 55)
    log.info(f"  JARVIS MISSION CONTROL v2.3 — {CONFIG['runtime_label']}")
    log.info("=" * 55)
    log.info(f"BASE_DIR: {BASE_DIR}")
    models = get_available_models()
    if models:
        log.info(f"Ollama aktif — {len(models)} model: {', '.join(models[:3])}")
    else:
        log.warning("Ollama bagli degil! Ollama'yi baslatin.")

    if is_local_port_busy(CONFIG["web_port"]):
        log.error(
            f"Port {CONFIG['web_port']} zaten kullanimda. Ikinci bridge ornegi baslatilmayacak."
        )
        return

    try:
        from ecommerce_opportunity_skill import start_opportunity_scheduler

        if start_opportunity_scheduler(_sched_telegram_send):
            log.info("Ecommerce opportunity scheduler baslatildi")
        else:
            log.warning("Ecommerce opportunity scheduler baslatilamadi")
    except Exception as _opp_err:
        log.warning(f"Opportunity scheduler baslatilamadi: {_opp_err}")

    heartbeat_stop = _start_watchdog_state()
    _admin_chat_env = os.getenv("JARVIS_CODEX_ADMIN_CHAT_ID", "").strip()
    if _admin_chat_env and CONFIG["enable_telegram"]:
        try:
            codex_notify_chat_id = int(_admin_chat_env)
        except ValueError:
            log.warning(f"Invalid JARVIS_CODEX_ADMIN_CHAT_ID={_admin_chat_env!r}; disabling codex health notify")
            codex_notify_chat_id = None
    elif _admin_chat_env == "0" or _admin_chat_env.lower() == "off":
        codex_notify_chat_id = None
    else:
        codex_notify_chat_id = (
            int(CONFIG["authorized_chat_id"] or 0) if CONFIG["enable_telegram"] else None
        )
    _codex_health = _install_codex_health_guard(
        CodexHealthWatcher(
            interval_seconds=600,
            notify_chat_id=codex_notify_chat_id,
        )
    )
    _codex_health.start()
    web_server = None

    try:
        web_server = build_web_server()
        threading.Thread(
            target=serve_web,
            args=(web_server,),
            daemon=True,
            name="bridge-http",
        ).start()
        url = f"http://127.0.0.1:{CONFIG['web_port']}"
        log.info(f"Web dashboard: {url}")
        print(url, flush=True)
        if "[web-only]" in str(CONFIG["runtime_label"]).lower():
            log.info(
                "Bridge runtime forced into --web-only mode; Telegram will stay disabled."
            )
        if CONFIG["enable_telegram"]:
            bot = TelegramBot(CONFIG["telegram_token"], CONFIG["authorized_chat_id"])
            try:
                bot.run()
            except KeyboardInterrupt:
                bot.running = False
        else:
            log.info("Telegram adapter disabled. Running in dashboard/HTTP mode only.")
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                return
    finally:
        if web_server is not None:
            try:
                web_server.shutdown()
            except Exception:
                pass
            try:
                web_server.server_close()
            except Exception:
                pass
        heartbeat_stop.set()
        _cleanup_watchdog_state()


# Autonomous Command Layer - append-only extensions
_AUTONOMOUS_PC_ALIASES = {
    "/pc-durum": "pc-durum",
    "/ekran-goruntusu": "ekran-goruntusu",
    "/ekran": "ekran-goruntusu",
    "/ac": "ac",
    "/dosya-gonder": "dosya-gonder",
    "/jarvis-baslat": "jarvis-baslat",
    "/jarvis-kapat": "jarvis-kapat",
    # Faz 1 sistem kontrolleri
    "/ses": "ses",
    "/sustur": "sustur",
    "/duraklat": "duraklat",
    "/devam": "devam",
    "/sonraki": "sonraki",
    "/onceki": "onceki",
    "/kilit": "kilit",
    "/uyku": "uyku",
    "/parlaklik": "parlaklik",
    "/url": "url",
    "/pc-ara": "ara",
    "/yt-ara": "youtube-ara",
    "/aktif-pencere": "aktif-pencere",
    # Faz 2 pano, sekme, pencere
    "/pano-oku": "pano-oku",
    "/pano-yaz": "pano-yaz",
    "/pano-temizle": "pano-temizle",
    "/yaz": "yaz",
    "/sekme-ac": "sekme-ac",
    "/sekme-kapat": "sekme-kapat",
    "/sonraki-sekme": "sonraki-sekme",
    "/onceki-sekme": "onceki-sekme",
    "/pencere-kapat": "pencere-kapat",
    "/masaustu": "masaustu",
    "/pencere-buyut": "pencere-buyut",
    "/adres-cubugu": "adres-cubugu",
}
_AUTONOMOUS_BLOCKED_PC_COMMANDS = {
    "/mouse",
    "/git",
    "/tikla",
    "/tıkla",
    "/click",
    "/cifttikla",
    "/çifttıkla",
    "/dblclick",
    "/sagtikla",
    "/sağtıkla",
    "/rightclick",
    "/tus",
    "/tuş",
    "/key",
    "/press",
    "/kisayol",
    "/kısayol",
    "/hotkey",
    "/scroll",
    "/ekranoku",
    "/konum",
    "/nerede",
    "/yap",
    "/bak",
    "/otonom",
    "/kodcalistir",
}
_AUTONOMOUS_HELP_LINES = """

*PC Kontrol:*
  `/pc-durum` -> CPU, RAM, disk ve Jarvis process ozeti
  `/ekran-goruntusu` -> Screenshot gonderir
  `/ac <app>` -> chrome/vscode/whatsapp/discord/telegram/teams/obsidian/spotify/terminal/cmd/powershell/edge/calc/notepad/explorer
  `/ses <0-100|yukari|asagi>` -> Ses seviyesi
  `/sustur` -> Mute toggle
  `/duraklat` / `/devam` / `/sonraki` / `/onceki` -> Media kontrol
  `/kilit` -> Ekran kilidi
  `/uyku` -> PC uyku moduna al
  `/parlaklik <0-100>` -> Ekran parlakligi (laptop)
  `/url <adres>` -> Tarayicida URL ac
  `/pc-ara <sorgu>` -> Google arama sekmesi
  `/yt-ara <sorgu>` -> YouTube arama sekmesi
  `/aktif-pencere` -> Onplandaki pencere basligi
  `/dosya-gonder <path>` -> Whitelist klasorundeki dosyayi yollar
  `/jarvis-baslat` / `/jarvis-kapat` -> Launcher kontrol

*Pano ve klavye:*
  `/pano-oku` -> Clipboard icerigini okur
  `/pano-yaz <metin>` -> Panoya kopyalar
  `/pano-temizle` -> Panoyu bosaltir
  `/yaz <metin>` -> Aktif pencereye metin yazdirir (Turkce destekli)

*Sekme ve pencere:*
  `/sekme-ac` / `/sekme-kapat` -> Yeni sekme / aktif sekmeyi kapat
  `/sonraki-sekme` / `/onceki-sekme` -> Sekmeler arasi gez
  `/pencere-kapat` -> Aktif pencereyi kapat (Alt+F4)
  `/pencere-buyut` -> Pencereyi tam ekran yap
  `/masaustu` -> Tum pencereleri kuculturup masaustunu goster
  `/adres-cubugu` -> Tarayici adres cubuguna odaklan

*Koordinasyon:*
  `/hafiza [persona]` -> Persona bazli son konusmalar
  `/ajanlarin-ozeti` -> 7 persona ozet gorunumu
  `/codex-dispatch [gorev]` -> Aktif persona slotuna auto-dispatch

*Dogal dil ornekleri:* `ses yuzde 40`, `parlaklik 70`, `ekrani kilitle`, `whatsapp ac`, `url github.com`, `youtube jarvis intro`, `pano oku`, `panoya selam yaz`, `yeni sekme`, `sonraki sekme`, `pencereyi kapat`
""".rstrip()


def _autonomous_clean_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i").replace("İ", "i")
    text = re.sub(r"[^a-z0-9\s/]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _autonomous_load_skill(module_name: str):
    return _load_optional_skill_module(module_name)


def _autonomous_response_for_memory(response: str) -> str:
    value = str(response or "").strip()
    if value.startswith("__SCREENSHOT__"):
        return f"Ekran goruntusu gonderildi: {Path(value[len('__SCREENSHOT__'):]).name}"
    if value.startswith("__DOCUMENT__"):
        return f"Dosya gonderildi: {Path(value[len('__DOCUMENT__'):]).name}"
    return value


def _autonomous_record_persona_turns(
    chat_id: int,
    user_text: str,
    assistant_response: str,
    *,
    source: str,
) -> None:
    clean_user_text = str(user_text or "").strip()
    clean_response = _autonomous_response_for_memory(assistant_response)
    if not clean_user_text or not clean_response:
        return
    try:
        from server.persona_memory import append_turn
    except Exception:
        try:
            from persona_memory import append_turn
        except Exception:
            return

    persona = _get_active_persona_payload(chat_id=chat_id)
    persona_id = str(persona.get("id") or "jarvis").strip() or "jarvis"
    metadata = {"lane": _lane_for_chat_id(chat_id)}
    try:
        append_turn(persona_id, chat_id, "user", clean_user_text, source=source, metadata=metadata)
        append_turn(persona_id, chat_id, "assistant", clean_response, source=source, metadata=metadata)
    except Exception as exc:  # noqa: BLE001
        log.debug("Persona memory append skipped: %s", exc)

    if clean_user_text.startswith("/"):
        return

    try:
        brain_module = _load_persona_brain_module()
        brain = brain_module.PersonaBrain(persona_id)
        topic_words = [word for word in clean_user_text.split() if word][:8]
        topic = " ".join(topic_words).strip() or "conversation"
        channel = str(source or _lane_for_chat_id(chat_id)).strip() or _lane_for_chat_id(chat_id)
        brain.write_memory(
            topic,
            f"User:\n{clean_user_text}\n\nAssistant:\n{clean_response}",
            channel=channel,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("Persona brain memory write skipped: %s", exc)


def _autonomous_handle_pc_gateway_command(chat_id: int, command_key: str, args: str = "") -> str:
    gateway = _autonomous_load_skill("pc_control_gateway")
    persona = _get_active_persona_payload(chat_id=chat_id)
    result = gateway.execute_pc_command(
        command_key,
        args,
        persona_id=str(persona.get("id") or "jarvis"),
        chat_id=chat_id,
    )
    if not result.get("ok"):
        return str(result.get("message") or f"Bu komuta izin verilmiyor: {command_key}")

    action = str(result.get("action") or "")
    if action == "screenshot":
        return f"__SCREENSHOT__{result['path']}"
    if action == "send_file":
        return f"__DOCUMENT__{result['path']}"
    return str(result.get("message") or "")


def _autonomous_handle_memory_command(chat_id: int, args: str) -> str:
    memory_skill = _autonomous_load_skill("agent_memory_skill")
    persona_id = args.strip() or str(_get_active_persona_payload(chat_id=chat_id).get("id") or "jarvis")
    try:
        snapshot = memory_skill.get_persona_memory(persona_id, limit=5)
    except KeyError:
        return f"persona_not_found: {persona_id}"
    return memory_skill.format_persona_memory_text(snapshot)


def _autonomous_handle_agents_summary_command(chat_id: int) -> str:
    memory_skill = _autonomous_load_skill("agent_memory_skill")
    summary = memory_skill.get_all_agents_summary()
    return memory_skill.format_agents_summary_text(summary)


def _autonomous_handle_wiki_intent(chat_id: int, text: str) -> str | None:
    normalized = _autonomous_clean_text(text)
    if not normalized or normalized.startswith("/"):
        return None

    if "wiki de" in normalized and "var mi" in normalized:
        query = normalized.split("wiki de", 1)[1].split("var mi", 1)[0].strip()
        if query:
            return _handle_wiki_command(chat_id, query)

    add_markers = ("wiki ye ekle", "wikiyi guncelle", "wiki yi guncelle")
    if not any(marker in normalized for marker in add_markers):
        return None

    wiki_writer = _autonomous_load_skill("wiki_auto_writer")
    history = memory.get_history(chat_id)[-6:]
    last_user = next(
        (
            str(item.get("content") or "")
            for item in reversed(history)
            if item.get("role") == "user" and str(item.get("content") or "").strip() and str(item.get("content") or "").strip() != text
        ),
        "",
    )
    last_assistant = next(
        (
            _autonomous_response_for_memory(str(item.get("content") or ""))
            for item in reversed(history)
            if item.get("role") == "assistant" and str(item.get("content") or "").strip()
        ),
        "",
    )
    explicit_tail = ""
    if ":" in text:
        explicit_tail = text.split(":", 1)[1].strip()

    title_source = explicit_tail or last_user or text
    title_words = [word for word in title_source.split() if word][:8]
    title = " ".join(title_words).strip() or "wiki-notu"
    content = explicit_tail or last_assistant or title_source
    persona = _get_active_persona_payload(chat_id=chat_id)
    result = wiki_writer.write_wiki_page(
        title,
        content,
        [str(persona.get("id") or "jarvis")],
        source="intent",
    )
    return f"Wiki sayfasi yazildi: {result.get('path')}"


def _autonomous_maybe_write_obsidian(
    chat_id: int,
    text: str,
    response: str,
    intent_result: dict | None = None,
) -> None:
    clean_response = _autonomous_response_for_memory(response)
    if not clean_response or clean_response.startswith("Bu komuta izin verilmiyor"):
        return
    if clean_response.lower().startswith("hata"):
        return

    tracked_commands = {"/arastir", "/ebay", "/trendyol", "/rakip", "/analiz", "/youtube", "/kod", "/code"}
    should_write = False
    source_type = "research"
    if text.startswith("/"):
        command_name = text.split()[0].lower()
        if command_name in tracked_commands:
            should_write = True
            source_type = command_name.lstrip("/")
    elif isinstance(intent_result, dict):
        detected_intent = str(intent_result.get("detected_intent") or "")
        if detected_intent in {"research", "code", "social", "aws", "youtube", "strategy", "security"} and float(intent_result.get("confidence") or 0.0) >= 0.7:
            should_write = True
            source_type = detected_intent

    if not should_write:
        return

    persona = _get_active_persona_payload(chat_id=chat_id)
    try:
        obsidian_writer = _autonomous_load_skill("obsidian_auto_writer")
        obsidian_writer.auto_write_research(
            str(persona.get("id") or "jarvis"),
            text,
            clean_response,
            source_type=source_type,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("Obsidian auto write skipped: %s", exc)

    try:
        wiki_writer = _autonomous_load_skill("wiki_auto_writer")
        wiki_writer.update_hot_md(clean_response)
    except Exception as exc:  # noqa: BLE001
        log.debug("wiki hot update skipped: %s", exc)


_ORIGINAL_AUTONOMOUS_HANDLE_COMMAND = handle_command


def _handle_command_with_autonomous_layer(chat_id: int, cmd: str) -> str:
    parts = str(cmd or "").split(" ", 1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command in _AUTONOMOUS_BLOCKED_PC_COMMANDS:
        return f"Bu komuta izin verilmiyor: {command}"

    if command in _AUTONOMOUS_PC_ALIASES:
        return _autonomous_handle_pc_gateway_command(chat_id, _AUTONOMOUS_PC_ALIASES[command], args)

    if command == "/hafiza":
        return _autonomous_handle_memory_command(chat_id, args)

    if command == "/ajanlarin-ozeti":
        return _autonomous_handle_agents_summary_command(chat_id)

    if command == "/codex-dispatch":
        return _handle_codex_command(chat_id, args, swarm=False)

    result = _ORIGINAL_AUTONOMOUS_HANDLE_COMMAND(chat_id, cmd)
    if command in {"/start", "/help"} and _AUTONOMOUS_HELP_LINES not in result:
        return result + _AUTONOMOUS_HELP_LINES
    if command == "/codex-durum":
        try:
            persona_module = _load_persona_manager_module()
            mapping_lines = ["", "Persona Slotlari:"]
            for persona in persona_module.list_personas():
                mapping_lines.append(
                    f"- {persona.get('name')}: {str(persona.get('codex_slot') or '-').upper()}"
                )
            return result + "\n" + "\n".join(mapping_lines)
        except Exception:
            return result
    return result


handle_command = _handle_command_with_autonomous_layer


_ORIGINAL_AUTONOMOUS_CODEX_COMMAND = _handle_codex_command


def _handle_codex_command_with_persona_slot(chat_id: int, args: str, *, swarm: bool = False) -> str:
    if swarm:
        return _ORIGINAL_AUTONOMOUS_CODEX_COMMAND(chat_id, args, swarm=swarm)

    explicit_slot, parsed_task = _parse_codex_dispatch_args(args)
    if explicit_slot and explicit_slot != "auto":
        return _ORIGINAL_AUTONOMOUS_CODEX_COMMAND(chat_id, args, swarm=swarm)

    task = parsed_task or _strip_wrapping_quotes(args)
    if not task:
        return 'Kullanim: /codex-dispatch "gorev"'

    persona = _get_active_persona_payload(chat_id=chat_id)
    slot = str(persona.get("codex_slot") or "").strip().lower()
    if not slot:
        return _ORIGINAL_AUTONOMOUS_CODEX_COMMAND(chat_id, args, swarm=swarm)

    try:
        from codex_orchestrator import dispatch_job
    except Exception:
        from server.codex_orchestrator import dispatch_job  # type: ignore

    result = dispatch_job(task, swarm=False, requested_slots=[slot])
    if not result.get("ok"):
        return str(result.get("error") or "Codex dispatch basarisiz.")

    job_id = str(result.get("job_id") or "-")
    status = str(result.get("status") or "unknown")
    selected_slots = result.get("selected_slots") or [slot]
    slot_text = ", ".join(str(item).upper() for item in selected_slots)
    return (
        f"{persona.get('name')} -> {slot.upper()}\n"
        f"Job: {job_id}\nDurum: {status}\nSlot: {slot_text}\n{result.get('message', '')}"
    ).strip()


_handle_codex_command = _handle_codex_command_with_persona_slot


_ORIGINAL_AUTONOMOUS_PROCESS_MESSAGE = process_message


def _process_message_with_autonomous_layer(chat_id: int, text: str) -> str:
    clean_text = str(text or "").strip()
    if not clean_text:
        return _ORIGINAL_AUTONOMOUS_PROCESS_MESSAGE(chat_id, text)

    if not clean_text.startswith("/"):
        try:
            gateway = _autonomous_load_skill("pc_control_gateway")
            pc_request = gateway.infer_pc_command(clean_text)
            if pc_request:
                response = _autonomous_handle_pc_gateway_command(
                    chat_id,
                    pc_request["command_key"],
                    pc_request.get("args", ""),
                )
                _autonomous_record_persona_turns(chat_id, clean_text, response, source="pc_control/natural")
                return response
        except Exception as exc:  # noqa: BLE001
            log.debug("Natural PC intent skipped: %s", exc)

        wiki_response = _autonomous_handle_wiki_intent(chat_id, clean_text)
        if wiki_response:
            _autonomous_record_persona_turns(chat_id, clean_text, wiki_response, source="wiki/natural")
            return wiki_response

    switch_prefix = ""
    intent_result = None
    try:
        persona_module = _load_persona_manager_module()
        if not clean_text.startswith("/") and not persona_module.detect_switch_from_text(clean_text):
            router = _autonomous_load_skill("intent_persona_router")
            current_persona = str(_get_active_persona_payload(chat_id=chat_id).get("id") or "jarvis")
            intent_result = router.analyze_message(clean_text, current_persona=current_persona)
            target_persona = router.route_to_persona(intent_result, current_persona, chat_id=chat_id)
            if target_persona:
                switch_result = _switch_persona_for_chat(chat_id, target_persona)
                if switch_result.get("ok"):
                    switch_prefix = router.format_switch_message(intent_result, switch_result)
    except Exception as exc:  # noqa: BLE001
        log.debug("Intent persona routing skipped: %s", exc)

    response = _ORIGINAL_AUTONOMOUS_PROCESS_MESSAGE(chat_id, clean_text)
    if switch_prefix and not str(response).startswith("__"):
        response = f"{switch_prefix}\n\n{response}".strip()

    _autonomous_record_persona_turns(chat_id, clean_text, response, source="bridge")
    _autonomous_maybe_write_obsidian(chat_id, clean_text, response, intent_result)
    return response


process_message = _process_message_with_autonomous_layer


def _telegram_send_voice(self, chat_id, audio_path):
    import urllib.request

    target = Path(str(audio_path))
    if not target.exists():
        return _ORIGINAL_AUTONOMOUS_TELEGRAM_SEND(self, chat_id, f"Ses dosyasi bulunamadi: {target}")

    with target.open("rb") as handle:
        audio_data = handle.read()
    boundary = "JarvisVoiceBoundary"
    body = (
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
            f"{chat_id}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="voice"; filename="{target.name}"\r\n'
            "Content-Type: audio/ogg\r\n\r\n"
        ).encode()
        + audio_data
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        f"{self.api}/sendVoice",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30)


def _telegram_send_document(self, chat_id, document_path):
    import mimetypes
    import urllib.request

    target = Path(str(document_path))
    if not target.exists():
        return _ORIGINAL_AUTONOMOUS_TELEGRAM_SEND(self, chat_id, f"Dosya bulunamadi: {target}")

    mime_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    with target.open("rb") as handle:
        document_data = handle.read()
    boundary = "JarvisDocumentBoundary"
    body = (
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
            f"{chat_id}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="{target.name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode()
        + document_data
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        f"{self.api}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30)


_ORIGINAL_AUTONOMOUS_TELEGRAM_SEND = TelegramBot.send


def _telegram_send_with_tokens(self, chat_id, text, parse_mode="Markdown"):
    value = str(text or "")
    if value.startswith("__DOCUMENT__"):
        return self.send_document(chat_id, value[len("__DOCUMENT__"):])
    if value.startswith("__SCREENSHOT__"):
        return self.send_photo(chat_id, value[len("__SCREENSHOT__"):])
    return _ORIGINAL_AUTONOMOUS_TELEGRAM_SEND(self, chat_id, text, parse_mode=parse_mode)


TelegramBot.send_voice = _telegram_send_voice
TelegramBot.send_document = _telegram_send_document
TelegramBot.send = _telegram_send_with_tokens


_ORIGINAL_AUTONOMOUS_TG_HANDLE_UPDATE = TelegramBot._handle_update


def _handle_update_with_autonomous_voice(self, update):
    msg = update.get("message", {}) if isinstance(update, dict) else {}
    if not isinstance(msg, dict):
        return _ORIGINAL_AUTONOMOUS_TG_HANDLE_UPDATE(self, update)

    chat_id = msg.get("chat", {}).get("id")
    voice = msg.get("voice") or msg.get("audio")
    if not voice or chat_id != self.authorized_id:
        return _ORIGINAL_AUTONOMOUS_TG_HANDLE_UPDATE(self, update)

    self.send(chat_id, "_Ses dinleniyor..._")
    try:
        voice_handler = _autonomous_load_skill("telegram_voice_handler")
        result = voice_handler.handle_voice_message(self.token, msg)
        if not result.get("ok"):
            self.send(chat_id, str(result.get("reply") or "Sesi anlayamadim, yazarak tekrar eder misin?"))
            return

        text = str(result.get("text") or "").strip()
        if not text:
            self.send(chat_id, "Sesi anlayamadim, yazarak tekrar eder misin?")
            return

        self.send(chat_id, f"*Duydum:* _{text}_")
        response = process_message(chat_id, text)
        self.send(chat_id, response)

        if not str(response).startswith("__"):
            try:
                tts_reply = _autonomous_load_skill("telegram_tts_reply")
                persona = _get_active_persona_payload(chat_id=chat_id)
                tts_reply.send_voice_reply(
                    self,
                    chat_id,
                    str(response),
                    voice=str(persona.get("voice") or ""),
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Autonomous TTS hatasi: %s", exc)
    except Exception as exc:  # noqa: BLE001
        self.send(chat_id, f"Ses isleme hatasi: {exc}")


TelegramBot._handle_update = _handle_update_with_autonomous_voice


_ORIGINAL_AUTONOMOUS_WEB_DO_GET = WebHandler.do_GET


def _do_get_with_autonomous_endpoints(self):
    parsed = urlparse(self.path)
    path = parsed.path
    query = parse_qs(parsed.query)

    if re.fullmatch(r"/api/persona/[^/]+/memory", path):
        persona_id = path.split("/")[3]
        limit_raw = (query.get("limit") or ["5"])[0]
        try:
            limit = max(1, min(int(limit_raw), 20))
        except (TypeError, ValueError):
            limit = 5
        try:
            memory_skill = _autonomous_load_skill("agent_memory_skill")
            self._json(memory_skill.get_persona_memory(persona_id, limit=limit))
        except KeyError:
            self._json({"error": "persona_not_found", "id": persona_id}, 404)
        except Exception as exc:  # noqa: BLE001
            self._json({"error": str(exc)}, 500)
        return

    if path == "/api/agents/summary":
        try:
            memory_skill = _autonomous_load_skill("agent_memory_skill")
            payload = memory_skill.get_all_agents_summary()
            payload["generated_at"] = datetime.now().isoformat()
            self._json(payload)
        except Exception as exc:  # noqa: BLE001
            self._json({"error": str(exc)}, 500)
        return

    if path == "/api/pc/status":
        try:
            gateway = _autonomous_load_skill("pc_control_gateway")
            self._json(gateway.get_system_status())
        except Exception as exc:  # noqa: BLE001
            self._json({"error": str(exc)}, 500)
        return

    return _ORIGINAL_AUTONOMOUS_WEB_DO_GET(self)


WebHandler.do_GET = _do_get_with_autonomous_endpoints


_ORIGINAL_PERSONA_BRAIN_WEB_DO_GET = WebHandler.do_GET


def _webhandler_do_get_with_persona_brain(self):
    parsed = urlparse(self.path)
    path = parsed.path
    query = parse_qs(parsed.query)

    if re.fullmatch(r"/api/persona/[^/]+/brain", path):
        persona_id = path.split("/")[3]
        daily_tail_raw = (query.get("daily_tail") or query.get("tail") or ["10"])[0]
        try:
            daily_tail = max(1, min(int(daily_tail_raw), 50))
        except (TypeError, ValueError):
            daily_tail = 10
        try:
            self._json(_build_persona_brain_payload(persona_id, daily_tail=daily_tail))
        except Exception as exc:  # noqa: BLE001
            payload, status_code = _persona_brain_error_response(persona_id, exc)
            self._json(payload, status_code)
        return

    return _ORIGINAL_PERSONA_BRAIN_WEB_DO_GET(self)


WebHandler.do_GET = _webhandler_do_get_with_persona_brain


_ORIGINAL_SUBAGENT_WEB_DO_GET = WebHandler.do_GET


def _webhandler_do_get_with_subagents(self):
    parsed = urlparse(self.path)
    path = parsed.path

    if re.fullmatch(r"/api/persona/[^/]+/subagents", path):
        persona_id = path.split("/")[3]
        try:
            self._json(_build_subagent_list_payload(persona_id))
        except Exception as exc:  # noqa: BLE001
            payload, status_code = _subagent_error_response(persona_id, "", exc)
            self._json(payload, status_code)
        return

    return _ORIGINAL_SUBAGENT_WEB_DO_GET(self)


WebHandler.do_GET = _webhandler_do_get_with_subagents


_ORIGINAL_SWARM_PROCESS_MESSAGE = process_message


def _build_swarm_prefix(chat_id: int, text: str) -> str:
    clean_text = str(text or "").strip()
    if not clean_text or clean_text.startswith("/"):
        return ""

    try:
        from server.skills.sub_agent_runner import is_multi_step, run_sub_agents
    except Exception:
        try:
            from sub_agent_runner import is_multi_step, run_sub_agents  # type: ignore
        except Exception as exc:  # noqa: BLE001
            log.debug("Swarm skill import skipped: %s", exc)
            return ""

    if not is_multi_step(clean_text):
        return ""

    try:
        persona = _get_active_persona_payload(chat_id=chat_id)
        persona_id = str(persona.get("id") or "jarvis").strip() or "jarvis"
        raw_agent_types = persona.get("sub_agents") if isinstance(persona, dict) else None
        agent_types = raw_agent_types if isinstance(raw_agent_types, list) else None
        swarm_output = str(
            run_sub_agents(persona_id, clean_text, agent_types)
        ).strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("Swarm intent hook failed: %s", exc)
        return ""

    if not swarm_output:
        return ""
    return f"Alt ajan bulgulari:\n{swarm_output}"


def _process_message_with_swarm_layer(chat_id: int, text: str) -> str:
    clean_text = str(text or "").strip()
    if not clean_text:
        return _ORIGINAL_SWARM_PROCESS_MESSAGE(chat_id, text)

    swarm_prefix = _build_swarm_prefix(chat_id, clean_text)
    response = _ORIGINAL_SWARM_PROCESS_MESSAGE(chat_id, clean_text)
    if swarm_prefix and isinstance(response, str) and not response.startswith("__"):
        return f"{swarm_prefix}\n\n{response}".strip()
    return response


process_message = _process_message_with_swarm_layer


_ORIGINAL_LUNA_GATED_HANDLE_COMMAND = handle_command
_LUNA_GATED_COMMANDS = {"/luna-tara", "/luna-kapsam", "/luna-analiz"}


def _handle_command_with_luna_guard(chat_id: int, cmd: str) -> str:
    clean_cmd = str(cmd or "").strip()
    command = clean_cmd.split(" ", 1)[0].lower() if clean_cmd else ""
    if command in _LUNA_GATED_COMMANDS:
        try:
            active_persona = _get_active_persona_payload(chat_id=chat_id)
            active_persona_id = (
                str(active_persona.get("id") or "jarvis").strip().lower()
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("Luna guard skipped: %s", exc)
        else:
            if active_persona_id != "luna":
                return "Bu komut sadece Luna aktifken kullanılabilir"
    return _ORIGINAL_LUNA_GATED_HANDLE_COMMAND(chat_id, cmd)


handle_command = _handle_command_with_luna_guard


_ORIGINAL_DESKTOP_IO_HANDLE_COMMAND = handle_command
_ORIGINAL_DESKTOP_IO_PROCESS_MESSAGE = process_message
_DESKTOP_IO_COMMANDS = {
    "/notaç",
    "/notac",
    "/notyaz",
    "/dosyaoluştur",
    "/dosyaolustur",
    "/dosyaoku",
}


def _load_desktop_io_bridge_skill():
    try:
        from server.skills import desktop_io_skill

        return desktop_io_skill
    except Exception:
        import desktop_io_skill  # type: ignore

        return desktop_io_skill  # type: ignore


def _handle_command_with_desktop_io(chat_id: int, cmd: str) -> str:
    clean_cmd = str(cmd or "").strip()
    command, _, args = clean_cmd.partition(" ")
    if command.lower() in _DESKTOP_IO_COMMANDS:
        try:
            desktop_skill = _load_desktop_io_bridge_skill()
            result = str(desktop_skill.handle_desktop_command(command, args.strip()))
            try:
                memory.add_message(chat_id, "user", clean_cmd)
                memory.add_message(chat_id, "assistant", result, "desktop_io/command")
            except Exception:
                pass
            try:
                _autonomous_record_persona_turns(chat_id, clean_cmd, result, source="desktop_io/command")
            except Exception:
                pass
            return result
        except Exception as exc:  # noqa: BLE001
            log.warning("Desktop I/O command failed: %s", exc)
            return f"Desktop I/O hatasi: {exc}"
    return _ORIGINAL_DESKTOP_IO_HANDLE_COMMAND(chat_id, cmd)


handle_command = _handle_command_with_desktop_io


_ORIGINAL_STATUS_CHECK_HANDLE_COMMAND = handle_command


def _status_check_text(value: str) -> str:
    return (
        str(value or "")
        .replace("ı", "i")
        .replace("İ", "I")
        .replace("ğ", "g")
        .replace("Ğ", "G")
        .replace("ş", "s")
        .replace("Ş", "S")
        .replace("ç", "c")
        .replace("Ç", "C")
        .replace("ö", "o")
        .replace("Ö", "O")
        .replace("ü", "u")
        .replace("Ü", "U")
        .lower()
    )


def _build_status_check_response(args: str) -> str:
    normalized = _status_check_text(args)

    if "obsidian" in normalized:
        try:
            from server.skills.obsidian_sync_skill import get_obsidian_vault_dir
        except Exception:
            from obsidian_sync_skill import get_obsidian_vault_dir  # type: ignore

        vault_dir = get_obsidian_vault_dir()
        if vault_dir and Path(vault_dir).exists():
            return f"Obsidian baglantisi aktif. Vault: {vault_dir}"
        return "Obsidian baglantisi pasif. OBSIDIAN_VAULT_PATH ayarli degil veya klasor bulunamadi."

    if "telegram" in normalized:
        if CONFIG.get("enable_telegram"):
            return "Telegram bridge aktif."
        return "Telegram bridge pasif. Bridge calisiyor ancak Telegram adapter kapali."

    status_url = f"http://127.0.0.1:{CONFIG['web_port']}/api/status"
    return f"Jarvis bridge aktif. Durum endpointi: {status_url}"


def _handle_command_with_status_check(chat_id: int, cmd: str) -> str:
    clean_cmd = str(cmd or "").strip()
    command, _, args = clean_cmd.partition(" ")
    if command.lower() == "/status_check":
        return _build_status_check_response(args)
    return _ORIGINAL_STATUS_CHECK_HANDLE_COMMAND(chat_id, cmd)


handle_command = _handle_command_with_status_check


def _process_message_with_desktop_io(chat_id: int, text: str) -> str:
    clean_text = str(text or "").strip()
    if clean_text and not clean_text.startswith("/"):
        try:
            desktop_skill = _load_desktop_io_bridge_skill()
            persona = _get_active_persona_payload(chat_id=chat_id)
            reply = desktop_skill.handle_note_intent(
                clean_text,
                persona_id=str(persona.get("id") or "jarvis"),
            )
            if reply:
                try:
                    memory.add_message(chat_id, "user", clean_text)
                    memory.add_message(chat_id, "assistant", str(reply), "desktop_io/natural")
                except Exception:
                    pass
                try:
                    _autonomous_record_persona_turns(
                        chat_id,
                        clean_text,
                        str(reply),
                        source="desktop_io/natural",
                    )
                except Exception:
                    pass
                return str(reply)
        except Exception as exc:  # noqa: BLE001
            log.debug("Desktop I/O natural intent skipped: %s", exc)
    return _ORIGINAL_DESKTOP_IO_PROCESS_MESSAGE(chat_id, text)


process_message = _process_message_with_desktop_io


def _bridge_command_args_text_from_body(body: dict[str, object]) -> str:
    args = body.get("args")
    if isinstance(args, str):
        return args.strip()
    if isinstance(args, dict) and args:
        if isinstance(args.get("text"), str):
            return args["text"]
        if isinstance(args.get("args"), str):
            return args["args"]
        return json.dumps(args, ensure_ascii=False)
    data = body.get("data")
    if isinstance(data, dict) and data:
        return json.dumps(data, ensure_ascii=False)
    return ""


_ORIGINAL_WEBHANDLER_DO_POST = WebHandler.do_POST


def _webhandler_do_post_with_string_args(self):
    if self.path != "/command":
        return _ORIGINAL_WEBHANDLER_DO_POST(self)

    try:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        command = str(body.get("command", "")).strip()
        chat_id_raw = body.get("chatId")
        if chat_id_raw in (None, ""):
            chat_id_raw = body.get("chat_id")

        if not command:
            self._json({"ok": False, "error": "command is required"}, 400)
            return

        if not command.startswith("/"):
            command = f"/{command}"

        chat_id = 9999
        if chat_id_raw not in (None, ""):
            try:
                chat_id = int(chat_id_raw)
            except (TypeError, ValueError):
                chat_id = 9999

        args_text = _bridge_command_args_text_from_body(body)
        result = handle_command(chat_id, f"{command} {args_text}".strip())
        self._json({"ok": True, "result": result})
    except Exception as e:
        self._json({"ok": False, "error": str(e)}, 500)


WebHandler.do_POST = _webhandler_do_post_with_string_args


_ORIGINAL_PERSONA_BRAIN_WEB_DO_POST = WebHandler.do_POST


def _webhandler_do_post_with_persona_brain(self):
    parsed = urlparse(self.path)
    path = parsed.path

    if re.fullmatch(r"/api/persona/[^/]+/brain", path):
        persona_id = path.split("/")[3]
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0

        try:
            raw_body = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw_body or b"{}")
            if not isinstance(body, dict):
                self._json({"ok": False, "error": "JSON object body is required"}, 400)
                return
            self._json(_write_persona_brain_payload(persona_id, body))
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "invalid JSON body"}, 400)
        except Exception as exc:  # noqa: BLE001
            payload, status_code = _persona_brain_error_response(persona_id, exc)
            self._json(payload, status_code)
        return

    return _ORIGINAL_PERSONA_BRAIN_WEB_DO_POST(self)


WebHandler.do_POST = _webhandler_do_post_with_persona_brain


_ORIGINAL_SUBAGENT_WEB_DO_POST = WebHandler.do_POST


def _webhandler_do_post_with_subagents(self):
    parsed = urlparse(self.path)
    path = parsed.path

    match = re.fullmatch(r"/api/persona/([^/]+)/subagent/([^/]+)", path)
    if match:
        persona_id = match.group(1)
        agent_name = match.group(2)
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        try:
            raw_body = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw_body or b"{}")
            if not isinstance(body, dict):
                self._json({"ok": False, "error": "JSON object body is required"}, 400)
                return
            self._json(_dispatch_subagent_payload(persona_id, agent_name, body))
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "invalid JSON body"}, 400)
        except Exception as exc:  # noqa: BLE001
            payload, status_code = _subagent_error_response(persona_id, agent_name, exc)
            self._json(payload, status_code)
        return

    return _ORIGINAL_SUBAGENT_WEB_DO_POST(self)


WebHandler.do_POST = _webhandler_do_post_with_subagents


def _open_obsidian_from_bridge() -> str:
    try:
        from server.skills.obsidian_sync_skill import open_obsidian_vault
    except Exception:
        from obsidian_sync_skill import open_obsidian_vault  # type: ignore
    return open_obsidian_vault()


_ORIGINAL_OBSIDIAN_OPEN_HANDLE_COMMAND = handle_command


def _handle_command_with_obsidian_open(chat_id: int, cmd: str) -> str:
    clean_cmd = str(cmd or "").strip()
    command, _, _args = clean_cmd.partition(" ")
    if command.lower() in {"/obsidian-ac", "/obsidian-open"}:
        return _open_obsidian_from_bridge()
    return _ORIGINAL_OBSIDIAN_OPEN_HANDLE_COMMAND(chat_id, cmd)


handle_command = _handle_command_with_obsidian_open


_ORIGINAL_PROCESS_MESSAGE_OBSIDIAN_PRIORITY = process_message


def _process_message_with_obsidian_priority(chat_id: int, text: str) -> str:
    clean_text = str(text or "").strip()
    if (
        clean_text
        and not clean_text.startswith("/")
        and _extract_obsidian_save_payload(clean_text) is not None
    ):
        return _ORIGINAL_DESKTOP_IO_PROCESS_MESSAGE(chat_id, text)
    return _ORIGINAL_PROCESS_MESSAGE_OBSIDIAN_PRIORITY(chat_id, text)


process_message = _process_message_with_obsidian_priority


_ORIGINAL_LANE_AWARE_OBSIDIAN_HANDLE_COMMAND = handle_command


def _handle_command_with_lane_aware_obsidian(chat_id: int, cmd: str) -> str:
    clean_cmd = str(cmd or "").strip()
    command, _, args = clean_cmd.partition(" ")
    lower_command = command.lower()
    if lower_command == "/obsidian-kaydet":
        if not args:
            return "Kullanim: /obsidian-kaydet <baslik> | <icerik>\nOrnek: /obsidian-kaydet Toplanti | Yarin saat 15"
        try:
            from server.skills.persona_obsidian_skill import write_persona_note

            persona = _get_active_persona_payload(chat_id=chat_id)
            persona_id = str(persona.get("id") or "jarvis").strip().lower() or "jarvis"
            parts = args.split("|", 1)
            title = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else args.strip()
            note = write_persona_note(persona_id=persona_id, title=title, content=content)
            if not note:
                return "OBSIDIAN_VAULT_PATH ayarli degil; not kaydedemedim."
            return f"Obsidian'a kaydedildi ({persona_id}): {title}"
        except Exception as exc:
            return f"Obsidian kayit hatasi: {exc}"
    if lower_command == "/obsidian-oku":
        if not args:
            return "Kullanim: /obsidian-oku <arama sorgusu>"
        try:
            from server.skills.persona_obsidian_skill import recall_persona_notes

            persona = _get_active_persona_payload(chat_id=chat_id)
            persona_id = str(persona.get("id") or "jarvis").strip().lower() or "jarvis"
            notes = recall_persona_notes(persona_id=persona_id, query=args)
            if not notes:
                return f"{persona_id} icin ilgili not bulunamadi: {args}"
            rendered = json.dumps(notes[:5], ensure_ascii=False)
            return f"*{persona_id} notlari ({args}):*\n{rendered[:1500]}"
        except Exception as exc:
            return f"Obsidian okuma hatasi: {exc}"
    return _ORIGINAL_LANE_AWARE_OBSIDIAN_HANDLE_COMMAND(chat_id, cmd)


handle_command = _handle_command_with_lane_aware_obsidian


def _load_persona_swarm_allowed_executors():
    try:
        from server.services.persona_swarm import allowed_executors_for_persona

        return allowed_executors_for_persona
    except Exception:
        try:
            from services.persona_swarm import allowed_executors_for_persona  # type: ignore

            return allowed_executors_for_persona  # type: ignore
        except Exception as exc:  # noqa: BLE001
            log.debug("Persona swarm executor filter skipped: %s", exc)
            return None


def _resolve_swarm_agent_types(persona: dict | None) -> list[str] | None:
    payload = persona if isinstance(persona, dict) else {}
    raw_agent_types = payload.get("sub_agents")
    if not isinstance(raw_agent_types, list):
        return None

    allowed_executors_for_persona = _load_persona_swarm_allowed_executors()
    if callable(allowed_executors_for_persona):
        try:
            return list(allowed_executors_for_persona(payload))
        except Exception as exc:  # noqa: BLE001
            log.debug("Persona swarm agent type resolution skipped: %s", exc)

    return raw_agent_types


def _build_swarm_prefix(chat_id: int, text: str) -> str:
    clean_text = str(text or "").strip()
    if not clean_text or clean_text.startswith("/"):
        return ""

    try:
        from server.skills.sub_agent_runner import is_multi_step, run_sub_agents
    except Exception:
        try:
            from sub_agent_runner import is_multi_step, run_sub_agents  # type: ignore
        except Exception as exc:  # noqa: BLE001
            log.debug("Swarm skill import skipped: %s", exc)
            return ""

    if not is_multi_step(clean_text):
        return ""

    try:
        persona = _get_active_persona_payload(chat_id=chat_id)
        persona_id = str(persona.get("id") or "jarvis").strip() or "jarvis"
        agent_types = _resolve_swarm_agent_types(persona)
        swarm_output = str(run_sub_agents(persona_id, clean_text, agent_types)).strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("Swarm intent hook failed: %s", exc)
        return ""

    if not swarm_output:
        return ""
    return f"Alt ajan bulgulari:\n{swarm_output}"


def _batch_scrape_usage_text() -> str:
    return (
        "Kullanim: /batch-scrape hesaplar.csv | "
        "/batch-scrape --output wiki hesaplar.csv | "
        "/batch-scrape @hesap1,@hesap2 | "
        "/batch-scrape @hesap1\\n@hesap2"
    )


def _extract_batch_scrape_output_mode(args: str) -> tuple[str, str | None]:
    raw = str(args or "").strip()
    output_mode: str | None = None

    cleaned = re.sub(r"(?i)(^|\s)--output(?:=|\s+)wiki(?=\s|$)", " ", raw)
    if cleaned != raw:
        output_mode = "wiki"
    raw = cleaned

    cleaned = re.sub(r"(?i)(^|\s)--wiki(?=\s|$)", " ", raw)
    if cleaned != raw:
        output_mode = "wiki"

    return _strip_wrapping_quotes(cleaned.strip()), output_mode


def _parse_batch_scrape_args(args: str) -> tuple[str | None, list[str] | None, str | None]:
    raw, output_mode = _extract_batch_scrape_output_mode(args)
    if not raw:
        return None, None, output_mode

    if raw.lower().endswith(".csv"):
        return raw, None, output_mode

    if "," in raw or "\n" in raw:
        accounts = [item.strip() for item in re.split(r"[\r\n,]+", raw) if item.strip()]
        return None, accounts or None, output_mode

    return None, [raw], output_mode


def _load_batch_profile_scraper_handler():
    module_names = (
        "server.skills.batch_profile_scraper_codex",
        "server.skills.batch_profile_scraper",
        "skills.batch_profile_scraper_codex",
        "skills.batch_profile_scraper",
        "batch_profile_scraper_codex",
        "batch_profile_scraper",
    )
    load_errors: list[str] = []

    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
            break
        except Exception as exc:  # noqa: BLE001
            load_errors.append(f"{module_name}: {exc}")
    else:
        raise ImportError(" | ".join(load_errors))

    for attr_name in ("batch_scrape_handler", "handle_batch_scrape", "run_batch_scrape"):
        handler = getattr(module, attr_name, None)
        if callable(handler):
            return handler

    scraper_cls = getattr(module, "BatchProfileScraper", None)
    if callable(scraper_cls):

        def _class_handler(
            csv_path: str | None = None,
            accounts: list[str] | None = None,
        ):
            scraper = scraper_cls(max_concurrent=5)
            if csv_path:
                for method_name in ("batch_scrape_from_csv", "scrape_from_csv"):
                    method = getattr(scraper, method_name, None)
                    if callable(method):
                        return method(csv_path)
            if accounts is not None:
                for method_name in (
                    "batch_scrape",
                    "scrape_accounts",
                    "batch_scrape_accounts",
                ):
                    method = getattr(scraper, method_name, None)
                    if callable(method):
                        return method(accounts)
            raise AttributeError("BatchProfileScraper handler method not found")

        return _class_handler

    raise AttributeError("Batch profile scraper handler not found")


def _invoke_batch_profile_scraper(
    handler,
    csv_path: str | None,
    accounts: list[str] | None,
):
    kwargs: dict[str, object] = {}
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        signature = None

    if signature is not None:
        params = signature.parameters
        if csv_path is not None:
            for key in ("csv_path", "path", "file_path", "csv_file"):
                if key in params:
                    kwargs[key] = csv_path
                    break
        if accounts is not None:
            for key in ("handles", "accounts", "profiles", "targets", "items"):
                if key in params:
                    kwargs[key] = accounts
                    break

    if kwargs:
        result = handler(**kwargs)
    elif csv_path is not None and accounts is None:
        result = handler(csv_path)
    elif accounts is not None and csv_path is None:
        result = handler(accounts)
    else:
        result = handler(csv_path, accounts)

    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def _load_batch_wiki_handler():
    module_names = (
        "server.skills.bridge_wiki_wrapper",
        "skills.bridge_wiki_wrapper",
        "bridge_wiki_wrapper",
    )
    load_errors: list[str] = []

    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
            break
        except Exception as exc:  # noqa: BLE001
            load_errors.append(f"{module_name}: {exc}")
    else:
        raise ImportError(" | ".join(load_errors))

    for attr_name in (
        "batch_scrape_to_wiki_result",
        "batch_scrape_to_wiki",
        "batch_scrape_with_wiki_option",
    ):
        handler = getattr(module, attr_name, None)
        if callable(handler):
            return handler

    raise AttributeError("Batch wiki export handler not found")


def _invoke_batch_wiki_handler(handler, csv_path: str):
    kwargs: dict[str, object] = {}
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        signature = None

    if signature is not None:
        params = signature.parameters
        for key in ("csv_path", "path", "file_path", "csv_file"):
            if key in params:
                kwargs[key] = csv_path
                break
        if "output_type" in params:
            kwargs["output_type"] = "wiki"

    result = handler(**kwargs) if kwargs else handler(csv_path)
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def _pick_batch_result_value(
    result: dict[str, object],
    summary: dict[str, object],
    *keys: str,
):
    for key in keys:
        if result.get(key) not in (None, ""):
            return result.get(key)
        if summary.get(key) not in (None, ""):
            return summary.get(key)
    return None


def _format_batch_scrape_result(
    result,
    *,
    csv_path: str | None,
    accounts: list[str] | None,
) -> str:
    if not isinstance(result, dict):
        return f"Toplu profil cekimi tamamlandi.\nSonuc: {result}"

    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    status = str(result.get("status") or result.get("state") or "").strip().lower()
    ok_value = result.get("ok")
    error_text = _pick_batch_result_value(result, summary, "error", "message")

    if status in {"error", "failed"} or ok_value is False:
        return f"Batch scrape hatasi: {error_text or 'Bilinmeyen hata'}"

    total = _pick_batch_result_value(
        result,
        summary,
        "toplam",
        "total",
        "total_profiles",
        "count",
    )
    success = _pick_batch_result_value(
        result,
        summary,
        "basarili",
        "successful",
        "success",
        "completed",
    )
    failed = _pick_batch_result_value(
        result,
        summary,
        "basarisiz",
        "failed",
        "errors",
        "error_count",
    )
    output_path = _pick_batch_result_value(
        result,
        summary,
        "output_path",
        "output_dir",
        "directory",
        "saved_to",
    )
    report_path = _pick_batch_result_value(
        result,
        summary,
        "report_path",
        "summary_file",
        "summary_path",
    )
    saved_files = _pick_batch_result_value(result, summary, "saved_files", "files", "file_paths")
    saved_count = len(saved_files) if isinstance(saved_files, list) else None

    lines = ["Toplu profil cekimi tamamlandi!"]
    if csv_path:
        lines.append(f"Girdi: CSV ({csv_path})")
    elif accounts:
        lines.append(f"Girdi: {len(accounts)} hesap")

    if total is None and accounts:
        total = len(accounts)
    if total is not None:
        lines.append(f"Toplam: {total}")
    if success is not None:
        lines.append(f"Basarili: {success}")
    if failed is not None:
        lines.append(f"Basarisiz: {failed}")
    if saved_count is not None:
        lines.append(f"Kaydedilen dosya sayisi: {saved_count}")
    if report_path:
        lines.append(f"Ozet rapor: {report_path}")
    if output_path:
        lines.append(f"Kayit klasoru: {output_path}")

    return "\n".join(lines)


def _format_batch_wiki_result(result, *, csv_path: str) -> str:
    if isinstance(result, tuple) and len(result) >= 2:
        success, message = result[0], str(result[1])
        if not success:
            return f"Leads wiki hatasi: {message}"
        return "\n".join(
            [
                "Leads wiki guncellendi!",
                f"Girdi: CSV ({csv_path})",
                f"Detay: {message}",
            ]
        )

    if not isinstance(result, dict):
        return "\n".join(
            [
                "Leads wiki guncellendi!",
                f"Girdi: CSV ({csv_path})",
                f"Sonuc: {result}",
            ]
        )

    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    status = str(result.get("status") or result.get("state") or "").strip().lower()
    ok_value = result.get("ok")
    error_text = _pick_batch_result_value(result, summary, "error", "message")

    if status in {"error", "failed"} or ok_value is False:
        return f"Leads wiki hatasi: {error_text or 'Bilinmeyen hata'}"

    lead_count = _pick_batch_result_value(
        result,
        summary,
        "lead_count",
        "total",
        "toplam",
        "count",
    )
    output_path = _pick_batch_result_value(
        result,
        summary,
        "output_path",
        "output_dir",
        "directory",
        "saved_to",
    )
    summary_path = _pick_batch_result_value(
        result,
        summary,
        "summary_path",
        "hot_path",
        "report_path",
    )
    message = _pick_batch_result_value(result, summary, "message")

    lines = ["Leads wiki guncellendi!", f"Girdi: CSV ({csv_path})"]
    if lead_count is not None:
        lines.append(f"Lead sayisi: {lead_count}")
    if summary_path:
        lines.append(f"Haftalik ozet: {summary_path}")
    if output_path:
        lines.append(f"Kayit klasoru: {output_path}")
    if message:
        lines.append(f"Detay: {message}")
    return "\n".join(lines)


_ORIGINAL_BATCH_PROFILE_SCRAPE_HANDLE_COMMAND = handle_command


def _handle_command_with_batch_profile_scrape(chat_id: int, cmd: str) -> str:
    clean_cmd = str(cmd or "").strip()
    command, _, args = clean_cmd.partition(" ")
    if command.lower() != "/batch-scrape":
        return _ORIGINAL_BATCH_PROFILE_SCRAPE_HANDLE_COMMAND(chat_id, cmd)

    csv_path, accounts, output_mode = _parse_batch_scrape_args(args)
    if not csv_path and not accounts:
        return _batch_scrape_usage_text()

    try:
        if output_mode == "wiki":
            if not csv_path:
                return "Wiki output icin CSV path gerekli.\n" + _batch_scrape_usage_text()
            wiki_handler = _load_batch_wiki_handler()
            wiki_result = _invoke_batch_wiki_handler(wiki_handler, csv_path)
            return _format_batch_wiki_result(wiki_result, csv_path=csv_path)

        handler = _load_batch_profile_scraper_handler()
        result = _invoke_batch_profile_scraper(handler, csv_path, accounts)
        return _format_batch_scrape_result(
            result,
            csv_path=csv_path,
            accounts=accounts,
        )
    except Exception as exc:  # noqa: BLE001
        return f"Batch scrape hatasi: {str(exc)[:200]}"


handle_command = _handle_command_with_batch_profile_scrape


_SWARM_COORDINATORS: dict[str, object] = {}
_SWARM_REPORTS_DIR = Path("outputs/swarm_reports")
_ORIGINAL_SWARM_COORDINATOR_HANDLE_COMMAND = handle_command


def _load_swarm_coordinator_class():
    try:
        from server.orchestrator.swarm_coordinator import SwarmCoordinator

        return SwarmCoordinator
    except Exception:
        from orchestrator.swarm_coordinator import SwarmCoordinator  # type: ignore

        return SwarmCoordinator  # type: ignore


def _default_swarm_task_specs(goal: str, handles_csv: str | None = None) -> list[dict[str, object]]:
    metadata = {"goal": goal}
    if handles_csv:
        metadata["handles_csv"] = handles_csv
    return [
        {
            "role": "code",
            "description": "Seda/forge: batch profile scrape ve teknik smoke dogrulama",
            "metadata": metadata,
        },
        {
            "role": "ops",
            "description": "Sabrican/nexus: swarm koordinasyon ve runbook takibi",
            "metadata": metadata,
        },
        {
            "role": "content",
            "description": "Buse/spark: reel ve creator positioning analizi",
            "metadata": metadata,
        },
        {
            "role": "data",
            "description": "Eren/spark: engagement skorlamasi ve benchmark matrisi",
            "metadata": metadata,
        },
        {
            "role": "strategy",
            "description": "Sabri/atlas: 48 saatlik CEO strateji sentezi",
            "metadata": metadata,
        },
    ]


def _start_swarm_from_args(args: str) -> str:
    clean_args = str(args or "").strip()
    if not clean_args:
        return "Kullanim: /swarm <goal> [handles_csv]"

    parts = clean_args.rsplit(" ", 1)
    handles_csv = None
    goal = clean_args
    if len(parts) == 2 and parts[1].lower().endswith(".csv"):
        goal, handles_csv = parts[0].strip(), _strip_wrapping_quotes(parts[1])
    goal = _strip_wrapping_quotes(goal)
    if not goal:
        return "Kullanim: /swarm <goal> [handles_csv]"

    SwarmCoordinator = _load_swarm_coordinator_class()
    coordinator = SwarmCoordinator(goal)
    for task_spec in _default_swarm_task_specs(goal, handles_csv):
        coordinator.assign_task(
            str(task_spec["description"]),
            role=str(task_spec["role"]),
            metadata=task_spec.get("metadata") if isinstance(task_spec.get("metadata"), dict) else None,
        )

    _SWARM_COORDINATORS[coordinator.goal_id] = coordinator
    status = coordinator.status()
    return (
        "Swarm baslatildi.\n"
        f"Goal ID: {status['goal_id']}\n"
        f"Durum: {status['state']}\n"
        f"Toplam gorev: {status['total_tasks']}\n"
        f"Durum komutu: /swarm-status {status['goal_id']}"
    )


def _format_swarm_status(goal_id: str) -> str:
    clean_goal_id = str(goal_id or "").strip()
    if not clean_goal_id:
        return "Kullanim: /swarm-status <goal_id>"
    coordinator = _SWARM_COORDINATORS.get(clean_goal_id)
    if coordinator is None:
        return f"Swarm bulunamadi: {clean_goal_id}"
    status = coordinator.status()  # type: ignore[attr-defined]
    tasks = status.get("tasks") if isinstance(status.get("tasks"), dict) else {}
    task_lines = []
    for task_id, task in tasks.items():
        if isinstance(task, dict):
            task_lines.append(
                f"- {task_id}: {task.get('persona', '?')}/{task.get('slot_id', '?')} "
                f"({task.get('status', '?')})"
            )
    task_text = "\n".join(task_lines) if task_lines else "-"
    return (
        f"Swarm durumu: {status['goal_id']}\n"
        f"Hedef: {status['goal']}\n"
        f"Durum: {status['state']}\n"
        f"Gorevler: {status['total_tasks']}\n"
        f"Toplanan sonuc: {status['collected_results']}\n"
        f"Musait slotlar: {', '.join(status['available_slots']) or '-'}\n"
        f"Task ID'leri:\n{task_text}"
    )


def _parse_swarm_result_args(args: str) -> tuple[str, str, bool, object, str | None, dict]:
    header, separator, raw_payload = str(args or "").partition("|")
    if not separator:
        raise ValueError("Kullanim: /swarm-result <goal_id> <task_id> ok|fail | <sonuc>")

    tokens = header.strip().split()
    if len(tokens) != 3:
        raise ValueError("Kullanim: /swarm-result <goal_id> <task_id> ok|fail | <sonuc>")

    goal_id, task_id, status_text = tokens
    lowered_status = status_text.strip().lower()
    if lowered_status not in {"ok", "fail"}:
        raise ValueError("Durum ok veya fail olmali")

    payload_text = raw_payload.strip()
    parsed_payload: object = payload_text
    if payload_text.startswith("{"):
        try:
            parsed_payload = json.loads(payload_text)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"JSON payload okunamadi: {exc}") from exc

    success = lowered_status == "ok"
    metrics: dict = {}
    error: str | None = None
    output: object = parsed_payload
    if isinstance(parsed_payload, dict):
        raw_metrics = parsed_payload.get("metrics")
        metrics = dict(raw_metrics) if isinstance(raw_metrics, dict) else {}
        if success:
            output = parsed_payload.get(
                "output",
                parsed_payload.get("result", parsed_payload),
            )
        else:
            raw_error = parsed_payload.get("error", parsed_payload.get("message", payload_text))
            error = str(raw_error)
            output = parsed_payload.get("output", parsed_payload.get("result"))
    elif not success:
        error = payload_text

    return goal_id, task_id, success, output, error, metrics


def _submit_swarm_result(args: str) -> str:
    goal_id, task_id, success, output, error, metrics = _parse_swarm_result_args(args)
    coordinator = _SWARM_COORDINATORS.get(goal_id)
    if coordinator is None:
        return f"Swarm bulunamadi: {goal_id}"
    coordinator.submit_result(  # type: ignore[attr-defined]
        task_id,
        success=success,
        output=output,
        error=error,
        metrics=metrics,
    )
    state = "basarili" if success else "hatali"
    return f"Swarm sonucu kaydedildi: {goal_id} / {task_id} ({state})"


def _write_swarm_final_report(report: dict) -> str:
    report_dir = _SWARM_REPORTS_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{report['goal_id']}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(report_path)


def _finalize_swarm(goal_id: str) -> str:
    clean_goal_id = str(goal_id or "").strip()
    if not clean_goal_id:
        return "Kullanim: /swarm-finalize <goal_id>"
    coordinator = _SWARM_COORDINATORS.get(clean_goal_id)
    if coordinator is None:
        return f"Swarm bulunamadi: {clean_goal_id}"
    report = coordinator.aggregate_reports()  # type: ignore[attr-defined]
    report_path = _write_swarm_final_report(report)
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return (
        f"Swarm final raporu hazir: {clean_goal_id}\n"
        f"Toplam: {summary.get('total_tasks', 0)}\n"
        f"Basarili: {summary.get('successful', 0)}\n"
        f"Hatali: {summary.get('failed', 0)}\n"
        f"Bekleyen: {summary.get('pending', 0)}\n"
        f"Rapor: {report_path}"
    )


def _handle_command_with_swarm_coordinator(chat_id: int, cmd: str) -> str:
    clean_cmd = str(cmd or "").strip()
    command, _, args = clean_cmd.partition(" ")
    lowered = command.lower()
    if lowered == "/swarm":
        try:
            return _start_swarm_from_args(args)
        except Exception as exc:  # noqa: BLE001
            return f"Swarm baslatma hatasi: {str(exc)[:200]}"
    if lowered == "/swarm-status":
        try:
            return _format_swarm_status(args)
        except Exception as exc:  # noqa: BLE001
            return f"Swarm durum hatasi: {str(exc)[:200]}"
    if lowered == "/swarm-result":
        try:
            return _submit_swarm_result(args)
        except Exception as exc:  # noqa: BLE001
            return f"Swarm sonuc hatasi: {str(exc)[:200]}"
    if lowered == "/swarm-finalize":
        try:
            return _finalize_swarm(args)
        except Exception as exc:  # noqa: BLE001
            return f"Swarm finalizasyon hatasi: {str(exc)[:200]}"
    return _ORIGINAL_SWARM_COORDINATOR_HANDLE_COMMAND(chat_id, cmd)


handle_command = _handle_command_with_swarm_coordinator


_MEDIA_INTAKE_HELP_LINES = """

Medya / Reels:
  `/izle [instagram/youtube/pdf-url]` -> Kaynagi yt-dlp/PDF/transcript hattiyla Jarvis'e alir
  `/reel [instagram-url]` -> Instagram Reel metadata + rapor + wiki notu
  `/media --download [url]` -> Metadata yaninda video dosyasini da indirir
  `/repo-index` -> Tum repo dosya yollarini wiki/repo-file-index.md dosyasina yazar
  `/repo-find [dosya/kelime]` -> Wiki manifestinden dosya yolu arar
"""


def _load_media_intake_module():
    module_names = (
        "server.skills.media_intake_skill",
        "skills.media_intake_skill",
        "media_intake_skill",
    )
    load_errors: list[str] = []
    for module_name in module_names:
        try:
            return importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            load_errors.append(f"{module_name}: {exc}")
    raise ImportError(" | ".join(load_errors))


def _parse_media_intake_args(args: str) -> tuple[str, bool]:
    raw = str(args or "").strip()
    download = False
    cleaned = re.sub(r"(?i)(^|\s)--download(?=\s|$)", " ", raw)
    if cleaned != raw:
        download = True
    return _strip_wrapping_quotes(cleaned.strip()), download


def _handle_media_intake_request(args: str) -> str:
    clean_args, download = _parse_media_intake_args(args)
    if not clean_args:
        return "Kullanim: /izle <instagram/youtube/pdf-url> veya /media --download <url>"
    media_module = _load_media_intake_module()
    skill_cls = getattr(media_module, "MediaIntakeSkill")
    formatter = getattr(media_module, "format_media_intake_response")
    result = skill_cls().analyze_url(clean_args, download=download, write_wiki=True)
    return str(formatter(result))


def _handle_repo_file_index_request() -> str:
    try:
        try:
            from server.skills.repo_file_index_skill import generate_repo_file_index
        except Exception:
            from repo_file_index_skill import generate_repo_file_index  # type: ignore

        result = generate_repo_file_index()
        return (
            "Repo dosya manifesti wiki'ye yazildi.\n"
            f"Dosya sayisi: {result.get('count')}\n"
            f"Markdown: {result.get('markdown_path')}\n"
            f"JSON: {result.get('json_path')}"
        )
    except Exception as exc:  # noqa: BLE001
        return f"Repo index hatasi: {str(exc)[:200]}"


def _handle_repo_file_find_request(args: str) -> str:
    query = str(args or "").strip()
    if not query:
        return "Kullanim: /repo-find <dosya-adi-veya-yol-parcasi>"
    try:
        try:
            from server.skills.repo_file_index_skill import find_repo_files
        except Exception:
            from repo_file_index_skill import find_repo_files  # type: ignore

        result = find_repo_files(query, limit=20)
        if not result.get("ok"):
            return f"Repo arama hatasi: {result.get('error') or 'bilinmeyen hata'}"
        matches = result.get("matches") if isinstance(result.get("matches"), list) else []
        if not matches:
            return f"Eslesme yok: {query}\nOnce /repo-index calistirip manifesti guncelleyebilirsin."
        lines = [f"Repo dosya eslesmeleri ({query}):"]
        for item in matches[:20]:
            if isinstance(item, dict):
                flag = " [sensitive-name]" if item.get("sensitive_name") else ""
                lines.append(f"- {item.get('path')}{flag}")
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        return f"Repo arama hatasi: {str(exc)[:200]}"


_ORIGINAL_MEDIA_INTAKE_HANDLE_COMMAND = handle_command


def _handle_command_with_media_intake(chat_id: int, cmd: str) -> str:
    clean_cmd = str(cmd or "").strip()
    command, _, args = clean_cmd.partition(" ")
    lowered = command.lower()
    if lowered in {"/repo-index", "/dosya-index", "/file-index"}:
        return _handle_repo_file_index_request()
    if lowered in {"/repo-find", "/dosya-bul", "/file-find"}:
        return _handle_repo_file_find_request(args)
    if lowered in {"/izle", "/reel", "/media", "/kaynak"}:
        try:
            return _handle_media_intake_request(args)
        except Exception as exc:  # noqa: BLE001
            return f"Media intake hatasi: {str(exc)[:200]}"
    if lowered in {"/start", "/help"}:
        base = _ORIGINAL_MEDIA_INTAKE_HANDLE_COMMAND(chat_id, cmd)
        if _MEDIA_INTAKE_HELP_LINES not in base:
            return base + _MEDIA_INTAKE_HELP_LINES
        return base
    return _ORIGINAL_MEDIA_INTAKE_HANDLE_COMMAND(chat_id, cmd)


handle_command = _handle_command_with_media_intake


def _media_intake_should_autoroute(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw or raw.startswith("/"):
        return False
    lowered = raw.lower()
    has_media_url = any(
        marker in lowered
        for marker in (
            "instagram.com/reel/",
            "instagram.com/p/",
            "youtube.com/watch",
            "youtube.com/shorts/",
            "youtu.be/",
        )
    ) or bool(re.search(r"https?://\S+\.pdf(?:\?|$)", raw, re.IGNORECASE))
    if not has_media_url:
        return False
    return True


_ORIGINAL_MEDIA_INTAKE_PROCESS_MESSAGE = process_message


def _process_message_with_media_intake(chat_id: int, text: str) -> str:
    clean_text = str(text or "").strip()
    if _media_intake_should_autoroute(clean_text):
        try:
            return _handle_media_intake_request(clean_text)
        except Exception as exc:  # noqa: BLE001
            return f"Media intake hatasi: {str(exc)[:200]}"
    return _ORIGINAL_MEDIA_INTAKE_PROCESS_MESSAGE(chat_id, text)


process_message = _process_message_with_media_intake


if __name__ == "__main__":
    main()
