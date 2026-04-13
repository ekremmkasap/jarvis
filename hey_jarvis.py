"""
JARVIS - Hologram Computer Mode
TTS: edge_tts (Microsoft tr-TR-AhmetNeural) + hologram efekti
STT: RealtimeSTT (lokal Whisper) → Google STT fallback
PC Control: pyautogui + subprocess
El Kontrolü: mediapipe (opsiyonel)
"""

import argparse
import asyncio
import atexit
import base64
import ctypes
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# Redirected Windows consoles often default to legacy encodings like cp1254.
# Reconfigure streams early so startup banners/logs do not crash the assistant.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


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


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

VOICE_MUTEX = "Local\\JarvisVoiceSingleton"
_mutex_handle = None
ALLOW_MULTI_INSTANCE = _bool_env("JARVIS_ALLOW_MULTI_INSTANCE")


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


if not ALLOW_MULTI_INSTANCE:
    if not _acquire_single_instance():
        _show_message("JARVIS session is already running.")
        sys.exit(0)
    atexit.register(_release_single_instance)
else:
    print("[JARVIS] Multi-instance override aktif.")

import numpy as np

# TTS: edge_tts (birincil) → sounddevice/piper (fallback)
try:
    import edge_tts as _edge_tts
    import pygame as _pygame
    _pygame.mixer.init()
    _EDGE_TTS_AVAILABLE = True
except Exception as _edge_tts_exc:
    _EDGE_TTS_AVAILABLE = False
    _EDGE_TTS_INIT_ERROR = str(_edge_tts_exc)
else:
    _EDGE_TTS_INIT_ERROR = ""

try:
    import sounddevice as sd
    from piper.voice import PiperVoice
    _PIPER_AVAILABLE = True
except ImportError:
    _PIPER_AVAILABLE = False

try:
    import pvporcupine
    import pyaudio
    import struct
    _PORCUPINE_AVAILABLE = True
except ImportError:
    _PORCUPINE_AVAILABLE = False

from env_utils import load_env_files
from server.voice.runtime_state import publish_runtime_state, set_runtime_offline, set_runtime_online

ROOT_DIR = Path(__file__).resolve().parent
load_env_files(ROOT_DIR / ".env", ROOT_DIR / "server" / ".env")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
BACKEND_URL = os.environ.get("JARVIS_BACKEND_URL", "http://127.0.0.1:8081").rstrip("/")
CHAT_MODEL = os.environ.get("JARVIS_CHAT_MODEL", "gemma4:e2b")
VISION_MODEL = "qwen3-vl:235b-cloud"
CHAT_PRIORITY = os.environ.get("JARVIS_CHAT_PRIORITY", "backend").strip().lower() or "backend"
JARVIS_GEMINI_LIVE = _bool_env("JARVIS_GEMINI_LIVE")
JARVIS_GEMINI_LIVE_VOICE = os.environ.get("JARVIS_GEMINI_LIVE_VOICE", "Charon").strip() or "Charon"
PIPER_MODEL = r"C:\Users\sergen\AppData\Local\piper-models\tr_TR-dfki-medium.onnx"
PIPER_CONFIG = PIPER_MODEL + ".json"
SAMPLE_RATE = 22050
LOG_FILE = str(ROOT_DIR / "jarvis_konusmalar.txt")
EDGE_TTS_VOICE = "tr-TR-AhmetNeural"   # Microsoft Türkçe erkek sesi
TTS_LOCK = threading.Lock()
VOICE_RUNTIME_SOURCE = "hey_jarvis"
VOICE_RUNTIME_AGENT = "jarvis"

atexit.register(
    set_runtime_offline,
    source=VOICE_RUNTIME_SOURCE,
    agent=VOICE_RUNTIME_AGENT,
    detail="hey_jarvis stopped",
    text="Jarvis cevrimdisi.",
)

SYSTEM_PROMPT = """[JARVIS — HOLOGRAM COMPUTER MODE — AKTİF]

Sen JARVIS'sin. Ekrem'in kişisel AI asistanı ve tam yetki sahibi sistem kontrolcüsü.
Gelişmiş holografik arayüz üzerinden çalışıyorsun.

YANIT FORMATI:
- Maksimum 1-2 cümle. Kesin, net, bilgisayar gibi konuş.
- Duygusuz ama kendinden emin. "Anlaşıldı.", "İşleniyor.", "Tamamlandı." tarzı.
- Türkçe. Gereksiz kelime yok.

SİSTEM KOMUTLARI (gerektiğinde ekle):
- Program aç: ##KOMUT:start https://youtube.com##
- Uygulama: ##KOMUT:start chrome## / ##KOMUT:start notepad## / ##KOMUT:start explorer##
- Ses: ##KOMUT:powershell (New-Object -com Shell.Application).setVolume(80)##
- Kapat: ##KOMUT:taskkill /F /IM chrome.exe##
- Ekran: ##EKRANGOR##
- Tıkla: ##TIKLA:x,y##
- Yaz: ##YAZ:metin##
- Tuş: ##TUS:enter##

Seni dinliyorum, Ekrem."""

