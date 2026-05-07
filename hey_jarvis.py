"""
JARVIS - Hologram Computer Mode
TTS: edge_tts (Microsoft tr-TR-AhmetNeural) + hologram efekti
STT: RealtimeSTT (lokal Whisper) â†’ Google STT fallback
PC Control: pyautogui + subprocess
El KontrolÃ¼: mediapipe (opsiyonel)
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

# TTS: edge_tts (birincil) â†’ sounddevice/piper (fallback)
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
from server.voice.runtime_state import (
    publish_runtime_state,
    set_runtime_offline,
    set_runtime_online,
)

ROOT_DIR = Path(__file__).resolve().parent
load_env_files(ROOT_DIR / ".env", ROOT_DIR / "server" / ".env")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
BACKEND_URL = os.environ.get("JARVIS_BACKEND_URL", "http://127.0.0.1:8081").rstrip("/")
CHAT_MODEL = os.environ.get("JARVIS_CHAT_MODEL", "gemma4:e2b")
VISION_MODEL = "qwen3-vl:235b-cloud"
CHAT_PRIORITY = (
    os.environ.get("JARVIS_CHAT_PRIORITY", "backend").strip().lower() or "backend"
)
JARVIS_GEMINI_LIVE = _bool_env("JARVIS_GEMINI_LIVE")
JARVIS_GEMINI_LIVE_VOICE = (
    os.environ.get("JARVIS_GEMINI_LIVE_VOICE", "Charon").strip() or "Charon"
)
JARVIS_OPEN_MIC = _bool_env("JARVIS_OPEN_MIC")
PIPER_MODEL = r"C:\Users\sergen\AppData\Local\piper-models\tr_TR-dfki-medium.onnx"
PIPER_CONFIG = PIPER_MODEL + ".json"
SAMPLE_RATE = 22050
LOG_FILE = str(ROOT_DIR / "jarvis_konusmalar.txt")
EDGE_TTS_VOICE = "tr-TR-AhmetNeural"  # Microsoft TÃ¼rkÃ§e erkek sesi
TTS_LOCK = threading.Lock()
VOICE_RUNTIME_SOURCE = "hey_jarvis"
VOICE_RUNTIME_AGENT = "jarvis"

# Swarm TTS queue kÃ¶prÃ¼sÃ¼ (bridge.py â†’ hey_jarvis polling)
_SWARM_TTS_QUEUE_PATH = ROOT_DIR / "state" / "swarm_tts_queue.json"
_SWARM_TTS_SEEN: set = set()
_SWARM_TTS_POLL_INTERVAL = 10.0


def _swarm_tts_poll_loop():
    """Arkaplan thread'i: state/swarm_tts_queue.json'Ä± izler, yeni eventleri seslendirir."""
    import json as _json
    _STALE_SECONDS = 60
    while True:
        try:
            if _SWARM_TTS_QUEUE_PATH.exists():
                data = _json.loads(_SWARM_TTS_QUEUE_PATH.read_text(encoding="utf-8"))
                now_ts = time.time()
                remaining = []
                for ev in data.get("queue", []):
                    eid = ev.get("event_id")
                    ev_ts = float(ev.get("ts") or 0)
                    if ev_ts and now_ts - ev_ts > _STALE_SECONDS:
                        continue
                    if not eid or eid in _SWARM_TTS_SEEN:
                        continue
                    _SWARM_TTS_SEEN.add(eid)
                    text = ev.get("text") or ""
                    if text:
                        try:
                            speak(text)
                        except Exception:
                            pass
                try:
                    _SWARM_TTS_QUEUE_PATH.write_text(
                        _json.dumps({"queue": remaining}), encoding="utf-8"
                    )
                except Exception:
                    pass
                if len(_SWARM_TTS_SEEN) > 200:
                    _SWARM_TTS_SEEN.clear()
        except Exception:
            pass
        time.sleep(_SWARM_TTS_POLL_INTERVAL)


def _start_swarm_tts_watcher():
    t = threading.Thread(target=_swarm_tts_poll_loop, daemon=True, name="swarm-tts-watcher")
    t.start()

atexit.register(
    set_runtime_offline,
    source=VOICE_RUNTIME_SOURCE,
    agent=VOICE_RUNTIME_AGENT,
    detail="hey_jarvis stopped",
    text="Jarvis cevrimdisi.",
)

SYSTEM_PROMPT = """[JARVIS â€” HOLOGRAM COMPUTER MODE â€” AKTÄ°F]

