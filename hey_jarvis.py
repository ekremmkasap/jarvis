"""
JARVIS - Full PC control + voice assistant
"""

import argparse
import atexit
import ctypes
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import wave
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--safe-start", action="store_true")
    parser.add_argument("--text-mode", action="store_true")
    parser.add_argument("--no-greeting", action="store_true")
    return parser.parse_known_args()[0]


ARGS = parse_args()
if os.environ.get("JARVIS_SAFE_START") == "1":
    ARGS.safe_start = True
if ARGS.safe_start:
    ARGS.text_mode = True
    ARGS.no_greeting = True

VOICE_MUTEX = "Local\\JarvisVoiceSingleton"
_mutex_handle = None


def _show_message(text: str):
    ctypes.windll.user32.MessageBoxW(None, text, "JARVIS", 0x40)


def _acquire_single_instance() -> bool:
    global _mutex_handle
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, VOICE_MUTEX)
    if not _mutex_handle:
        return True
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        return False
    return True


def _release_single_instance():
    global _mutex_handle
    if _mutex_handle:
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None


if not _acquire_single_instance():
    _show_message("JARVIS session is already running.")
    sys.exit(0)

atexit.register(_release_single_instance)

import numpy as np
import sounddevice as sd
from piper.voice import PiperVoice
import pvporcupine
import pyaudio
import struct

from env_utils import load_env_files

ROOT_DIR = Path(__file__).resolve().parent
load_env_files(ROOT_DIR / ".env", ROOT_DIR / "server" / ".env")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
BACKEND_URL = os.environ.get("JARVIS_BACKEND_URL", "http://127.0.0.1:8081").rstrip("/")
CHAT_MODEL = "minimax-m2.7:cloud"
VISION_MODEL = "qwen3-vl:235b-cloud"
PIPER_MODEL = r"C:\Users\sergen\AppData\Local\piper-models\tr_TR-dfki-medium.onnx"
PIPER_CONFIG = PIPER_MODEL + ".json"
SAMPLE_RATE = 22050
LOG_FILE = str(ROOT_DIR / "jarvis_konusmalar.txt")

SYSTEM_PROMPT = """Sen JARVIS'sin. Ekrem'in kisisel AI asistanisin. Windows bilgisayarini tam kontrol ediyorsun.

Kullanici bir sey istediginde:
1. Kisa yanit ver (1 cumle)
2. Gerekirse su formatta komut ekle: ##KOMUT:start https://youtube.com##

Komut ornekleri:
- YouTube ac: ##KOMUT:start https://www.youtube.com##
- Spotify ac: ##KOMUT:start spotify:##
- Chrome ac: ##KOMUT:start chrome##
- Notepad ac: ##KOMUT:start notepad##
- Dosya yoneticisi: ##KOMUT:start explorer##
- Ses ac: ##KOMUT:powershell (New-Object -com Shell.Application).setVolume(80)##
- Kapat: ##KOMUT:taskkill /F /IM chrome.exe##
- Ekran goruntusu: ##EKRANGOR##
- Mouse tikla: ##TIKLA:x,y##
- Yazi yaz: ##YAZ:metin##
- Tus bas: ##TUS:enter##

Kisa ve net konus. Turkce. Ekrem sabirsiz biri."""

_history = []
_voice = None


def _load_voice():
    global _voice
    if _voice is not None:
        return _voice
    print("[TTS] Yukleniyor...")
    _voice = PiperVoice.load(PIPER_MODEL, config_path=PIPER_CONFIG, use_cuda=False)
    print("[TTS] Hazir.")
    return _voice


def speak(text: str):
    if not text.strip():
        return
    print(f"Jarvis: {text}")
    try:
        clean = re.sub(r"##[A-Z]+:[^#]*##", "", text)
        clean = re.sub(r"[*_`#]", "", clean).strip()
        if not clean:
            clean = "Tamam."
        voice = _load_voice()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)
            voice.synthesize(clean[:200], wav_file)
        buf.seek(44)
        data = np.frombuffer(buf.read(), dtype=np.int16)
        sd.play(data, SAMPLE_RATE)
        sd.wait()
    except Exception as exc:
        print(f"[TTS hata] {exc}")


