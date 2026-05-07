"""
Jarvis Skill — YouTube Unified
3 YouTube reposunu birleştirir:
  - youtube-transcript-api (Python, hızlı)
  - mcp-server-youtube-transcript (Node MCP)
  - youtube-mcp-server (Python MCP)
"""
import re, os, json, sys
from pathlib import Path

REPO_YTA  = Path(__file__).parent.parent.parent / "external-repos" / "youtube-transcript-api"
REPO_MCP1 = Path(__file__).parent.parent.parent / "external-repos" / "mcp-server-youtube-transcript"
REPO_MCP2 = Path(__file__).parent.parent.parent / "external-repos" / "youtube-mcp-server"


def _extract_video_id(url_or_id: str) -> str:
    """URL veya ID'den video ID çıkar."""
    patterns = [
        r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for p in patterns:
        m = re.search(p, url_or_id)
        if m:
            return m.group(1)
    return url_or_id.strip()


def get_transcript(url_or_id: str, lang: str = "tr") -> str:
    """YouTube transcript al — youtube-transcript-api ile."""
    if not url_or_id:
        return "Kullanim: /transkript [youtube-url-veya-id]"

    video_id = _extract_video_id(url_or_id)

    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
        # Önce TR, sonra EN dene
        for try_lang in [lang, "tr", "en", "a.tr", "a.en"]:
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[try_lang])
                text = " ".join(t["text"] for t in transcript)
                word_count = len(text.split())
                return (
                    f"📄 **Transkript** (`{video_id}` | {word_count} kelime)\n\n"
                    f"{text[:2000]}"
                    + (f"\n\n_...{word_count-300} kelime daha_" if word_count > 300 else "")
                )
            except (NoTranscriptFound, Exception):
                continue

        # Tüm dilleri dene
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available = [t.language_code for t in transcript_list]
        return (
            f"⚠️ `{lang}` transkript yok.\n"
            f"Mevcut diller: {', '.join(available)}\n"
            f"Kullanım: `/transkript {video_id} en`"
        )
    except Exception as e:
        return f"❌ Transkript alınamadı: {e}"


def transcript_summary(url_or_id: str, call_llm=None) -> str:
    """Transkripti al ve özetle."""
    raw = get_transcript(url_or_id)
    if raw.startswith("❌") or raw.startswith("⚠️"):
        return raw

    if not call_llm:
        return raw

    try:
        text = raw.split("\n\n", 1)[-1][:3000]
        summary = call_llm(f"Bu YouTube transkriptini Türkçe özetle:\n\n{text}")
        vid = _extract_video_id(url_or_id)
        return f"🎬 **Video Özeti** (`{vid}`)\n\n{summary}"
    except Exception as e:
        return f"❌ Özet hatası: {e}\n\nHam transkript:\n{raw[:800]}"


def list_backends() -> str:
    lines = ["🎬 **YouTube Backend'leri**", ""]
    yta_ok = True
    try:
        import youtube_transcript_api
        v = getattr(youtube_transcript_api, "__version__", "?")
        lines.append(f"  🟢 youtube-transcript-api v{v} (Python, aktif)")
    except ImportError:
        yta_ok = False
        lines.append("  🔴 youtube-transcript-api (kurulu değil)")

    mcp1 = REPO_MCP1 / "package.json"
    lines.append(f"  {'🟢' if mcp1.exists() else '🔴'} mcp-server-youtube-transcript (Node MCP)")

    mcp2 = REPO_MCP2 / "youtube_mcp_server.py"
    lines.append(f"  {'🟢' if mcp2.exists() else '🔴'} youtube-mcp-server (Python MCP)")
    return "\n".join(lines)