Sen JARVIS'sin. Ekrem'in kiÅŸisel AI asistanÄ± ve tam yetki sahibi sistem kontrolcÃ¼sÃ¼.
GeliÅŸmiÅŸ holografik arayÃ¼z Ã¼zerinden Ã§alÄ±ÅŸÄ±yorsun.

YANIT FORMATI:
- Maksimum 1-2 cÃ¼mle. Kesin, net, bilgisayar gibi konuÅŸ.
- Duygusuz ama kendinden emin. "AnlaÅŸÄ±ldÄ±.", "Ä°ÅŸleniyor.", "TamamlandÄ±." tarzÄ±.
- TÃ¼rkÃ§e. Gereksiz kelime yok.

SÄ°STEM KOMUTLARI (gerektiÄŸinde ekle):
- Program aÃ§: ##KOMUT:start https://youtube.com##
- Uygulama: ##KOMUT:start chrome## / ##KOMUT:start notepad## / ##KOMUT:start explorer##
- Ses: ##KOMUT:powershell (New-Object -com Shell.Application).setVolume(80)##
- Kapat: ##KOMUT:taskkill /F /IM chrome.exe##
- Ekran: ##EKRANGOR##
- TÄ±kla: ##TIKLA:x,y##
- Yaz: ##YAZ:metin##
- TuÅŸ: ##TUS:enter##