def ask_llm(text: str, image_b64: str = None) -> str:
    if image_b64 is None and BACKEND_URL:
        try:
            payload = json.dumps({"message": text}).encode()
            request = urllib.request.Request(
                f"{BACKEND_URL}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read())
            reply = (data.get("response") or "").strip()
            if reply:
                _history.append({"role": "user", "content": text})
                _history.append({"role": "assistant", "content": reply})
                return reply
        except Exception as exc:
            print(f"[BACKEND fallback] {exc}")

    history_text = ""
    for item in _history[-6:]:
        role = "Ekrem" if item["role"] == "user" else "Jarvis"
        history_text += f"{role}: {item['content']}\n"

    full_prompt = f"{history_text}Ekrem: {text}\nJarvis:"
    body = {
        "model": CHAT_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": full_prompt,
        "stream": False,
        "options": {"num_predict": 150, "temperature": 0.7},
    }
    if image_b64:
        body["images"] = [image_b64]

    try:
        payload = json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if OLLAMA_KEY:
            headers["Authorization"] = f"Bearer {OLLAMA_KEY}"
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            reply = json.loads(response.read()).get("response", "").strip()
        if reply:
            _history.append({"role": "user", "content": text})
            _history.append({"role": "assistant", "content": reply})
        return reply or "Anlayamadim, tekrar soyle."
    except Exception as exc:
        return f"Model hatasi: {exc}"


def take_screenshot() -> str:
    import base64
    import tempfile

    import pyautogui

    path = os.path.join(tempfile.gettempdir(), "jarvis_ss.png")
    pyautogui.screenshot().save(path)
    with open(path, "rb") as file_handle:
        return base64.b64encode(file_handle.read()).decode()


def execute_commands(response: str) -> str:
    import pyautogui

    for match in re.finditer(r"##KOMUT:([^#]+)##", response):
        cmd = match.group(1).strip()
        print(f"[PC] {cmd}")
        try:
            subprocess.Popen(cmd, shell=True)
            time.sleep(0.3)
        except Exception as exc:
            print(f"[PC hata] {exc}")

    if "##EKRANGOR##" in response:
        print("[PC] Ekran goruntusu aliniyor...")
        img = take_screenshot()
        vision_resp = ask_llm("Bu ekranda ne goruyorsun? Kisaca anlat.", img)
        speak(vision_resp)

    for match in re.finditer(r"##TIKLA:(\d+),(\d+)##", response):
        x, y = int(match.group(1)), int(match.group(2))
        print(f"[PC] Tikla ({x},{y})")
        pyautogui.click(x, y)

    for match in re.finditer(r"##YAZ:([^#]+)##", response):
        text = match.group(1)
        print(f"[PC] Yaz: {text}")
        pyautogui.write(text, interval=0.05)

    for match in re.finditer(r"##TUS:([^#]+)##", response):
        key = match.group(1).strip().lower()
        print(f"[PC] Tus: {key}")
        pyautogui.press(key)

    clean = re.sub(r"##[^#]+##", "", response).strip()
    return clean or "Tamam."


ANYDESK_EXE = r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe"
ANYDESK_PS = r"C:\Users\sergen\Desktop\jarvis-mission-control\anydesk_kabul.ps1"

QUICK_COMMANDS = {
    r"anydesk.*kabul|kabul.*anydesk|baglanti.*kabul|gelen.*kabul|istegi.*kabul": (
        f'powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ANYDESK_PS}"',
        "AnyDesk baglantisi kabul edildi.",
    ),
    r"anydesk.*ac|ac.*anydesk": (f'"{ANYDESK_EXE}"', "AnyDesk acildi."),
    r"youtube.*ac|ac.*youtube": ("start https://www.youtube.com", "YouTube acildi."),
    r"spotify.*ac|muzik.*ac|sarki.*cal": ("start spotify:", "Spotify acildi."),
    r"chrome.*ac|tarayici.*ac": ("start chrome", "Chrome acildi."),
    r"dosya.*yonetici|explorer.*ac": ("start explorer", "Dosya yoneticisi acildi."),
    r"not.*defteri|notepad": ("start notepad", "Notepad acildi."),
    r"hesap.*maki|calculator": ("start calc", "Hesap makinesi acildi."),
    r"ekran.*goruntus|screenshot": (None, "__SCREENSHOT__"),
    # r"bilgisayari.*kapat|shut.*down": ("shutdown /s /t 30", "Bilgisayar 30 saniyede kapanacak."),  # GÜVENLİK: devre dışı
}


def try_quick_command(text: str):
    text_lower = text.lower()
    for pattern, (cmd, reply) in QUICK_COMMANDS.items():
        if not re.search(pattern, text_lower):
            continue
        if reply == "__SCREENSHOT__":
            print("[PC] Ekran goruntusu...")
            img = take_screenshot()
            vision_resp = ask_llm("Ekranda ne var? Kisaca anlat.", img)
            speak(vision_resp)
            return True
        if cmd:
            subprocess.Popen(cmd, shell=True)
        speak(reply)
        return True
    return False


def log(ekrem: str, jarvis: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as file_handle:
        file_handle.write(f"[{ts}] Ekrem: {ekrem}\n")
        file_handle.write(f"[{ts}] Jarvis: {jarvis}\n\n")


def handle(text: str):
    text = text.strip()
    if not text or len(text) < 2:
        return
    print(f"\nSen: {text}")
    if try_quick_command(text):
        log(text, "(hizli komut)")
        return
    response = ask_llm(text)
    clean = execute_commands(response)
    speak(clean)
    log(text, clean)


def run_text_loop():
    while True:
        try:
            text = input("Sen: ").strip()
            if text:
                handle(text)
        except KeyboardInterrupt:
            break


def _build_recorder_kwargs():
    stt_device = os.environ.get("JARVIS_STT_DEVICE", "cpu").strip().lower() or "cpu"
    compute_type = os.environ.get("JARVIS_STT_COMPUTE_TYPE", "").strip()
    if not compute_type:
        compute_type = "int8" if stt_device == "cpu" else "default"

    kwargs = {
        "language": "tr",
        "model": "tiny",  # DÜZELTME: "small" → "tiny" (test'te çalıştığı doğrulandı)
        "device": stt_device,
        "compute_type": compute_type,
        "spinner": False,
        "input_device_index": 1,  # DÜZELTME: Logitech G733 Gaming Headset (test'te doğrulandı)
        # Wake word detection GEÇİCİ OLARAK KAPALI - test için
        # TODO: pvporcupine veya çalışan openWakeWord yapılandırması ekle
        # "wakeword_backend": "openwakeword",
        # "openwakeword_model_paths": "hey_jarvis",
        # "openwakeword_inference_framework": "onnx",
        # "wake_words": "hey jarvis",
        # "wake_words_sensitivity": 0.35,
        "silero_sensitivity": 0.4,
        "silero_use_onnx": True,
        "faster_whisper_vad_filter": False,
        "post_speech_silence_duration": 1.2,
        "min_length_of_recording": 0.8,
        "min_gap_between_recordings": 0.5,
        "enable_realtime_transcription": False,
        "print_transcription_time": True,
    }
    # ENV değişkeninden device index override edilebilir
    device_index = os.environ.get("JARVIS_INPUT_DEVICE_INDEX", "").strip()
    if device_index:
        try:
            kwargs["input_device_index"] = int(device_index)
            print(f"[MIK] Input device override: {device_index}")
        except ValueError:
            print(f"[MIK] Gecersiz JARVIS_INPUT_DEVICE_INDEX: {device_index}")
    print(
        f"[STT] Device={stt_device} compute_type={compute_type} "
        "faster_whisper_vad_filter=False"
    )
    return kwargs


def run_wake_word_mode():
    """
    Pvporcupine wake word detection mode.
    Continuously listens for "jarvis" keyword, then activates STT.
    """
    porcupine = None
    pa = None
    audio_stream = None

    try:
        import speech_recognition as sr

        # Initialize porcupine with built-in "jarvis" keyword
        access_key = os.environ.get("PICOVOICE_ACCESS_KEY", "")
        if not access_key:
            print("[WAKE] PICOVOICE_ACCESS_KEY bulunamadi!")
            print("[WAKE] Picovoice Console'dan (https://console.picovoice.ai/) ucretsiz key alin")
            print("[WAKE] .env dosyasina PICOVOICE_ACCESS_KEY=<your_key> ekleyin")
            print("[WAKE] Wake word olmadan normal mod baslatiliyor...\n")
            return run_continuous_listen_mode()

        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=["jarvis"],  # Built-in keyword
            sensitivities=[0.5]   # 0.0-1.0, higher = more sensitive
        )

        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
            input_device_index=1  # Logitech G733
        )

        print("[WAKE] Wake word detection aktif: 'Jarvis' deyin")
        print("[WAKE] Porcupine baslatildi (sample_rate={}, frame_length={})".format(
            porcupine.sample_rate, porcupine.frame_length))

        recognizer = sr.Recognizer()
        mic = sr.Microphone(device_index=1)

        while True:
            # Listen for wake word
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            keyword_index = porcupine.process(pcm)

            if keyword_index >= 0:
                # Wake word detected!
                print("\n[WAKE] 'Jarvis' algilandi! Dinliyorum...")

                # Play beep sound (optional)
                try:
                    beep_data = np.sin(2 * np.pi * 800 * np.arange(0, 0.1, 1/22050)).astype(np.float32)
                    sd.play(beep_data, 22050)
                    sd.wait()
                except:
                    pass

                # Now listen for command
                try:
                    with mic as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)

                    print('[STT] Isleniyor...')
                    text = recognizer.recognize_google(audio, language='tr-TR')
                    if text:
                        handle(text)
                    else:
                        print('[STT] Anlasilamadi')

                except sr.WaitTimeoutError:
                    print('[STT] Timeout - tekrar "Jarvis" deyin')
                except sr.UnknownValueError:
                    print('[STT] Anlasilamadi - tekrar "Jarvis" deyin')
                except sr.RequestError as e:
                    print(f'[STT] Google hatasi: {e}')

                print("[WAKE] Tekrar 'Jarvis' bekleniyor...\n")

    except KeyboardInterrupt:
        raise
    except Exception as exc:
        import traceback
        print(f"\n[WAKE] Wake word modu hatasi: {exc}")
        traceback.print_exc()
        print("[WAKE] Normal moda geciliyor...\n")
        return run_continuous_listen_mode()
    finally:
        if audio_stream:
            audio_stream.close()
        if pa:
            pa.terminate()
        if porcupine:
            porcupine.delete()


