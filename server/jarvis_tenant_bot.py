#!/usr/bin/env python3
"""
JARVIS — jarvis_tenant_bot.py
Her musteri icin izole calisir.
Kullanim: python3 /opt/jarvis/jarvis_tenant_bot.py --config /opt/jarvis/tenants/TENANT_ID/config.json
"""

import os, sys, json, time, logging, threading, argparse, sqlite3
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

# ── Args ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
args = parser.parse_args()

# ── Tenant Config ─────────────────────────────────────────────────
with open(args.config) as f:
    TC = json.load(f)

TENANT_ID   = TC["tenant_id"]
TENANT_NAME = TC["name"]
TG_TOKEN    = TC["telegram_token"]
CHAT_ID     = TC["authorized_chat_id"]
MEMORY_DIR  = TC.get("memory_dir", f"/opt/jarvis/tenants/{TENANT_ID}/memory")
SOUL_MD     = TC.get("soul_md", "/opt/jarvis/soul.md")
FEATURES    = TC.get("features", [])
PLAN        = TC.get("plan", "starter")
OLLAMA_URL  = "http://127.0.0.1:11434"

os.makedirs(MEMORY_DIR, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────
log_file = os.path.join(MEMORY_DIR, "bot.log")
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{TENANT_ID}] %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
log = logging.getLogger(TENANT_ID)

# ── Soul ──────────────────────────────────────────────────────────
try:
    with open(SOUL_MD) as f:
        SOUL = f.read()
    log.info(f"Soul yuklendi: {SOUL_MD}")
except Exception as e:
    SOUL = f"Sen Jarvis'sin, {TENANT_NAME} adina calisiyorsun. Zeki ve pratik bir AI asistanisin."
    log.warning(f"soul.md bulunamadi: {e}")

# ── SQLite Hafiza ─────────────────────────────────────────────────
DB_PATH = os.path.join(MEMORY_DIR, "memory.db")

def db_init():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        ts TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
    c.commit()
    c.close()

def db_save(role, content):
    c = sqlite3.connect(DB_PATH)
    c.execute("INSERT INTO conversations (role,content) VALUES (?,?)", (role, content))
    c.commit()
    c.close()

