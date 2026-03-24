"""
JARVIS - Tam Bilgisayar Kontrolü + Sesli Asistan
=================================================
Konuş → Jarvis anlar → PC'yi kontrol eder → Sesli yanıt verir
"""

import os, sys, json, time, re, io, wave, subprocess, urllib.request
from datetime import datetime
import numpy as np
import sounddevice as sd
from piper.voice import PiperVoice

# ─── Ayarlar ────────────────────────────────────────────────────────────────
OLLAMA_URL   = "http://127.0.0.1:11434"
OLLAMA_KEY   = "ee772cf9b7ac4c0c90fff1de8ce1c61a.IABOZ2BhMZ_4x4J3ojNOczI4"
CHAT_MODEL   = "minimax-m2.7:cloud"
VISION_MODEL = "qwen3-vl:235b-cloud"
PIPER_MODEL  = r"C:\Users\sergen\AppData\Local\piper-models\tr_TR-dfki-medium.onnx"
PIPER_CONFIG = PIPER_MODEL + ".json"
SAMPLE_RATE  = 22050
LOG_FILE     = r"C:\Users\sergen\Desktop\jarvis-mission-control\jarvis_konusmalar.txt"

SYSTEM_PROMPT = """Sen JARVIS'sin. Ekrem'in kişisel AI asistanısın. Windows bilgisayarını tam kontrol ediyorsun.

Kullanıcı bir şey istediğinde:
1. Kısa yanıt ver (1 cümle)
2. Gerekirse şu formatta komut ekle: ##KOMUT:start https://youtube.com##

Komut örnekleri:
- YouTube aç: ##KOMUT:start https://www.youtube.com##
- Spotify aç: ##KOMUT:start spotify:##
- Chrome aç: ##KOMUT:start chrome##
- Notepad aç: ##KOMUT:start notepad##
- Dosya yöneticisi: ##KOMUT:start explorer##
- Ses aç: ##KOMUT:powershell (New-Object -com Shell.Application).setVolume(80)##
- Kapat: ##KOMUT:taskkill /F /IM chrome.exe##
- Ekran görüntüsü: ##EKRANGÖR##
- Mouse tıkla: ##TIKLA:x,y##
- Yazı yaz: ##YAZ:metin##
- Tuş bas: ##TUS:enter##

Kısa ve net konuş. Türkçe. Ekrem sabırsız biri."""

# ─── TTS ────────────────────────────────────────────────────────────────────
print("[TTS] Yukleniyor...")
_voice = PiperVoice.load(PIPER_MODEL, config_path=PIPER_CONFIG, use_cuda=False)
print("[TTS] Hazir.")

def speak(text: str):
    if not text.strip():
        return
    print(f"Jarvis: {text}")
    try:
        clean = re.sub(r'##[A-Z]+:[^#]*##', '', text)
        clean = re.sub(r'[*_`#]', '', clean).strip()
        if not clean:
            clean = "Tamam."
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE)
            _voice.synthesize(clean[:200], w)
        buf.seek(44)
        data = np.frombuffer(buf.read(), dtype=np.int16)
        sd.play(data, SAMPLE_RATE); sd.wait()
    except Exception as e:
        print(f"[TTS hata] {e}")

# ─── LLM ────────────────────────────────────────────────────────────────────
_history = []

def ask_llm(text: str, image_b64: str = None) -> str:
    # Geçmiş konuşmayı prompt'a ekle
    history_text = ""
    for h in _history[-6:]:
        role = "Ekrem" if h["role"] == "user" else "Jarvis"
        history_text += f"{role}: {h['content']}\n"

    full_prompt = f"{history_text}Ekrem: {text}\nJarvis:"

    body = {
        "model": CHAT_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": full_prompt,
        "stream": False,
        "options": {"num_predict": 150, "temperature": 0.7}
    }
    if image_b64:
        body["images"] = [image_b64]

    try:
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate", data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {OLLAMA_KEY}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read()).get("response", "").strip()
            if resp:
                _history.append({"role": "user", "content": text})
                _history.append({"role": "assistant", "content": resp})
            return resp or "Anlayamadim, tekrar soyle."
    except Exception as e:
        return f"Model hatasi: {e}"

# ─── PC KONTROL ──────────────────────────────────────────────────────────────
def take_screenshot() -> str:
    """Ekran görüntüsü al, base64 döndür."""
    import pyautogui, base64, tempfile
    path = os.path.join(tempfile.gettempdir(), "jarvis_ss.png")
    pyautogui.screenshot().save(path)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def execute_commands(response: str) -> str:
    """Yanıttaki ##KOMUT## bloklarını çalıştır."""
    import pyautogui

    # Shell komutu
    for match in re.finditer(r'##KOMUT:([^#]+)##', response):
        cmd = match.group(1).strip()
        print(f"[PC] {cmd}")
        try:
            subprocess.Popen(cmd, shell=True)
            time.sleep(0.3)
        except Exception as e:
            print(f"[PC hata] {e}")

    # Ekran görüntüsü + vision analizi
    if "##EKRANGÖR##" in response:
        print("[PC] Ekran goruntüsü aliniyor...")
        img = take_screenshot()
        vision_resp = ask_llm("Bu ekranda ne görüyorsun? Kısaca anlat.", img)
        speak(vision_resp)

    # Mouse tıklama
    for match in re.finditer(r'##TIKLA:(\d+),(\d+)##', response):
        x, y = int(match.group(1)), int(match.group(2))
        print(f"[PC] Tikla ({x},{y})")
        pyautogui.click(x, y)

    # Klavye yazma
    for match in re.finditer(r'##YAZ:([^#]+)##', response):
        text = match.group(1)
        print(f"[PC] Yaz: {text}")
        pyautogui.write(text, interval=0.05)

    # Tuş basma
    for match in re.finditer(r'##TUS:([^#]+)##', response):
        key = match.group(1).strip().lower()
        print(f"[PC] Tus: {key}")
        pyautogui.press(key)

    # Temiz yanıtı döndür
    clean = re.sub(r'##[^#]+##', '', response).strip()
    return clean or "Tamam."

