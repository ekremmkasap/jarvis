"""
YouTube Skill — YouTube API key + transcript-api
Transcript, özet ve full metadata çeker.
"""
from __future__ import annotations

import re
import os
import urllib.request
import json
from typing import Optional

API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


def _extract_video_id(url_or_id: str) -> Optional[str]:
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, url_or_id)
        if m:
            return m.group(1)
    return None


def _get_metadata(video_id: str) -> dict:
    """Google YouTube API'den video metadata çek"""
    if not API_KEY:
        return {}

    try:
        url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={API_KEY}&part=snippet,statistics,contentDetails"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())

        if not data.get("items"):
            return {}

        item = data["items"][0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        return {
            "title": snippet.get("title", ""),
            "uploader": snippet.get("channelTitle", ""),
            "view_count": stats.get("viewCount", "0"),
            "like_count": stats.get("likeCount", "0"),
            "upload_date": snippet.get("publishedAt", ""),
        }
    except Exception:
        return {}


def get_transcript(url_or_id: str, max_chars: int = 3000) -> dict:
    """
    Video URL veya ID'den transcript çeker.
    Döner: {"video_id", "transcript", "summary", "char_count", "error"}
    """
    video_id = _extract_video_id(url_or_id.strip())
    if not video_id:
        return {"error": f"Geçerli YouTube URL/ID bulunamadı: {url_or_id}"}

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    except ImportError:
        return {"error": "youtube-transcript-api yüklü değil. pip install youtube-transcript-api"}

    transcript_text = ""
    used_lang = ""
    for langs in (["tr", "tr-TR"], ["en", "en-US"], ["tr", "en"]):
        try:
            entries = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
            transcript_text = " ".join(e["text"] for e in entries if e.get("text", "").strip())
            used_lang = langs[0]
            break
        except (TranscriptsDisabled, NoTranscriptFound):
            continue
        except Exception:
            continue

    if not transcript_text:
        return {"video_id": video_id, "error": "Transcript bulunamadı (devre dışı veya mevcut değil)"}

    summary = transcript_text[:max_chars]
    if len(transcript_text) > max_chars:
        summary += f"... [{len(transcript_text)} karakter, kısaltıldı]"

    metadata = _get_metadata(video_id)

    return {
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "transcript": transcript_text,
        "summary": summary,
        "char_count": len(transcript_text),
        "lang": used_lang,
        "error": None,
        **metadata,
    }


def format_report(result: dict) -> str:
    nl = chr(10)
    if result.get("error"):
        return f"YouTube hata: {result['error']}"

    title = result.get("title", "")
    uploader = result.get("uploader", "")
    views = result.get("view_count", "0")
    likes = result.get("like_count", "0")

    output = f"🎬 {title}" + nl
    if uploader:
        output += f"📢 {uploader}" + nl
    output += f"👁️ {views} views | 👍 {likes} likes" + nl
    output += f"🔗 youtu.be/{result['video_id']}" + nl
    output += f"Dil: {result.get('lang','?')} | {result.get('char_count',0)} karakter" + nl + nl
    output += "📝 Transcript:" + nl
    output += result.get("summary", "")

    return output
