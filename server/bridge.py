#!/usr/bin/env python3
"""
JARVIS MISSION CONTROL — bridge.py v2.2 (Windows/Pinokio Edition)
Multi-Model AI Router | Telegram + Web Dashboard | eBay + Trendyol Skills
"""

import os
import json
import time
import logging
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError

# ─────────────────────────── PATHS ────────────────────────────────
BASE_DIR = Path(__file__).parent          # app/
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ─────────────────────────── ENV / API KEYS ───────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
SERPER_API_KEY    = os.environ.get("SERPER_API_KEY", "")
OLLAMA_API_KEY    = os.environ.get("OLLAMA_API_KEY", "ee772cf9b7ac4c0c90fff1de8ce1c61a.IABOZ2BhMZ_4x4J3ojNOczI4")

KNOWLEDGE_DIR = str(BASE_DIR / "knowledge")
SOUL_PATH     = str(BASE_DIR / "soul.md")
SKILLS_PATH   = str(BASE_DIR / "skills")
PRINTIFY_TOKEN_PATH = str(BASE_DIR / "printify_token.txt")

# skills dizinini import path'e ekle
if SKILLS_PATH not in sys.path:
    sys.path.insert(0, SKILLS_PATH)

# ─────────────────────────── CONFIG ───────────────────────────────
CONFIG = {
    "telegram_token": "8295826032:AAGn4XRJxQi98hqqZLRMcvOEaeowSGYDt-k",
    "authorized_chat_id": 5847386182,
    "ollama_url": "http://127.0.0.1:11434",
    "web_port": 8081,
    "log_file": str(DATA_DIR / "jarvis.log"),
    "memory_file": str(DATA_DIR / "memory.json"),
}

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

# ─────────────────────────── MODEL ROUTES ─────────────────────────
MODEL_ROUTES = {
    "code": {
        "model": "qwen3-coder:480b-cloud",
        "fallback": "deepseek-v3.1:671b-cloud",
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
        "model": "minimax-m2:cloud",
        "fallback": "minimax-m2.7:cloud",
        "keywords": [],
        "system": "Sen yardimci bir AI asistanisin. Kisa ve net yanit ver."
    },
    "chat": {
        "model": "minimax-m2:cloud",
        "fallback": "minimax-m2.7:cloud",
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
ACTIVE_AGENTS = {}
CONTENT_FACTORY_SESSIONS = {}

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
                    "backend": "openai", "model_name": "llama3.2:latest",
                    "base_url": "http://127.0.0.1:11434/v1", "api_key": "ollama"
                }
                log.info("ReMe: Ollama embedding aktif (OpenAI key girilmedi)")
            _reme_instance = ReMe(
                working_dir=str(BASE_DIR / ".reme"),
                enable_logo=False, log_to_console=False,
                default_llm_config={
                    "backend": "openai", "model_name": "llama3.2:latest",
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
class Memory:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()

    def _load(self):
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"sessions": {}, "history": [], "stats": {"total_queries": 0}}

    def _save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_message(self, chat_id, role, content, model=None):
        key = str(chat_id)
        if key not in self.data["sessions"]:
            self.data["sessions"][key] = []
        self.data["sessions"][key].append({
            "role": role, "content": content,
            "model": model, "time": datetime.now().isoformat()
        })
        self.data["sessions"][key] = self.data["sessions"][key][-20:]
        self.data["stats"]["total_queries"] += 1
        self._save()

    def get_history(self, chat_id, last_n=10):
        key = str(chat_id)
        msgs = self.data["sessions"].get(key, [])
        return [{"role": m["role"], "content": m["content"]} for m in msgs[-last_n:]]

    def clear(self, chat_id):
        self.data["sessions"][str(chat_id)] = []
        self._save()

memory = Memory(CONFIG["memory_file"])

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

def get_available_models() -> list:
    try:
        req = Request(f"{CONFIG['ollama_url']}/api/tags")
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except:
        return []

def call_ollama(model: str, messages: list, system: str = None, max_tokens: int = 1024, num_ctx: int = 2048) -> str:
    # Cloud modeller (:cloud suffix) available kontrolü atla — Ollama direkt yönlendirir
    if not model.endswith(":cloud"):
        available = get_available_models()
        if not any(model.split(":")[0] in m for m in available):
            model = available[0] if available else None
        if not model:
            return "Hicbir Ollama modeli bulunamadi. Ollama'nin calistigini kontrol edin."
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": max_tokens, "num_ctx": num_ctx}
    }
    if system:
        payload["system"] = system
    try:
        data = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
        req = Request(f"{CONFIG['ollama_url']}/api/chat", data=data,
                     headers=headers, method="POST")
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "Bos yanit")
    except URLError as e:
        for _retry in range(2):
            time.sleep(2 ** _retry)
            try:
                with urlopen(req, timeout=120) as _resp:
                    _result = json.loads(_resp.read())
                    return _result.get("message", {}).get("content", "Bos yanit")
            except Exception:
                pass
        return f"Ollama baglanamadi: {e}"

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

