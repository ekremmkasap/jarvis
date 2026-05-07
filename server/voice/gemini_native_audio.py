#!/usr/bin/env python3
"""
JARVIS VOICE LAYER — GEMINI 2.5 FLASH NATIVE AUDIO
Real-time voice interaction via Gemini 2.5 Flash live API
Pattern adapted from Mark-XXXV (FatihMakes)
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import logging
import warnings

# Suppress deprecation warning
warnings.filterwarnings("ignore", category=FutureWarning)

# Load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Ensure UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("server/logs/gemini_voice.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("jarvis.voice.gemini")

try:
    import google.genai as genai
    from google.genai import types
except ImportError:
    log.error("google-genai not installed. Run: pip install google-genai")
    sys.exit(1)

try:
    import pyaudio
    import wave
except ImportError:
    log.error("PyAudio not installed. Run: pip install pyaudio")
    sys.exit(1)


class GeminiVoiceAgent:
    """Real-time voice interaction with Gemini 2.5 Flash"""

    def __init__(self, api_key: str, model: str = "models/gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

        # Audio settings (standard for speech)
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = 1024
        self.CHANNELS = 1
        self.FORMAT = pyaudio.paInt16

        # State
        self.is_listening = False
        self.conversation_history = []
        self.session_start = datetime.now()

        log.info(f"[Gemini Voice] Initialized with model: {self.model}")

    async def capture_audio_chunk(self, duration_seconds: float = 5) -> bytes:
        """Capture audio from microphone"""
        log.debug(f"Capturing audio for {duration_seconds}s...")

        p = pyaudio.PyAudio()

        try:
            stream = p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK_SIZE
            )

            frames = []
            num_chunks = int(self.SAMPLE_RATE / self.CHUNK_SIZE * duration_seconds)

            for _ in range(num_chunks):
                data = stream.read(self.CHUNK_SIZE)
                frames.append(data)

            stream.stop_stream()
            stream.close()

            # Convert frames to bytes
            audio_data = b"".join(frames)
            log.debug(f"Captured {len(audio_data)} bytes of audio")

            return audio_data

        finally:
            p.terminate()

    async def send_audio_to_gemini(self, audio_data: bytes) -> str:
        """Send audio to Gemini and get text response"""
        try:
            log.info("Sending audio to Gemini...")

            # Create message with audio
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_audio(
                                data=audio_data,
                                mime_type="audio/wav"
                            ),
                            types.Part.from_text("Bu ses mesajına Türkçe olarak yanıt ver.")
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=1000
                )
            )

            result = response.text
            log.info(f"Gemini response: {result[:100]}...")

            return result

        except Exception as e:
            log.error(f"Gemini API error: {e}")
            return f"Hata: {str(e)}"

    async def text_to_speech_with_gemini(self, text: str) -> bytes:
        """Generate speech audio from text using Gemini"""
        try:
            log.info(f"Generating speech for: {text[:50]}...")

            # Gemini 2.5 Flash can generate audio responses
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(
                                f"Bu metni Türkçe sesi ile söyle: {text}"
                            )
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=500
                )
            )

            # Return audio if available, otherwise fallback to piper
            if response.audio_content:
                log.debug("Audio generated by Gemini")
                return response.audio_content
            else:
                log.warning("Gemini didn't return audio, falling back to Piper TTS")
                return None

        except Exception as e:
            log.error(f"TTS error: {e}")
            return None

    async def play_audio(self, audio_data: bytes):
        """Play audio using PyAudio"""
        if not audio_data:
            log.warning("No audio data to play")
            return

        try:
            log.debug(f"Playing audio ({len(audio_data)} bytes)...")

            p = pyaudio.PyAudio()
            stream = p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                output=True,
                frames_per_buffer=self.CHUNK_SIZE
            )

            # Write audio in chunks
            for i in range(0, len(audio_data), self.CHUNK_SIZE):
                chunk = audio_data[i:i + self.CHUNK_SIZE]
                stream.write(chunk)

            stream.stop_stream()
            stream.close()
            p.terminate()

            log.info("Audio playback complete")

        except Exception as e:
            log.error(f"Audio playback error: {e}")

    async def conversation_turn(self) -> dict:
        """Single conversation turn: capture -> send -> respond"""
        log.info("=== Starting conversation turn ===")

        try:
            # Step 1: Capture user audio
            user_audio = await self.capture_audio_chunk(duration_seconds=5)

            if not user_audio:
                log.warning("No audio captured")
                return {"error": "No audio captured"}

            # Step 2: Send to Gemini
            gemini_response = await self.send_audio_to_gemini(user_audio)

            # Step 3: Generate speech response
            response_audio = await self.text_to_speech_with_gemini(gemini_response)

            # Step 4: Play response
            if response_audio:
                await self.play_audio(response_audio)
            else:
                log.info(f"Text response (no TTS): {gemini_response}")

            # Log conversation
            turn = {
                "timestamp": datetime.now().isoformat(),
                "gemini_response": gemini_response,
                "has_audio_response": response_audio is not None
            }
            self.conversation_history.append(turn)

            return turn

        except Exception as e:
            log.error(f"Conversation turn error: {e}")
            return {"error": str(e)}

    async def run_continuous_loop(self, duration_hours: float = 1):
        """Run continuous conversation loop"""
        log.info(f"Starting continuous voice loop for {duration_hours} hours")

        start_time = datetime.now()
        turn_count = 0

        while True:
            elapsed = (datetime.now() - start_time).total_seconds() / 3600

            if elapsed > duration_hours:
                log.info(f"Loop duration ({duration_hours}h) reached. Stopping.")
                break

            turn_count += 1
            log.info(f"Turn {turn_count}, Elapsed: {elapsed:.2f}h")

            result = await self.conversation_turn()

            if result.get("error"):
                log.warning(f"Turn failed: {result['error']}")
                await asyncio.sleep(5)
                continue

            # Wait before next turn
            await asyncio.sleep(2)

        log.info(f"Loop complete. Total turns: {turn_count}")

        # Save conversation log
        self._save_conversation_log()

    def _save_conversation_log(self):
        """Save conversation history to file"""
        try:
            log_path = Path("server/logs/voice_conversations.jsonl")
            log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(log_path, "a", encoding="utf-8") as f:
                for turn in self.conversation_history:
                    f.write(json.dumps(turn, ensure_ascii=False) + "\n")

            log.info(f"Conversation saved to {log_path}")

        except Exception as e:
            log.error(f"Failed to save conversation log: {e}")


async def test_gemini_voice():
    """Quick test of Gemini voice"""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        log.error("GEMINI_API_KEY not set in .env")
        return

    agent = GeminiVoiceAgent(api_key)

    # Run single test turn
    log.info("Running test conversation...")
    result = await agent.conversation_turn()
    log.info(f"Test result: {result}")


async def main():
    """Main entry point"""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        log.error("GEMINI_API_KEY not set in environment")
        sys.exit(1)

    agent = GeminiVoiceAgent(api_key)

    try:
        # Run continuous loop (test: 1 minute)
        await agent.run_continuous_loop(duration_hours=0.0167)  # 1 minute

    except KeyboardInterrupt:
        log.info("Interrupted by user")

    except Exception as e:
        log.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
