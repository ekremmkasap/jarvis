from __future__ import annotations

"""Slack -> Jarvis local bridge.

Jarvis runtime, Codex'in Slack plugin baglantisini otomatik kullanamaz. Bu dosya
ayri bir Slack app token setiyle Slack Socket Mode eventlerini lokal Jarvis
bridge `/api/chat` endpoint'ine aktarir.

Default olarak sadece DMs ve app mentions islenir. Kanalda bot mention yoksa
veya mesaj `jarvis` / `/jarvis` ile baslamiyorsa cevap verilmez.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BRIDGE_URL = "http://127.0.0.1:8081"
MAX_SLACK_MESSAGE_CHARS = 3500


@dataclass(frozen=True)
class SlackBridgeConfig:
    bot_token: str
    app_token: str
    signing_secret: str
    bridge_url: str
    bot_user_id: str
    respond_in_threads: bool = True


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def load_config() -> SlackBridgeConfig:
    return SlackBridgeConfig(
        bot_token=_env("SLACK_BOT_TOKEN"),
        app_token=_env("SLACK_APP_TOKEN"),
        signing_secret=_env("SLACK_SIGNING_SECRET"),
        bridge_url=_env("BRIDGE_URL", _env("JARVIS_BACKEND_URL", DEFAULT_BRIDGE_URL)).rstrip("/"),
        bot_user_id=_env("SLACK_BOT_USER_ID"),
        respond_in_threads=_env("JARVIS_SLACK_THREAD_REPLIES", "1").lower()
        not in {"0", "false", "no", "off"},
    )


def redact_secret(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 8:
        return "***"
    return text[:4] + "..." + text[-4:]


def is_bolt_available() -> bool:
    try:
        import slack_bolt  # noqa: F401
        import slack_sdk  # noqa: F401

        return True
    except Exception:
        return False


def stable_slack_chat_id(team_id: str, channel_id: str, user_id: str) -> int:
    seed = f"slack:{team_id}:{channel_id}:{user_id}".encode("utf-8", errors="ignore")
    digest = hashlib.sha256(seed).hexdigest()
    return 700000 + int(digest[:8], 16) % 800000000


def should_ignore_event(event: dict[str, Any], bot_user_id: str = "") -> bool:
    if not isinstance(event, dict):
        return True
    if event.get("bot_id"):
        return True
    if event.get("subtype") in {
        "bot_message",
        "message_changed",
        "message_deleted",
        "channel_join",
        "channel_leave",
    }:
        return True
    if bot_user_id and event.get("user") == bot_user_id:
        return True
    if not str(event.get("text") or "").strip():
        return True
    return False


def strip_bot_mention(text: str, bot_user_id: str = "") -> str:
    clean = str(text or "").strip()
    clean = re.sub(r"<@[^>]+>\s*", "", clean).strip()
    if bot_user_id:
        clean = clean.replace(f"<@{bot_user_id}>", "").strip()
    return clean


def extract_jarvis_text(event: dict[str, Any], bot_user_id: str = "") -> str:
    text = strip_bot_mention(str(event.get("text") or ""), bot_user_id)
    lowered = text.lower()
    for prefix in ("/jarvis", "jarvis:", "jarvis,", "jarvis "):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    if lowered == "jarvis":
        return "yardim"
    return text.strip()


def should_handle_message(event: dict[str, Any], bot_user_id: str = "") -> bool:
    channel_type = str(event.get("channel_type") or "").lower()
    text = str(event.get("text") or "").strip()
    lowered = strip_bot_mention(text, bot_user_id).lower()
    if channel_type == "im":
        return True
    if bot_user_id and f"<@{bot_user_id}>" in text:
        return True
    return lowered.startswith(("/jarvis", "jarvis:", "jarvis,", "jarvis "))


def build_bridge_payload(event: dict[str, Any], text: str) -> dict[str, Any]:
    team_id = str(event.get("team") or event.get("team_id") or "")
    channel_id = str(event.get("channel") or "")
    user_id = str(event.get("user") or "")
    thread_ts = str(event.get("thread_ts") or event.get("ts") or "")
    return {
        "message": text,
        "text": text,
        "chat_id": stable_slack_chat_id(team_id, channel_id, user_id),
        "chatId": stable_slack_chat_id(team_id, channel_id, user_id),
        "source": "slack",
        "lane": "slack",
        "slack": {
            "team_id": team_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "thread_ts": thread_ts,
            "event_ts": event.get("ts"),
        },
    }


def post_to_jarvis_bridge(payload: dict[str, Any], bridge_url: str, timeout: int = 60) -> str:
    endpoint = bridge_url.rstrip("/") + "/api/chat"
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    if isinstance(data, dict):
        for key in ("response", "reply", "message", "text", "result"):
            value = data.get(key)
            if value:
                return str(value)
    return str(data)


def bridge_health(bridge_url: str, timeout: int = 3) -> bool:
    for path in ("/api/status", "/health"):
        try:
            with urlopen(bridge_url.rstrip("/") + path, timeout=timeout) as response:
                if 200 <= int(response.status) < 300:
                    return True
        except Exception:
            continue
    return False


def format_slack_reply(text: str) -> str:
    clean = str(text or "").strip()
    if not clean:
        return "Jarvis cevap uretmedi."
    if len(clean) <= MAX_SLACK_MESSAGE_CHARS:
        return clean
    return clean[: MAX_SLACK_MESSAGE_CHARS - 30].rstrip() + "\n\n[Jarvis cevabi kisaltti]"


def check_status(config: SlackBridgeConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    has_bot = bool(cfg.bot_token)
    has_app = bool(cfg.app_token)
    bolt = is_bolt_available()
    return {
        "ok": has_bot and has_app and bolt,
        "bot_token_present": has_bot,
        "bot_token": redact_secret(cfg.bot_token),
        "app_token_present": has_app,
        "app_token": redact_secret(cfg.app_token),
        "signing_secret_present": bool(cfg.signing_secret),
        "slack_bolt_available": bolt,
        "bridge_url": cfg.bridge_url,
        "bridge_alive": bridge_health(cfg.bridge_url),
        "enabled_env": _env("JARVIS_ENABLE_SLACK", "0"),
    }


def _handle_event(event: dict[str, Any], say, config: SlackBridgeConfig) -> None:
    if should_ignore_event(event, config.bot_user_id):
        return
    if not should_handle_message(event, config.bot_user_id):
        return

    text = extract_jarvis_text(event, config.bot_user_id)
    if not text:
        return

    payload = build_bridge_payload(event, text)
    try:
        response = post_to_jarvis_bridge(payload, config.bridge_url)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        response = f"Jarvis bridge'e ulasilamadi: {exc}"
    except Exception as exc:  # noqa: BLE001
        response = f"Jarvis Slack bridge hatasi: {exc}"

    reply_kwargs = {"text": format_slack_reply(response)}
    if config.respond_in_threads:
        thread_ts = event.get("thread_ts") or event.get("ts")
        if thread_ts:
            reply_kwargs["thread_ts"] = thread_ts
    say(**reply_kwargs)


def run_socket_mode(config: SlackBridgeConfig | None = None) -> int:
    cfg = config or load_config()
    if not cfg.bot_token or not cfg.app_token:
        print("Slack token eksik. SLACK_BOT_TOKEN ve SLACK_APP_TOKEN gerekli.")
        return 2
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except Exception as exc:  # noqa: BLE001
        print(f"slack-bolt kurulu degil veya import edilemedi: {exc}")
        return 2

    app = App(token=cfg.bot_token, signing_secret=cfg.signing_secret or None)

    @app.event("app_mention")
    def _on_app_mention(event, say):  # type: ignore[no-untyped-def]
        _handle_event(event, say, cfg)

    @app.message(re.compile(".*"))
    def _on_message(event, say):  # type: ignore[no-untyped-def]
        _handle_event(event, say, cfg)

    print(
        "Jarvis Slack bridge basliyor: "
        f"bot={redact_secret(cfg.bot_token)} app={redact_secret(cfg.app_token)} "
        f"bridge={cfg.bridge_url}"
    )
    SocketModeHandler(app, cfg.app_token).start()
    return 0


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jarvis Slack Socket Mode bridge")
    parser.add_argument("--check", action="store_true", help="Config ve dependency durumunu yaz")
    args = parser.parse_args(argv)

    config = load_config()
    if args.check:
        print(json.dumps(check_status(config), ensure_ascii=False, indent=2))
        return 0
    return run_socket_mode(config)


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))

