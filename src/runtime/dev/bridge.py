#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║          JARVIS MISSION CONTROL — bridge.py v2.0                 ║
║          Multi-Model AI Router | Telegram + Web Dashboard        ║
╚══════════════════════════════════════════════════════════════════╝

Mimari:
  Telegram / Web → bridge.py → [Model Router] → Ollama API
                                  ├── deepseek-r1    (akıl/plan)
                                  ├── deepseek-coder (kod yazma)
                                  ├── llama3.2       (genel chat)
                                  ├── moondream      (görsel)
                                  └── mistral        (analiz)
"""

import os
import json
import time
import logging
import threading
import subprocess
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
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

# Model routing kuralları
MODEL_ROUTES = {
    "code": {
        "model": "deepseek-coder:latest",
        "fallback": "qwen2.5-coder:7b",
        "keywords": ["kod", "yaz", "python", "javascript", "bug", "hata", "script",
                     "code", "write", "function", "class", "debug", "fix", "program"],
        "system": "Sen uzman bir yazılım geliştiricisin. Temiz, yorumlanmış ve çalışan kod yaz."
    },
    "reasoning": {
        "model": "deepseek-r1:latest",
        "fallback": "llama3.2:latest",
        "keywords": ["neden", "analiz", "planla", "strateji", "düşün", "mantık",
                     "why", "analyze", "plan", "strategy", "think", "reason", "decide"],
        "system": "Sen derin düşünen bir stratejist ve analistsin. Adım adım mantık yürüt."
    },
    "search": {
        "model": "llama3.2:latest",
        "fallback": "mistral:latest",
        "keywords": ["ara", "bul", "ebay", "ürün", "fiyat", "piyasa",
                     "search", "find", "product", "price", "market", "trend"],
        "system": "Sen bir e-ticaret ve piyasa araştırma uzmanısın. Detaylı ve pratik bilgi ver."
    },
    "system": {
        "model": "llama3.2:latest",
        "fallback": "mistral:latest",
        "keywords": ["durum", "sistem", "servis", "sunucu", "çalıştır", "durdur",
                     "status", "service", "server", "run", "stop", "restart", "memory", "cpu"],
        "system": "Sen bir Linux sistem yöneticisisin. Komutları doğru ve güvenli ver."
    },
    "chat": {
        "model": "llama3.2:latest",
        "fallback": "mistral:latest",
        "keywords": [],  # default
        "system": "Sen Jarvis'sin — Tony Stark'ın AI asistanı gibi zeki, yardımsever ve pratik bir AI. Türkçe ve İngilizce konuşabilirsin."
    }
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

# ─────────────────────────── MEMORY ───────────────────────────────
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
            "role": role,
            "content": content,
            "model": model,
            "time": datetime.now().isoformat()
        })
        # Son 20 mesajı tut
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

# ─────────────────────────── MODEL ROUTER ─────────────────────────
def detect_route(text: str) -> dict:
    """Mesaja göre en uygun modeli seç"""
    text_lower = text.lower()
    
    for route_name, route in MODEL_ROUTES.items():
        if route_name == "chat":
            continue
        for kw in route["keywords"]:
            if kw in text_lower:
                log.info(f"Route detected: {route_name} (keyword: {kw})")
                return route_name, route
    
    return "chat", MODEL_ROUTES["chat"]

def get_available_models() -> list:
    """Ollama'daki mevcut modelleri listele"""
    try:
        req = Request(f"{CONFIG['ollama_url']}/api/tags")
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except:
        return []

