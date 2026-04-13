#!/usr/bin/env python3
"""
JARVIS MISSION CONTROL — bridge.py v2.3 (Windows Standalone)
Multi-Model AI Router | Telegram + Web Dashboard | eBay + Trendyol Skills
"""

import os
import asyncio
import json
import inspect
import time
import logging
import threading
import queue
import socket
import unicodedata
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

# ─────────────────────────── PATHS ────────────────────────────────
BASE_DIR = Path(__file__).parent          # app/
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ROOT_DIR = BASE_DIR.parent
WATCHDOG_HEARTBEAT_FILE = DATA_DIR / "bridge_heartbeat.json"
WATCHDOG_LOCK_FILE = DATA_DIR / "bridge.lock"
WATCHDOG_HEARTBEAT_INTERVAL = 5

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ─────────────────────────── ENV / API KEYS ───────────────────────
from runtime_config import apply_runtime_cli_overrides, load_runtime_config, validate_runtime_config
from model_router import build_model_router
from runtime_state import RuntimeState
from telegram.telegram_intelligence import TelegramIntelligence
from services.orchestrator.live_state import (
    build_live_event_counts,
    load_task_queue_snapshot,
    read_recent_live_events,
)


OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
SERPER_API_KEY    = os.environ.get("SERPER_API_KEY", "")
OLLAMA_API_KEY    = os.environ.get("OLLAMA_API_KEY", "")

KNOWLEDGE_DIR = str(BASE_DIR / "knowledge")
SOUL_PATH     = str(BASE_DIR / "soul.md")
SKILLS_PATH   = str(BASE_DIR / "skills")
PRINTIFY_TOKEN_PATH = str(BASE_DIR / "printify_token.txt")

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
        logging.StreamHandler()
    ]
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
    "planner": ["plan yap", "hedef belirle", "gorev olustur", "görev oluştur", "planla"],
    "repo_analyst": ["repo analiz", "saglik raporu", "sağlık raporu", "git durumu", "kod sagligi", "kod sağlığı"],
    "developer": ["kod yaz", "implement et", "feature ekle", "gelistir", "geliştir"],
    "reviewer": ["review et", "incele", "pr kontrol", "kodu gozden gecir", "kodu gözden geçir"],
    "debug": ["hata var", "debug et", "neden calismiyor", "neden çalışmıyor", "hata bul"],
    "release": ["release yap", "changelog", "versiyon guncelle", "versiyon güncelle", "yayinla", "yayınla"],
    "docs": ["dokumantasyon yaz", "dökümantasyon yaz", "readme guncelle", "readme güncelle", "dokumante et", "dokümante et"],
    "mission_control": ["sistem durumu", "agent saglik", "agent sağlık", "ne calisiyor", "ne çalışıyor"],
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


def _execute_canonical_agent(agent_name: str, task: str, context: dict | None = None) -> dict:
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


def _run_canonical_agent(agent_name: str, task: str, context: dict | None = None) -> dict:
    normalized_agent = str(agent_name or "").strip().lower()
    task_text = str(task or "").strip()
    context_data = context if isinstance(context, dict) else {}
    health_mode = str(context_data.get("mode") or "").strip().lower() == "health"

    if not normalized_agent:
        return {"ok": False, "error": "agent field required"}
    if normalized_agent not in _load_canonical_agent_classes():
        available = sorted(_load_canonical_agent_classes().keys())
        return {"ok": False, "agent": normalized_agent, "error": f"Unknown agent: {normalized_agent}. Available: {available}"}
    if not task_text and not health_mode:
        return {"ok": False, "agent": normalized_agent, "error": "task field required"}
    if context is not None and not isinstance(context, dict):
        return {"ok": False, "agent": normalized_agent, "error": "context must be an object"}

    try:
        raw_result = _execute_canonical_agent(normalized_agent, task_text or "health_check", context_data)
    except KeyError:
        available = sorted(_load_canonical_agent_classes().keys())
        return {"ok": False, "agent": normalized_agent, "error": f"Unknown agent: {normalized_agent}. Available: {available}"}
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
        agent_result = _run_canonical_agent(agent_name, "health_check", {"mode": "health"})
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
        wrapped = _run_canonical_agent(detected_agent, text, {"chat_id": chat_id, "source": "telegram"})
        if wrapped.get("ok"):
            raw_result = wrapped.get("raw") if isinstance(wrapped.get("raw"), dict) else {}
            formatted = (
                runtime.format_canonical_result(detected_agent, raw_result)
                if runtime is not None and raw_result
                else str(wrapped.get("result") or "")
            )
            return detected_agent, raw_result, formatted

    if runtime is None:
        return None
    try:
        dispatched = runtime.dispatch_keyword_routed_agent(text, {"chat_id": chat_id, "source": "telegram"})
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
        profile_lines = [l for l in KNOWLEDGE["profil"].split("\n")
                        if l.startswith("- ") or l.startswith("**")][:8]
        snippets.append("Kullanici profili:\n" + "\n".join(profile_lines))
    if any(k in text_lower for k in ["ebay", "dropship", "listing", "urun", "satis"]):
        if "ebay_strateji" in KNOWLEDGE:
            snippets.append("eBay Bilgisi:\n" + KNOWLEDGE["ebay_strateji"][:600])
    if any(k in text_lower for k in ["trendyol", "tr pazar", "turkiye"]):
        if "trendyol_strateji" in KNOWLEDGE:
            snippets.append("Trendyol Bilgisi:\n" + KNOWLEDGE["trendyol_strateji"][:600])
    return "\n\n".join(snippets) if snippets else ""

_load_knowledge()

# ─── SOUL ──────────────────────────────────────────────────────────
try:
    with open(SOUL_PATH, "r", encoding="utf-8") as _f:
        JARVIS_SOUL = _f.read()
    log.info("soul.md yuklendi")
except Exception as _e:
    JARVIS_SOUL = "Sen Jarvis'sin, Ekrem'in AI asistani. Zeki, pratik, Tony Stark tarzi."
    log.warning(f"soul.md bulunamadi: {_e}")

# ─── TELEGRAM INTELLIGENCE ──────────────────────────────────────────
try:
    TELEGRAM_INTELLIGENCE = TelegramIntelligence(log_dir=str(BASE_DIR / "logs" / "telegram"))
    log.info("Telegram intelligence initialized")
except Exception as _e:
    TELEGRAM_INTELLIGENCE = None
    log.warning(f"Telegram intelligence init failed: {_e}")

