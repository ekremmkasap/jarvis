#!/usr/bin/env python3
"""
JARVIS MISSION CONTROL — bridge.py v2.1
Multi-Model AI Router | Telegram + Web Dashboard | eBay + Trendyol Skills
"""

import os
import json
import time
import logging
import threading
import subprocess
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError

# ─────────────────────────── CONFIG ───────────────────────────────
CONFIG = {
    "telegram_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "authorized_chat_id": int(os.environ.get("TELEGRAM_CHAT_ID", "0") or 0),
    "ollama_url": "http://127.0.0.1:11434",
    "web_port": 8080,
    "log_file": "/home/userk/.jarvis/jarvis.log",
    "memory_file": "/home/userk/.jarvis/memory.json",
}

# ─────────────────────────── LOGGING ──────────────────────────────
os.makedirs("/home/userk/.jarvis", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("jarvis")


# ─── KNOWLEDGE BASE (Eğitim Dosyaları) ────────────────────────────────────────
import glob as _glob

KNOWLEDGE_DIR = "/opt/jarvis/knowledge"
KNOWLEDGE = {}

def _load_knowledge():
    global KNOWLEDGE
    try:
        files = _glob.glob(f"{KNOWLEDGE_DIR}/*.md")
        for fp in files:
            name = fp.split("/")[-1].replace(".md", "")
            with open(fp, "r") as f:
                KNOWLEDGE[name] = f.read()
        log.info(f"Bilgi bankasi yuklendi: {list(KNOWLEDGE.keys())}")
    except Exception as e:
        log.warning(f"Bilgi bankasi yuklenemedi: {e}")

def get_relevant_knowledge(text: str) -> str:
    """Mesaja gore alakali bilgi snippet'i sec"""
    text_lower = text.lower()
    snippets = []
    
    # Her zaman profil ekle (kisa)
    if "profil" in KNOWLEDGE:
        profile_lines = [l for l in KNOWLEDGE["profil"].split("\n") 
                        if l.startswith("- ") or l.startswith("**")][:8]
        snippets.append("Kullanici profili:\n" + "\n".join(profile_lines))
    
    # eBay sorusuysa
    if any(k in text_lower for k in ["ebay", "dropship", "listing", "urun", "satis"]):
        if "ebay_strateji" in KNOWLEDGE:
            # Ilk 500 karakter
            snippets.append("eBay Bilgisi:\n" + KNOWLEDGE["ebay_strateji"][:600])
    
    # Trendyol sorusuysa
    if any(k in text_lower for k in ["trendyol", "tr pazar", "turkiye"]):
        if "trendyol_strateji" in KNOWLEDGE:
            snippets.append("Trendyol Bilgisi:\n" + KNOWLEDGE["trendyol_strateji"][:600])
    
    return "\n\n".join(snippets) if snippets else ""

_load_knowledge()

# ─── SOUL (Kimlik) — must be before MODEL_ROUTES ──────────────────
try:
    with open("/opt/jarvis/soul.md", "r") as _f:
        JARVIS_SOUL = _f.read()
    log.info("✅ soul.md yuklendi")
except Exception as _e:
    JARVIS_SOUL = "Sen Jarvis'sin, Ekrem'in AI asistani. Zeki, pratik, Tony Stark tarzi."
    log.warning(f"soul.md bulunamadi: {_e}")

# ─────────────────────────── MODEL ROUTES ─────────────────────────
MODEL_ROUTES = {
    "code": {
        "model": "deepseek-coder:latest",
        "fallback": "qwen2.5-coder:7b",
        "keywords": ["kod", "yaz", "python", "javascript", "bug", "hata", "script",
                     "code", "write", "function", "class", "debug", "fix", "program"],
        "system": "Sen uzman bir yazilim gelistiricisin. Temiz, yorumlanmis ve calisan kod yaz."
    },
    "reasoning": {
        "model": "deepseek-r1:latest",
        "fallback": "llama3.2:latest",
        "keywords": ["neden", "analiz", "planla", "strateji", "dusun", "mantik",
                     "why", "analyze", "plan", "strategy", "think", "reason", "decide"],
        "system": "Sen derin dusunen bir stratejist ve analistsin. Adim adim mantik yurut."
    },
    "search": {
        "model": "llama3.2:latest",
        "fallback": "mistral:latest",
        "keywords": ["ara", "bul", "ebay", "trendyol", "urun", "fiyat", "piyasa",
                     "search", "find", "product", "price", "market", "trend"],
        "system": "Sen bir e-ticaret ve piyasa arastirma uzmaninisin. Detayli ve pratik bilgi ver."
    },
    "system": {
        "model": "llama3.2:latest",
        "fallback": "mistral:latest",
        "keywords": ["durum", "sistem", "servis", "sunucu", "calistir", "durdur",
                     "status", "service", "server", "run", "stop", "restart", "memory", "cpu"],
        "system": "Sen bir Linux sistem yoneticisisin. Komutlari dogru ve guvenli ver."
    },
    "chat": {
        "model": "llama3.2:latest",
        "fallback": "mistral:latest",
        "keywords": [],
        "system": JARVIS_SOUL
    }
}

# ─────────────────────────── MEMORY ───────────────────────────────
def _get_best_model(task_type="general"):
    """Görev türüne göre en iyi modeli seç"""
    import urllib.request as ur, json
    try:
        with ur.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            models = [m["name"] for m in json.loads(r.read())["models"]]
    except:
        return "llama3.2:latest"
    
    preferences = {
        "code":    ["qwen2.5-coder:7b", "deepseek-coder:latest", "qwen2.5-coder:3b", "llama3.2:latest"],
        "reason":  ["deepseek-r1:8b", "llama3.1:latest", "mistral:latest", "llama3.2:latest"],
        "vision":  ["llava:7b", "moondream:latest", "llama3.2:latest"],
        "embed":   ["nomic-embed-text:latest", "llama3.2:latest"],
        "general": ["mistral:latest", "llama3.1:latest", "llama3.2:latest"],
    }
    for candidate in preferences.get(task_type, preferences["general"]):
        if any(candidate in m for m in models):
            return candidate
    return "llama3.2:latest"


# ─── MEMORY SYSTEM ───────────────────────────────────────────────────────────
import sys as _sys
_sys.path.insert(0, "/opt/jarvis/skills")
try:
    from memory_skill import save_message, get_history, format_history_for_ollama
    from memory_skill import save_fact, get_facts, get_user_context
    from memory_skill import add_task, get_tasks, update_task, daily_memory_report
    from memory_skill import init_db
    init_db()
    MEMORY_ENABLED = True
except Exception as _me:
    MEMORY_ENABLED = False
    def save_message(*a, **k): pass
    def get_history(*a, **k): return []
    def format_history_for_ollama(*a, **k): return []
    def get_user_context(*a, **k): return ""
    def add_task(*a, **k): return 0
    def get_tasks(*a, **k): return "Hafıza kapalı"
    def update_task(*a, **k): return ""
    def daily_memory_report(*a, **k): return "Hafıza kapalı"
# ─────────────────────────────────────────────────────────────────────────────
# ─── INTENT CLASSIFIER ───────────────────────────────────────────────────────
try:
    from intent_skill import classify_intent, handle_with_intent
    INTENT_ENABLED = True
except Exception as _ie:
    INTENT_ENABLED = False
    def classify_intent(t): return None
    def handle_with_intent(t, u=None): return None
# ─────────────────────────────────────────────────────────────────────────────

class Memory:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()

    def _load(self):
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except:
            return {"sessions": {}, "history": [], "stats": {"total_queries": 0}}

    def _save(self):
        with open(self.filepath, "w") as f:
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
        if route_name == "chat":
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

def call_ollama(model: str, messages: list, system: str = None) -> str:
    available = get_available_models()
    if not any(model.split(":")[0] in m for m in available):
        model = available[0] if available else None
    if not model:
        return "Hicbir Ollama modeli bulunamadi."
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 1024}
    }
    if system:
        payload["system"] = system
    try:
        data = json.dumps(payload).encode()
        req = Request(f"{CONFIG['ollama_url']}/api/chat", data=data,
                     headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "Bos yanit")
    except URLError as e:
        return f"Ollama hatasi: {e}"

