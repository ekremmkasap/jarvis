#!/usr/bin/env python3
"""
Jarvis Heartbeat — Sabah 08:00 Günlük Brief
Cron: 0 8 * * * /usr/bin/python3 /opt/jarvis/skills/heartbeat.py
"""

import os
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from env_utils import load_env_files

load_env_files(ROOT_DIR / ".env", ROOT_DIR / "server" / ".env")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

def get_system_stats():
    """Sistem istatistiklerini topla"""
    stats = {}
    try:
        cpu = subprocess.run(
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'",
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        stats["cpu"] = cpu or "?"

        mem = subprocess.run(
            "free -h | awk '/^Mem:/ {printf \"%s / %s\", $3, $2}'",
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        stats["mem"] = mem or "?"

        disk = subprocess.run(
            "df -h / | awk 'NR==2 {printf \"%s / %s (%s)\", $3, $2, $5}'",
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        stats["disk"] = disk or "?"

        uptime = subprocess.run(
            "uptime -p", shell=True, capture_output=True, text=True
        ).stdout.strip()
        stats["uptime"] = uptime or "?"

        jarvis_ok = subprocess.run(
            "systemctl is-active jarvis.service",
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        stats["jarvis"] = "✅ Aktif" if jarvis_ok == "active" else "❌ Durdu"

        ollama_ok = subprocess.run(
            "systemctl is-active ollama.service",
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        stats["ollama"] = "✅ Aktif" if ollama_ok == "active" else "❌ Durdu"

    except Exception as e:
        stats["error"] = str(e)
    return stats

def get_ollama_suggestion():
    """Ollama'dan günlük motivasyon + öneri al"""
    try:
        today = datetime.now().strftime("%A, %d %B")
        payload = {
            "model": "llama3.2:latest",
            "messages": [{
                "role": "user",
                "content": f"""Bugün {today}. 
Sen Jarvis'sin. Ekrem'e günlük sabah briefi ver.
KISA olsun (max 3 cümle):
1. eBay için bugünkü fırsat ipucu
2. Yapılması gereken bir görev önerisi  
3. Stark tarzı bir motivasyon cümlesi
Türkçe yaz."""
            }],
            "stream": False,
            "options": {"temperature": 0.8, "num_predict": 200}
        }
        data = json.dumps(payload).encode()
        req = Request(
            f"{OLLAMA_URL}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "")
    except Exception as e:
        return f"(AI önerisi alınamadı: {e})"

def send_telegram(text):
    """Telegram'a mesaj gönder"""
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }).encode()
    req = Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def main():
    now = datetime.now()
    stats = get_system_stats()
    suggestion = get_ollama_suggestion()

    message = f"""☀️ *Jarvis Sabah Briefingi*
_{now.strftime('%d %B %Y — %H:%M')}_

━━━━━━━━━━━━━━━
🖥️ *Sistem Durumu*
• CPU: `{stats.get('cpu', '?')}%`
• RAM: `{stats.get('mem', '?')}`
• Disk: `{stats.get('disk', '?')}`
• Uptime: `{stats.get('uptime', '?')}`
• Jarvis: {stats.get('jarvis', '?')}
• Ollama: {stats.get('ollama', '?')}

━━━━━━━━━━━━━━━
🤖 *Jarvis Günlük Önerisi*
{suggestion}

━━━━━━━━━━━━━━━
💡 `/ebay` · `/plan` · `/status` · `/help`"""

    try:
        send_telegram(message)
        print(f"[{now.strftime('%H:%M')}] Brief gönderildi.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
