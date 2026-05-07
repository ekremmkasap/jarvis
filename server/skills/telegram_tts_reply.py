from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


DEFAULT_EDGE_VOICE = os.getenv("TELEGRAM_TTS_VOICE", "tr-TR-AhmetNeural")


def _normalize_voice_name(voice: str | None) -> str:
    clean = str(voice or "").strip()
    if not clean:
        return DEFAULT_EDGE_VOICE
    if clean.startswith("tr-TR-"):
        return clean
    if clean.endswith("Neural"):
        return f"tr-TR-{clean}"
    return DEFAULT_EDGE_VOICE


def _sanitize_text(text: str) -> str:
    clean = re.sub(r"[*_`#>\[\]()]", " ", str(text or ""))
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:600]


def _resolve_ffmpeg() -> str:
    for candidate in (
        os.getenv("FFMPEG_PATH", "").strip(),
        shutil.which("ffmpeg") or "",
    ):
        if candidate:
            return candidate
    raise FileNotFoundError("ffmpeg bulunamadi")


async def _edge_tts_to_mp3(text: str, voice: str, output_path: Path) -> Path:
    import edge_tts  # type: ignore

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    return output_path


def synthesize_voice_ogg(text: str, voice: str | None = None) -> Path:
    clean_text = _sanitize_text(text)
    if not clean_text:
        raise ValueError("text is required")

    ffmpeg = _resolve_ffmpeg()
    tmp_dir = Path(tempfile.mkdtemp(prefix="jarvis_tts_"))
    mp3_path = tmp_dir / "reply.mp3"
    ogg_path = tmp_dir / "reply.ogg"

    try:
        asyncio.run(_edge_tts_to_mp3(clean_text, _normalize_voice_name(voice), mp3_path))
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(mp3_path),
                "-c:a",
                "libopus",
                "-b:a",
                "64k",
                str(ogg_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        return ogg_path
    except Exception:
        for candidate in (ogg_path, mp3_path):
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            tmp_dir.rmdir()
        except OSError:
            pass
        raise


def send_voice_reply(
    bridge,
    chat_id: int,
    text: str,
    voice: str | None = None,
) -> bool:
    if bridge is None or not hasattr(bridge, "send_voice"):
        raise AttributeError("bridge.send_voice() gereklidir")

    if not _sanitize_text(text):
        return False

    ogg_path = synthesize_voice_ogg(text, voice=voice)
    try:
        bridge.send_voice(chat_id, str(ogg_path))
        return True
    finally:
        try:
            ogg_path.unlink(missing_ok=True)
        except OSError:
            pass
        try:
            ogg_path.parent.rmdir()
        except OSError:
            pass


__all__ = [
    "DEFAULT_EDGE_VOICE",
    "send_voice_reply",
    "synthesize_voice_ogg",
]
