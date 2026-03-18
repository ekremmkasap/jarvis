"""
Upload a completely fresh, clean bridge.py v2.1 to the server.
This replaces the patched version.
"""
import paramiko
import time

host, username, password = "192.168.1.109", "userk", "userk1"

BRIDGE_V2 = r'''#!/usr/bin/env python3
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
    "telegram_token": "8295826032:AAGn4XRJxQi98hqqZLRMcvOEaeowSGYDt-k",
    "authorized_chat_id": 5847386182,
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
    route_name, route = detect_route(text)
    history = memory.get_history(chat_id)
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
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

# ─────────────────────────── MAIN ─────────────────────────────────
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
'''

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)

    # Write clean bridge.py
    sftp = client.open_sftp()
    with sftp.file("/opt/jarvis/openclaw/bridge.py", "w") as f:
        f.write(BRIDGE_V2)
    sftp.close()
    print("bridge.py v2.1 written")

    # Syntax check
    _, sy, _ = client.exec_command(
        "python3 -m py_compile /opt/jarvis/openclaw/bridge.py && echo SYNTAX_OK 2>&1",
        get_pty=True
    )
    sy_out = sy.read().decode().strip()
    print(f"Syntax: {sy_out}")

    if "SYNTAX_OK" in sy_out:
        client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
        time.sleep(4)
        _, st, _ = client.exec_command("systemctl is-active jarvis.service")
        print(f"Service: {st.read().decode().strip()}")
        _, lo, _ = client.exec_command("tail -8 /home/userk/.jarvis/jarvis.log")
        print("\nLog:\n" + lo.read().decode())
    else:
        print("SYNTAX ERROR — not restarting")

    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()

print("Done.")