# ─── NLP INTENT (hızlı komutlar, LLM'e gerek yok) ────────────────────────────
ANYDESK_EXE = r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe"
ANYDESK_PS  = r"C:\Users\sergen\Desktop\jarvis-mission-control\anydesk_kabul.ps1"

QUICK_COMMANDS = {
    # AnyDesk kabul
    r'anydesk.*kabul|kabul.*anydesk|baglanti.*kabul|gelen.*kabul|istegi.*kabul': (
        f'powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ANYDESK_PS}"',
        'AnyDesk bağlantısı kabul edildi.'),
    # AnyDesk aç
    r'anydesk.*ac|ac.*anydesk': (f'"{ANYDESK_EXE}"', 'AnyDesk açıldı.'),
    # YouTube
    r'youtube.*ac|ac.*youtube': ('start https://www.youtube.com', 'YouTube açıldı.'),
    # Spotify
    r'spotify.*ac|muzik.*ac|sarki.*cal': ('start spotify:', 'Spotify açıldı.'),
    # Chrome
    r'chrome.*ac|tarayici.*ac': ('start chrome', 'Chrome açıldı.'),
    # Dosya yöneticisi
    r'dosya.*yonetici|explorer.*ac': ('start explorer', 'Dosya yöneticisi açıldı.'),
    # Notepad
    r'not.*defteri|notepad': ('start notepad', 'Notepad açıldı.'),
    # Hesap makinesi
    r'hesap.*maki|calculator': ('start calc', 'Hesap makinesi açıldı.'),
    # Ekran görüntüsü
    r'ekran.*goruntus|screenshot': (None, '__SCREENSHOT__'),
    # Kapat
    r'bilgisayari.*kapat|shut.*down': ('shutdown /s /t 30', 'Bilgisayar 30 saniyede kapanacak.'),
}

def try_quick_command(text: str):
    """Basit komutları LLM'e sormadan direkt çalıştır."""
    text_lower = text.lower()
    for pattern, (cmd, reply) in QUICK_COMMANDS.items():
        if re.search(pattern, text_lower):
            if reply == '__SCREENSHOT__':
                print("[PC] Ekran goruntüsü...")
                img = take_screenshot()
                vision_resp = ask_llm("Ekranda ne var? Kısaca anlat.", img)
                speak(vision_resp)
                return True
            if cmd:
                subprocess.Popen(cmd, shell=True)
            speak(reply)
            return True
    return False

# ─── KONUŞMA KAYIT ───────────────────────────────────────────────────────────
def log(ekrem: str, jarvis: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] Ekrem: {ekrem}\n")
        f.write(f"[{ts}] Jarvis: {jarvis}\n\n")

# ─── ANA İŞLEYİCİ ────────────────────────────────────────────────────────────
def handle(text: str):
    text = text.strip()
    if not text or len(text) < 2:
        return
    print(f"\nSen: {text}")

    # Hızlı komut?
    if try_quick_command(text):
        log(text, "(hızlı komut)")
        return

    # LLM'e sor
    response = ask_llm(text)
    clean = execute_commands(response)
    speak(clean)
    log(text, clean)

# ─── ANA DÖNGÜ ────────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*50)
    print("  JARVIS - Tam Bilgisayar Kontrolu")
    print("  Konusunca algilar | Ctrl+C = cikis")
    print("="*50 + "\n")

    speak("Merhaba! Jarvis hazır. Hey Jarvis de ve konuş.")

    try:
        from RealtimeSTT import AudioToTextRecorder
        # Wake word olmadan sürekli dinle ama sadece yeterince güçlü seslere yanıt ver
        recorder = AudioToTextRecorder(
            language="tr",
            model="small",
            spinner=False,
            input_device_index=9,             # Logitech G733 - sabit cihaz
            silero_sensitivity=0.6,
            silero_use_onnx=True,
            post_speech_silence_duration=1.2,
            min_length_of_recording=0.8,
            min_gap_between_recordings=0.5,
            on_recording_start=lambda: print("[MIK] Dinliyorum..."),
            on_recording_stop=lambda: print("[MIK] Isleniyor..."),
        )
        print("[MIK] Hazir - konusunca algilar (arka plan filtre edildi)\n")
        while True:
            recorder.text(handle)
    except Exception as e:
        print(f"[!] RealtimeSTT hatasi: {e}")
        speak("Yazı moduna geçiyorum.")
        while True:
            try:
                t = input("Sen: ").strip()
                if t:
                    handle(t)
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        speak("Görüşürüz!")
        print("\n[Jarvis kapatildi]")