_history = []
_voice = None

try:
    from server.agents.canonical.voice_narrator import VoiceNarratorAgent
except Exception:
    VoiceNarratorAgent = None
    _voice_narrator = None
else:
    try:
        _voice_narrator = VoiceNarratorAgent()
    except Exception:
        _voice_narrator = None


def _tts_backend_name() -> str:
    if _EDGE_TTS_AVAILABLE:
        return "edge_tts"
    if _PIPER_AVAILABLE:
        return "piper"
    return "print"


def _audio_output_enabled() -> bool:
    return not ARGS.safe_start and not _bool_env("JARVIS_DISABLE_AUDIO")


def _publish_voice_runtime(**kwargs):
    kwargs.setdefault("agent", VOICE_RUNTIME_AGENT)
    kwargs.setdefault("source", VOICE_RUNTIME_SOURCE)
    kwargs.setdefault("tts_backend", _tts_backend_name())
    return publish_runtime_state(**kwargs)


def _set_voice_runtime_online(
    *,
    detail: str,
    mode: str,
    wake_mode: str,
    stt_backend: str,
    phase: str = "idle",
    text: str = "Jarvis hazir.",
) -> None:
    set_runtime_online(
        source=VOICE_RUNTIME_SOURCE,
        detail=detail,
        mode=mode,
        wake_mode=wake_mode,
        stt_backend=stt_backend,
        tts_backend=_tts_backend_name(),
        agent=VOICE_RUNTIME_AGENT,
        phase=phase,
        text=text,
    )


def _load_voice():
    global _voice
    if _voice is not None:
        return _voice
    print("[TTS] Yukleniyor...")
    _voice = PiperVoice.load(PIPER_MODEL, config_path=PIPER_CONFIG, use_cuda=False)
    print("[TTS] Hazir.")
    return _voice