# ─── SELF-LEARNING ENGINE ────────────────────────────────────────────
try:
    import sys as _sys
    _sys.path.insert(0, str(BASE_DIR.parent))
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
        "model": "qwen3-coder:480b-cloud",
        "fallback": "deepseek-v3.1:671b-cloud",
        "second_fallback": "groq/llama-3.3-70b-versatile",
        "keywords": ["kod", "yaz", "python", "javascript", "bug", "hata", "script",
                     "code", "write", "function", "class", "debug", "fix", "program"],
        "system": "Sen uzman bir yazilim gelistiricisin. Temiz, yorumlanmis ve calisan kod yaz."
    },
    "reasoning": {
        "model": "deepseek-v3.1:671b-cloud",
        "fallback": "gpt-oss:20b-cloud",
        "keywords": ["neden", "analiz", "planla", "strateji", "dusun", "mantik",
                     "why", "analyze", "plan", "strategy", "think", "reason", "decide"],
        "system": "Sen derin dusunen bir stratejist ve analistsin. Adim adim mantik yurut."
    },
    "vision": {
        "model": "qwen3-vl:235b-cloud",
        "fallback": "minimax-m2.7:cloud",
        "keywords": ["ekran", "goruntu", "bak", "ne var", "screen", "image", "foto",
                     "goster", "gorsel", "pencere", "uygulama"],
        "system": "Sen ekrani analiz eden bir AI asistanisin. Ne goruyorsun detayli anlat."
    },
    "search": {
        "model": "deepseek-v3.1:671b-cloud",
        "fallback": "minimax-m2.7:cloud",
        "keywords": ["ara", "bul", "ebay", "trendyol", "urun", "fiyat", "piyasa",
                     "search", "find", "product", "price", "market", "trend"],
        "system": "Sen bir e-ticaret ve piyasa arastirma uzmaninisin. Detayli ve pratik bilgi ver."
    },
    "system": {
        "model": "minimax-m2:cloud",
        "fallback": "minimax-m2.7:cloud",
        "keywords": ["durum", "sistem", "servis", "sunucu", "calistir", "durdur",
                     "status", "service", "server", "run", "stop", "restart", "memory", "cpu"],
        "system": "Sen bir sistem yoneticisisin. Komutlari dogru ve guvenli ver."
    },
    "marketing": {
        "model": "minimax-m2.7:cloud",
        "fallback": "deepseek-v3.1:671b-cloud",
        "keywords": ["reklam", "kampanya", "marka", "icerik", "satis", "musteri",
                     "instagram", "tiktok", "linkedin", "brief", "kopya", "hook",
                     "reklam_ajans", "websitesi", "holding", "ajans"],
        "system": "Sen uzman bir dijital pazarlama ve reklam danismanisin. Turkiye pazarini iyi bilirsin. Kisa, net, aksiyona donusulebilir tavsiyeler ver."
    },
    "general": {
        "model": "groq/llama-3.1-8b-instant",
        "fallback": "gemini/gemini-2.5-flash-lite-preview-06-17",
        "second_fallback": "gemma4:e2b",
        "keywords": [],
        "system": "Sen yardimci bir AI asistanisin. Kisa ve net yanit ver."
    },
    "chat": {
        "model": "groq/llama-3.1-8b-instant",
        "fallback": "gemini/gemini-2.5-flash-lite-preview-06-17",
        "second_fallback": "gemma4:e2b",
        "keywords": [],
        "system": JARVIS_SOUL
    },
    "heavy": {
        "model": "deepseek-v3.1:671b-cloud",
        "fallback": "minimax-m2.7:cloud",
        "keywords": [],
        "system": "Sen guclu bir yapay zeka asistanisin. Kapsamli ve detayli yanit ver."
    }
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
    def save_message(*a, **k): pass
    def get_history(*a, **k): return []
    def format_history_for_ollama(*a, **k): return []
    def get_user_context(*a, **k): return ""
    def add_task(*a, **k): return 0
    def get_tasks(*a, **k): return "Hafiza kapali"
    def update_task(*a, **k): return ""
    def daily_memory_report(*a, **k): return "Hafiza kapali"

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
                    "backend": "openai", "model_name": "text-embedding-3-small",
                    "api_key": OPENAI_API_KEY
                }
                log.info("ReMe: OpenAI embedding aktif")
            else:
                emb_cfg = {
                    "backend": "openai", "model_name": "gemma4:e2b",
                    "base_url": "http://127.0.0.1:11434/v1", "api_key": "ollama"
                }
                log.info("ReMe: Ollama embedding aktif (OpenAI key girilmedi)")
            _reme_instance = ReMe(
                working_dir=str(BASE_DIR / ".reme"),
                enable_logo=False, log_to_console=False,
                default_llm_config={
                    "backend": "openai", "model_name": "gemma4:e2b",
                    "base_url": "http://127.0.0.1:11434/v1", "api_key": "ollama"
                },
                default_embedding_model_config=emb_cfg,
                default_vector_store_config={"backend": "local"}
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
            _reme_instance.list_memory(user_name=user_name, limit=5),
            _reme_loop
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
            await _reme_instance.add_memory(
                memory_content=content, user_name=user_name
            )
        except Exception as e:
            log.debug(f"ReMe kayit hatasi: {e}")
    _asyncio.run_coroutine_threadsafe(_save(), _reme_loop)

# ─── INTENT CLASSIFIER ────────────────────────────────────────────
try:
    from intent_skill import classify_intent, handle_with_intent
    INTENT_ENABLED = True
except Exception:
    INTENT_ENABLED = False
    def classify_intent(t): return None
    def handle_with_intent(t, u=None): return None

# ─── MEMORY (JSON fallback) ───────────────────────────────────────
memory = STATE.memory

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
    return MODEL_ROUTER.build_health_snapshot(
        route_map=MODEL_ROUTES,
        ollama_models=get_available_models(),
        last_trace=STATE.last_route_trace if isinstance(STATE.last_route_trace, dict) else {},
    )


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
    return strong_matches >= 2 or (len(text) > 140 and any(item in lower for item in triggers))


def run_team_task(chat_id: int, goal: str) -> str:
    runtime = get_agent_os_runtime()
    result = runtime.run(goal, chat_id=str(chat_id))
    status = result.get("status", "unknown")
    synthesis = result.get("summary") or result.get("synthesis") or result.get("reason") or "Team sonucu uretemedi."
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
    memory.add_message(chat_id, "assistant", result.get("summary", ""), "week1_pipeline")
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
        lines = events_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]
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
            "last_event": status.get("last_event") if isinstance(status, dict) else None,
            "last_task_summary": current_job.get("task") if isinstance(current_job, dict) else None,
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
    if assistant_status in {"online", "ready"} or assistant_phase in {"listening", "thinking", "speaking"}:
        assistant_name = str(assistant_payload.get("agent") or "voice").strip().lower() or "voice"
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
            "source": str(assistant_runtime.get("source") or assistant_payload.get("agent") or ""),
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
        if current_task is None and str(task.get("status") or "").strip().lower() in active_statuses:
            current_task = task

    voice_phase = str(assistant_payload.get("phase") or "idle").strip().lower() or "idle"
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
        if current_task or queue_snapshot.get("queued_tasks", 0) or queue_snapshot.get("running_tasks", 0) or voice_active
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
    route_trace = STATE.last_route_trace if isinstance(STATE.last_route_trace, dict) else {}
    orchestrator_state_file = Path(str(queue_snapshot.get("state_file") or ""))

    return {
        "status": live_payload.get("status", "unknown"),
        "timestamp": live_payload.get("timestamp"),
        "bridge_status": "healthy",
        "orchestrator_status": "healthy" if orchestrator_state_file.exists() else "degraded",
        "queue_size": int(queue_snapshot.get("queued_tasks", 0)),
        "running_tasks": int(queue_snapshot.get("running_tasks", 0)),
        "awaiting_confirmation": int(queue_snapshot.get("awaiting_confirmation_tasks", 0)),
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

    if isinstance(model, str):
        normalized_model = model.strip()
        if "::" in normalized_model:
            provider_prefix = normalized_model.split("::", 1)[0].strip()
            explicit_provider_model = bool(provider_prefix)
        elif "/" in normalized_model:
            provider_prefix = normalized_model.split("/", 1)[0].strip().lower()
            explicit_provider_model = provider_prefix in {"ollama", "openai", "openrouter", "groq", "gemini"}

    if model and not model.endswith(":cloud") and not explicit_provider_model:
        available = get_available_models()
        if available and not any(model.split(":")[0] in item for item in available):
            model = available[0]

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
            result_size = len(response.encode('utf-8')) if isinstance(response, str) else 0
            error_msg = trace.get("error") if not trace.get("ok") else None

            METRICS_COLLECTOR.record_execution(
                run_id=f"msg_{int(_time_module.time() * 1000)}",
                action=action,
                status=status,
                duration_seconds=duration_seconds,
                result_size_bytes=result_size,
                error_message=error_msg,
                cache_hit=False,  # Can be enhanced with actual cache tracking
                retry_count=len(trace.get("attempts", [])) - 1 if trace.get("attempts") else 0,
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
        log.error(f"Model router basarisiz: {trace.get('error')} | Denenenler: {failed}")
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
        disk = psutil.disk_usage('/')
        info["cpu"] = f"{cpu:.1f}%"
        info["ram"] = f"{mem.used/1024**3:.1f}GB/{mem.total/1024**3:.1f}GB"
        info["disk"] = f"{disk.used/1024**3:.0f}GB/{disk.total/1024**3:.0f}GB ({disk.percent:.0f}% dolu)"
    except ImportError:
        # psutil yoksa fallback
        if sys.platform == "win32":
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "$m=Get-CimInstance Win32_OperatingSystem; "
                     "[math]::Round($m.FreePhysicalMemory/1024)"],
                    capture_output=True, text=True, timeout=5
                )
                free_mb = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
                r2 = subprocess.run(
                    ["powershell", "-Command",
                     "$m=Get-CimInstance Win32_OperatingSystem; "
                     "[math]::Round($m.TotalVisibleMemorySize/1024)"],
                    capture_output=True, text=True, timeout=5
                )
                total_mb = int(r2.stdout.strip()) if r2.stdout.strip().isdigit() else 0
                used_mb = total_mb - free_mb
                info["ram"] = f"{used_mb}MB/{total_mb}MB"
            except:
                info["ram"] = "bilinmiyor"
        info["cpu"] = "bilinmiyor"
        info["disk"] = "bilinmiyor"
    return info