def run_command_safe(cmd: str) -> str:
    ALLOWED = ["ps", "top", "free", "df", "ollama", "systemctl status",
               "journalctl", "ls", "cat", "echo", "ping", "ip addr", "ss"]
    if not any(cmd.startswith(a) for a in ALLOWED):
        return "Bu komut icin izin yok."
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout[:2000] or result.stderr[:500] or "Cikti yok."
    except subprocess.TimeoutExpired:
        return "Komut zaman asimina ugradi."

# ─────────────────────────── COMMANDS ─────────────────────────────
def handle_command(chat_id: int, cmd: str) -> str:
    parts = cmd.split(" ", 2)
    command = parts[0].lower()
    args = " ".join(parts[1:]) if len(parts) > 1 else ""

    if command in ("/start", "/help"):
        available = get_available_models()
        models_str = "\n".join([f"  - {m}" for m in available]) or "  - (model yok)"
        return f"""*Jarvis Mission Control v2.1*

*Komutlar:*
  `/status` -> Sistem durumu
  `/models` -> AI modeller
  `/reset` -> Gecmisi sil
  `/ebay [urun]` -> eBay analizi
  `/hava [şehir]` -> Hava durumu
  `/haber [konu]` -> Son haberler
  `/altin` -> Altın & döviz fiyatları
  `/kur [100 USD TRY]` -> Döviz çevirici
  `/hesap [işlem]` -> Hesap makinesi
  `/printify [niyet]` -> Printify POD analizi
  `/trendyol [urun]` -> Trendyol TR analizi
  `/code [gorev]` -> Kod yaz
  `/plan [proje]` -> Plan olustur
  `$ [komut]` -> Sunucu komutu

*Modeller:*
{models_str}

*Routing:* Mesajina gore otomatik model secilir."""

    elif command == "/status":
        try:
            cpu = subprocess.run("top -bn1 | grep 'Cpu' | awk '{print $2}'",
                               shell=True, capture_output=True, text=True).stdout.strip()
            mem = subprocess.run("free -h | awk '/^Mem:/ {print $3\"/\"$2}'",
                               shell=True, capture_output=True, text=True).stdout.strip()
            models = get_available_models()
            stats = memory.data["stats"]
            return f"""*Jarvis Sistem Durumu*
CPU: `{cpu}%` | RAM: `{mem}`
AI Modeller: {len(models)} aktif
Toplam Sorgu: {stats['total_queries']}
Saat: {datetime.now().strftime('%H:%M:%S')}
Servis: Aktif"""
        except Exception as e:
            return f"Durum alinamadi: {e}"

    elif command == "/models":
        models = get_available_models()
        return "Mevcut Modeller:\n" + "\n".join([f"- {m}" for m in models]) if models else "Ollama bagli degil."

    elif command == "/reset":
        memory.clear(chat_id)
        return "Konusma gecmisi temizlendi."

    elif command == "/ebay":
        query = args or "kazancli dropshipping urun"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from ebay_research import analyze_product, format_report
            result = analyze_product(query)
            return format_report(result)
        except Exception as e:
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

    elif command == "/hafiza":
        uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
        return daily_memory_report(uid)

    elif command == "/gorev":
        uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
        return get_tasks(uid)

    elif command == "/gorev-ekle":
        if not args:
            return "Kullanım: /gorev-ekle Görev başlığı"
        uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
        task_id = add_task(uid, args, "normal")
        return f"✅ Görev eklendi: #{task_id} — {args}"

    elif command == "/gorev-bitti":
        if not args:
            return "Kullanım: /gorev-bitti [id]"
        uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
        try:
            return update_task(uid, int(args.strip()), "done")
        except:
            return "❌ Geçersiz görev ID"

    elif command == "/hava":
        city = args or "Istanbul"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import get_weather
            return get_weather(city)
        except Exception as e:
            return f"Hava hatası: {e}"

    elif command == "/haber":
        topic = args or "turkiye"
        import urllib.request as ur, re
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
            lines = [f"📰 **Son Haberler — {topic.upper()}**\n"]
            for i, t in enumerate(titles[1:6]):
                lines.append(f"{i+1}. {t.strip()}")
            return "\n".join(lines) if len(lines) > 1 else "❌ Haber bulunamadı."
        except Exception as e:
            return f"❌ Haber hatası: {e}"

    elif command == "/altin":
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import get_gold_price
            return get_gold_price()
        except Exception as e:
            return f"Altın hatası: {e}"

    elif command == "/kur":
        parts = args.split() if args else []
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import get_currency
            if len(parts) >= 3:
                return get_currency(float(parts[0]), parts[1], parts[2])
            elif len(parts) == 2:
                return get_currency(1, parts[0], parts[1])
            else:
                return get_currency(1, "USD", "TRY")
        except Exception as e:
            return f"Kur hatası: {e}"

    elif command == "/hesap":
        if not args:
            return "Kullanım: /hesap 2+2 veya /hesap sqrt(144)"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import calculate
            return calculate(args)
        except Exception as e:
            return f"Hesap hatası: {e}"

    elif command == "/printify":
        query = args or "genel"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            import importlib, os
            token = ""
            try:
                with open("/opt/jarvis/printify_token.txt") as f:
                    token = f.read().strip()
            except:
                pass
            if not token:
                return "Printify token gerekli. /printify_setup komutu ile ayarla veya token’ı /opt/jarvis/printify_token.txt dosyasına yaz."
            from printify_skill import format_overview, analyze_product_opportunity
            if query in ("genel", "durum", "status", "shop"):
                return format_overview(token)
            else:
                return analyze_product_opportunity(token, query)
        except Exception as e:
            return f"Printify hatası: {e}"

    elif command == "/trendyol":
        query = args or "bluetooth kulaklik"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from trendyol_skill import full_trendyol_analysis
            return full_trendyol_analysis(query)
        except Exception as e:
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

    elif command == "/agent":
        agent_name = args.strip()
        if not agent_name:
            import sys
            sys.path.insert(0, "/opt/jarvis/skills")
            try:
                from claude_agent_skill import list_all_agents
                agents = list_all_agents()
                txt = "\n".join([f"- {a}" for a in agents[:50]])
                return f"🤖 *Yüklü Ajanlar ({len(agents)})*:\n\n{txt}"
            except Exception as e:
                return f"Ajanlar listelenemedi: {e}"
        
        # specific agent execution
        try:
            import sys
            sys.path.insert(0, "/opt/jarvis/skills")
            from claude_agent_skill import get_agent_prompt
            prompt = get_agent_prompt(agent_name)
            if not prompt:
                return f"❌ '{agent_name}' adinda bir ajan bulunamadi. /agent yazip listeyi gor."
            # Set the user state/memory to use this agent context
            return f"✅ *{agent_name.upper()}* ajani aktif edildi! Lutfen simdi soru sor.\n\n_Agent Profile Preview:_ {prompt[:100]}..."
        except Exception as e:
            return f"❌ Ajan kullanilamiyor: {e}"

    return f"Bilinmeyen komut: {command}\n/help yaz yardim icin."