Seni dinliyorum, Ekrem."""

_history = []
_voice = None
_last_greeted_persona = "jarvis"

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


def _publish_post_speech_runtime_state(*, runtime_agent: str, preview_text: str) -> None:
    if JARVIS_OPEN_MIC:
        _publish_voice_runtime(
            phase="listening",
            text="Dinliyorum...",
            latest_preview=preview_text,
            last_response=preview_text,
            runtime_status="online",
            runtime_detail="Mikrofon dinlemede",
            mode="realtime_stt",
            wake_mode="open_mic",
            stt_backend="realtime_stt",
            agent=runtime_agent,
        )
        return

    _publish_voice_runtime(
        phase="idle",
        text=preview_text,
        last_response=preview_text,
        runtime_status="online",
        runtime_detail="Hazir",
        agent=runtime_agent,
    )


def _get_active_persona_runtime() -> dict:
    try:
        from server.persona_manager import get_active_persona

        persona = get_active_persona()
        if isinstance(persona, dict):
            return persona
    except Exception:
        pass
    return {"id": "jarvis", "voice": "AhmetNeural"}


def _normalize_wake_alias(value: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return cleaned.strip(" ,.:;!?")


def _current_wake_aliases() -> list[str]:
    aliases = ["jarvis"]
    active_persona = _get_active_persona_runtime()
    for candidate in (active_persona.get("id"), active_persona.get("name")):
        alias = _normalize_wake_alias(candidate)
        if alias and alias not in aliases:
            aliases.append(alias)
    phonetic_aliases = {
        "mert": ["matt", "met"],
    }
    for alias in list(aliases):
        for phonetic in phonetic_aliases.get(alias, []):
            if phonetic not in aliases:
                aliases.append(phonetic)
    return aliases


def _current_wake_phrase() -> str:
    aliases = _current_wake_aliases()
    display = ["Jarvis" if alias == "jarvis" else alias.title() for alias in aliases]
    if len(display) == 1:
        return display[0]
    return " veya ".join(display)


def _find_wake_alias(text: str) -> tuple[str, tuple[int, int]] | tuple[None, None]:
    normalized = _normalize_wake_alias(text)
    for alias in _current_wake_aliases():
        match = re.search(rf"\b{re.escape(alias)}\b", normalized, re.IGNORECASE)
        if match:
            return alias, match.span()
    return None, None


def _current_voice_name() -> str:
    active_persona = _get_active_persona_runtime()
    persona_voice = str(active_persona.get("voice") or "").strip() or "AhmetNeural"
    if not persona_voice:
        persona_voice = "AhmetNeural"
    if persona_voice.lower().startswith("tr-tr-"):
        return persona_voice
    return f"tr-TR-{persona_voice}"


def _current_runtime_agent() -> str:
    return str(_get_active_persona_runtime().get("id") or VOICE_RUNTIME_AGENT)


def _maybe_speak_persona_greeting(
    *, expected_previous_persona: str | None = None
) -> bool:
    global _last_greeted_persona

    if ARGS.no_greeting:
        return False

    active_persona = _get_active_persona_runtime()
    persona_id = str(active_persona.get("id") or VOICE_RUNTIME_AGENT).strip().lower()
    if not persona_id:
        persona_id = VOICE_RUNTIME_AGENT

    if expected_previous_persona is not None and persona_id == expected_previous_persona:
        return False
    if persona_id == _last_greeted_persona:
        return False

    greeting = str(active_persona.get("greeting") or "").strip()
    _last_greeted_persona = persona_id
    if not greeting:
        return False

    speak(greeting, track_response=False)
    return True


def _publish_voice_runtime(**kwargs):
    kwargs.setdefault("agent", _current_runtime_agent())
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
    agent: str | None = None,
) -> None:
    set_runtime_online(
        source=VOICE_RUNTIME_SOURCE,
        detail=detail,
        mode=mode,
        wake_mode=wake_mode,
        stt_backend=stt_backend,
        tts_backend=_tts_backend_name(),
        agent=agent or _current_runtime_agent(),
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
    1. Ring modÃ¼lasyon  â€” metalik titreÅŸim
    2. Hafif pitch shift â€” biraz daha derin
    3. Echo             â€” holografik alan hissi
    4. Normalize        â€” ses seviyesi koru
    """
    if data is None or len(data) < 100:
        return data  # Ã‡ok kÄ±sa ses â†’ efektsiz geÃ§

    audio = data.astype(np.float32) / 32768.0

    # 1) Ring modÃ¼lasyon (metalik ses iÃ§in ~80Hz taÅŸÄ±yÄ±cÄ±)
    t = np.arange(len(audio)) / sample_rate
    carrier = np.sin(2 * np.pi * 80 * t)
    ring = audio * (0.70 + 0.30 * carrier)

    # 2) Hafif pitch shift â€” %8 yavaÅŸlatarak pitch dÃ¼ÅŸÃ¼r
    stretch_factor = 1.08
    old_len = len(ring)
    new_len = int(old_len * stretch_factor)
    if new_len < 1:
        return data
    indices = np.linspace(0, old_len - 1, new_len)
    pitched = np.interp(indices, np.arange(old_len), ring)
    # Orijinal uzunluÄŸa kÄ±rp
    pitched = (
        pitched[:old_len]
        if len(pitched) > old_len
        else np.pad(pitched, (0, old_len - len(pitched)))
    )

    # 3) Echo (holografik alan)
    echo_samples = int(sample_rate * 0.038)  # 38ms
    echoed = pitched.copy()
    if echo_samples < len(echoed):
        echoed[echo_samples:] += pitched[:-echo_samples] * 0.22

    # 4) Ä°kinci echo (derinlik)
    echo2_samples = int(sample_rate * 0.075)  # 75ms
    if echo2_samples < len(echoed):
        echoed[echo2_samples:] += pitched[:-echo2_samples] * 0.10

    # 5) Normalize
    peak = np.max(np.abs(echoed))
    if peak > 0:
        echoed = echoed / peak * 0.92

    return (echoed * 32767).astype(np.int16)