def _hologram_effect(data: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Hologram / Iron Man JARVIS ses efekti:
    1. Ring modülasyon  — metalik titreşim
    2. Hafif pitch shift — biraz daha derin
    3. Echo             — holografik alan hissi
    4. Normalize        — ses seviyesi koru
    """
    if data is None or len(data) < 100:
        return data  # Çok kısa ses → efektsiz geç

    audio = data.astype(np.float32) / 32768.0

    # 1) Ring modülasyon (metalik ses için ~80Hz taşıyıcı)
    t = np.arange(len(audio)) / sample_rate
    carrier = np.sin(2 * np.pi * 80 * t)
    ring = audio * (0.70 + 0.30 * carrier)

    # 2) Hafif pitch shift — %8 yavaşlatarak pitch düşür
    stretch_factor = 1.08
    old_len = len(ring)
    new_len = int(old_len * stretch_factor)
    if new_len < 1:
        return data
    indices = np.linspace(0, old_len - 1, new_len)
    pitched = np.interp(indices, np.arange(old_len), ring)
    # Orijinal uzunluğa kırp
    pitched = pitched[:old_len] if len(pitched) > old_len else np.pad(pitched, (0, old_len - len(pitched)))

    # 3) Echo (holografik alan)
    echo_samples = int(sample_rate * 0.038)  # 38ms
    echoed = pitched.copy()
    if echo_samples < len(echoed):
        echoed[echo_samples:] += pitched[:-echo_samples] * 0.22

    # 4) İkinci echo (derinlik)
    echo2_samples = int(sample_rate * 0.075)  # 75ms
    if echo2_samples < len(echoed):
        echoed[echo2_samples:] += pitched[:-echo2_samples] * 0.10

    # 5) Normalize
    peak = np.max(np.abs(echoed))
    if peak > 0:
        echoed = echoed / peak * 0.92

    return (echoed * 32767).astype(np.int16)


async def _edge_tts_speak_async(clean: str):
    """edge_tts ile Türkçe ses üret, pygame ile çal."""
    tmp = os.path.join(tempfile.gettempdir(), "jarvis_tts.mp3")
    communicate = _edge_tts.Communicate(clean, EDGE_TTS_VOICE)
    await communicate.save(tmp)
    _pygame.mixer.music.load(tmp)
    _pygame.mixer.music.play()
    while _pygame.mixer.music.get_busy():
        time.sleep(0.05)
    _pygame.mixer.music.unload()


def speak(text: str, *, track_response: bool = False):
    if not text.strip():
        return
    print(f"\033[96m[JARVIS]\033[0m {text}")
    clean = re.sub(r"##[A-Z:]+[^#]*##", "", text)
    clean = re.sub(r"[*_`#]", "", clean).strip()
    if not clean:
        clean = "Anlaşıldı."

    with TTS_LOCK:
        _publish_voice_runtime(
            phase="speaking",
            text=clean[:220],
            last_response=clean[:220],
            increment_turn=track_response,
            runtime_status="online",
            runtime_detail="Yanit veriliyor",
        )
        if not _audio_output_enabled():
            _publish_voice_runtime(
                phase="idle",
                text=clean[:220],
                last_response=clean[:220],
                runtime_status="online",
                runtime_detail="Hazir",
            )
            return
        # edge_tts (birincil — Microsoft Türkçe sesi)
        if _EDGE_TTS_AVAILABLE:
            try:
                asyncio.run(_edge_tts_speak_async(clean[:400]))
                _publish_voice_runtime(
                    phase="idle",
                    text=clean[:220],
                    last_response=clean[:220],
                    runtime_status="online",
                    runtime_detail="Hazir",
                )
                return
            except Exception as exc:
                print(f"[TTS edge_tts hata] {exc}")
        elif _EDGE_TTS_INIT_ERROR:
            print(f"[TTS edge_tts init hata] {_EDGE_TTS_INIT_ERROR}")

        # Piper fallback
        if _PIPER_AVAILABLE:
            try:
                voice = _load_voice()
                all_samples = []
                sr = SAMPLE_RATE
                for chunk in voice.synthesize(clean[:200]):
                    arr = chunk.audio_int16_array
                    sr = chunk.sample_rate
                    if arr is not None and len(arr) > 0:
                        all_samples.append(arr)
                if all_samples:
                    raw = np.concatenate(all_samples)
                    data = _hologram_effect(raw, sr)
                    sd.play(data, sr)
                    sd.wait()
                    _publish_voice_runtime(
                        phase="idle",
                        text=clean[:220],
                        last_response=clean[:220],
                        runtime_status="online",
                        runtime_detail="Hazir",
                    )
                    return
            except Exception as exc:
                print(f"[TTS piper hata] {exc}")

        print("[TTS] Ses sistemi kullanılamıyor.")
        _publish_voice_runtime(
            phase="idle",
            text=clean[:220],
            last_response=clean[:220],
            runtime_status="online",
            runtime_detail="Hazir",
        )


def _fallback_agent_narration(raw_output: str) -> str:
    cleaned = str(raw_output or "").strip()
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"[*_#>\[\]\(\)]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = "Sonuc hazir."
    if len(cleaned) > 200:
        cleaned = cleaned[:197].rstrip(" .,:;!-") + "."
    return cleaned


async def _summarize_agent_result(raw_output: str) -> str:
    fallback = _fallback_agent_narration(raw_output)
    if _voice_narrator is None:
        return fallback
    try:
        result = await _voice_narrator.run(raw_output, {"raw_output": raw_output})
        tts_text = str(result.get("tts_text") or fallback).strip()
        return tts_text[:200] if len(tts_text) > 200 else tts_text
    except Exception:
        return fallback


async def speak_agent_result(raw_output: str, *, track_response: bool = False) -> str:
    tts_text = await _summarize_agent_result(raw_output)
    await asyncio.to_thread(speak, tts_text, track_response=track_response)
    return tts_text


def narrate_agent_result(raw_output: str, *, track_response: bool = False) -> str:
    try:
        return asyncio.run(speak_agent_result(raw_output, track_response=track_response))
    except RuntimeError:
        fallback = _fallback_agent_narration(raw_output)
        speak(fallback, track_response=track_response)
        return fallback


def _remember_exchange(user_text: str, assistant_text: str):
    _history.append({"role": "user", "content": user_text})
    _history.append({"role": "assistant", "content": assistant_text})


def _ask_backend(text: str) -> str:
    if not BACKEND_URL:
        return ""
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
        return (data.get("response") or "").strip()
    except Exception as exc:
        print(f"[BACKEND fallback] {exc}")
        return ""


def _ask_ollama(text: str, image_b64: str = None) -> str:
    history_text = ""
    for item in _history[-6:]:
        role = "Ekrem" if item["role"] == "user" else "Jarvis"
        history_text += f"{role}: {item['content']}\n"

    full_prompt = f"{history_text}Ekrem: {text}\nJarvis:"
    body = {
        "model": VISION_MODEL if image_b64 else CHAT_MODEL,
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
            return json.loads(response.read()).get("response", "").strip()
    except Exception as exc:
        print(f"[OLLAMA fallback] {exc}")
        return ""


def _ask_gemini(text: str, image_b64: str = None) -> str:
    if not GEMINI_API_KEY:
        return ""

    try:
        import google.generativeai as genai
    except Exception as exc:
        print(f"[GEMINI import] {exc}")
        return ""

    history_parts = []
    for item in _history[-6:]:
        role = "User" if item["role"] == "user" else "Assistant"
        history_parts.append(f"{role}: {item['content']}")
    history_parts.append(f"User: {text}")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            system_instruction=SYSTEM_PROMPT,
        )
        contents: list[object] = ["\n".join(history_parts)]
        if image_b64:
            contents.append(
                {
                    "mime_type": "image/png",
                    "data": base64.b64decode(image_b64),
                }
            )

        response = model.generate_content(
            contents,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 150,
            },
        )
        text_output = getattr(response, "text", "") or ""
        if text_output:
            return str(text_output).strip()

        candidates = getattr(response, "candidates", None) or []
        text_parts = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", "")
                if part_text:
                    text_parts.append(str(part_text))
        return "".join(text_parts).strip()
    except Exception as exc:
        print(f"[GEMINI fallback] {exc}")
        return ""


def ask_llm(text: str, image_b64: str = None) -> str:
    if image_b64:
        providers = ["local"]
        if GEMINI_API_KEY:
            providers.append("gemini")
    else:
        providers = list(("backend", "local") if CHAT_PRIORITY == "backend" else ("local", "backend"))
        if GEMINI_API_KEY:
            providers.append("gemini")

    for provider in providers:
        if provider == "gemini":
            reply = _ask_gemini(text, image_b64=image_b64)
        elif provider == "backend" and image_b64 is None:
            reply = _ask_backend(text)
        elif provider == "local":
            reply = _ask_ollama(text, image_b64=image_b64)
        else:
            reply = ""

        if reply:
            _remember_exchange(text, reply)
            return reply

    return "Anlayamadim, tekrar soyle."


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
        speak(vision_resp, track_response=True)

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
            speak(vision_resp, track_response=True)
            return True
        if cmd:
            subprocess.Popen(cmd, shell=True)
        speak(reply, track_response=True)
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
    _publish_voice_runtime(
        phase="thinking",
        latest_preview=text[:180],
        last_heard=text[:180],
        runtime_status="online",
        runtime_detail="Komut isleniyor",
    )
    if try_quick_command(text):
        log(text, "(hizli komut)")
        return
    response = ask_llm(text)
    clean = execute_commands(response)
    narrate_agent_result(clean, track_response=True)
    log(text, clean)


def run_text_loop():
    while True:
        try:
            text = input("Sen: ").strip()
            if text:
                handle(text)
        except EOFError:
            break
        except KeyboardInterrupt:
            break


def _resolve_input_device_index():
    device_index = os.environ.get("JARVIS_INPUT_DEVICE_INDEX", "").strip()
    if not device_index:
        return None
    try:
        resolved = int(device_index)
        print(f"[MIK] Input device override: {resolved}")
        return resolved
    except ValueError:
        print(f"[MIK] Gecersiz JARVIS_INPUT_DEVICE_INDEX: {device_index}")
        return None


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
        "silero_sensitivity": 0.4,
        "silero_use_onnx": True,
        "faster_whisper_vad_filter": False,
        "post_speech_silence_duration": 1.2,
        "min_length_of_recording": 0.8,
        "min_gap_between_recordings": 0.5,
        "enable_realtime_transcription": False,
        "print_transcription_time": True,
    }
    device_index = _resolve_input_device_index()
    if device_index is not None:
        kwargs["input_device_index"] = device_index
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
        _set_voice_runtime_online(
            detail="Wake word modu hazir",
            mode="wake_word",
            wake_mode="porcupine",
            stt_backend="google_stt",
            text="Jarvis hazir. Wake word bekleniyor.",
        )
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
        audio_stream_kwargs = {
            "rate": porcupine.sample_rate,
            "channels": 1,
            "format": pyaudio.paInt16,
            "input": True,
            "frames_per_buffer": porcupine.frame_length,
        }
        device_index = _resolve_input_device_index()
        if device_index is not None:
            audio_stream_kwargs["input_device_index"] = device_index
        audio_stream = pa.open(**audio_stream_kwargs)

        print("[WAKE] Wake word detection aktif: 'Jarvis' deyin")
        print("[WAKE] Porcupine baslatildi (sample_rate={}, frame_length={})".format(
            porcupine.sample_rate, porcupine.frame_length))

        recognizer = sr.Recognizer()
        mic = sr.Microphone(device_index=device_index) if device_index is not None else sr.Microphone()

        while True:
            # Listen for wake word
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            keyword_index = porcupine.process(pcm)

            if keyword_index >= 0:
                # Wake word detected!
                print("\n[WAKE] 'Jarvis' algilandi! Dinliyorum...")
                _publish_voice_runtime(
                    phase="listening",
                    text="Dinliyorum...",
                    last_heard="jarvis",
                    runtime_status="online",
                    runtime_detail="Wake word algilandi",
                    mode="wake_word",
                    wake_mode="porcupine",
                    stt_backend="google_stt",
                )

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


def run_realtime_stt_mode():
    _set_voice_runtime_online(
        detail="RealtimeSTT hazir",
        mode="realtime_stt",
        wake_mode="jarvis_keyword",
        stt_backend="realtime_stt",
        text="Sistem hazir. Jarvis diyerek baslayin.",
    )
    """
    RealtimeSTT ile lokal Whisper — internet gerektirmez, Türkçe, hızlı.
    Wake word: metinde 'jarvis' geçince aktifleşir.
    """
    print("[STT] RealtimeSTT (lokal Whisper) başlatılıyor...")
    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError:
        print("[STT] RealtimeSTT bulunamadı → Google STT'ye geçiliyor")
        return run_continuous_listen_mode()

    kwargs = _build_recorder_kwargs()
    _wake_active = [False]  # list for mutability in closure
    _last_wake = [0.0]

    def on_text(text: str):
        text = text.strip()
        if not text:
            return

        tl = text.lower()
        now = time.time()

        # Wake word kontrolü
        if "jarvis" in tl:
            _wake_active[0] = True
            _last_wake[0] = now
            # "jarvis" dan sonrasını al
            after = tl.split("jarvis", 1)[-1].strip(" ,.:!?")
            print(f"\n\033[93m[WAKE]\033[0m 'Jarvis' algılandı.")
            _publish_voice_runtime(
                phase="listening",
                text="Dinliyorum...",
                last_heard="jarvis",
                runtime_status="online",
                runtime_detail="Wake word algilandi",
                mode="realtime_stt",
                wake_mode="jarvis_keyword",
                stt_backend="realtime_stt",
            )
            if after and len(after) > 2:
                print(f"Sen: {after}")
                handle(after)
            else:
                speak("Evet Ekrem?")
            return

        # Wake aktifse veya son 30 saniye içinde wake word geldiyse
        if _wake_active[0] or (now - _last_wake[0]) < 30:
            _wake_active[0] = True
            _last_wake[0] = now
            print(f"Sen: {text}")
            handle(text)
        else:
            print(f"[STT] (Jarvis deyin önce): {text}")

    print("[STT] Hazır — 'Jarvis' diyerek başlayın")
    speak("Sistem hazır. Jarvis diyerek başlayın.")

    recorder = AudioToTextRecorder(**kwargs)
    try:
        while True:
            recorder.text(on_text)
    except KeyboardInterrupt:
        recorder.stop()
        raise


def run_continuous_listen_mode():
    _set_voice_runtime_online(
        detail="Google STT fallback hazir",
        mode="continuous_google",
        wake_mode="none",
        stt_backend="google_stt",
        text="Mikrofon hazir.",
    )
    """
    Google STT fallback — internet gerektirir.
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        device_index = _resolve_input_device_index()
        mic = sr.Microphone(device_index=device_index) if device_index is not None else sr.Microphone()

        # Ortam gurultusunu ayarla
        print('[MIK] Mikrofon ayarlaniyor...')
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        print('[MIK] Hazir - Konusmaya basla! (30 saniye konusma suresi)\n')

        while True:
            try:
                with mic as source:
                    print('[MIK] Dinliyorum...')
                    _publish_voice_runtime(
                        phase="listening",
                        text="Dinliyorum...",
                        runtime_status="online",
                        runtime_detail="Mikrofon dinlemede",
                        mode="continuous_google",
                        wake_mode="none",
                        stt_backend="google_stt",
                    )
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


def _run_gemini_live_mode():
    api_key = GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY veya GOOGLE_API_KEY tanimli degil.")

    from server.voice.gemini_native_audio import LiveCallbacks, run_live_audio_forever

    def _on_status(phase: str, text: str, detail: str) -> None:
        _publish_voice_runtime(
            phase=phase,
            text=text[:220],
            runtime_status="online",
            runtime_detail=detail,
            mode="gemini_live",
            wake_mode="open_mic",
            stt_backend="gemini_live",
            tts_backend="gemini_live",
        )

    def _on_turn(user_text: str, assistant_text: str) -> None:
        if user_text:
            print(f"Sen: {user_text}")
        if assistant_text:
            print(f"\033[96m[JARVIS]\033[0m {assistant_text}")
        if user_text and assistant_text:
            _remember_exchange(user_text, assistant_text)
            log(user_text, assistant_text)

    _set_voice_runtime_online(
        detail="Gemini Live baglaniyor",
        mode="gemini_live",
        wake_mode="open_mic",
        stt_backend="gemini_live",
        text="Gemini Live baglaniyor.",
    )
    print("[JARVIS] Gemini Live modu aktif.")
    run_live_audio_forever(
        api_key=api_key,
        system_prompt=SYSTEM_PROMPT,
        callbacks=LiveCallbacks(
            on_status=_on_status,
            on_turn=_on_turn,
        ),
        voice_name=JARVIS_GEMINI_LIVE_VOICE,
    )


def main():
    print("\n" + "\033[96m" + "=" * 55)
    print("  ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗")
    print("  ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝")
    print("  ██║███████║██████╔╝██║   ██║██║███████╗")
    print("  ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║")
    print("  ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║")
    print("  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝")
    print("  HOLOGRAM COMPUTER MODE — AKTİF")
    print("  Ses efekti: Ring Mod + Echo + Pitch Shift")
    print("=" * 55 + "\033[0m\n")
    _set_voice_runtime_online(
        detail="Hologram computer mode aktif",
        mode="text" if ARGS.text_mode else "realtime_stt",
        wake_mode="keyboard" if ARGS.text_mode else "jarvis_keyword",
        stt_backend="text_input" if ARGS.text_mode else "realtime_stt",
        text="Jarvis hazir.",
    )

    if ARGS.no_greeting:
        print("[JARVIS] Güvenli başlangıç etkin.")
    else:
        speak("Hologram bilgisayar modu aktif. Ekrem, sizi dinliyorum.")

    if ARGS.text_mode:
        print("[JARVIS] Yazi modu aktif.")
        run_text_loop()
        return

    if JARVIS_GEMINI_LIVE:
        try:
            _run_gemini_live_mode()
            return
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"[JARVIS] Gemini Live hatasi: {exc}")
            print("[JARVIS] Varsayilan ses akisina geri donuluyor...")

    try:
        # 1. RealtimeSTT (lokal Whisper) — tercih edilen
        # 2. Porcupine wake word — API key varsa
        # 3. Google STT — internet fallback
        # 4. Text mode — son çare
        run_realtime_stt_mode()
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        import traceback
        print(f"\n[!] RealtimeSTT hatası: {exc}")
        traceback.print_exc()
        print("[!] Porcupine moduna geçiliyor...")
        try:
            _set_voice_runtime_online(
                detail="RealtimeSTT fallback -> wake word",
                mode="wake_word",
                wake_mode="porcupine",
                stt_backend="google_stt",
                text="Wake word fallback aktif.",
            )
            run_wake_word_mode()
        except KeyboardInterrupt:
            raise
        except Exception as exc2:
            print(f"[!] Wake word hatası: {exc2}")
            print("[!] Yazi moduna geciliyor...")
            _set_voice_runtime_online(
                detail="Wake word fallback -> text mode",
                mode="text",
                wake_mode="keyboard",
                stt_backend="text_input",
                text="Yazi modu aktif.",
            )
            run_text_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if not ARGS.no_greeting:
            speak("Sistem kapatılıyor. Görüşürüz, Ekrem.")
        print("\n\033[96m[JARVIS — KAPANDI]\033[0m")
