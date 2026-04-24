#!/usr/bin/env python3
"""
Jarvis Whisper Skill
Telegram veya yerel ses dosyalarini metne cevirir.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
AUDIO_TMP_DIR = Path(tempfile.gettempdir()) / "jarvis_audio"
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_TRANSCRIPTION_MODEL = os.getenv(
    "GROQ_TRANSCRIPTION_MODEL",
    os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo"),
)


def ensure_whisper() -> tuple[bool, str | None]:
    """Whisper import edilebiliyor mu kontrol et."""
    result = subprocess.run(
        [sys.executable, "-c", "import whisper; print(whisper.__version__)"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, result.stdout.strip() or None
    return False, None


def install_whisper() -> bool:
    """openai-whisper kur."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "openai-whisper"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _get_groq_api_key() -> str:
    direct_key = os.getenv("GROQ_API_KEY", "").strip()
    if direct_key:
        return direct_key

    try:
        from key_pool import get_groq_key
    except Exception:
        try:
            from server.key_pool import get_groq_key  # type: ignore
        except Exception:
            return ""

    try:
        return str(get_groq_key() or "").strip()
    except Exception:
        return ""


def _extract_transcription_text(payload: Any) -> str:
    text = getattr(payload, "text", None)
    if text:
        return str(text).strip()

    if isinstance(payload, dict):
        return str(payload.get("text") or "").strip()

    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return str(dumped.get("text") or "").strip()

    return str(payload or "").strip()


def _transcribe_with_groq(source_path: Path, language: str = "tr") -> str:
    api_key = _get_groq_api_key()
    if not api_key:
        raise RuntimeError("Groq API key bulunamadi")

    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"openai SDK yuklenemedi: {exc}") from exc

    client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
    with source_path.open("rb") as audio_file:
        response = client.audio.transcriptions.create(
            model=GROQ_TRANSCRIPTION_MODEL,
            file=audio_file,
            language=language,
        )

    text = _extract_transcription_text(response)
    if not text:
        raise RuntimeError("Groq bos transkript dondu")
    return text


def _transcribe_with_local_whisper(source_path: Path, language: str = "tr") -> str:
    """Yerel Whisper fallback'i."""
    script = f"""
import json
import whisper

model = whisper.load_model({WHISPER_MODEL!r})
result = model.transcribe({str(source_path)!r}, language={language!r}, fp16=False)
print(json.dumps({{"text": result.get("text", ""), "lang": result.get("language")}}, ensure_ascii=False))
"""
    script_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".py",
            delete=False,
            mode="w",
            encoding="utf-8",
            dir=tempfile.gettempdir(),
        ) as handle:
            handle.write(script)
            script_path = Path(handle.name)

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            return f"Transkripsiyon hatasi: {stderr[:200]}"

        output = (result.stdout or "").strip()
        if not output:
            return ""
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            return output
        return str(payload.get("text") or "").strip()
    except subprocess.TimeoutExpired:
        return "Transkripsiyon hatasi: zaman asimi"
    except Exception as exc:  # noqa: BLE001
        return f"Transkripsiyon hatasi: {exc}"
    finally:
        if script_path is not None:
            try:
                script_path.unlink(missing_ok=True)
            except OSError:
                pass


def transcribe_audio(audio_path: str, language: str = "tr") -> str:
    """Ses dosyasini metne cevir."""
    source_path = Path(audio_path).expanduser()
    if not source_path.exists():
        return f"Transkripsiyon hatasi: dosya bulunamadi ({source_path})"

    try:
        return _transcribe_with_groq(source_path, language=language)
    except Exception:
        return _transcribe_with_local_whisper(source_path, language=language)


def download_voice_message(bot_token: str, file_id: str, out_path: str) -> bool:
    """Telegram'dan ses dosyasini indir."""
    req = Request(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}")
    with urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read())
    file_path = str(payload["result"]["file_path"])

    req2 = Request(f"https://api.telegram.org/file/bot{bot_token}/{file_path}")
    with urlopen(req2, timeout=30) as resp:
        content = resp.read()

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return True


def process_voice_in_bridge(update: dict, bot_token: str) -> str | None:
    """
    Bridge.py'den cagrilir:
    Telegram voice/audio mesaji geldiginde sesli komutu isle.
    """
    msg = update.get("message", {}) if isinstance(update, dict) else {}
    voice = msg.get("voice") or msg.get("audio")
    if not isinstance(voice, dict):
        return None

    AUDIO_TMP_DIR.mkdir(parents=True, exist_ok=True)
    file_id = str(voice.get("file_id") or "").strip()
    if not file_id:
        return "Ses islenemedi: file_id yok"

    ext = ".ogg" if msg.get("voice") else ".mp3"
    audio_path = AUDIO_TMP_DIR / f"{file_id}{ext}"
    try:
        download_voice_message(bot_token, file_id, str(audio_path))
        return transcribe_audio(str(audio_path))
    except Exception as exc:  # noqa: BLE001
        return f"Ses islenemedi: {exc}"
    finally:
        try:
            audio_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    ok, version = ensure_whisper()
    if ok:
        print(f"Whisper kurulu: {version}")
    else:
        print("Whisper kurulu degil")
