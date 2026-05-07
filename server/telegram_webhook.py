#!/usr/bin/env python3
"""
TELEGRAM WEBHOOK — Jarvis Autonomous Loop Updates
"""

import os
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler
import logging

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.orchestrator.live_state import load_task_queue_snapshot, read_recent_live_events

log = logging.getLogger("telegram_webhook")


class TelegramWebhookHandler(BaseHTTPRequestHandler):
    """Telegram updates handle et"""

    def do_POST(self):
        """Telegram message received"""
        if self.path == "/webhook/telegram":
            self._handle_telegram_webhook()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        """Status check"""
        if self.path == "/webhook/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "OK", "service": "telegram_webhook"}
            self.wfile.write(json.dumps(response).encode())

    def _handle_telegram_webhook(self):
        """Telegram update'i işle"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()

        try:
            update = json.loads(body)
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")

            log.info(f"📱 Telegram: [{chat_id}] {text}")

            # Handle commands
            if text.startswith("/start-loop"):
                self._handle_start_loop(chat_id, text)
            elif text.startswith("/loop-status"):
                self._handle_loop_status(chat_id)
            elif text.startswith("/stop-loop"):
                self._handle_stop_loop(chat_id)

            # Always respond 200
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())

        except Exception as e:
            log.error(f"Webhook error: {e}")
            self.send_response(500)
            self.end_headers()

    def _handle_start_loop(self, chat_id: int, text: str):
        """Start autonomous loop"""
        parts = text.split(" ", 1)
        goal = parts[1] if len(parts) > 1 else "Jarvis optimization"

        log.info(f"🚀 Starting autonomous loop: {goal}")

        # Save chat_id for updates
        config_file = Path("server/config/telegram_autonomous.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "goal": goal,
            "chat_id": chat_id,
            "started_at": str(__import__("datetime").datetime.now()),
            "duration_hours": 24
        }

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        log.info(f"Config saved: {config_file}")

    def _handle_loop_status(self, chat_id: int):
        """Send loop status"""
        queue_snapshot = load_task_queue_snapshot()
        recent_events = read_recent_live_events(limit=3)
        latest_event = recent_events[-1] if recent_events else {}

        log.info(
            "Loop status for chat %s: queued=%s running=%s awaiting_confirmation=%s latest=%s",
            chat_id,
            queue_snapshot.get("queued_tasks", 0),
            queue_snapshot.get("running_tasks", 0),
            queue_snapshot.get("awaiting_confirmation_tasks", 0),
            latest_event.get("message", "no live events"),
        )

    def _handle_stop_loop(self, chat_id: int):
        """Stop loop"""
        config_file = Path("server/config/telegram_autonomous.json")
        if config_file.exists():
            config_file.unlink()
            log.info("Loop stopped")


def send_telegram_message(chat_id: int, text: str, parse_mode: str | None = "Markdown"):
    """Telegram'a message gönder"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        log.warning("TELEGRAM_BOT_TOKEN not set")
        return

    import urllib.request
    import urllib.parse

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    data = urllib.parse.urlencode(payload).encode()

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error(f"Telegram send error: {e}")
