from __future__ import annotations

"""
Jarvis Voice Service
- Wake word: "Hey Jarvis" via openWakeWord (offline, pre-trained, no API key)
- STT: faster-whisper / whisper
- TTS: edge-tts / pyttsx3 / print
- Sends commands to Orchestrator via HTTP POST /voice
"""

import json
import logging
import os
import queue
import struct
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Callable, Optional
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

log = logging.getLogger("voice.service")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:8091")
PICOVOICE_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")
WAKE_WORD = os.getenv("VOICE_WAKE_WORD", "jarvis").lower()
STT_MODEL = os.getenv("VOICE_STT_MODEL", "base")
TTS_ENGINE_PREF = os.getenv("VOICE_TTS_ENGINE", "edge")
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 512
RECORD_SECONDS = 8
ENERGY_THRESHOLD = 800


class TTSEngine:
    """Text-to-speech — tries edge-tts, then pyttsx3, then print."""

    def __init__(self):
        self._backend = self._detect()

    def _detect(self) -> str:
        if TTS_ENGINE_PREF == "edge":
            try:
                import edge_tts  # noqa
                return "edge"
            except ImportError:
                pass
        try:
            import pyttsx3  # noqa
            return "pyttsx3"
        except ImportError:
            pass
        return "print"

    def speak(self, text: str):
        log.info("[TTS] %s", text)
        if self._backend == "edge":
            import asyncio
            asyncio.run(self._edge_speak(text))
        elif self._backend == "pyttsx3":
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        else:
            print(f"[JARVIS] {text}")

    async def _edge_speak(self, text: str):
        import edge_tts, subprocess
        voice = os.getenv("VOICE_TTS_VOICE", "en-US-GuyNeural")
        communicate = edge_tts.Communicate(text, voice=voice)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        await communicate.save(tmp)
        for player in ["ffplay", "mpv", "mplayer"]:
            try:
                subprocess.run(
                    [player, "-nodisp", "-autoexit", tmp],
                    capture_output=True, timeout=30,
                )
                break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        try:
            import os as _os
            _os.unlink(tmp)
        except Exception:
            pass


class STTEngine:
    """Speech-to-text using faster-whisper or whisper."""

    def __init__(self, model: str = STT_MODEL):
        self._model = None
        self._backend = "none"
        self._load(model)

    def _load(self, model: str):
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(model, device="cpu", compute_type="int8")
            self._backend = "faster_whisper"
            log.info("STT: faster-whisper loaded (%s)", model)
            return
        except ImportError:
            pass
        try:
            import whisper
            self._model = whisper.load_model(model)
            self._backend = "whisper"
            log.info("STT: whisper loaded (%s)", model)
        except ImportError:
            log.warning("STT: no whisper backend. Install: pip install faster-whisper")

    def transcribe(self, audio_bytes: bytes) -> str:
        if self._backend == "none" or self._model is None:
            return ""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        try:
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_bytes)
            if self._backend == "faster_whisper":
                segments, _ = self._model.transcribe(tmp, language="en")
                return " ".join(s.text for s in segments).strip()
            else:
                result = self._model.transcribe(tmp)
                return result["text"].strip()
        finally:
            try:
                import os as _os
                _os.unlink(tmp)
            except Exception:
                pass


class VoiceService:
    def __init__(self):
        self.tts = TTSEngine()
        self.stt = STTEngine()
        self._running = False
        self._muted = False
        self._recording = False
        self._audio_buffer: list[bytes] = []
        self._record_start = 0.0
        self._oww = None
        self._load_oww()

    def send_to_orchestrator(self, text: str) -> dict:
        payload = json.dumps({"text": text, "session_id": "voice"}).encode()
        req = Request(
            f"{ORCHESTRATOR_URL}/voice",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            log.error("Orchestrator unreachable: %s", e)
            return {}

    def on_wake_word(self):
        log.info("Wake word detected!")
        self.tts.speak("Yes, I'm listening.")
        self._recording = True
        self._audio_buffer = []
        self._record_start = time.time()

    def _load_oww(self):
        """Load openWakeWord model for 'hey_jarvis'."""
        try:
            from openwakeword.model import Model
            self._oww = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            log.info("openWakeWord loaded — listening for 'Hey Jarvis'")
            return True
        except Exception as e:
            log.warning("openWakeWord unavailable: %s — using energy fallback", e)
            self._oww = None
            return False

    def _check_wake(self, frame: bytes) -> bool:
        """Check wake word via openWakeWord or energy+STT fallback."""
        # openWakeWord path (preferred)
        if self._oww is not None:
            try:
                import numpy as np
                audio_data = np.frombuffer(frame, dtype=np.int16)
                predictions = self._oww.predict(audio_data)
                score = predictions.get("hey_jarvis", 0.0)
                if score > 0.5:
                    log.info("Hey Jarvis detected (score=%.2f)", score)
                    return True
                return False
            except Exception:
                pass

        # Energy + STT fallback
        try:
            samples = struct.unpack(f"{len(frame) // 2}h", frame)
            energy = sum(abs(s) for s in samples) / len(samples)
            if energy > ENERGY_THRESHOLD:
                text = self.stt.transcribe(frame)
                if WAKE_WORD in text.lower():
                    return True
        except Exception:
            pass
        return False

    def run(self):
        try:
            import pyaudio
        except ImportError:
            log.error("pyaudio not installed. Run: pip install pyaudio")
            self.tts.speak("Voice service unavailable — pyaudio not installed.")
            return

        self.tts.speak("Jarvis Mission Control is online. Say Hey Jarvis to activate.")
        self._running = True

        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=SAMPLE_RATE,
            channels=CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=CHUNK,
        )
        log.info("Voice service listening. Wake word: 'Hey %s'", WAKE_WORD.capitalize())

        try:
            while self._running:
                if self._muted:
                    time.sleep(0.1)
                    continue

                frame = stream.read(CHUNK, exception_on_overflow=False)

                if self._recording:
                    self._audio_buffer.append(frame)
                    if time.time() - self._record_start >= RECORD_SECONDS:
                        self._recording = False
                        audio = b"".join(self._audio_buffer)
                        self._audio_buffer = []

                        text = self.stt.transcribe(audio)
                        log.info("Transcribed: '%s'", text)

                        if text:
                            self.tts.speak(f"Processing: {text[:60]}")
                            result = self.send_to_orchestrator(text)
                            task_id = result.get("task_id", "")
                            if task_id:
                                if result.get("requires_confirmation"):
                                    self.tts.speak(f"Task {task_id} requires your confirmation.")
                                else:
                                    self.tts.speak(f"Task {task_id} dispatched.")
                        else:
                            self.tts.speak("I didn't catch that. Please try again.")
                else:
                    if self._check_wake(frame):
                        self.on_wake_word()

        except KeyboardInterrupt:
            pass
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            self.tts.speak("Jarvis going offline.")
            log.info("Voice service stopped.")

    def mute(self):
        self._muted = True

    def unmute(self):
        self._muted = False

    def stop(self):
        self._running = False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    VoiceService().run()
