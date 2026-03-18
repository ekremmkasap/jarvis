#!/usr/bin/env python3
"""
JARVIS — Sesli Asistan v1.0 (Pinokio/Windows Edition)
Mikrofon → Whisper (STT) → Ollama (AI) → XTTS / pyttsx3 (TTS)

Kurulum:
    pip install sounddevice numpy faster-whisper pyttsx3 requests

Kullanım:
    python voice_jarvis.py
    (SPACE) → dinle, (Q) → çık, (M) → model değiştir
"""

import os
import sys
import time
import json
import queue
import struct
import threading
import tempfile
import logging
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("voice_jarvis")

# ── Config ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()

def load_env():
    env = BASE_DIR / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

CONFIG = {
    "ollama_url": os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
    "model": os.environ.get("VOICE_MODEL", "llama3.2:latest"),
    "whisper_model": os.environ.get("WHISPER_MODEL", "tiny"),  # tiny/base/small
    "tts_engine": os.environ.get("TTS_ENGINE", "auto"),  # auto/pyttsx3/xtts
    "xtts_url": os.environ.get("XTTS_URL", "http://127.0.0.1:8020"),
    "sample_rate": 16000,
    "silence_threshold": 500,   # Ses eşiği
    "silence_duration": 1.5,    # Sessizlik süresi (saniye) → kayıt dur
}

# ── Soul (Kimlik) ─────────────────────────────────────────────────────
SOUL = """Sen Jarvis'sin — Tony Stark'ın yapay zekasından ilham alan sesli asistan.
Sahibin: Ekrem. Zeki, pratik, bazen alaycı ama her zaman sonuç odaklı.
ÇIKTI KURALLARI:
- Kısa ve net konuş (max 2-3 cümle, sesli yanıt olduğu için!)
- Türkçe varsayılan
- Asla markdown kullanma (*bold*, # başlık vs) — düz metin, çünkü sesli okunacak
- Rakam, emoji veya özel karakter yerine kelime kullan
"""

# ── Konuşma Geçmişi ──────────────────────────────────────────────────
HISTORY = []
MAX_HISTORY = 10

# ─────────────────────────────────────────────────────────────────────
# TTS ENGINE
# ─────────────────────────────────────────────────────────────────────

class TTSEngine:
    def __init__(self):
        self.engine_name = "none"
        self._init_engine()

    def _init_engine(self):
        mode = CONFIG["tts_engine"]

        # XTTS dene (Pinokio'da kuruluysa)
        if mode in ("auto", "xtts"):
            try:
                req = Request(f"{CONFIG['xtts_url']}/docs", method="GET")
                urlopen(req, timeout=2)
                self.engine_name = "xtts"
                log.info("✅ TTS: XTTS v2 aktif")
                return
            except:
                if mode == "xtts":
                    log.warning("XTTS bağlanamadı, pyttsx3'e geçiliyor")

        # pyttsx3 dene (Windows SAPI — her zaman mevcut)
        try:
            import pyttsx3
            self._pyttsx3 = pyttsx3.init()
            # Türkçe ses bul
            voices = self._pyttsx3.getProperty("voices")
            tr_voice = next((v for v in voices if "tr" in v.id.lower() or
                             "turkish" in v.name.lower()), None)
            if tr_voice:
                self._pyttsx3.setProperty("voice", tr_voice.id)
                log.info(f"✅ TTS: pyttsx3 Türkçe ({tr_voice.name})")
            else:
                log.info("✅ TTS: pyttsx3 (varsayılan ses)")
            self._pyttsx3.setProperty("rate", 185)   # Konuşma hızı
            self._pyttsx3.setProperty("volume", 0.95)
            self.engine_name = "pyttsx3"
            return
        except ImportError:
            log.warning("pyttsx3 kurulu değil: pip install pyttsx3")
        except Exception as e:
            log.warning(f"pyttsx3 başlatılamadı: {e}")

        log.warning("⚠️ TTS: Ses motoru yok — metin sadece terminale yazılacak")

    def speak(self, text: str):
        """Metni seslendir."""
        # Temizle: markdown, emoji vb.
        import re
        text = re.sub(r"[*_`#]", "", text)
        text = text.strip()
        if not text:
            return

        print(f"\n🤖 Jarvis: {text}\n")

        if self.engine_name == "xtts":
            self._speak_xtts(text)
        elif self.engine_name == "pyttsx3":
            self._speak_pyttsx3(text)

    def _speak_pyttsx3(self, text: str):
        try:
            self._pyttsx3.say(text)
            self._pyttsx3.runAndWait()
        except Exception as e:
            log.error(f"pyttsx3 hata: {e}")

    def _speak_xtts(self, text: str):
        try:
            payload = json.dumps({
                "text": text,
                "language": "tr",
                "speaker_wav": None,
                "speed": 1.0
            }).encode()
            req = Request(
                f"{CONFIG['xtts_url']}/tts_to_audio",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=30) as resp:
                audio_data = resp.read()
            # Ses çal
            self._play_audio(audio_data)
        except Exception as e:
            log.error(f"XTTS hata: {e}")
            # Fallback: terminale yaz
            pass

    def _play_audio(self, audio_bytes: bytes):
        try:
            import sounddevice as sd
            import numpy as np
            import io
            import wave
            buf = io.BytesIO(audio_bytes)
            with wave.open(buf) as wf:
                rate = wf.getframerate()
                data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
            sd.play(data, rate, blocking=True)
        except Exception as e:
            log.error(f"Ses çalma hata: {e}")