async def _edge_tts_speak_async(clean: str):
    """edge_tts ile TÃ¼rkÃ§e ses Ã¼ret, pygame ile Ã§al (thread-safe, TTS_LOCK already held by caller)."""
    tmp = os.path.join(tempfile.gettempdir(), "jarvis_tts.mp3")
    
    # Generate audio (may take 1-3s for Turkish)
    try:
        communicate = _edge_tts.Communicate(clean, _current_voice_name())
        await communicate.save(tmp)
    except Exception as e:
        print(f"[TTS] edge_tts generation failed: {e}")
        return
    
    # Play audio with timeout protection
    try:
        _pygame.mixer.music.load(tmp)
        _pygame.mixer.music.play()
        
        # Increased sleep interval to reduce frame drops (0.1s instead of 0.05s)
        # Timeout: max 30 seconds for any TTS playback
        timeout = time.time() + 30
        while _pygame.mixer.music.get_busy():
            if time.time() > timeout:
                print("[TTS] Playback timeout, stopping")
                _pygame.mixer.music.stop()
                break
            time.sleep(0.1)  # â† 2x slower polling = less CPU/queue pressure
        
        _pygame.mixer.music.unload()
    except Exception as e:
        print(f"[TTS] Playback error: {e}")
        try:
            _pygame.mixer.music.stop()
        except:
            pass