def call_ollama(model: str, messages: list, system: str = None) -> str:
    """Ollama API'yi çağır ve yanıt al"""
    available = get_available_models()
    
    # Model kontrolü ve fallback
    if not any(model in m for m in available):
        log.warning(f"Model {model} not found, using llama3.2")
        model = "llama3.2:latest"
        if not any("llama3.2" in m for m in available):
            model = available[0] if available else None
    
    if not model:
        return "❌ Hiçbir Ollama modeli bulunamadı. `ollama list` ile kontrol et."

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
        req = Request(
            f"{CONFIG['ollama_url']}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "Boş yanıt")
    except URLError as e:
        log.error(f"Ollama error: {e}")
        return f"❌ Ollama bağlantı hatası: {e}"
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return f"❌ Hata: {e}"

def run_system_command(cmd: str) -> str:
    """Sistem komutlarını güvenli çalıştır"""
    ALLOWED = ["ps", "top", "free", "df", "ollama", "systemctl status",
               "journalctl", "ls", "cat", "echo", "ping", "ip addr"]
    if not any(cmd.startswith(a) for a in ALLOWED):
        return "⛔ Bu komut için izin yok."
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout[:2000] or result.stderr[:500] or "Komut çalıştı, çıktı yok."
    except subprocess.TimeoutExpired:
        return "⏱️ Komut zaman aşımına uğradı."
    except Exception as e:
        return f"Hata: {e}"

def process_message(chat_id: int, text: str) -> str:
    """Mesajı işle ve yanıt döndür"""
    text = text.strip()
    
    # Özel komutlar
    if text.startswith("/"):
        return handle_command(chat_id, text)
    
    # Model routing
    route_name, route = detect_route(text)
    
    # Sistem komutu kontrolü
    if text.startswith("$ ") or text.startswith("!"):
        cmd = text[2:].strip()
        result = run_system_command(cmd)
        memory.add_message(chat_id, "user", text)
        memory.add_message(chat_id, "assistant", result, "system")
        return f"```\n{result}\n```"
    
    # Konuşma geçmişini al
    history = memory.get_history(chat_id)
    history.append({"role": "user", "content": text})
    
    # AI yanıtı al
    model = route["model"]
    response = call_ollama(model, history, route["system"])
    
    # Belleğe kaydet
    memory.add_message(chat_id, "user", text)
    memory.add_message(chat_id, "assistant", response, model)
    
    # Yanıt başlığı ekle
    model_short = model.split(":")[0].replace("deepseek-", "DS-")
    header = f"🤖 [{model_short}] "
    
    return header + response

def handle_command(chat_id: int, cmd: str) -> str:
    """Bot komutlarını işle"""
    parts = cmd.split(" ", 2)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command == "/start" or command == "/help":
        available = get_available_models()
        models_str = "\n".join([f"  • {m}" for m in available]) or "  • (model bulunamadı)"
        return f"""🤖 **Jarvis Mission Control v2.0**

**Komutlar:**
  `/status` → Sistem durumu
  `/models` → Mevcut AI modeller
  `/reset` → Konuşmayı sıfırla
  `/ebay [ürün]` → eBay ürün araştırması
  `/code [görev]` → Kod yaz
  `/plan [proje]` → Proje planla
  `$ [komut]` → Sunucu komutu çalıştır

**Mevcut modeller:**
{models_str}

**Routing:** Mesajına göre otomatik model seçilir 🎯"""

    elif command == "/status":
        try:
            cpu = subprocess.run("top -bn1 | grep 'Cpu' | awk '{print $2}'", 
                               shell=True, capture_output=True, text=True).stdout.strip()
            mem = subprocess.run("free -h | awk '/^Mem:/ {print $3\"/\"$2}'",
                               shell=True, capture_output=True, text=True).stdout.strip()
            models = get_available_models()
            stats = memory.data["stats"]
            return f"""📊 **Jarvis Durum Raporu**
━━━━━━━━━━━━━━━━━━━━
🖥️ CPU: {cpu}%
💾 RAM: {mem}
🤖 Ollama Modeller: {len(models)} adet
📝 Toplam Sorgu: {stats['total_queries']}
⏰ Saat: {datetime.now().strftime('%H:%M:%S')}
✅ Sistem çalışıyor"""
        except Exception as e:
            return f"❌ Durum alınamadı: {e}"

    elif command == "/models":
        models = get_available_models()
        if not models:
            return "❌ Ollama çalışmıyor veya model yok."
        model_list = "\n".join([f"  • {m}" for m in models])
        return f"🤖 **Mevcut AI Modeller:**\n{model_list}"

    elif command == "/reset":
        memory.clear(chat_id)
        return "🔄 Konuşma geçmişi temizlendi."

    elif command == "/ebay":
        query = args or "kazançlı dropshipping ürünü"
        route = MODEL_ROUTES["search"]
        prompt = f"""eBay dropshipping için şunu analiz et: {query}

Şunları ver:
1. Ürün kategorisi ve neden karlı
2. Tahmini kar marjı
3. Tedarikçi kaynakları (AliExpress, Amazon, vb.)
4. Rekabet analizi
5. Önerilen başlık ve anahtar kelimeler"""
        history = [{"role": "user", "content": prompt}]
        response = call_ollama(route["model"], history, route["system"])
        memory.add_message(chat_id, "user", f"/ebay {query}")
        memory.add_message(chat_id, "assistant", response, route["model"])
        return f"🛒 **eBay Analizi:**\n\n{response}"

    elif command == "/code":
        task = args or "Merhaba dünya"
        route = MODEL_ROUTES["code"]
        prompt = f"Şu görevi yerine getir ve tam çalışan kod yaz: {task}"
        history = [{"role": "user", "content": prompt}]
        response = call_ollama(route["model"], history, route["system"])
        memory.add_message(chat_id, "user", f"/code {task}")
        memory.add_message(chat_id, "assistant", response, route["model"])
        return f"💻 **Kod:**\n\n{response}"

    elif command == "/plan":
        task = args or "proje"
        route = MODEL_ROUTES["reasoning"]
        prompt = f"""Şu proje için detaylı adım adım plan oluştur: {task}

Format:
1. Hedef ve kapsam
2. Gereksinimler
3. Adım adım uygulama planı
4. Potansiyel riskler ve çözümleri
5. Başarı kriterleri"""
        history = [{"role": "user", "content": prompt}]
        response = call_ollama(route["model"], history, route["system"])
        memory.add_message(chat_id, "user", f"/plan {task}")
        memory.add_message(chat_id, "assistant", response, route["model"])
        return f"📋 **Plan:**\n\n{response}"

    return f"❓ Bilinmeyen komut: {command}\n/help yaz yardım için."

# ─────────────────────────── TELEGRAM ─────────────────────────────
class TelegramBot:
    def __init__(self, token, authorized_id):
        self.token = token
        self.authorized_id = authorized_id
        self.api = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.running = True

    def send(self, chat_id, text, parse_mode="Markdown"):
        # 4096 karakter sınırı
        while text:
            chunk = text[:4000]
            text = text[4000:]
            payload = json.dumps({
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode
            }).encode()
            try:
                req = Request(
                    f"{self.api}/sendMessage",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                urlopen(req, timeout=10)
            except Exception as e:
                log.error(f"Send error: {e}")

    def get_updates(self):
        try:
            url = f"{self.api}/getUpdates?offset={self.offset}&timeout=30&limit=10"
            req = Request(url)
            with urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read())
                return data.get("result", [])
        except Exception as e:
            log.error(f"GetUpdates error: {e}")
            time.sleep(5)
            return []

    def run(self):
        log.info("🤖 Jarvis Telegram bot başlatıldı")
        self.send(self.authorized_id, 
                  "🚀 **Jarvis Mission Control v2.0 Aktif!**\n\nMulti-model AI router hazır.\n`/help` yaz yardım için.")
        
        while self.running:
            updates = self.get_updates()
            for update in updates:
                self.offset = update["update_id"] + 1
                try:
                    self._handle_update(update)
                except Exception as e:
                    log.error(f"Update handling error: {e}")

    def _handle_update(self, update):
        msg = update.get("message", {})
        if not msg:
            return
        
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        username = msg.get("from", {}).get("username", "?")
        
        if chat_id != self.authorized_id:
            log.warning(f"Unauthorized: {chat_id} (@{username})")
            return
        
        if not text:
            return
        
        log.info(f"📨 [{username}]: {text[:50]}")
        self.send(chat_id, "⏳ _İşleniyor..._")
        
        response = process_message(chat_id, text)
        self.send(chat_id, response)
        log.info(f"✅ Yanıt gönderildi ({len(response)} karakter)")

# ─────────────────────────── WEB DASHBOARD ────────────────────────
WEB_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jarvis Mission Control</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; min-height: 100vh; }
  
  header { background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px 30px; 
           border-bottom: 1px solid #00ff88; display: flex; align-items: center; gap: 15px; }
  header h1 { font-size: 1.8em; color: #00ff88; }
  header p { color: #888; margin-top: 4px; font-size: 0.9em; }
  .status-dot { width: 12px; height: 12px; border-radius: 50%; background: #00ff88; 
                box-shadow: 0 0 10px #00ff88; animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px; }
  @media(max-width: 768px) { .grid { grid-template-columns: 1fr; } }
  
  .card { background: #11111b; border: 1px solid #222; border-radius: 12px; padding: 20px; }
  .card h2 { font-size: 1em; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; }
  
  .stat { display: flex; justify-content: space-between; align-items: center; 
          padding: 10px 0; border-bottom: 1px solid #1a1a2e; }
  .stat:last-child { border: none; }
  .stat-label { color: #666; font-size: 0.9em; }
  .stat-value { color: #00ff88; font-weight: bold; font-family: monospace; }
  
  .chat-box { background: #0d0d1a; border-radius: 12px; padding: 20px; }
  .chat-input { display: flex; gap: 10px; margin-bottom: 15px; }
  .chat-input input { flex: 1; background: #1a1a2e; border: 1px solid #333; 
                      border-radius: 8px; padding: 10px 15px; color: #e0e0e0; font-size: 1em; }
  .chat-input input:focus { border-color: #00ff88; outline: none; }
  .chat-input button { background: #00ff88; color: #000; border: none; padding: 10px 20px;
                       border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 0.95em; }
  .chat-input button:disabled { opacity: 0.5; cursor: not-allowed; }
  
  .messages { max-height: 400px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
  .message { padding: 10px 15px; border-radius: 8px; max-width: 90%; font-size: 0.95em; line-height: 1.5; }
  .message.user { background: #1a2744; align-self: flex-end; border: 1px solid #2244aa; }
  .message.assistant { background: #1a2a1a; align-self: flex-start; border: 1px solid #224422; }
  .message.system { background: #1a1a1a; color: #666; font-style: italic; align-self: center; font-size: 0.8em; }
  .message pre { background: #0a0a0a; padding: 10px; border-radius: 4px; overflow-x: auto; margin-top: 8px; }
  
  .model-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.75em;
                 background: #002211; color: #00ff88; border: 1px solid #00ff44; margin-bottom: 5px; }
  
  .full-width { grid-column: 1 / -1; }
  .models-list { display: flex; flex-wrap: wrap; gap: 8px; }
  .model-tag { background: #1a1a2e; border: 1px solid #333; padding: 6px 12px;
               border-radius: 20px; font-size: 0.85em; color: #aaa; font-family: monospace; }
  .model-tag.active { border-color: #00ff88; color: #00ff88; }
</style>
</head>
<body>
<header>
  <div class="status-dot"></div>
  <div>
    <h1>⚡ Jarvis Mission Control</h1>
    <p>Multi-model AI Gateway — {time}</p>
  </div>
</header>

<div class="grid">
  <!-- Stats -->
  <div class="card">
    <h2>📊 Sistem Durumu</h2>
    <div class="stat"><span class="stat-label">Toplam Sorgu</span><span class="stat-value">{total_queries}</span></div>
    <div class="stat"><span class="stat-label">Ollama Modeller</span><span class="stat-value">{model_count} aktif</span></div>
    <div class="stat"><span class="stat-label">Web Port</span><span class="stat-value">:{web_port}</span></div>
    <div class="stat"><span class="stat-label">Telegram</span><span class="stat-value">✅ Bağlı</span></div>
    <div class="stat"><span class="stat-label">Bellek Oturumları</span><span class="stat-value">{session_count}</span></div>
  </div>

  <!-- Model Router Map -->
  <div class="card">
    <h2>🔀 Model Router</h2>
    <div class="stat"><span class="stat-label">💬 Chat/Genel</span><span class="stat-value">llama3.2</span></div>
    <div class="stat"><span class="stat-label">💻 Kod Yazma</span><span class="stat-value">deepseek-coder</span></div>
    <div class="stat"><span class="stat-label">🧠 Akıl/Plan</span><span class="stat-value">deepseek-r1</span></div>
    <div class="stat"><span class="stat-label">🛒 eBay/Arama</span><span class="stat-value">llama3.2</span></div>
    <div class="stat"><span class="stat-label">🖥️ Sistem</span><span class="stat-value">Shell</span></div>
  </div>

  <!-- Chat -->
  <div class="card full-width">
    <h2>💬 Web Chat</h2>
    <div class="chat-box">
      <div class="chat-input">
        <input type="text" id="msg-input" placeholder="Mesajınızı yazın... (/help, /ebay, /code, /status)" 
               onkeypress="if(event.key==='Enter') sendMsg()"/>
        <button onclick="sendMsg()" id="send-btn">Gönder</button>
      </div>
      <div class="messages" id="messages">
        <div class="message system">Jarvis çevrimiçi. Mesaj gönderin.</div>
      </div>
    </div>
  </div>

  <!-- Available Models -->
  <div class="card full-width">
    <h2>🤖 Yüklü Modeller</h2>
    <div class="models-list" id="model-list">
      {model_tags}
    </div>
  </div>
</div>

<script>
const WEB_CHAT_ID = 0;  // Web chat ID

async function sendMsg() {
  const input = document.getElementById('msg-input');
  const btn = document.getElementById('send-btn');
  const text = input.value.trim();
  if (!text) return;
  
  addMessage('user', text);
  input.value = '';
  btn.disabled = true;
  addMessage('system', 'Jarvis düşünüyor...');
  
  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await resp.json();
    removeLastSystem();
    addMessage('assistant', data.response, data.model);
  } catch(e) {
    removeLastSystem();
    addMessage('system', 'Hata: ' + e.message);
  }
  btn.disabled = false;
}

function addMessage(role, text, model=null) {
  const container = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message ' + role;
  
  if (model) {
    const badge = document.createElement('div');
    badge.className = 'model-badge';
    badge.textContent = '🤖 ' + model.split(':')[0];
    div.appendChild(badge);
  }
  
  const content = document.createElement('div');
  // Markdown-like formatting
  content.innerHTML = text
    .replace(/```([\\s\\S]*?)```/g, '<pre>$1</pre>')
    .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
    .replace(/_(.*?)_/g, '<em>$1</em>')
    .replace(/\\n/g, '<br>');
  div.appendChild(content);
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeLastSystem() {
  const container = document.getElementById('messages');
  const systems = container.querySelectorAll('.message.system');
  if (systems.length > 0) systems[systems.length-1].remove();
}
</script>
</body>
</html>"""

class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logs

    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            self._serve_dashboard()
        elif self.path == "/api/status":
            self._serve_status()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/chat":
            self._handle_chat()
        else:
            self.send_error(404)

    def _serve_dashboard(self):
        models = get_available_models()
        model_tags = "".join(
            f'<span class="model-tag active">{m}</span>' for m in models
        ) or '<span class="model-tag">Ollama bağlantısı yok</span>'
        
        html = WEB_TEMPLATE.format(
            time=datetime.now().strftime("%H:%M:%S"),
            total_queries=memory.data["stats"]["total_queries"],
            model_count=len(models),
            session_count=len(memory.data["sessions"]),
            web_port=CONFIG["web_port"],
            model_tags=model_tags
        )
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_status(self):
        models = get_available_models()
        data = {
            "status": "online",
            "models": models,
            "stats": memory.data["stats"],
            "time": datetime.now().isoformat()
        }
        self._json_response(data)

    def _handle_chat(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            text = body.get("message", "")
            
            route_name, route = detect_route(text)
            response = process_message(9999, text)  # Web chat ID: 9999
            
            self._json_response({
                "response": response,
                "model": route["model"],
                "route": route_name
            })
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

# ─────────────────────────── MAIN ─────────────────────────────────
def start_web_server():
    server = HTTPServer(("0.0.0.0", CONFIG["web_port"]), WebHandler)
    log.info(f"🌐 Web dashboard: http://0.0.0.0:{CONFIG['web_port']}")
    server.serve_forever()

def main():
    log.info("═" * 60)
    log.info("  JARVIS MISSION CONTROL v2.0 — Başlatılıyor...")
    log.info("═" * 60)
    
    # Ollama kontrol
    models = get_available_models()
    if models:
        log.info(f"✅ Ollama aktif — {len(models)} model: {', '.join(models[:3])}")
    else:
        log.warning("⚠️ Ollama'ya bağlanılamadı. Servis başlatılsın mı kontrol et.")
    
    # Web server ayrı thread'de başlat
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    # Telegram bot ana thread'de çalıştır
    bot = TelegramBot(CONFIG["telegram_token"], CONFIG["authorized_chat_id"])
    
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("\n👋 Jarvis kapatılıyor...")
        bot.running = False

if __name__ == "__main__":
    main()