# ─────────────────────────────────────────────────────────────────────
# STT ENGINE (Whisper)
# ─────────────────────────────────────────────────────────────────────

class STTEngine:
    def __init__(self):
        self.model = None
        self._load()

    def _load(self):
        try:
            from faster_whisper import WhisperModel
            model_size = CONFIG["whisper_model"]
            log.info(f"Whisper modeli yükleniyor: {model_size}...")
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            log.info("✅ STT: Whisper hazır")
        except ImportError:
            log.warning("faster-whisper kurulu değil: pip install faster-whisper")
        except Exception as e:
            log.error(f"Whisper yüklenemedi: {e}")

    def transcribe(self, audio_path: str) -> str:
        if not self.model:
            return ""
        try:
            segments, info = self.model.transcribe(
                audio_path,
                language="tr",
                beam_size=3,
                vad_filter=True,
            )
            text = " ".join(s.text for s in segments).strip()
            return text
        except Exception as e:
            log.error(f"Transkripsiyon hata: {e}")
            return ""


# ─────────────────────────────────────────────────────────────────────
# MİKROFON KAYIT
# ─────────────────────────────────────────────────────────────────────

class Recorder:
    def __init__(self):
        self.sr = CONFIG["sample_rate"]
        self._check()

    def _check(self):
        try:
            import sounddevice as sd
            import numpy as np
            self._sd = sd
            self._np = np
            log.info("✅ Mikrofon: sounddevice hazır")
        except ImportError:
            log.error("sounddevice kurulu değil: pip install sounddevice numpy")
            sys.exit(1)

    def record_until_silence(self, max_seconds=30) -> str:
        """Ses kaydeder, sessizlik algılanınca durur. WAV dosya yolu döner."""
        sd = self._sd
        np = self._np

        print("🎤 Dinliyorum... (konuşmayı bitirince dur)")

        chunk = int(self.sr * 0.1)      # 100ms chunk
        silence_chunks = int(CONFIG["silence_duration"] / 0.1)
        threshold = CONFIG["silence_threshold"]

        frames = []
        silent_count = 0
        started = False

        with sd.InputStream(samplerate=self.sr, channels=1,
                            dtype="int16", blocksize=chunk) as stream:
            for _ in range(int(max_seconds / 0.1)):
                data, _ = stream.read(chunk)
                amplitude = np.abs(data).mean()

                if amplitude > threshold:
                    started = True
                    silent_count = 0
                    frames.append(data.copy())
                elif started:
                    frames.append(data.copy())
                    silent_count += 1
                    if silent_count >= silence_chunks:
                        break

        if not frames:
            return ""

        # WAV kaydet
        import wave
        audio = np.concatenate(frames, axis=0)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sr)
            wf.writeframes(audio.tobytes())
        return tmp.name


# ─────────────────────────────────────────────────────────────────────
# OLLAMA AI
# ─────────────────────────────────────────────────────────────────────

def ask_ollama(user_text: str) -> str:
    global HISTORY

    HISTORY.append({"role": "user", "content": user_text})
    if len(HISTORY) > MAX_HISTORY * 2:
        HISTORY = HISTORY[-MAX_HISTORY * 2:]

    payload = json.dumps({
        "model": CONFIG["model"],
        "messages": HISTORY,
        "system": SOUL,
        "stream": False,
        "options": {
            "temperature": 0.75,
            "num_predict": 200,
            "num_ctx": 2048,
        }
    }).encode()

    try:
        req = Request(
            f"{CONFIG['ollama_url']}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        reply = result.get("message", {}).get("content", "").strip()
        if reply:
            HISTORY.append({"role": "assistant", "content": reply})
        return reply or "Anlamadım, tekrar söyler misin?"
    except URLError as e:
        return f"Ollama bağlantı hatası: Ollama açık mı?"
    except Exception as e:
        return f"Hata: {e}"


# ─────────────────────────────────────────────────────────────────────
# ANA DÖNGÜ
# ─────────────────────────────────────────────────────────────────────

def main():
    print("""
╔══════════════════════════════════════════╗
║   JARVIS — Sesli Asistan v1.0           ║
║   Pinokio / Windows Edition             ║
╠══════════════════════════════════════════╣
║  ENTER  → Dinlemeye başla               ║
║  Q+ENTER→ Çık                           ║
║  R+ENTER→ Geçmişi sıfırla              ║
╚══════════════════════════════════════════╝
""")

    # Modülleri yükle
    tts = TTSEngine()
    stt = STTEngine()
    rec = Recorder()

    # Karşılama
    greeting = "Merhaba. Jarvis hazır. Konuşabilirsiniz."
    tts.speak(greeting)

    while True:
        try:
            cmd = input("\n[ENTER=Dinle | Q=Çık | R=Sıfırla] > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if cmd == "q":
            tts.speak("Görüşürüz.")
            break

        if cmd == "r":
            global HISTORY
            HISTORY = []
            print("✅ Konuşma geçmişi sıfırlandı.")
            continue

        # Kayıt
        audio_path = rec.record_until_silence()
        if not audio_path:
            print("⚠️ Ses algılanamadı.")
            continue

        # STT
        print("🔄 Transkript ediliyor...")
        user_text = stt.transcribe(audio_path)

        # Temp dosyayı sil
        try:
            os.unlink(audio_path)
        except:
            pass

        if not user_text:
            print("⚠️ Anlaşılamadı, tekrar deneyin.")
            continue

        print(f"👤 Sen: {user_text}")

        # AI
        print("🤔 Düşünüyor...")
        reply = ask_ollama(user_text)

        # TTS
        tts.speak(reply)


if __name__ == "__main__":
    main()