def _fit_tts_text(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned

    preferred_cutoffs = [". ", "? ", "! ", "; ", ": "]
    min_boundary = max(32, int(limit * 0.58))
    for marker in preferred_cutoffs:
        idx = cleaned.rfind(marker, 0, limit + 1)
        if idx >= min_boundary:
            return cleaned[: idx + len(marker.strip())].strip()

    word_idx = cleaned.rfind(" ", 0, limit + 1)
    if word_idx >= min_boundary:
        return cleaned[:word_idx].strip()

    return cleaned[:limit].strip()


def speak(text: str, *, track_response: bool = False):
    if not text.strip():
        return
    print(f"\033[96m[JARVIS]\033[0m {text}")
    clean = re.sub(r"##[A-Z:]+[^#]*##", "", text)
    clean = re.sub(r"[*_`#]", "", clean).strip()
    if not clean:
        clean = "AnlaÅŸÄ±ldÄ±."
    preview_text = _fit_tts_text(clean, 220)
    spoken_text = _fit_tts_text(clean, 520)
    piper_text = _fit_tts_text(clean, 320)

    active_persona = _get_active_persona_runtime()
    runtime_agent = str(active_persona.get("id") or VOICE_RUNTIME_AGENT)

    with TTS_LOCK:
        _publish_voice_runtime(
            phase="speaking",
            text=preview_text,
            last_response=preview_text,
            increment_turn=track_response,
            runtime_status="online",
            runtime_detail="Yanit veriliyor",
            agent=runtime_agent,
        )
        if not _audio_output_enabled():
            _publish_post_speech_runtime_state(
                runtime_agent=runtime_agent,
                preview_text=preview_text,
            )
            return
        # edge_tts (birincil â€” Microsoft TÃ¼rkÃ§e sesi)
        if _EDGE_TTS_AVAILABLE:
            try:
                # Run TTS with event loop safety
                try:
                    asyncio.run(_edge_tts_speak_async(spoken_text))
                except RuntimeError as e:
                    # Nested event loop issue, try direct execution
                    if "asyncio.run() cannot be called from a running event loop" in str(e):
                        import concurrent.futures
                        import threading
                        def _run_async():
                            asyncio.run(_edge_tts_speak_async(spoken_text))
                        t = threading.Thread(target=_run_async, daemon=True)
                        t.start()
                        t.join(timeout=35)
                    else:
                        raise
                
                _publish_post_speech_runtime_state(
                    runtime_agent=runtime_agent,
                    preview_text=preview_text,
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
                for chunk in voice.synthesize(piper_text):
                    arr = chunk.audio_int16_array
                    sr = chunk.sample_rate
                    if arr is not None and len(arr) > 0:
                        all_samples.append(arr)
                if all_samples:
                    raw = np.concatenate(all_samples)
                    data = _hologram_effect(raw, sr)
                    sd.play(data, sr)
                    sd.wait()
                    _publish_post_speech_runtime_state(
                        runtime_agent=runtime_agent,
                        preview_text=preview_text,
                    )
                    return
            except Exception as exc:
                print(f"[TTS piper hata] {exc}")

        print("[TTS] Ses sistemi kullanÄ±lamÄ±yor.")
        _publish_post_speech_runtime_state(
            runtime_agent=runtime_agent,
            preview_text=preview_text,
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
        return asyncio.run(
            speak_agent_result(raw_output, track_response=track_response)
        )
    except RuntimeError:
        fallback = _fallback_agent_narration(raw_output)
        speak(fallback, track_response=track_response)
        return fallback


def _remember_exchange(user_text: str, assistant_text: str):
    _history.append({"role": "user", "content": user_text})
    _history.append({"role": "assistant", "content": assistant_text})


def _wiki_query_tokens(text: str) -> list[str]:
    seen = set()
    tokens: list[str] = []
    for token in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ_-]+", str(text or "").lower()):
        normalized = token.strip(" -_")
        if len(normalized) < 3 or normalized in seen:
            continue
        seen.add(normalized)
        tokens.append(normalized)
        if len(tokens) >= 8:
            break
    return tokens


def _slice_wiki_excerpt(content: str, tokens: list[str], limit: int = 900) -> str:
    clean = re.sub(r"\s+", " ", str(content or "")).strip()
    if not clean:
        return ""
    lower = clean.lower()
    for token in tokens:
        idx = lower.find(token)
        if idx >= 0:
            start = max(0, idx - 180)
            end = min(len(clean), idx + limit)
            return clean[start:end].strip()
    return clean[:limit].strip()


def _build_wiki_context(text: str) -> str:
    wiki_dir = ROOT_DIR / "wiki"
    if not wiki_dir.exists():
        return ""

    tokens = _wiki_query_tokens(text)
    sections: list[str] = []

    for filename, limit in (("hot.md", 1000), ("index.md", 800)):
        path = wiki_dir / filename
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        excerpt = _slice_wiki_excerpt(content, tokens, limit=limit)
        if excerpt:
            sections.append(f"[wiki/{filename}]\n{excerpt}")

    scored_pages: list[tuple[int, Path, str]] = []
    for path in wiki_dir.glob("*.md"):
        if path.name in {"hot.md", "index.md", "repo-file-index.md"}:
            continue
        try:
            if path.stat().st_size > 250_000:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        haystack = f"{path.stem}\n{content}".lower()
        score = sum(3 if token in path.stem.lower() else 1 for token in tokens if token in haystack)
        if score <= 0:
            continue
        excerpt = _slice_wiki_excerpt(content, tokens, limit=700)
        if excerpt:
            scored_pages.append((score, path, excerpt))

    for _, path, excerpt in sorted(scored_pages, key=lambda item: (-item[0], item[1].name))[:4]:
        sections.append(f"[wiki/{path.name}]\n{excerpt}")

    if not sections:
        return ""

    return (
        "[Jarvis wiki baglami]\n"
        "Asagidaki baglam repo icindeki wiki ve ikinci beyin notlarindan geldi. "
        "Yanit verirken bunu kullan, ama gereksiz yere oldugu gibi tekrar etme.\n\n"
        + "\n\n".join(sections)
    )


def _augment_prompt_with_wiki_context(text: str) -> str:
    wiki_context = _build_wiki_context(text)
    if not wiki_context:
        return text
    return f"{wiki_context}\n\n[Kullanici mesaji]\n{text}"


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
        import google.genai as genai
        from google.genai import types
    except Exception as exc:
        print(f"[GEMINI import] {exc}")
        return ""

    history_parts = []
    for item in _history[-6:]:
        role = "User" if item["role"] == "user" else "Assistant"
        history_parts.append(f"{role}: {item['content']}")
    history_parts.append(f"User: {text}")

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        parts = [types.Part.from_text(text="\n".join(history_parts))]
        if image_b64:
            parts.append(
                types.Part.from_bytes(
                    data=base64.b64decode(image_b64),
                    mime_type="image/png",
                )
            )

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=150,
            ),
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
    contextual_text = text if image_b64 else _augment_prompt_with_wiki_context(text)
    if image_b64:
        providers = ["local"]
        if GEMINI_API_KEY:
            providers.append("gemini")
    else:
        providers = list(
            ("backend", "local") if CHAT_PRIORITY == "backend" else ("local", "backend")
        )
        if GEMINI_API_KEY:
            providers.append("gemini")

    for provider in providers:
        if provider == "gemini":
            reply = _ask_gemini(contextual_text, image_b64=image_b64)
        elif provider == "backend" and image_b64 is None:
            reply = _ask_backend(contextual_text)
        elif provider == "local":
            reply = _ask_ollama(contextual_text, image_b64=image_b64)
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
    # r"bilgisayari.*kapat|shut.*down": ("shutdown /s /t 30", "Bilgisayar 30 saniyede kapanacak."),  # GÃœVENLÄ°K: devre dÄ±ÅŸÄ±
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
    _maybe_speak_persona_greeting()
    print(f"\nSen: {text}")
    active_persona_before = _current_runtime_agent().strip().lower() or VOICE_RUNTIME_AGENT
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
    _maybe_speak_persona_greeting(expected_previous_persona=active_persona_before)
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
    device_name = os.environ.get("JARVIS_INPUT_DEVICE_NAME", "").strip().lower()
    if device_name:
        try:
            devices = sd.query_devices()
            default_input = None
            try:
                default_device = sd.default.device
                if isinstance(default_device, (list, tuple)) and default_device:
                    default_input = int(default_device[0])
            except Exception:
                default_input = None

            candidates = []
            for idx, device in enumerate(devices):
                if int(device.get("max_input_channels", 0) or 0) < 1:
                    continue
                name = str(device.get("name") or "")
                if device_name not in name.lower():
                    continue
                hostapi = int(device.get("hostapi", -1) or -1)
                score = 0
                if idx == default_input:
                    score += 100
                if name.lower() == device_name:
                    score += 50
                if "logitech" in name.lower():
                    score += 25
                score += {0: 40, 1: 30, 2: 20, 3: 10}.get(hostapi, 0)
                candidates.append((score, idx, name))

            if candidates:
                _, resolved, resolved_name = sorted(candidates, key=lambda item: (-item[0], item[1]))[0]
                print(f"[MIK] Input device name match: {resolved} ({resolved_name})")
                return resolved
            print(f"[MIK] Input device name bulunamadi: {device_name}")
        except Exception as exc:
            print(f"[MIK] Input device name resolve hatasi: {exc}")

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
        "model": "tiny",  # DÃœZELTME: "small" â†’ "tiny" (test'te Ã§alÄ±ÅŸtÄ±ÄŸÄ± doÄŸrulandÄ±)
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


def _configure_google_recognizer(recognizer):
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.non_speaking_duration = 0.5
    recognizer.phrase_threshold = 0.25


def _looks_non_turkish_stt(text: str) -> bool:
    return bool(text and re.search(r"[\u0400-\u04FF]", text))


def _normalize_stt_text(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _recognize_google_turkish(recognizer, audio) -> str:
    attempts = [("tr-TR", "regional"), ("tr", "generic")]
    last_error = None

    for language, label in attempts:
        try:
            text = recognizer.recognize_google(audio, language=language, show_all=False)
        except Exception as exc:
            last_error = exc
            continue

        text = _normalize_stt_text(text)
        if not text:
            continue

        if label == "regional" and _looks_non_turkish_stt(text):
            print("[STT] Supheli karakterler algilandi, generic Turkish fallback deneniyor...")
            continue

        return text

    if last_error:
        raise last_error
    return ""


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
            print(
                "[WAKE] Picovoice Console'dan (https://console.picovoice.ai/) ucretsiz key alin"
            )
            print("[WAKE] .env dosyasina PICOVOICE_ACCESS_KEY=<your_key> ekleyin")
            print("[WAKE] Wake word olmadan normal mod baslatiliyor...\n")
            return run_continuous_listen_mode()

        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=["jarvis"],  # Built-in keyword
            sensitivities=[0.5],  # 0.0-1.0, higher = more sensitive
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
        print(
            "[WAKE] Porcupine baslatildi (sample_rate={}, frame_length={})".format(
                porcupine.sample_rate, porcupine.frame_length
            )
        )

        recognizer = sr.Recognizer()
        _configure_google_recognizer(recognizer)
        _configure_google_recognizer(recognizer)
        mic = (
            sr.Microphone(device_index=device_index)
            if device_index is not None
            else sr.Microphone()
        )

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
                    beep_data = np.sin(
                        2 * np.pi * 800 * np.arange(0, 0.1, 1 / 22050)
                    ).astype(np.float32)
                    sd.play(beep_data, 22050)
                    sd.wait()
                except:
                    pass

                # Now listen for command
                try:
                    with mic as source:
                        # Longer noise calibration for Turkish TÃ¼rkÃ§e voice/background
                        recognizer.adjust_for_ambient_noise(source, duration=1.0)
                        audio = recognizer.listen(
                            source, timeout=10, phrase_time_limit=15
                        )

                    print("[STT] Isleniyor...")
                    # Use Turkish language explicitly, with fallback
                    text = _recognize_google_turkish(recognizer, audio)
                    
                    if text:
                        handle(text)
                    else:
                        print("[STT] Anlasilamadi")

                except sr.WaitTimeoutError:
                    print('[STT] Timeout - tekrar "Jarvis" deyin')
                except sr.UnknownValueError:
                    print('[STT] Anlasilamadi - tekrar "Jarvis" deyin')
                except sr.RequestError as e:
                    print(f"[STT] Google hatasi: {e}")

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
    wake_phrase = _current_wake_phrase()
    _set_voice_runtime_online(
        detail="RealtimeSTT acik mikrofon hazir" if JARVIS_OPEN_MIC else "RealtimeSTT hazir",
        mode="realtime_stt",
        wake_mode="open_mic" if JARVIS_OPEN_MIC else "jarvis_keyword",
        stt_backend="realtime_stt",
        phase="listening" if JARVIS_OPEN_MIC else "idle",
        text="Mikrofon hazir. Dogrudan konusabilirsiniz."
        if JARVIS_OPEN_MIC
        else f"Sistem hazir. {wake_phrase} diyerek baslayin.",
    )
    """
    RealtimeSTT local Whisper path.
    Wake word: 'jarvis' or the active persona name.
    """
    print("[STT] RealtimeSTT (lokal Whisper) baslatiliyor...")
    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError:
        print("[STT] RealtimeSTT bulunamadi -> Google STT'ye geciliyor")
        return run_continuous_listen_mode()

    kwargs = _build_recorder_kwargs()
    _wake_active = [False]
    _last_wake = [0.0]

    def on_text(text: str):
        text = text.strip()
        if not text:
            return

        tl = text.lower()
        now = time.time()

        if JARVIS_OPEN_MIC:
            _publish_voice_runtime(
                phase="listening",
                text="Dinliyorum...",
                last_heard=text[:180],
                runtime_status="online",
                runtime_detail="Mikrofon dinlemede",
                mode="realtime_stt",
                wake_mode="open_mic",
                stt_backend="realtime_stt",
            )
            print(f"Sen: {text}")
            handle(text)
            return

        wake_alias, wake_span = _find_wake_alias(tl)

        if wake_alias and wake_span:
            _wake_active[0] = True
            _last_wake[0] = now
            after = tl[wake_span[1]:].strip(" ,.:!?")
            wake_display = "Jarvis" if wake_alias == "jarvis" else wake_alias.title()
            print(f"\n\033[93m[WAKE]\033[0m '{wake_display}' algilandi.")
            _publish_voice_runtime(
                phase="listening",
                text="Dinliyorum...",
                last_heard=wake_display,
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

        if _wake_active[0] or (now - _last_wake[0]) < 30:
            _wake_active[0] = True
            _last_wake[0] = now
            print(f"Sen: {text}")
            handle(text)
        else:
            print(f"[STT] ({wake_phrase} deyin once): {text}")

    if JARVIS_OPEN_MIC:
        print("[STT] Hazir - acik mikrofon aktif")
        speak("Mikrofon hazir. Dogrudan konusabilirsiniz.")
    else:
        print(f"[STT] Hazir - '{wake_phrase}' diyerek baslayin")
        speak(f"Sistem hazir. {wake_phrase} diyerek baslayin.")

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
    Google STT fallback â€” internet gerektirir.
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        device_index = _resolve_input_device_index()
        mic = (
            sr.Microphone(device_index=device_index)
            if device_index is not None
            else sr.Microphone()
        )

        # Ortam gurultusunu ayarla
        print("[MIK] Mikrofon ayarlaniyor...")
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        print("[MIK] Hazir - Konusmaya basla! (30 saniye konusma suresi)\n")

        while True:
            try:
                with mic as source:
                    print("[MIK] Dinliyorum...")
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
                print("[MIK] Isleniyor...")
                try:
                    text = _recognize_google_turkish(recognizer, audio)
                    if text:
                        print(f"Sen: {text}")
                        handle(text)
                except sr.UnknownValueError:
                    pass  # Anlasilamadi, tekrar dinle
                except sr.RequestError as e:
                    print(f"[MIK] Google STT hatasi: {e}")
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
    print("  â–ˆâ–ˆâ•— â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•—   â–ˆâ–ˆâ•—â–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—")
    print("  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â•â•â•")
    print("  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—")
    print("  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â•šâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•”â•â–ˆâ–ˆâ•‘â•šâ•â•â•â•â–ˆâ–ˆâ•‘")
    print("  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘ â•šâ–ˆâ–ˆâ–ˆâ–ˆâ•”â• â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘")
    print("  â•šâ•â•â•šâ•â•  â•šâ•â•â•šâ•â•  â•šâ•â•  â•šâ•â•â•â•  â•šâ•â•â•šâ•â•â•â•â•â•â•")
    print("  HOLOGRAM COMPUTER MODE â€” AKTÄ°F")
    print("  Ses efekti: Ring Mod + Echo + Pitch Shift")
    print("=" * 55 + "\033[0m\n")
    _set_voice_runtime_online(
        detail="Hologram computer mode aktif",
        mode="text" if ARGS.text_mode else "realtime_stt",
        wake_mode="keyboard" if ARGS.text_mode else ("open_mic" if JARVIS_OPEN_MIC else "jarvis_keyword"),
        stt_backend="text_input" if ARGS.text_mode else "realtime_stt",
        phase="listening" if JARVIS_OPEN_MIC and not ARGS.text_mode else "idle",
        text="Mikrofon hazir." if JARVIS_OPEN_MIC else "Jarvis hazir.",
    )

    _start_swarm_tts_watcher()

    if ARGS.no_greeting:
        print("[JARVIS] GÃ¼venli baÅŸlangÄ±Ã§ etkin.")
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
        # 1. RealtimeSTT (lokal Whisper) â€” tercih edilen
        # 2. Porcupine wake word â€” API key varsa
        # 3. Google STT â€” internet fallback
        # 4. Text mode â€” son Ã§are
        run_realtime_stt_mode()
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        import traceback

        print(f"\n[!] RealtimeSTT hatasÄ±: {exc}")
        traceback.print_exc()
        print("[!] Porcupine moduna geÃ§iliyor...")
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
            print(f"[!] Wake word hatasÄ±: {exc2}")
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
            speak("Sistem kapatÄ±lÄ±yor. GÃ¶rÃ¼ÅŸÃ¼rÃ¼z, Ekrem.")
        print("\n\033[96m[JARVIS â€” KAPANDI]\033[0m")