# ─────────────────────────── PROCESS MESSAGE ──────────────────────
def process_message(chat_id: int, text: str) -> str:
    text = text.strip()
    if text.startswith("/"):
        return handle_command(chat_id, text)
    if text.startswith("$ ") or text.startswith("!"):
        cmd = text[2:].strip()
        result = run_command_safe(cmd)
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", result, "system")
        return f"```\n{result}\n```"
    # ── INTENT CHECK: Doğal dil → komut (komut prefix gerektirmez) ──
    if INTENT_ENABLED:
        try:
            _intent_response = handle_with_intent(text, str(chat_id))
            if _intent_response:
                memory.add_message(chat_id, "user", text)
                memory.add_message(chat_id, "assistant", _intent_response)
                # Show detected intent hint
                _detected = classify_intent(text)
                _cmd = _detected.get("command", "") if _detected else ""
                return f"🎯 `{_cmd}`\n\n{_intent_response}"
        except Exception as _ie:
            pass  # Fall through to AI on intent error
    # ── END INTENT CHECK ─────────────────────────────────────────────

    route_name, route = detect_route(text)
    history = memory.get_history(chat_id)
    knowledge = get_relevant_knowledge(text)
    if knowledge:
        history.insert(0, {"role": "system", "content": knowledge})
    history.append({"role": "user", "content": text})
    model = route["model"]
    response = call_ollama(model, history, route["system"])
    memory.add_message(chat_id, "user", text)
    memory.add_message(chat_id, "assistant", response, model)
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
                  "*Jarvis Mission Control v2.1 Aktif!*\nMulti-model AI router hazir.\n`/help` yaz yardim icin.")
        while self.running:
            updates = self.get_updates()
            for update in updates:
                self.offset = update["update_id"] + 1
                try:
                    self._handle_update(update)
                except Exception as e:
                    log.error(f"Update error: {e}")

    def _handle_update(self, update):
        msg = update.get("message", {})
        if not msg:
            return
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        username = msg.get("from", {}).get("username", "?")
        if chat_id != self.authorized_id or not text:
            return
        log.info(f"[{username}]: {text[:50]}")
        self.send(chat_id, "_Isleniyor..._")
        response = process_message(chat_id, text)
        self.send(chat_id, response)

