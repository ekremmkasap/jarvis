#!/usr/bin/env python3
"""
JARVIS VOICE LAYER — GEMINI 2.5 FLASH TEXT + VOICE
Conversational AI using Gemini (text for now, audio later)
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
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("jarvis.voice.gemini")

try:
    import google.genai as genai
    from google.genai import types
except ImportError:
    log.error("google-genai not installed. Run: pip install google-genai")
    sys.exit(1)


class GeminiVoiceAgent:
    """Conversational AI with Gemini 2.5 Flash"""

    def __init__(self, api_key: str, model: str = "models/gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=self.api_key)
        self.conversation_history = []
        self.session_start = datetime.now()

        log.info(f"[Gemini] Initialized with model: {self.model}")

    async def send_message(self, user_input: str) -> str:
        """Send message to Gemini and get response"""
        try:
            log.info(f"User: {user_input[:60]}...")

            # Build message with history
            messages = []
            for turn in self.conversation_history[-10:]:  # Last 10 turns
                messages.append({
                    "role": "user",
                    "parts": [turn["user_text"]]
                })
                messages.append({
                    "role": "model",
                    "parts": [turn["response"]]
                })

            # Add current message
            messages.append({
                "role": "user",
                "parts": [user_input]
            })

            # Call Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=500
                )
            )

            result = response.text
            log.info(f"Gemini: {result[:60]}...")

            # Store in history
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_text": user_input,
                "response": result
            })

            return result

        except Exception as e:
            log.error(f"Gemini error: {e}")
            return f"Hata: {str(e)}"

    async def interactive_loop(self):
        """Run interactive conversation loop"""
        log.info("Starting interactive chat (type 'quit' to exit)")
        log.info("=" * 50)

        while True:
            try:
                # Get user input (blocking, in real app use aioinput)
                user_input = input("\nSiz: ").strip()

                if user_input.lower() in ["quit", "exit", "cikis"]:
                    log.info("Exiting...")
                    break

                if not user_input:
                    continue

                # Get Gemini response
                response = await self.send_message(user_input)
                print(f"\nJarvis: {response}\n")

            except KeyboardInterrupt:
                log.info("Interrupted by user")
                break
            except Exception as e:
                log.error(f"Error in loop: {e}")
                continue

    def save_conversation(self):
        """Save conversation to file"""
        try:
            log_dir = Path("server/logs")
            log_dir.mkdir(parents=True, exist_ok=True)

            log_path = log_dir / "voice_conversations.jsonl"

            with open(log_path, "a", encoding="utf-8") as f:
                for turn in self.conversation_history:
                    f.write(json.dumps(turn, ensure_ascii=False) + "\n")

            log.info(f"Conversation saved to {log_path}")

        except Exception as e:
            log.error(f"Failed to save: {e}")


async def main():
    """Main entry point"""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        log.error("GEMINI_API_KEY or GOOGLE_API_KEY not set")
        sys.exit(1)

    agent = GeminiVoiceAgent(api_key)

    try:
        await agent.interactive_loop()
        agent.save_conversation()

    except KeyboardInterrupt:
        log.info("Shutting down...")

    except Exception as e:
        log.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
