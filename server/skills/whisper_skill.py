#!/usr/bin/env python3
"""
Jarvis Whisper Skill — Telegram Sesli Mesaj → Metin → AI
Telegram'dan ses mesajı geldiğinde otomatik metne çevirir ve işler.
"""

import subprocess
import os
import json
import tempfile
from pathlib import Path

WHISPER_MODEL = "base"  # tiny/base/small/medium/large
OLLAMA_URL = "http://127.0.0.1:11434"
AUDIO_TMP_DIR = "/tmp/jarvis_audio"

def ensure_whisper():
    """Whisper kurulu mu kontrol et, değilse kur"""
    result = subprocess.run(
        "python3 -c 'import whisper; print(whisper.__version__)'",
        shell=True, capture_output=True, text=True
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, None

def install_whisper():
    """openai-whisper kur"""
    print("Whisper kuruluyor...")
    result = subprocess.run(
        "pip3 install --break-system-packages openai-whisper 2>&1",
        shell=True, capture_output=True, text=True
    )
    return result.returncode == 0

def transcribe_audio(audio_path: str, language: str = "tr") -> str:
    """Ses dosyasını metne çevir"""
    # Whisper Python API kullan
    script = f'''
import whisper
import json
model = whisper.load_model("{WHISPER_MODEL}")
result = model.transcribe("{audio_path}", language="{language}", fp16=False)
print(json.dumps({{"text": result["text"], "lang": result.get("language", "?")}}, ensure_ascii=False))
'''
    tmpfile = "/tmp/_whisper_run.py"
    with open(tmpfile, "w") as f:
        f.write(script)
    
    result = subprocess.run(
        f"python3 {tmpfile}",
        shell=True, capture_output=True, text=True, timeout=120
    )
    
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout.strip())
            return data["text"].strip()
        except:
            return result.stdout.strip()
    else:
        return f"Transkripsiyon hatası: {result.stderr[:200]}"

def download_voice_message(bot_token: str, file_id: str, out_path: str) -> bool:
    """Telegram'dan ses dosyasını indir"""
    from urllib.request import urlopen, Request
    
    # Get file path
    req = Request(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}")
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        file_path = data["result"]["file_path"]
    
    # Download file
    url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    req2 = Request(url)
    with urlopen(req2, timeout=30) as resp:
        content = resp.read()
    
    with open(out_path, "wb") as f:
        f.write(content)
    
    return True

def process_voice_in_bridge(update: dict, bot_token: str) -> str:
    """
    Bridge.py'den çağrılır:
    Telegram voice/audio mesajı geldiğinde sesli komutu işle.
    """
    msg = update.get("message", {})
    voice = msg.get("voice") or msg.get("audio")
    
    if not voice:
        return None
    
    os.makedirs(AUDIO_TMP_DIR, exist_ok=True)
    file_id = voice["file_id"]
    ext = ".ogg" if msg.get("voice") else ".mp3"
    audio_path = f"{AUDIO_TMP_DIR}/{file_id}{ext}"
    
    try:
        download_voice_message(bot_token, file_id, audio_path)
        
        text = transcribe_audio(audio_path)
        
        # Clean up
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        return text
        
    except Exception as e:
        return f"Ses işlenemedi: {e}"

if __name__ == "__main__":
    # Kurulum testi
    ok, ver = ensure_whisper()
    if ok:
        print(f"✅ Whisper {ver} kurulu")
    else:
        print("Whisper kurulu değil, kuruluyor...")
        if install_whisper():
            print("✅ Whisper kuruldu!")
        else:
            print("❌ Kurulum başarısız")