# ─────────────────────────── WEB DASHBOARD ────────────────────────
class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
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
<div><h1>Jarvis Mission Control</h1><p>Multi-model AI Gateway — {datetime.now().strftime('%H:%M:%S')}</p></div>
</header>
<div class="grid">
<div class="card">
<h2>Sistem</h2>
<div class="stat"><span class="stat-label">Toplam Sorgu</span><span class="stat-val">{stats['total_queries']}</span></div>
<div class="stat"><span class="stat-label">AI Modeller</span><span class="stat-val">{len(models)} aktif</span></div>
<div class="stat"><span class="stat-label">Web Port</span><span class="stat-val">:8080</span></div>
<div class="stat"><span class="stat-label">Telegram</span><span class="stat-val">Bagli</span></div>
</div>
<div class="card">
<h2>Router</h2>
<div class="stat"><span class="stat-label">Sohbet</span><span class="stat-val">llama3.2</span></div>
<div class="stat"><span class="stat-label">Kod</span><span class="stat-val">deepseek-coder</span></div>
<div class="stat"><span class="stat-label">Akil/Plan</span><span class="stat-val">deepseek-r1</span></div>
<div class="stat"><span class="stat-label">eBay/Trendyol</span><span class="stat-val">llama3.2</span></div>
</div>
<div class="card full">
<h2>Web Chat</h2>
<div class="chat">
<div class="chat-row">
<input id="inp" placeholder="/help /ebay /trendyol /code /status..." onkeypress="if(event.key==='Enter')send()"/>
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
            self.wfile.write(html.encode())
        elif self.path.startswith("/auth/callback"):
            self._handle_shopify_oauth()
            return
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


    def _handle_shopify_oauth(self):
        """Handle Shopify OAuth callback"""
        from urllib.parse import urlparse, parse_qs
        from urllib.request import urlopen, Request
        import json
        
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [""])[0]
        shop = params.get("shop", [""])[0]
        
        if not code or not shop:
            self._json({"error": "Missing code or shop"}, 400)
            return
        
        # Exchange code for token
        payload = json.dumps({
            "client_id": "658472d581c8894deb450f7f6f9de137",
            "client_secret": "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",
            "code": code
        }).encode()
        
        try:
            req = Request(
                f"https://{shop}/admin/oauth/access_token",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=15) as resp:
                token_data = json.loads(resp.read())
                token = token_data.get("access_token", "")
            
            # Save token
            with open("/opt/jarvis/shopify_token.txt", "w") as f:
                f.write(f"SHOP={shop}\nTOKEN={token}\n")
            
            log.info(f"Shopify OAuth complete! Token: {token[:20]}...")
            
            # Send HTML response
            html = f"""<html><body style="background:#0a0a0f;color:#00ff88;font-family:sans-serif;text-align:center;padding:50px">
            <h1>✅ Jarvis Shopify Bağlantısı Tamam!</h1>
            <p>Token alındı ve kaydedildi.</p>
            <p>Şimdi ürünler çekiliyor...</p>
            </body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())
            
            # Trigger product sync in background
            import threading
            threading.Thread(target=_sync_shopify_products, args=(shop, token), daemon=True).start()
            
        except Exception as e:
            log.error(f"OAuth error: {e}")
            self._json({"error": str(e)}, 500)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

# ─────────────────────────── MAIN ─────────────────────────────────
def _sync_shopify_products(shop, token):
    """Sync all products from Shopify store"""
    import json, time
    from urllib.request import urlopen, Request
    
    log.info(f"Shopify urun sync basliyor: {shop}")
    all_products = []
    page_info = None
    
    while True:
        url = f"https://{shop}/admin/api/2024-01/products.json?limit=250"
        if page_info:
            url += f"&page_info={page_info}"
        
        try:
            req = Request(url, headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json"
            })
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                products = data.get("products", [])
                all_products.extend(products)
                log.info(f"  Sayfa: {len(all_products)} urun")
                
                # Check for pagination
                link_header = resp.headers.get("Link", "")
                if "rel=\"next\"" in link_header:
                    import re
                    m = re.search(r'page_info=([^&>]+)', link_header.split("rel=\"next\"")[0])
                    page_info = m.group(1) if m else None
                else:
                    break
                time.sleep(0.5)
        except Exception as e:
            log.error(f"Sync error: {e}")
            break
    
    # Save knowledge file
    lines = [f"# Shopify Mağaza: {shop}", f"# Toplam: {len(all_products)} urun", ""]
    
    vendors = list(set(p.get("vendor","") for p in all_products if p.get("vendor")))
    types = list(set(p.get("product_type","") for p in all_products if p.get("product_type")))
    
    lines.append(f"## Ozet")
    lines.append(f"- Toplam Urun: {len(all_products)}")
    lines.append(f"- Kategoriler: {', '.join(types[:10]) or '-'}")
    lines.append(f"- Tedarikciler: {', '.join(vendors[:10]) or '-'}")
    lines.append("")
    lines.append("## Urunler")
    
    for p in all_products:
        variants = p.get("variants", [])
        prices = [float(v.get("price",0)) for v in variants if v.get("price")]
        min_p = min(prices) if prices else 0
        max_p = max(prices) if prices else 0
        stock = sum(v.get("inventory_quantity",0) for v in variants)
        price_str = f"${min_p:.2f}" if min_p==max_p else f"${min_p:.2f}-${max_p:.2f}"
        
        lines.append(f"- **{p.get('title','-')}** | {price_str} | Stok:{stock} | {p.get('product_type','-')}")
    
    knowledge = "\n".join(lines)
    with open("/opt/jarvis/knowledge/shopify_store.md", "w") as f:
        f.write(knowledge)
    
    # Reload knowledge
    global KNOWLEDGE
    KNOWLEDGE["shopify_store"] = knowledge
    log.info(f"✅ Shopify sync tamamlandi: {len(all_products)} urun")

def start_web():
    HTTPServer(("0.0.0.0", CONFIG["web_port"]), WebHandler).serve_forever()

def main():
    log.info("=" * 55)
    log.info("  JARVIS MISSION CONTROL v2.1 — Baslatiyor...")
    log.info("=" * 55)
    models = get_available_models()
    if models:
        log.info(f"Ollama aktif — {len(models)} model: {', '.join(models[:3])}")
    else:
        log.warning("Ollama bagli degil!")
    threading.Thread(target=start_web, daemon=True).start()
    log.info(f"Web dashboard: http://0.0.0.0:{CONFIG['web_port']}")
    bot = TelegramBot(CONFIG["telegram_token"], CONFIG["authorized_chat_id"])
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.running = False

if __name__ == "__main__":
    main()