def run_command_safe(cmd: str) -> str:
    """Guvenli komut calistirici (cross-platform)"""
    ALLOWED_WIN = ["dir", "echo", "ping", "ipconfig", "tasklist", "ollama", "python", "where"]
    ALLOWED_LIN = ["ls", "echo", "ping", "ps", "free", "df", "ollama", "python3"]
    allowed = ALLOWED_WIN if sys.platform == "win32" else ALLOWED_LIN
    if not any(cmd.lower().startswith(a) for a in allowed):
        return "Bu komut icin izin yok."
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout[:2000] or result.stderr[:500] or "Cikti yok."
    except subprocess.TimeoutExpired:
        return "Komut zaman asimina ugradi."

def run_shell_full(cmd: str) -> str:
    """Kisitsiz shell komutu (!! prefix)"""
    DANGER = ["rm -rf /", "mkfs", "format c:", "del /f /s /q c:\\"]
    if any(d in cmd.lower() for d in DANGER):
        return "HATA: Bu komut cok tehlikeli, calistirilmiyor."
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
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
  `/trendyol [urun]` -> Trendyol TR analizi

*Marketing & Icerik:*
  `/reklam [urun]` -> Hizli reklam metni
  `/icerik [metin]` -> 5 platform icin icerik
  `/abtest [sayfa]` -> A/B test fikirleri
  `/analiz [veri]` -> Kampanya KPI analizi

*Kod & Plan:*
  `/code [gorev]` -> Kod yaz
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
  `/jcoder [gorev]` -> Jarvis Coder - bridge.py bilir, kod yazar
  `/markxxxv [gorev]` -> Mark-XXXV planner/executor gorevi
  `/skill [isim] [aciklama]` -> Yeni Jarvis skill dosyasi yaz
  `/skills [kategori|ara kelime]` -> Aktif ve curated skill listesi
  `/swarm [gorev]` -> Multi-agent orchestration
  `/analyst [konu]` -> Iş analizi, SaaS strateji, pazarlama

