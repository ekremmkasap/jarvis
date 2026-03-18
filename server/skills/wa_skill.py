#!/usr/bin/env python3
\"\"\"
Jarvis WhatsApp Skill â€” bridge.py ile entegrasyon
WhatsApp mesajlarÄ±nÄ± alÄ±r, bridge.py aracÄ±lÄ±ÄŸÄ±yla AI'ya yÃ¶nlendirir.
\"\"\"

import json
import os
from urllib.request import urlopen, Request

WA_API = "http://127.0.0.1:3001"

def send_whatsapp(to: str, message: str) -> bool:
    \"\"\"WhatsApp mesajÄ± gÃ¶nder\"\"\"
    payload = json.dumps({"to": to, "message": message}).encode()
    req = Request(f"{WA_API}/send", data=payload,
                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        return False

def get_pending_messages() -> list:
    \"\"\"WhatsApp'tan bekleyen mesajlarÄ± al\"\"\"
    try:
        req = Request(f"{WA_API}/queue")
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except:
        return []

def is_connected() -> bool:
    \"\"\"WhatsApp baÄŸlÄ± mÄ±?\"\"\"
    try:
        req = Request(f"{WA_API}/status")
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("ready", False)
    except:
        return False

def get_qr_path() -> str:
    \"\"\"QR kod dosyasÄ±\"\"\"
    return "/home/userk/.jarvis/wa_qr.txt"