*AI Uzman Ajanlar:*
  `/jcoder [gorev]` -> Jarvis Coder - bridge.py bilir, kod yazar
  `/skill [isim] [aciklama]` -> Yeni Jarvis skill dosyasi yaz
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

*Yeni Ajanlar:*
  `/agent growth-hacker` -> Buyume stratejisti
  `/agent icerik-stratejisti` -> Cok platform icerik
  `/agent pazar-arastirmacisi` -> Pazar & rakip analizi
  `/agent seo-uzmani` -> TR SEO optimizasyonu
  `/agent rakip-analisti` -> Rekabet istihbarat

*Modeller:*
{models_str}"""

    elif command == "/status":
        try:
            info = get_system_info()
            models = get_available_models()
            stats = memory.data["stats"]
            return f"""*Jarvis Sistem Durumu*
CPU: `{info['cpu']}` | RAM: `{info['ram']}`
AI Modeller: {len(models)} aktif
Toplam Sorgu: {stats['total_queries']}
Saat: {datetime.now().strftime('%H:%M:%S')}
Servis: Aktif (Pinokio)"""
        except Exception as e:
            return f"Durum alinamadi: {e}"

    elif command == "/durum":
        try:
            info = get_system_info()
            models = get_available_models()
            lines = ["*Jarvis Sistem Durumu*\n"]
            lines.append(f"CPU: `{info['cpu']}`")
            lines.append(f"RAM: `{info['ram']}`")
            lines.append(f"Disk: `{info['disk']}`")
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
            return "Kullanim: /model [route] [model]\nOrnek: /model chat qwen3:8b\nOrnek: /model reasoning minimax-m2.7:cloud\n\nRoute'lar: " + ", ".join(MODEL_ROUTES.keys())
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
            response = call_ollama(route["model"], history, route["system"])
            memory.add_message(chat_id, "user", f"/ebay {query}")
            memory.add_message(chat_id, "assistant", response, route["model"])
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
            response = call_ollama(route["model"], history, route["system"])
            return f"*Trendyol Analizi:*\n\n{response}"

    elif command == "/code":
        task = args or "Merhaba dunya"
        route = MODEL_ROUTES["code"]
        history = [{"role": "user", "content": f"Su gorevi icin tam calisir kod yaz: {task}"}]
        response = call_ollama(route["model"], history, route["system"])
        memory.add_message(chat_id, "user", f"/code {task}")
        memory.add_message(chat_id, "assistant", response, route["model"])
        return f"*Kod:*\n\n{response}"

    elif command == "/plan":
        task = args or "proje"
        route = MODEL_ROUTES["reasoning"]
        prompt = f"Su proje icin detayli plan olustur: {task}\n1.Hedef 2.Gereksinimler 3.Adimlar 4.Riskler 5.Basari kriterleri"
        history = [{"role": "user", "content": prompt}]
        response = call_ollama(route["model"], history, route["system"])
        memory.add_message(chat_id, "user", f"/plan {task}")
        memory.add_message(chat_id, "assistant", response, route["model"])
        return f"*Plan:*\n\n{response}"

    elif command == "/task":
        task_goal = args or "Genel durum ozeti ve yapilacaklar listesi hazirla"
        try:
            from ollama_orchestrator import OrchestratorSkill
            orch = OrchestratorSkill(call_ollama)
            result = orch.run(task_goal)
            memory.add_message(chat_id, "user", f"/task {task_goal}")
            memory.add_message(chat_id, "assistant", result, "orchestrator")
            return result
        except Exception:
            route = MODEL_ROUTES["code"]
            history = [{"role": "user", "content": f"Bu gorevi tamamla: {task_goal}"}]
            response = call_ollama(route["model"], history, route["system"])
            memory.add_message(chat_id, "user", f"/task {task_goal}")
            memory.add_message(chat_id, "assistant", response, route["model"])
            return f"*Task Sonucu:*\n\n{response}"

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
                "model": "llama3.2:latest"
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
            max_tokens=110, num_ctx=512)
        memory.add_message(chat_id, "user", f"/reklam {urun}")
        memory.add_message(chat_id, "assistant", response, route["model"])
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
            max_tokens=130, num_ctx=512)
        memory.add_message(chat_id, "user", f"/icerik {metin[:50]}")
        memory.add_message(chat_id, "assistant", response, route["model"])
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
            max_tokens=120, num_ctx=512)
        memory.add_message(chat_id, "user", f"/rakip {hedef}")
        memory.add_message(chat_id, "assistant", response, route["model"])
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
            max_tokens=130, num_ctx=512)
        memory.add_message(chat_id, "user", f"/abtest {sayfa[:50]}")
        memory.add_message(chat_id, "assistant", response, route["model"])
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
            max_tokens=120, num_ctx=512)
        memory.add_message(chat_id, "user", f"/analiz {veri[:50]}")
        memory.add_message(chat_id, "assistant", response, route["model"])
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
        reply = call_ollama(route["model"], [{"role": "user", "content": prompt}],
                           max_tokens=800, num_ctx=2048)
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
        reply = call_ollama(route["model"], [{"role": "user", "content": prompt}],
                           max_tokens=600, num_ctx=4096)
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
        reply = call_ollama(route["model"], [{"role":"user","content":args}],
                           system=system_prompt, max_tokens=1500, num_ctx=4096)
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
        reply = call_ollama(route["model"],
                           [{"role":"user","content":f"Skill yaz: {args}"}],
                           system=system_prompt, max_tokens=1500, num_ctx=4096)
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
        reply = call_ollama(route["model"], [{"role":"user","content":args}],
                           system=system_prompt, max_tokens=1200, num_ctx=4096)
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
        return handle_command(chat_id, text)

    # ── NATURAL LANGUAGE INTERCEPTS ────────────────────────────────
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
        model = active_agent.get("model", "llama3.2:latest")
        response = call_ollama(model, hist, active_agent["prompt"])
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", response, model)
        return f"[{active_agent['name'].upper()}] {response}"

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
    response = call_ollama(model, hist, _system)
    memory.add_message(chat_id, "user", text)
    memory.add_message(chat_id, "assistant", response, model)
    reme_save(text, response)
    model_short = model.split(":")[0].replace("deepseek-", "DS-")
    return f"[{model_short}] {response}"

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
                  "*Jarvis Mission Control v2.4 Aktif!* (Pinokio Edition)\nMulti-model AI router + Uzak Yonetim hazir.\n`/help` yaz yardim icin.")
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
        if self.path in ("/", "/dashboard"):
            models = get_available_models()
            stats = memory.data["stats"]
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
<div><h1>Jarvis Mission Control</h1><p>Pinokio Edition — {datetime.now().strftime('%H:%M:%S')}</p></div>
</header>
<div class="grid">
<div class="card">
<h2>Sistem</h2>
<div class="stat"><span class="stat-label">Toplam Sorgu</span><span class="stat-val">{stats['total_queries']}</span></div>
<div class="stat"><span class="stat-label">AI Modeller</span><span class="stat-val">{len(models)} aktif</span></div>
<div class="stat"><span class="stat-label">Web Port</span><span class="stat-val">:{CONFIG['web_port']}</span></div>
<div class="stat"><span class="stat-label">Platform</span><span class="stat-val">Pinokio/Windows</span></div>
</div>
<div class="card">
<h2>Router</h2>
<div class="stat"><span class="stat-label">Sohbet</span><span class="stat-val">llama3.2</span></div>
<div class="stat"><span class="stat-label">Kod</span><span class="stat-val">deepseek-coder</span></div>
<div class="stat"><span class="stat-label">Akil/Plan</span><span class="stat-val">llama3.2</span></div>
<div class="stat"><span class="stat-label">eBay/Trendyol</span><span class="stat-val">llama3.2</span></div>
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
}}catch(e){{removeLastSys();addMsg('sys','Hata: '+e);}}
}}
function addMsg(role,text,model){{
const c=document.getElementById('msgs');
const d=document.createElement('div'); d.className='msg '+role;
if(model){{const b=document.createElement('div');b.className='badge';b.textContent=model.split(':')[0];d.appendChild(b);}}
const t=document.createElement('div');
t.innerHTML=text.replace(/```([\\s\\S]*?)```/g,'<pre>$1</pre>').replace(/\\*\\*(.+?)\\*\\*/g,'<b>$1</b>').replace(/\\n/g,'<br>');
d.appendChild(t); c.appendChild(d); c.scrollTop=c.scrollHeight;
}}
function removeLastSys(){{
const s=document.querySelectorAll('.msg.sys');
if(s.length)s[s.length-1].remove();
}}
</script></body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/api/status":
            data = {"status": "online", "models": get_available_models(),
                    "stats": memory.data["stats"], "time": datetime.now().isoformat()}
            self._json(data)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/chat":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                text = body.get("message", "")
                route_name, route = detect_route(text)
                response = process_message(9999, text)
                self._json({"response": response, "model": route["model"], "route": route_name})
            except Exception as e:
                self._json({"error": str(e)}, 500)
        else:
            self.send_error(404)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

# ─────────────────────────── MAIN ─────────────────────────────────
def start_web():
    HTTPServer(("127.0.0.1", CONFIG["web_port"]), WebHandler).serve_forever()

def main():
    log.info("=" * 55)
    log.info("  JARVIS MISSION CONTROL v2.2 — Pinokio Edition")
    log.info("=" * 55)
    log.info(f"BASE_DIR: {BASE_DIR}")
    models = get_available_models()
    if models:
        log.info(f"Ollama aktif — {len(models)} model: {', '.join(models[:3])}")
    else:
        log.warning("Ollama bagli degil! Ollama'yi baslatin.")
    threading.Thread(target=start_web, daemon=True).start()
    time.sleep(1)
    url = f"http://127.0.0.1:{CONFIG['web_port']}"
    log.info(f"Web dashboard: {url}")
    print(url, flush=True)
    bot = TelegramBot(CONFIG["telegram_token"], CONFIG["authorized_chat_id"])
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.running = False

if __name__ == "__main__":
    main()