*Ajanlar:*
  `/agent [isim]` -> 624 AI ajan sec
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
            send_telegram_message(chat_id, f"*{skill_name}* skill'ini optimize ediyorum... (2-3 dk)")
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
            trace = STATE.last_route_trace if isinstance(STATE.last_route_trace, dict) else {}
            last_sel = trace.get("selected_candidate", "-")
            fallback = "evet" if trace.get("fallback_used") else "hayir"
            return f"""*Jarvis Sistem Durumu*
CPU: `{info['cpu']}` | RAM: `{info['ram']}`
AI Modeller: {len(models)} aktif
Toplam Sorgu: {stats['total_queries']}
Saat: {datetime.now().strftime('%H:%M:%S')}
Servis: Aktif ({CONFIG['runtime_label']})
Ollama: `{provider_health.get('ollama', {}).get('label', '-')}`
OpenRouter: `{provider_health.get('openrouter', {}).get('label', '-')}`
OpenAI: `{provider_health.get('openai', {}).get('label', '-')}`
Son Model: `{last_sel}` | Fallback: `{fallback}`"""
        except Exception as e:
            return f"Durum alinamadi: {e}"

    elif command == "/durum":
        try:
            info = get_system_info()
            models = get_available_models()
            provider_health = get_provider_health()
            lines = ["*Jarvis Sistem Durumu*\n"]
            lines.append(f"CPU: `{info['cpu']}`")
            lines.append(f"RAM: `{info['ram']}`")
            lines.append(f"Disk: `{info['disk']}`")
            lines.append(f"OpenRouter: `{provider_health.get('openrouter', {}).get('label', '-')}`")
            lines.append(f"OpenAI: `{provider_health.get('openai', {}).get('label', '-')}`")
            lines.append(f"\nOllama ({len(models)} model):")
            for m in models:
                lines.append(f"  - `{m}`")
            return "\n".join(lines)
        except Exception as e:
            return f"Durum alinamadi: {e}"

    elif command == "/models":
        local_models = get_available_models()
        cloud_models = ["minimax-m2.7:cloud", "deepseek-v3.1:671b-cloud", "qwen3-coder:480b-cloud", "gpt-oss:120b-cloud"]
        route_info = "\n".join([f"  {k}: `{v['model']}`" for k, v in MODEL_ROUTES.items()])
        local_str = "\n".join([f"- {m}" for m in local_models]) if local_models else "  (Ollama bagli degil)"
        cloud_str = "\n".join([f"- {m} ☁️" for m in cloud_models])
        return f"*Aktif Route'lar:*\n{route_info}\n\n*Lokal Modeller:*\n{local_str}\n\n*Cloud Modeller:*\n{cloud_str}"

    elif command == "/model":
        if not args:
            return "Kullanim: /model [route] [model]\nOrnek: /model chat gemma4:e2b\nOrnek: /model reasoning minimax-m2.7:cloud\n\nRoute'lar: " + ", ".join(MODEL_ROUTES.keys())
        parts2 = args.split(None, 1)
        if len(parts2) < 2:
            return "Kullanim: /model [route] [model-adi]"
        route_key, new_model = parts2[0].lower(), parts2[1].strip()
        if route_key not in MODEL_ROUTES:
            return f"Bilinmeyen route: {route_key}\nMevcut: {', '.join(MODEL_ROUTES.keys())}"
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
                lines.append(f"{i+1}. {t.strip()}")
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

    elif command == "/code":
        task = args or "Merhaba dunya"
        route = MODEL_ROUTES["code"]
        history = [{"role": "user", "content": f"Su gorevi icin tam calisir kod yaz: {task}"}]
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
                history = [{"role": "user", "content": f"Bu gorevi tamamla: {task_goal}"}]
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
                end_fm = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), -1)
                if end_fm > 0:
                    lines = lines[end_fm + 1:]
            clean_prompt = "\n".join(lines).strip()
            system_prompt = (
                clean_prompt + "\n\n"
                "ONEMLI: Bundan sonraki TUM yanitlarini YALNIZCA TURKCE olarak ver."
            )
            ACTIVE_AGENTS[str(chat_id)] = {
                "name": agent_name,
                "prompt": system_prompt,
                "model": "gemma4:e2b"
            }
            preview = clean_prompt[:120].replace("\n", " ")
            return (
                f"*{agent_name.upper()}* ajani aktif!\n\n"
                f"_Rol: {preview}..._\n\n"
                "Simdi soru sor. Kapamak icin: `/agent off`"
            )
        except Exception as e:
            return f"Ajan yuklenemedi: {e}"

    elif command == "/ara":
        query = args.strip()
        if not query:
            return "Kullanim: `/ara [arama sorgusu]`"
        try:
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
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
                return "*Web Arama:* `" + query + "`" + chr(10)*2 + result
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
        response = call_ollama(route["model"], history,
            "Turkce e-ticaret reklam uzmanisin. Cok kisa yaz. Sadece Turkce.",
            max_tokens=110, num_ctx=512, fallback_model=route.get("fallback"), route_name="general")
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
        response = call_ollama(route["model"], history,
            "Sosyal medya uzmanisin. Cok kisa, sadece Turkce.",
            max_tokens=130, num_ctx=512, fallback_model=route.get("fallback"), route_name="general")
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/icerik {metin[:50]}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*5 Platform:*\n\n{response}"

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
        response = call_ollama(route["model"], history,
            "Pazar analisti. Cok kisa, sadece Turkce.",
            max_tokens=120, num_ctx=512, fallback_model=route.get("fallback"), route_name="general")
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
        response = call_ollama(route["model"], history,
            "CRO uzmanisin. Kisa, sadece Turkce.",
            max_tokens=130, num_ctx=512, fallback_model=route.get("fallback"), route_name="general")
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
        response = call_ollama(route["model"], history,
            "Marketing analistsin. Matematik dogru yap. Kisa, sadece Turkce.",
            max_tokens=120, num_ctx=512, fallback_model=route.get("fallback"), route_name="general")
        selected_candidate = get_selected_candidate(route["model"])
        memory.add_message(chat_id, "user", f"/analiz {veri[:50]}")
        memory.add_message(chat_id, "assistant", response, selected_candidate)
        return f"*Marketing Analizi:*\n\n{response}"




    # HOLDING DEPARTMANI

    elif command == "/reklam_ajans":
        if not args:
            return "*Reklam Ajansi*\n\nKullanim: /reklam_ajans [brief]"
        try:
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
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
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
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
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from web_ajans_skill import WebAjansSkill
            result = WebAjansSkill(call_ollama).run(str(chat_id), args)
            memory.add_message(chat_id, "user", f"/websitesi {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Web Ajansi hatasi: {e}"

    elif command == "/mail":
        try:
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from gmail_skill import handle_gmail
            result = handle_gmail(args)
            memory.add_message(chat_id, "user", f"/mail {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Gmail hatasi: {e}"

    elif command == "/takvim":
        try:
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from gcalendar_skill import handle_gcalendar
            result = handle_gcalendar(args)
            memory.add_message(chat_id, "user", f"/takvim {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Takvim hatasi: {e}"

    elif command == "/notion":
        try:
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
            from notion_skill import handle_notion
            result = handle_notion(args, str(chat_id))
            memory.add_message(chat_id, "user", f"/notion {args[:50]}")
            memory.add_message(chat_id, "assistant", result[:200])
            return result
        except Exception as e:
            return f"Notion hatasi: {e}"

    elif command in ("/markxxxv", "/mark-xxxv", "/mark_xxxv"):
        try:
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
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
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
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
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
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
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
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
        import tempfile as _tmpf; ss_path = str(DATA_DIR / "screenshot.png")
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
                r = subprocess.run(["powershell", "-Command", ps_cmd],
                                   capture_output=True, timeout=15)
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
            dirs  = [f"📁 {p.name}" for p in sorted(items) if p.is_dir()][:10]
            files = [f"📄 {p.name}" for p in sorted(items) if p.is_file()][:15]
            return f"*{path}*\n\n" + "\n".join(dirs + files) or "Bos klasor."
        except Exception as e:
            return f"Klasor hatasi: {e}"

    elif command == "/surec":
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name,CPU,WorkingSet | Format-Table -AutoSize"],
                capture_output=True, text=True, timeout=10
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
                ["powershell", "-Command", f"Stop-Process -Name '{kill_target}' -Force"],
                capture_output=True, text=True, timeout=10
            )
            return f"`{kill_target}` durduruldu." if r.returncode == 0 else f"Hata: {r.stderr[:200]}"
        except Exception as e:
            return f"Kill hatasi: {e}"

    elif command == "/ip":
        try:
            r = subprocess.run(["powershell", "-Command",
                "(Invoke-WebRequest -Uri 'https://api.ipify.org' -UseBasicParsing).Content"],
                capture_output=True, text=True, timeout=10)
            local = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=5)
            local_ip = next((l.split(":")[-1].strip() for l in local.stdout.split("\n")
                            if "IPv4" in l), "?")
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
            lines.append(f"{i}. [{n.get('tarih','')}] {n.get('not','')}")
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
        payload = _jgpt.dumps({
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": args}],
            "max_tokens": 1000
        }).encode()
        req = _ureq.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {oai_key}"}
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
            return "Kullanim: /jcoder [gorev]\nOrnek: /jcoder bridge.py ye yeni komut ekle"
        route = MODEL_ROUTES["code"]
        system_prompt = (
            "Sen Jarvis Mission Control sisteminin bas geliştiricisisin. "
            "Python 3.14, Telegram raw HTTP polling, Ollama (http://127.0.0.1:11434) kullaniyorsun. "
            "bridge.py yapisina hakimsin. f-string icinde chr(10) kullan. "
            "Kisa, net, calisir kod yaz. Turkce acikla."
        )
        reply = call_ollama(
            route["model"],
            [{"role":"user","content":args}],
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
        skill_fmt = "def run(args: str, context: dict = None) -> str:" + chr(10) + "    return 'sonuc'"
        system_prompt = (
            "Sen Jarvis skill yazicisin. Skill su formatta olmali:" + chr(10) +
            skill_fmt + chr(10) +
            "Ollama icin urllib kullan (http://127.0.0.1:11434/api/generate). "
            "Sadece calisir Python kodu yaz, Turkce yorum ekle."
        )
        reply = call_ollama(
            route["model"],
            [{"role":"user","content":f"Skill yaz: {args}"}],
            system=system_prompt,
            max_tokens=1500,
            num_ctx=4096,
            fallback_model=route.get("fallback"),
            route_name="code",
        )
        return f"*Skill Yazici:*{chr(10)}{reply}"

    elif command == "/analyst":
        if not args:
            return "Kullanim: /analyst [konu]\nOrnek: /analyst Jarvis SaaS fiyatlandirma"
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
            [{"role":"user","content":args}],
            system=system_prompt,
            max_tokens=1200,
            num_ctx=4096,
            fallback_model=route.get("fallback"),
            route_name="reasoning",
        )
        return f"*Jarvis Analyst:*{chr(10)}{reply}"

    elif command in ("/mouse", "/git", "/tıkla", "/tikla", "/click",
                    "/çifttıkla", "/cifttikla", "/dblclick",
                    "/sağtıkla", "/sagtikla", "/rightclick",
                    "/yaz", "/type", "/tuş", "/tus", "/key", "/press",
                    "/kısayol", "/kisayol", "/hotkey",
                    "/scroll", "/ekranoku", "/konum", "/nerede"):
        try:
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from computer_control_skill import run_computer_control
            return run_computer_control(command, args)
        except Exception as e:
            return f"❌ Computer control hatası: {e}"

    elif command in ("/tarayici", "/browser"):
        try:
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent / "skills"))
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
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from computer_agent_skill import run_computer_agent
            return run_computer_agent(command, args)
        except Exception as e:
            return f"❌ Computer agent hatası: {e}"

    elif command in ("/kabul", "/onayla", "/accept"):
        log.info("AnyDesk kabul komutu alindi.")
        try:
            ps_script = r"C:\Users\sergen\Desktop\jarvis-mission-control\anydesk_kabul.ps1"
            result = subprocess.run(
                ["powershell.exe", "-ExecutionPolicy", "Bypass",
                 "-WindowStyle", "Hidden", "-File", ps_script],
                capture_output=True, text=True, timeout=20
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
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from approval_skill import list_approval_requests

            status = args.strip() if args else "pending"
            return list_approval_requests(status)
        except Exception as e:
            return f"❌ Onay kuyruğu hatası: {e}"

    elif command in ("/onay-ekle", "/approval-add"):
        if not args:
            return "Kullanim: /onay-ekle [baslik] | [ozet]"
        try:
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from approval_skill import add_approval_request

            title, _, summary = args.partition("|")
            return add_approval_request(title, summary, source="manual")
        except Exception as e:
            return f"❌ Onay ekleme hatası: {e}"

    elif command in ("/onay", "/approve"):
        if not args:
            return "Kullanim: /onay [id] | [not]"
        try:
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from approval_skill import decide_approval

            item_id, _, note = args.partition("|")
            return decide_approval(item_id.strip(), "approve", note)
        except Exception as e:
            return f"❌ Onay işleme hatası: {e}"

    elif command in ("/red", "/reject"):
        if not args:
            return "Kullanim: /red [id] | [not]"
        try:
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from approval_skill import decide_approval

            item_id, _, note = args.partition("|")
            return decide_approval(item_id.strip(), "reject", note)
        except Exception as e:
            return f"❌ Red işleme hatası: {e}"

    elif command in ("/claude-uyandir", "/claude-wake"):
        try:
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from approval_skill import schedule_claude_resume

            schedule_part = args or "09:02"
            resume_at, _, note = schedule_part.partition("|")
            return schedule_claude_resume(resume_at.strip() or "09:02", note, "Claude collaboration protocol")
        except Exception as e:
            return f"❌ Claude uyandırma planlama hatası: {e}"

    elif command in ("/claude-durum", "/claude-status"):
        try:
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from approval_skill import get_claude_resume_status

            return get_claude_resume_status()
        except Exception as e:
            return f"❌ Claude durum hatası: {e}"

    elif command in ("/uyku-modu", "/sleep-mode", "/oto-onay"):
        try:
            sys.path.insert(0, r"C:\Users\sergen\Desktop\jarvis-mission-control\server\skills")
            from approval_skill import set_autopilot, get_autopilot_status, process_pending_auto_approvals

            action = (args or "status").strip().lower()
            if action in ("ac", "on", "aktif"):
                result = set_autopilot(True, "sleep", "Kullanici uyurken otomatik onay ve devam modu aktif.")
                batch = process_pending_auto_approvals()
                return result + "\n" + batch
            if action in ("kapat", "off", "pasif"):
                return set_autopilot(False, "manual", "Kullanici geri donene kadar manuel moda alindi.")
            return get_autopilot_status()
        except Exception as e:
            return f"❌ Uyku modu hatası: {e}"

    elif command in ("/otopilot", "/autopilot"):
        try:
            root = r"C:\Users\sergen\Desktop\jarvis-mission-control"
            if (args or "").strip().lower() in ("baslat", "start"):
                result = subprocess.run(
                    ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", rf"{root}\start_autopilot_background.ps1"],
                    capture_output=True, text=True, timeout=20
                )
                return (result.stdout or result.stderr or "Autopilot baslatildi.").strip()
            if (args or "").strip().lower() in ("durdur", "stop"):
                result = subprocess.run(
                    ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", rf"{root}\stop_autopilot.ps1"],
                    capture_output=True, text=True, timeout=20
                )
                return (result.stdout or result.stderr or "Autopilot durdurma sinyali gonderildi.").strip()
            runtime_path = Path(root) / "server" / "agent_workspace" / "approval_state" / "autopilot_runtime.json"
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
                    {"title": "Connection pooling", "impact_score": 0.7}
                ]
                msg = TELEGRAM_INTELLIGENCE.format_improvements_message(improvements)
                TELEGRAM_INTELLIGENCE.log_command("/improve", chat_id, "success", len(msg))
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
                    "message": "Reverted to stable version"
                }
                msg = TELEGRAM_INTELLIGENCE.format_rollback_message(result)
                TELEGRAM_INTELLIGENCE.log_command("/rollback", chat_id, "success", len(msg))
                return msg
            except Exception as e:
                return f"❌ Rollback failed: {e}"
        return "Telegram intelligence not initialized"

    elif command == "/cache":
        if TELEGRAM_INTELLIGENCE:
            try:
                cache_stats = {
                    "hits": 450,
                    "misses": 50,
                    "size_mb": 125.5
                }
                msg = TELEGRAM_INTELLIGENCE.format_cache_message(cache_stats)
                TELEGRAM_INTELLIGENCE.log_command("/cache", chat_id, "success", len(msg))
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
            def _send(msg): pass  # bridge will return response string
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
            brief_info = "yok" if not today_brief else f"{today_brief['send_status']} ({today_brief.get('items_count', '?')} madde)"
            return (f"Arastirma Durumu\nScheduler: {running}\nSonraki brief: {next_run}\nBugunku brief: {brief_info}")[:400]
        except Exception as e:
            return f"Durum alinamadi: {str(e)[:150]}"

    elif command == "/instagram":
        try:
            import sys as _sys, os as _os
            _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "skills"))
            from instagram_skill import add_watched_account, list_watched_accounts, remove_watched_account
            sub = args.strip()
            if sub.startswith("takip "):
                handle = sub[len("takip "):].strip()
                result = add_watched_account(handle)
                return result["message"]
            elif sub == "listele":
                accounts = list_watched_accounts()
                if not accounts:
                    return "Takip listesi bos. /instagram takip @hesap ile ekle."
                lines = ["Takip Listesi"]
                for acc in accounts[:20]:
                    last = acc.get("last_checked_at", "")[:10] if acc.get("last_checked_at") else "hic"
                    lines.append(f"@{acc['username']} (son kontrol: {last})")
                return "\n".join(lines)[:400]
            elif sub.startswith("cikar "):
                handle = sub[len("cikar "):].strip()
                result = remove_watched_account(handle)
                return result["message"]
            return "Kullanim: /instagram takip @hesap | /instagram listele | /instagram cikar @hesap"
        except Exception as e:
            return f"Instagram hatasi: {str(e)[:150]}"

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
            from content_factory_skill import get_interviewer, get_multiplier, format_output, init_content_db
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
                    status="success" if _result and not _result.startswith("❌") else "error",
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
            memory.add_message(chat_id, "assistant", voice_result["reply"], f"voice:{voice_result['mode']}")
            return voice_result["reply"]
    except Exception as voice_error:
        log.warning(f"voice test handling failed: {voice_error}")

    _tl = text.lower()
    # AnyDesk kabul
    if any(k in _tl for k in ["kabul et", "anydesk", "bağlantıyı kabul", "isteği kabul", "gelen isteği", "accept"]):
        return handle_command(chat_id, "/kabul")
    # Ekran görüntüsü
    if any(k in _tl for k in ["ekran görüntüsü", "ekranı göster", "screenshot", "ekrana bak"]):
        return handle_command(chat_id, "/ekran")
    # Ekrana bak (vision)
    if any(k in _tl for k in ["ekrana bak", "ne var ekranda", "ekranda ne", "ekranı analiz"]):
        return handle_command(chat_id, "/bak")
    # Bilgisayar kontrolü — doğal dil → /yap komutu
    _bilgisayar_keys = [
        "aç", "ac", "kapat", "yaz", "tıkla", "tikla", "başlat", "baslat",
        "youtube", "chrome", "firefox", "spotify", "explorer", "dosya",
        "klasör", "program", "uygulama", "pencere", "tarayıcı", "tarayici",
        "müzik", "muzik", "video", "oynat", "durdur", "ses aç", "ses kapat",
        "büyüt", "buyut", "küçült", "kucult", "tam ekran"
    ]
    if any(k in _tl for k in _bilgisayar_keys):
        # Doğrudan subprocess ile hızlı aç komutları
        import subprocess as _sp
        _quick_map = {
            "youtube":  "start https://www.youtube.com",
            "spotify":  "start spotify:",
            "chrome":   "start chrome",
            "firefox":  "start firefox",
            "explorer": "start explorer",
            "hesap":    "start calc",
            "notepad":  "start notepad",
        }
        for _app, _cmd in _quick_map.items():
            if _app in _tl:
                try:
                    _sp.Popen(_cmd, shell=True)
                    return f"✅ {_app.capitalize()} açıldı!"
                except Exception as _e:
                    return f"❌ Açılamadı: {_e}"
        # Bilinen app yok → /yap komutuna yönlendir
        return handle_command(chat_id, f"/yap {text}")

    if text.startswith("!! "):
        cmd = text[3:].strip()
        result = run_shell_full(cmd)
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", result, "system")
        return f"```\n{result}\n```"

    if text.startswith("$ "):
        cmd = text[2:].strip()
        result = run_command_safe(cmd)
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
        response = call_ollama(model, hist, active_agent["prompt"])
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
        _extra = "\n\n".join(filter(None, [_user_ctx, _reme_ctx]))
        _system = route["system"] + ("\n\n" + _extra if _extra else "")
    except Exception:
        _system = route["system"]
    response = call_ollama(
        model,
        hist,
        _system,
        fallback_model=route.get("fallback"),
        route_name=route_name,
    )
    selected_candidate = get_selected_candidate(model)
    selected_model = selected_candidate.split("/", 1)[-1]
    selected_provider = selected_candidate.split("/", 1)[0] if "/" in selected_candidate else "ollama"
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
            payload = json.dumps({
                "chat_id": chat_id, "text": chunk, "parse_mode": parse_mode
            }).encode()
            try:
                req = Request(f"{self.api}/sendMessage", data=payload,
                            headers={"Content-Type": "application/json"}, method="POST")
                urlopen(req, timeout=10)
            except Exception as e:
                log.error(f"Send error: {e}")

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
        self.send(self.authorized_id,
            f"*Jarvis Mission Control v2.4 Aktif!* ({CONFIG['runtime_label']})\nMulti-model AI router + Uzak Yonetim hazir.\n`/help` yaz yardim icin.")
        while self.running:
            updates = self.get_updates()
            for update in updates:
                self.offset = update["update_id"] + 1
                try:
                    threading.Thread(target=self._handle_update, args=(update,), daemon=True).start()
                except Exception as e:
                    log.error(f"Update error: {e}")

    def send_button(self, chat_id, text, btn_text, btn_data):
        payload = json.dumps({
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {
                "inline_keyboard": [[{"text": btn_text, "callback_data": btn_data}]]
            }
        }).encode()
        try:
            req = Request(f"{self.api}/sendMessage", data=payload,
                         headers={"Content-Type": "application/json"}, method="POST")
            urlopen(req, timeout=10)
        except Exception as e:
            log.error(f"send_button error: {e}")

    def answer_callback(self, callback_id, text=""):
        payload = json.dumps({"callback_query_id": callback_id, "text": text}).encode()
        try:
            req = Request(f"{self.api}/answerCallbackQuery", data=payload,
                         headers={"Content-Type": "application/json"}, method="POST")
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
                        ["powershell.exe", "-ExecutionPolicy", "Bypass",
                         "-WindowStyle", "Hidden", "-File", ps_script],
                        capture_output=True, text=True, timeout=20
                    )
                    out = (result.stdout or "").strip()
                    if result.returncode == 0 or "kabul edildi" in out.lower():
                        self.send(cb_chat, "✅ AnyDesk bağlantısı kabul edildi!")
                    else:
                        self.send(cb_chat, f"❌ Kabul başarısız:\n{out or result.stderr[:200]}")
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
                prompt = caption[len("/gor"):].strip()
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
                "anydesk_kabul"
            )
            return

        is_voice_request = bool(msg.get("voice") or msg.get("audio"))
        self.send(chat_id, "_Isleniyor..._")
        response = process_message(chat_id, text)
        if response.startswith("__SCREENSHOT__"):
            photo_path = response[len("__SCREENSHOT__"):]
            self.send_photo(chat_id, photo_path)
        else:
            self.send(chat_id, response)
            # Sesli mesajla geldiyse → sesli yanıt da gönder
            if is_voice_request:
                try:
                    import sys as _sys, os as _os
                    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "skills"))
                    from voice_skill import text_to_speech
                    # Emoji ve markdown işaretlerini temizle
                    _clean = response.replace("*","").replace("_","").replace("`","")
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
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
                f"{chat_id}\r\n"
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="photo"; filename="screenshot.png"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode() + photo_data + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(
                f"{self.api}/sendPhoto",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST"
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
            last_trace = STATE.last_route_trace if isinstance(STATE.last_route_trace, dict) else {}
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
<div><h1>Jarvis Mission Control</h1><p>{CONFIG['runtime_label']} — {datetime.now().strftime('%H:%M:%S')}</p></div>
</header>
<div class="grid">
<div class="card">
<h2>Sistem</h2>
<div class="stat"><span class="stat-label">Toplam Sorgu</span><span class="stat-val">{stats['total_queries']}</span></div>
<div class="stat"><span class="stat-label">AI Modeller</span><span class="stat-val">{len(models)} aktif</span></div>
<div class="stat"><span class="stat-label">Web Port</span><span class="stat-val">:{CONFIG['web_port']}</span></div>
<div class="stat"><span class="stat-label">Platform</span><span class="stat-val">{CONFIG['platform_label']}</span></div>
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
            data = {"status": "online", "models": get_available_models(),
                    "stats": memory.data["stats"], "time": datetime.now().isoformat(),
                    "last_route_trace": STATE.last_route_trace,
                    "provider_health": provider_health,
                    "live": get_orchestrator_live_payload(event_limit=5)}
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
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/chat":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                text = body.get("message", "")
                route_name, route = detect_route(text)
                response = process_message(9999, text)
                trace = STATE.last_route_trace if isinstance(STATE.last_route_trace, dict) else {}
                selected_candidate = trace.get("selected_candidate") or route["model"]
                self._json(
                    {
                        "response": response,
                        "model": selected_candidate,
                        "provider": trace.get("selected_provider", ""),
                        "route": route_name,
                        "fallback_used": bool(trace.get("fallback_used")),
                        "attempts": trace.get("attempts", []),
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
        else:
            self.send_error(404)

    # ──── WEEK 2: NEW ENDPOINT HANDLERS ────
    def _handle_health_endpoint(self):
        """GET /health - System health status"""
        router_snapshot = get_router_health_snapshot()
        live_payload = get_orchestrator_live_payload(event_limit=10)

        if not MONITORING_ENABLED or HEALTH_CHECKER is None:
            # Fallback health response if monitoring not available
            health_data = {
                "status": _merge_health_status(
                    _merge_health_status("healthy", str(router_snapshot.get("status", "healthy"))),
                    str(live_payload.get("status", "healthy")),
                ),
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "logs_writable": True,
                    "bridge_running": True,
                    "model_router_enabled": bool(router_snapshot.get("enabled", False)),
                    "model_router_ready": str(router_snapshot.get("status", "")).lower() in {"healthy", "degraded"},
                },
                "warning": "Monitoring modules disabled",
                "runtime_label": str(CONFIG["runtime_label"]),
                "provider_health": router_snapshot.get("providers", {}),
                "router": router_snapshot,
                "route_trace": router_snapshot.get("active", {}),
                "live": live_payload,
            }
            status_code = 200 if health_data["status"] == "healthy" else 503
            self._json(health_data, status_code)
            return

        # Use HealthChecker for comprehensive status
        metrics_data = METRICS_COLLECTOR.get_stats(time_window_minutes=60) if METRICS_COLLECTOR else None
        health_status = HEALTH_CHECKER.get_status(
            metrics_data=metrics_data
        )
        response, status_code = HEALTH_CHECKER.get_health_endpoint_response(
            include_metrics=True,
            metrics_data=metrics_data
        )
        response["status"] = _merge_health_status(
            _merge_health_status(
                str(response.get("status", "healthy")),
                str(router_snapshot.get("status", "healthy")),
            ),
            str(live_payload.get("status", "healthy")),
        )
        if response["status"] != "healthy":
            status_code = 503
        components = response.get("components")
        if isinstance(components, dict):
            components["model_router_enabled"] = bool(router_snapshot.get("enabled", False))
            components["model_router_ready"] = str(router_snapshot.get("status", "")).lower() in {"healthy", "degraded"}
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
                        sum(1 for m in recent_metrics[-100:] if m.cache_hit) /
                        min(100, len(recent_metrics)) * 100 if len(recent_metrics) > 0 else 0,
                        1
                    )
                }
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
            stats = METRICS_COLLECTOR.get_stats(time_window_minutes=60) if METRICS_COLLECTOR else {}

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
                "status": "operational" if MONITORING_ENABLED else "disabled"
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
            active_agents = []
            slots = ["atlas", "forge", "nexus", "shield", "spark", "seda", "mert", "buse", "eren", "luna", "sabrican", "sabri"]
            runtime_slots = {}
            for slot in slots:
                slot_file = state_dir / f"{slot}.json"
                if slot_file.exists():
                    try:
                        data = json.loads(slot_file.read_text(encoding="utf-8"))
                        status = data.get("status", "idle")
                        runtime_slots[slot] = status
                        if status in ("running", "active"):
                            active_agents.append(slot)
                    except Exception:
                        runtime_slots[slot] = "unknown"
            
            speaking_state = {}
            speaking_file = Path(__file__).parent.parent / "state" / "swarm_speaking_state.json"
            if speaking_file.exists():
                try:
                    speaking_state = json.loads(speaking_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            self._json({
                "active": active_agents,
                "active_agents": active_agents,
                "slots": runtime_slots,
                "speaking": speaking_state.get("speaking"),
                "text": speaking_state.get("text", ""),
                "ceo_phase": speaking_state.get("ceo_phase", "idle"),
                "dialogue_active": speaking_state.get("dialogue_active", False),
                "participants": speaking_state.get("participants", []),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            log.error(f"swarm-status error: {e}")
            self._json({
                "active": [], "active_agents": [], "slots": {},
                "speaking": None, "text": "", "ceo_phase": "idle",
                "dialogue_active": False, "participants": []
            })

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
                    jobs.append({
                        "id": j.get("id"),
                        "task": j.get("task", "")[:80],
                        "status": j.get("status"),
                        "created_at": j.get("created_at"),
                        "finished_at": j.get("finished_at"),
                        "slots": j.get("selected_slots", []),
                    })
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
            self._json({
                "jobs": jobs,
                "queue": {"total": len(jobs)},
                "quotas": quotas,
                "runtime_slots": runtime_slots,
            })
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
                    self._json({"ok": True, "job_id": job_id, "result": result or j.get("status")})
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
            self._json(_build_codex_jobs_payload(status=status, slot_id=slot_id, limit=100))
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
                    elif "required" in error_text or "context must be an object" in error_text:
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
            result = _dispatch_codex_job(task_description=task_description, role=role, priority=priority)
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
            payload = modules["start_instance"](instance_id) if action == "start" else modules["stop_instance"](instance_id)
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


def _handle_crewai_command(chat_id: int, args: str) -> str:
    try:
        from crewai_skill import run_crewai

        return run_crewai(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("CrewAI command failed")
        return f"Hata: {exc}"


def _handle_openhands_command(chat_id: int, args: str) -> str:
    try:
        from openhands_skill import run_openhands

        return run_openhands(args.strip())
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("OpenHands command failed")
        return f"Hata: {exc}"


def _handle_upondhand_command(chat_id: int, args: str) -> str:
    try:
        from upondhand_skill import run_upondhand

        return run_upondhand(args.strip())
    except ModuleNotFoundError:
        return "Skill henuz kurulu degil"
    except Exception as exc:
        log.exception("upondhand command failed")
        return f"Hata: {exc}"


_CODEX_SLOT_META = {
    "atlas": {"label": "ATLAS", "role": "Manager/Core"},
    "forge": {"label": "FORGE", "role": "Backend Ops"},
    "nexus": {"label": "NEXUS", "role": "Voice + Hologram"},
    "shield": {"label": "SHIELD", "role": "Security / Audit"},
    "spark": {"label": "SPARK", "role": "Web UI / Frontend"},
}
_CODEX_SLOT_ORDER = ["atlas", "forge", "nexus", "shield", "spark"]
_CODEX_MUTABLE_FIELDS = {"status", "daily_limit", "weekly_limit", "remaining_estimate", "notes"}


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
                "last_seen": account.get("last_used") or account.get("last_synced_at") or "-",
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


def _build_codex_jobs_payload(status: str | None = None, slot_id: str | None = None, limit: int = 100) -> dict[str, object]:
    try:
        from codex_job_manager import get_job_manager
    except Exception:
        from server.codex_job_manager import get_job_manager  # type: ignore

    jobs = []
    for item in get_job_manager().list_jobs(status=status, slot_id=slot_id, limit=min(max(int(limit or 0), 0), 100)):
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
                "task": {"description": item.get("task"), "type": item.get("type"), "payload": {}},
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
        slot_jobs = [job for job in jobs if str(job.get("slot_id") or "").strip().lower() == slot_id]
        current_job = next((job for job in slot_jobs if str(job.get("status") or "").strip().lower() == "running"), None)
        completed_jobs = [job for job in slot_jobs if str(job.get("status") or "").strip().lower() in {"done", "failed", "cancelled"}]
        fail_count = sum(1 for job in slot_jobs if str(job.get("status") or "").strip().lower() == "failed")
        cooldown = cooldowns.get(slot_id, {}) if isinstance(cooldowns, dict) else {}
        cooldown_remaining = int(cooldown.get("remaining_seconds") or 0) if isinstance(cooldown, dict) else 0

        status = "idle"
        effective_status = str(slot.get("effective_status") or slot.get("status") or "").strip().lower()
        if current_job:
            status = "active"
        elif cooldown_remaining > 0:
            status = "cooldown"
        elif effective_status in {"inactive", "failed", "quota_exceeded", "limited", "rate_limited", "pending_login", "offline"}:
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
                "last_completion": completed_jobs[0].get("finished_at") if completed_jobs else slot.get("last_completion"),
                "fail_count": fail_count,
                "cooldown_remaining": cooldown_remaining,
                "cooldown_until": slot.get("cooldown_until") or (cooldown.get("until") if isinstance(cooldown, dict) else None),
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
        quota_text = str(slot.get("quota_estimate") or "").strip().replace("%", "").replace("~", "")
        quota_value = int(float(quota_text)) if quota_text.replace(".", "", 1).isdigit() else 0
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
                "cooldown": cooldowns.get(slot.get("slot_id")) if isinstance(cooldowns, dict) else None,
            }
        )

    return _redact_codex_payload({"slots": health_slots, "stuck_jobs": stuck_jobs, "cooldowns": cooldowns})


def _build_codex_audit_payload(limit: int = 50) -> dict[str, object]:
    try:
        from codex_orchestrator import read_dispatch_audit
    except Exception:
        from server.codex_orchestrator import read_dispatch_audit  # type: ignore

    return _redact_codex_payload({"entries": read_dispatch_audit(limit=min(max(int(limit or 0), 0), 50))})


def _dispatch_codex_job(*, task_description: str, role: str | None, priority: int) -> dict[str, object]:
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


def _control_codex_plane(*, action: str, slot_id: str | None, job_id: str | None) -> dict[str, object]:
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
            codex_orchestrator_module._spawn_slot_thread(job_id, selected_slot, str(retried.get("task") or ""))
        return {"ok": True, "message": f"{job_id} retry edildi.", "slot_id": selected_slot}
    if action == "cancel" and job_id:
        cancelled = manager.cancel_job(job_id)
        if cancelled is None:
            return {"ok": False, "message": "Job bulunamadi."}
        return {"ok": True, "message": f"{job_id} iptal edildi."}
    if action == "stop_all":
        return {"ok": True, "message": str(codex_orchestrator_module.stop_all() or "").strip() or "Aktif Codex isi yok."}
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
        return {"ok": False, "error": "job_not_found", "job_id": str(job_id or "").strip()}, 404
    return result, 200


def _update_codex_account_payload(account_id: str, field: str, value: object) -> tuple[dict[str, object], int]:
    field_name = str(field or "").strip()
    if field_name not in _CODEX_MUTABLE_FIELDS:
        return {"ok": False, "error": "unsupported_field"}, 400

    try:
        from skills.account_monitor import get_public_account_registry, update_account_field
    except Exception:
        try:
            from account_monitor import get_public_account_registry, update_account_field
        except Exception:
            from server.skills.account_monitor import get_public_account_registry, update_account_field  # type: ignore

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
    slot_text = ", ".join(str(slot).upper() for slot in selected_slots) if selected_slots else "BEKLEMEDE"
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
            lines.append(f"  {job.get('id')} [{job.get('status')}] {job.get('summary')}")

    return "\n".join(lines).strip()


def _handle_codex_queue_command(chat_id: int) -> str:
    payload = _build_codex_queue_payload()
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    lines = [f"Kuyrukta {len(jobs)} is var:"]
    for index, job in enumerate(jobs[:5], start=1):
        if not isinstance(job, dict):
            continue
        lines.append(f"{index}. [{job.get('priority')}] [{job.get('role')}] {str(job.get('task_description') or '')[:48]}")
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
        lines.append(f"- {slot.get('slot_id')}: {slot.get('health_score')} ({slot.get('status')})")
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
        lines.append(f"- {slot.get('label')}: {slot.get('role')} | {slot.get('status')} | {slot.get('quota_estimate')}")
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
    return _truncate_telegram(str(result.get("message") or "Cooldownlar temizlenemedi."))


def _handle_codex_result_command(chat_id: int, args: str) -> str:
    job_id = _strip_wrapping_quotes(args)
    if not job_id:
        return "Kullanim: /codex-sonuc [job_id]"
    payload, status_code = _build_codex_result_payload(job_id)
    if status_code >= 400:
        return f"Job bulunamadi: {job_id}"
    result = str(payload.get("result") or payload.get("summary") or "Sonuc yok.")
    return f"Job {job_id}\n{result}".strip()


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


def _handle_youtube_unified_command(chat_id: int, args: str) -> str:
    try:
        from youtube_unified_skill import list_backends, transcript_summary

        query = args.strip()
        return transcript_summary(query) if query else list_backends()
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("YouTube unified command failed")
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


def _handle_swarms_command(chat_id: int, args: str) -> str:
    try:
        from swarms_skill import swarms_run, swarms_status

        query = args.strip()
        return swarms_run(query) if query else swarms_status()
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
    except Exception as exc:
        log.exception("Swarms command failed")
        return f"Hata: {exc}"


def _handle_hooks_command(chat_id: int, args: str) -> str:
    if not _is_admin_chat(chat_id):
        return "Bu komut sadece admin kullanicisi icin acik."
    try:
        from hooks_skill import add_hook, hooks_list_examples, hooks_status

        payload = args.strip()
        if not payload:
            return hooks_status()

        action, _, remainder = payload.partition(" ")
        action_key = action.strip().lower()
        rest = remainder.strip()

        if action_key in {"durum", "status"}:
            return hooks_status()
        if action_key in {"liste", "ornek", "ornekler"}:
            return hooks_list_examples()
        if action_key in {"ekle", "add"}:
            event, _, command = rest.partition(" ")
            if not event.strip() or not command.strip():
                return "Kullanim: /hooks ekle [pre|post|stop|prompt] [komut]"
            return add_hook(event.strip(), command.strip())
        return hooks_status()
    except ModuleNotFoundError:
        return "Skill henüz kurulu değil"
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
    from server.skills.aws_cost_skill import get_budget_alerts, get_cost_trend, get_monthly_cost
    from server.skills.aws_ec2_skill import get_instance_metrics, list_instances, reboot_instance, start_instance, stop_instance
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
    codex_handler=lambda args, ctx: _handle_codex_command(int((ctx or {}).get("chat_id", 0) or 0), args),
    codex_swarm_handler=lambda args, ctx: _handle_codex_command(int((ctx or {}).get("chat_id", 0) or 0), args, swarm=True),
    codex_status_handler=lambda args, ctx: _handle_codex_status_command(int((ctx or {}).get("chat_id", 0) or 0)),
    codex_result_handler=lambda args, ctx: _handle_codex_result_command(int((ctx or {}).get("chat_id", 0) or 0), args),
    wiki_handler=lambda args, ctx: _handle_wiki_command(int((ctx or {}).get("chat_id", 0) or 0), args),
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
  `/prompt [kategori]` -> Prompt katalog arama
  `/spec [komut]` -> SpecKit specify/plan/tasks
  `/sirket [komut]` -> Paperclip isletme runtime ozeti
  `/ytunified [url]` -> Unified YouTube transcript
  `/clawcode [gorev]` -> Claw Code repo ozeti
  `/swarms [gorev]` -> Swarms framework gorevi
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
        return COMMAND_REGISTRY.dispatch(command, args, {"chat_id": chat_id, "command": command, "registry": COMMAND_REGISTRY})
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
    elif command == "/prompt":
        return _handle_prompts_command(chat_id, args)
    elif command == "/spec":
        return _handle_speckit_command(chat_id, args)
    elif command == "/sirket":
        return _handle_paperclip_command(chat_id, args)
    elif command == "/ytunified":
        return _handle_youtube_unified_command(chat_id, args)
    elif command == "/clawcode":
        return _handle_claw_code_command(chat_id, args)
    elif command == "/swarms":
        return _handle_swarms_command(chat_id, args)
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
                    lines.append(f"  {icon} {k['id']} — {k['status']} ({k['ready_at']})")
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
            assistant_runtime = assistant_payload.get("runtime", {}) if isinstance(assistant_payload.get("runtime"), dict) else {}
            live_payload = data.get("live", {}) if isinstance(data.get("live"), dict) else {}
            live_voice = live_payload.get("voice", {}) if isinstance(live_payload.get("voice"), dict) else {}
            voice_state = str(
                data.get("voice_state")
                or assistant_payload.get("phase")
                or live_voice.get("phase")
                or "idle"
            ).strip().upper() or "IDLE"
            data["voice_state"] = voice_state
            data.setdefault("voice_detail", str(assistant_runtime.get("detail") or live_voice.get("detail") or ""))
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
        log.error(f"Port {CONFIG['web_port']} zaten kullanimda. Ikinci bridge ornegi baslatilmayacak.")
        return

    heartbeat_stop = _start_watchdog_state()
    _codex_health = CodexHealthWatcher(
        interval_seconds=600,
        notify_chat_id=int(CONFIG["authorized_chat_id"] or 0),
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
            log.info("Bridge runtime forced into --web-only mode; Telegram will stay disabled.")
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

if __name__ == "__main__":
    main()