def run_continuous_listen_mode():
    """
    Continuous listening mode (fallback if wake word unavailable).
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        mic = sr.Microphone(device_index=1)  # Logitech G733

        # Ortam gurultusunu ayarla
        print('[MIK] Mikrofon ayarlaniyor...')
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        print('[MIK] Hazir - Konusmaya basla! (30 saniye konusma suresi)\n')

        while True:
            try:
                with mic as source:
                    print('[MIK] Dinliyorum...')
                    audio = recognizer.listen(source, timeout=30, phrase_time_limit=30)
                print('[MIK] Isleniyor...')
                try:
                    text = recognizer.recognize_google(audio, language='tr-TR')
                    if text:
                        print(f'Sen: {text}')
                        handle(text)
                except sr.UnknownValueError:
                    pass  # Anlasilamadi, tekrar dinle
                except sr.RequestError as e:
                    print(f'[MIK] Google STT hatasi: {e}')
            except sr.WaitTimeoutError:
                pass  # Timeout, tekrar dinle
            except KeyboardInterrupt:
                raise
    except KeyboardInterrupt:
        raise


def main():
    print("\n" + "=" * 50)
    print("  JARVIS - Tam Bilgisayar Kontrolu")
    print("  Konusunca algilar | Ctrl+C = cikis")
    print("=" * 50 + "\n")

    if ARGS.no_greeting:
        print("[JARVIS] Guvenli baslangic etkin. Mikrofon otomatik acilmadi.")
    else:
        speak("Merhaba! Jarvis hazir. Hey Jarvis de ve konus.")

    if ARGS.text_mode:
        print("[JARVIS] Yazi modu aktif.")
        run_text_loop()
        return

    try:
        # Try wake word mode first, falls back to continuous mode if unavailable
        run_wake_word_mode()
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        import traceback
        print(f"\n[!] Ses modu hatasi: {exc}")
        traceback.print_exc()
        print("[!] Yazi moduna geciliyor...")
        run_text_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if not ARGS.no_greeting:
            speak("Gorusuruz!")
        print("\n[Jarvis kapatildi]")
