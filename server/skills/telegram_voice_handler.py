from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


MAX_VOICE_DURATION_SECONDS = 60
ERROR_PREFIXES = (
    "transkripsiyon hatasi",
    "ses islenemedi",
    "whisper hatasi",
    "ses tanima zaman asimi",
)


def _extract_message(message_or_update: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(message_or_update, dict):
        return {}
    if isinstance(message_or_update.get("message"), dict):
        return dict(message_or_update["message"])
    return dict(message_or_update)


def _extract_voice(message_or_update: dict[str, Any]) -> dict[str, Any]:
    message = _extract_message(message_or_update)
    payload = message.get("voice") or message.get("audio") or {}
    return payload if isinstance(payload, dict) else {}


def _telegram_json(url: str) -> dict[str, Any]:
    with urlopen(Request(url), timeout=15) as response:
        payload = json.loads(response.read())
    return payload if isinstance(payload, dict) else {}


def download_telegram_voice(bot_token: str, file_id: str) -> tuple[Path, dict[str, Any]]:
    if not str(bot_token or "").strip():
        raise ValueError("bot_token is required")
    if not str(file_id or "").strip():
        raise ValueError("file_id is required")

    file_payload = _telegram_json(
        f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    )
    file_info = file_payload.get("result") if isinstance(file_payload, dict) else {}
    if not isinstance(file_info, dict):
        raise RuntimeError("Telegram file metadata unavailable")

    remote_path = str(file_info.get("file_path") or "").strip()
    suffix = Path(remote_path).suffix or ".ogg"
    tmp_dir = Path(tempfile.mkdtemp(prefix="jarvis_tg_voice_"))
    output_path = tmp_dir / f"{file_id}{suffix}"

    download_url = f"https://api.telegram.org/file/bot{bot_token}/{remote_path}"
    with urlopen(Request(download_url), timeout=30) as response:
        output_path.write_bytes(response.read())

    return output_path, file_info


def handle_voice_message(
    bot_token: str,
    message_or_update: dict[str, Any],
    *,
    language: str = "tr",
) -> dict[str, Any]:
    message = _extract_message(message_or_update)
    voice = _extract_voice(message_or_update)
    if not voice:
        return {
            "ok": False,
            "error": "voice_not_found",
            "reply": "Sesi anlayamadim, yazarak tekrar eder misin?",
        }

    duration = int(voice.get("duration") or 0)
    chat_id = message.get("chat", {}).get("id")
    file_id = str(voice.get("file_id") or "").strip()

    if duration > MAX_VOICE_DURATION_SECONDS:
        return {
            "ok": False,
            "error": "voice_too_long",
            "chat_id": chat_id,
            "duration_seconds": duration,
            "reply": "Lutfen 60 saniye altinda sesli mesaj gonder.",
        }

    try:
        from whisper_skill import transcribe_audio
    except Exception:
        from server.skills.whisper_skill import transcribe_audio  # type: ignore

    downloaded_path: Path | None = None
    try:
        downloaded_path, file_info = download_telegram_voice(bot_token, file_id)
        text = str(
            transcribe_audio(str(downloaded_path), language=language) or ""
        ).strip()
        if not text or any(text.lower().startswith(prefix) for prefix in ERROR_PREFIXES):
            return {
                "ok": False,
                "error": "transcription_failed",
                "chat_id": chat_id,
                "file_id": file_id,
                "duration_seconds": duration,
                "reply": "Sesi anlayamadim, yazarak tekrar eder misin?",
                "raw_text": text,
            }
        return {
            "ok": True,
            "chat_id": chat_id,
            "file_id": file_id,
            "duration_seconds": duration,
            "telegram_file_path": str(file_info.get("file_path") or ""),
            "text": text,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": "voice_processing_failed",
            "chat_id": chat_id,
            "file_id": file_id,
            "duration_seconds": duration,
            "reply": "Sesi anlayamadim, yazarak tekrar eder misin?",
            "details": str(exc),
        }
    finally:
        if downloaded_path is not None:
            try:
                downloaded_path.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                downloaded_path.parent.rmdir()
            except OSError:
                pass


__all__ = [
    "MAX_VOICE_DURATION_SECONDS",
    "download_telegram_voice",
    "handle_voice_message",
]
