#!/usr/bin/env python3
"""
run_local.py — Jarvis Lokal Test CLI
Telegram gerektirmez. Sunucudaki Ollama'ya bağlanır.
Kullanım: python run_local.py
CTRL+C ile çık.
"""

import json
import urllib.request
import urllib.error
import sys
import re

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
OLLAMA_URL  = "http://192.168.1.109:11434/api/chat"
DEFAULT_MODEL = "llama3.2:latest"

ROUTES = [
    {
        "keywords": ["kod", "python", "bug", "fix", "script", "yaz", "fonksiyon", "class", "hata"],
        "model": "deepseek-coder:latest",
        "system": "Sen bir yazılım geliştirme uzmanısın. Türkçe açıkla, kod örnekleri ver.",
        "label": "CODE"
    },
    {
        "keywords": ["neden", "analiz", "planla", "strateji", "düşün", "mantık", "neden", "çünkü"],
        "model": "deepseek-coder:latest",
        "system": "Sen bir stratejik düşünür ve analist olarak görev yapıyorsun. Adım adım analiz et.",
        "label": "REASON"
    },
    {
        "keywords": ["ebay", "trendyol", "ürün", "fiyat", "satış", "dropship", "kâr"],
        "model": "llama3.2:latest",
        "system": "Sen bir e-ticaret ve pazar araştırma uzmanısın.",
        "label": "ECOM"
    },
    {
        "keywords": ["sistem", "sunucu", "servis", "cpu", "ram", "disk", "durum"],
        "model": "llama3.2:latest",
        "system": "Sen bir sistem yöneticisisin. Sunucu ve servis konularında yardım et.",
        "label": "OPS"
    },
]

SYSTEM_DEFAULT = "Sen Jarvis'sin, Ekrem'in kişisel AI asistanı. Türkçe konuş, kısa ve net cevap ver."

# ─────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────
def detect_route(text: str) -> dict:
    text_lower = text.lower()
    for route in ROUTES:
        for kw in route["keywords"]:
            if kw in text_lower:
                return route
    return {"model": DEFAULT_MODEL, "system": SYSTEM_DEFAULT, "label": "CHAT"}

# ─────────────────────────────────────────────
# OLLAMA CALL
# ─────────────────────────────────────────────
def call_ollama(model: str, messages: list, system: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
        "options": {"num_predict": 512, "num_ctx": 2048}
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                return result.get("message", {}).get("content", "Yanıt alınamadı.")
        except urllib.error.URLError as e:
            if attempt < 2:
                import time; time.sleep(2 ** attempt)
                continue
            return f"Ollama bağlantı hatası: {e}"
        except Exception as e:
            return f"Hata: {e}"

# ─────────────────────────────────────────────
# ANA DÖNGÜ
# ─────────────────────────────────────────────
def main():
    history = []
    print("=" * 55)
    print("  Jarvis — Lokal Test CLI")
    print(f"  Ollama: {OLLAMA_URL}")
    print("  Çıkmak için: CTRL+C veya 'exit' yaz")
    print("=" * 55)
    print()

    while True:
        try:
            user_input = input("Sen: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Görüşürüz!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "çık"):
            print("  Görüşürüz!")
            break
        if user_input.lower() == "/reset":
            history.clear()
            print("  Konuşma geçmişi temizlendi.\n")
            continue
        if user_input.lower() == "/help":
            print("  Komutlar:")
            print("    /reset  — konuşmayı sıfırla")
            print("    /exit   — çık")
            print()
            continue

        route = detect_route(user_input)
        print(f"  [{route['label']}] {route['model']}", end=" → ", flush=True)

        history.append({"role": "user", "content": user_input})
        response = call_ollama(route["model"], history[-10:], route["system"])
        history.append({"role": "assistant", "content": response})

        print(f"\nJarvis: {response}\n")

if __name__ == "__main__":
    main()