def db_history(n=12):
    c = sqlite3.connect(DB_PATH)
    rows = c.execute(
        "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    c.close()
    return list(reversed(rows))

def db_count():
    c = sqlite3.connect(DB_PATH)
    n = c.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    c.close()
    return n

db_init()

# ── Model Router ──────────────────────────────────────────────────
ROUTES = {
    "code": {
        "model": "deepseek-coder:latest", "fallback": "qwen2.5-coder:7b",
        "kw": ["kod","yaz","python","javascript","bug","script","code","function","hata","class","sql"],
    },
    "reasoning": {
        "model": "deepseek-r1:latest", "fallback": "llama3.2:latest",
        "kw": ["neden","analiz","planla","strateji","dusun","karar","analyze","plan","compare"],
    },
    "chat": {
        "model": "llama3.2:latest", "fallback": "mistral:latest",
        "kw": [],
    },
}

def detect_route(text):
    t = text.lower()
    for name, r in ROUTES.items():
        if any(k in t for k in r["kw"]):
            return name, r
    return "chat", ROUTES["chat"]

def available_models():
    try:
        with urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as r:
            return [m["name"] for m in json.loads(r.read())["models"]]
    except Exception:
        return []

def pick_model(route):
    avail = available_models()
    for m in [route["model"], route["fallback"]]:
        if m in avail:
            return m
    return avail[0] if avail else "llama3.2:latest"

def ollama_chat(model, messages):
    body = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = Request(
        f"{OLLAMA_URL}/api/chat", data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urlopen(req, timeout=120) as r:
        return json.loads(r.read())["message"]["content"]

def ai_reply(text):
    rname, route = detect_route(text)
    model = pick_model(route)
    history = db_history(12)
    msgs = [{"role": "system", "content": SOUL}]
    for role, content in history:
        msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": text})
    log.info(f"route={rname} model={model}")
    try:
        reply = ollama_chat(model, msgs)
        db_save("user", text)
        db_save("assistant", reply)
        return reply, model
    except Exception as e:
        log.error(f"AI error: {e}")
        return "Sistem gecici olarak mesgul. Lutfen tekrar deneyin.", model

# ── Telegram ──────────────────────────────────────────────────────
TG_BASE = f"https://api.telegram.org/bot{TG_TOKEN}"

def tg(method, **kw):
    try:
        body = json.dumps(kw).encode()
        req = Request(
            f"{TG_BASE}/{method}", data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f"TG {method}: {e}")
        return {}

def send(cid, text):
    for i in range(0, len(text), 4000):
        tg("sendMessage", chat_id=cid, text=text[i:i+4000], parse_mode="Markdown")
        if len(text) > 4000:
            time.sleep(0.3)

# ── Plan Ozellikleri ──────────────────────────────────────────────
PLAN_FEATURES = {
    "starter": ["chat", "status", "help", "clear"],
    "pro":     ["chat", "status", "help", "clear", "ebay", "trendyol", "web"],
    "agency":  ["chat", "status", "help", "clear", "ebay", "trendyol", "web", "code", "vision"],
}

def has_feature(feat):
    return feat in PLAN_FEATURES.get(PLAN, []) or feat in FEATURES

# ── Komut Handler ─────────────────────────────────────────────────
GREETINGS = {"merhaba","selam","hey","hello","hi","naber","nasilsin","iyimisin","ne haber"}

def handle(update):
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    cid  = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    if not text:
        return

    if cid != CHAT_ID:
        tg("sendMessage", chat_id=cid, text="Bu bot yetkili kullanicilara ozeldir.")
        return

    log.info(f"MSG: {text[:80]}")
    tl = text.lower()

    # Selamlama
    if tl in GREETINGS or (tl.split() and tl.split()[0] in GREETINGS):
        first = TENANT_NAME.split()[0]
        send(cid, f"Merhaba {first}! Size nasil yardimci olabilirim?")
        return

    # /status
    if text == "/status":
        avail = available_models()
        out = (
            f"*Jarvis Durum — {TENANT_NAME}*\n"
            f"Plan: `{PLAN}` | Tenant: `{TENANT_ID}`\n"
            f"Aktif ozellikler: `{', '.join(FEATURES) or 'temel'}`\n"
            f"Ollama: {len(avail)} model aktif\n"
            f"Hafiza: {db_count()} kayit"
        )
        send(cid, out)
        return

    # /help
    if text == "/help":
        cmds = "/status — Sistem durumu\n/help — Bu menu\n/clear — Hafizayi temizle"
        if has_feature("ebay"):
            cmds += "\n/ebay [urun] — eBay arastirma"
        if has_feature("trendyol"):
            cmds += "\n/trendyol [urun] — Trendyol analizi"
        send(cid, f"*Jarvis Komutlari — {TENANT_NAME}*\n\n{cmds}\n\nDogal dilde de yazabilirsiniz!")
        return

    # /clear
    if text == "/clear":
        c = sqlite3.connect(DB_PATH)
        c.execute("DELETE FROM conversations")
        c.commit()
        c.close()
        send(cid, "Hafiza temizlendi.")
        return

    # /ebay (pro + agency)
    if text.startswith("/ebay") and has_feature("ebay"):
        query = text[5:].strip() or "genel analiz"
        tg("sendChatAction", chat_id=cid, action="typing")
        reply, _ = ai_reply(
            f"eBay urun arastirmasi yap: {query}. "
            f"Kar marji, rekabet yogunlugu ve ideal fiyat araligini analiz et."
        )
        send(cid, reply)
        return

    # /trendyol (pro + agency)
    if text.startswith("/trendyol") and has_feature("trendyol"):
        query = text[9:].strip() or "genel analiz"
        tg("sendChatAction", chat_id=cid, action="typing")
        reply, _ = ai_reply(
            f"Trendyol pazar analizi yap: {query}. "
            f"Pazar buyuklugu, rekabet ve fiyat stratejisini incele."
        )
        send(cid, reply)
        return

    # Genel AI yanit
    tg("sendChatAction", chat_id=cid, action="typing")
    reply, model = ai_reply(text)
    send(cid, reply)

# ── Ana Polling Dongusu ───────────────────────────────────────────
def run():
    log.info("=" * 55)
    log.info(f"  Tenant: {TENANT_NAME} [{TENANT_ID}] Plan:{PLAN}")
    log.info(f"  Chat ID: {CHAT_ID} | Soul: {SOUL_MD}")
    log.info("=" * 55)
    offset = 0
    while True:
        try:
            r = tg("getUpdates", offset=offset, timeout=30, limit=10)
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                threading.Thread(target=handle, args=(upd,), daemon=True).start()
        except Exception as e:
            log.error(f"Poll error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run()
