from __future__ import annotations

"""Jarvis media intake skill.

URL kaynaklarini Jarvis icine alir:
- Instagram/Reels/TikTok/YouTube gibi video URL'leri icin yt-dlp metadata
- YouTube icin mevcut transcript skill fallback'i
- PDF URL/local path icin opsiyonel text extraction

Bu modul credential yazdirmaz. Cookie path sadece lokal dosya olarak kullanilir.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = ROOT / "server"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "media_intake"
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")


def _slugify(value: str, fallback: str = "media") -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80] or fallback


def extract_first_url(text: str) -> str:
    match = URL_RE.search(str(text or ""))
    return match.group(0).rstrip(").,]") if match else ""


def detect_source_type(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw.endswith(".pdf") or ".pdf?" in raw:
        return "pdf"
    if "instagram.com" in raw:
        if "/reel/" in raw or "/reels/" in raw:
            return "instagram_reel"
        return "instagram"
    if "youtube.com" in raw or "youtu.be" in raw:
        return "youtube"
    if "tiktok.com" in raw:
        return "tiktok"
    if raw.startswith("http://") or raw.startswith("https://"):
        return "web_media"
    path = Path(raw)
    if path.suffix.lower() == ".pdf":
        return "pdf"
    return "unknown"


def _pick_first(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _limit(text: str, max_chars: int = 1800) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 20].rstrip() + " ...[kisaltildi]"


def find_cookie_file(url: str, explicit: str | None = None) -> Path | None:
    candidates: list[Path] = []
    env_value = explicit or os.environ.get("JARVIS_YTDLP_COOKIES") or ""
    if env_value.strip():
        candidates.append(Path(env_value).expanduser())

    lower_url = str(url or "").lower()
    if "instagram.com" in lower_url:
        candidates.extend(
            [
                SERVER_DIR / "instagram_cookies.txt",
                SERVER_DIR / "www.instagram.com_cookies (4).txt",
                SERVER_DIR / "www.instagram.com_cookies (3).txt",
                SERVER_DIR / "www.instagram.com_cookies (2).txt",
                ROOT / "temp_cookies.txt",
            ]
        )

    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
                return candidate
        except OSError:
            continue
    return None


def _ytdlp_available() -> bool:
    try:
        import yt_dlp  # noqa: F401

        return True
    except Exception:
        return False


def _build_ytdlp_options(
    *,
    url: str,
    output_dir: Path,
    download: bool,
    cookie_file: Path | None,
    cookies_from_browser: str | None = None,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ignoreerrors": False,
        "outtmpl": str(output_dir / "%(extractor_key)s_%(id)s.%(ext)s"),
        "writethumbnail": False,
    }
    if not download:
        options["skip_download"] = True
    browser_name = str(cookies_from_browser or "").strip()
    if browser_name:
        options["cookiesfrombrowser"] = (browser_name, None, None, None)
    elif cookie_file is not None:
        options["cookiefile"] = str(cookie_file)
    if "instagram.com" in str(url).lower():
        options["extractor_args"] = {"instagram": {"include_stories": ["false"]}}
    return options


def _normalize_ytdlp_info(info: dict[str, Any], url: str, source_type: str) -> dict[str, Any]:
    description = _pick_first(
        info.get("description"),
        info.get("caption"),
        info.get("title"),
    )
    return {
        "source_type": source_type,
        "url": info.get("webpage_url") or url,
        "id": info.get("id"),
        "title": _pick_first(info.get("title"), info.get("fulltitle"), "Baslik yok"),
        "uploader": _pick_first(info.get("uploader"), info.get("channel"), info.get("creator")),
        "uploader_id": _pick_first(info.get("uploader_id"), info.get("channel_id")),
        "duration_seconds": _safe_float(info.get("duration")),
        "view_count": _safe_int(info.get("view_count")),
        "like_count": _safe_int(info.get("like_count")),
        "comment_count": _safe_int(info.get("comment_count")),
        "repost_count": _safe_int(info.get("repost_count")),
        "thumbnail": info.get("thumbnail"),
        "description": description,
        "tags": info.get("tags") if isinstance(info.get("tags"), list) else [],
        "upload_date": info.get("upload_date") or info.get("timestamp"),
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "webpage_url_domain": info.get("webpage_url_domain"),
    }


def _youtube_transcript(url: str) -> dict[str, Any]:
    try:
        try:
            from server.skills.youtube_skill import get_transcript
        except Exception:
            from youtube_skill import get_transcript  # type: ignore

        result = get_transcript(url, max_chars=3000)
        if not isinstance(result, dict) or result.get("error"):
            return {"ok": False, "error": str(result.get("error") if isinstance(result, dict) else result)}
        return {
            "ok": True,
            "video_id": result.get("video_id"),
            "lang": result.get("lang"),
            "char_count": result.get("char_count"),
            "transcript": result.get("transcript") or "",
            "summary": result.get("summary") or "",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _extract_pdf_text(source: str, output_dir: Path) -> dict[str, Any]:
    local_path: Path | None = None
    temp_pdf = output_dir / "source.pdf"
    if source.lower().startswith(("http://", "https://")):
        request = Request(source, headers={"User-Agent": "JarvisMediaIntake/1.0"})
        with urlopen(request, timeout=30) as response:
            temp_pdf.write_bytes(response.read())
        local_path = temp_pdf
    else:
        local_path = Path(source).expanduser()

    if not local_path.exists():
        return {"ok": False, "error": f"PDF bulunamadi: {source}"}

    text = ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(local_path))
        parts = []
        for page in reader.pages[:20]:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"PDF text extraction icin pypdf gerekli veya PDF okunamadi: {exc}",
        }

    text_path = output_dir / "pdf_text.txt"
    text_path.write_text(text, encoding="utf-8")
    return {
        "ok": True,
        "path": str(local_path),
        "text_path": str(text_path),
        "char_count": len(text),
        "text_excerpt": _limit(text, 3000),
    }


def _build_marketing_notes(metadata: dict[str, Any], transcript: dict[str, Any] | None) -> list[str]:
    if metadata.get("error"):
        return [
            "Metadata sinirli alindi; Instagram icin export cookie dosyasini yenilemek veya acik izinle browser cookie fallback'i kullanmak gerekir."
        ]

    title = str(metadata.get("title") or "")
    description = str(metadata.get("description") or "")
    source_type = str(metadata.get("source_type") or "")
    text = f"{title}\n{description}".lower()
    notes: list[str] = []

    if any(word in text for word in ("comment", "yorum", "dm", "link", "free", "ucretsiz", "prompt")):
        notes.append("CTA/lead magnet sinyali var; yorum veya DM tetikleyici olarak incelenmeli.")
    if any(word in text for word in ("ai", "agent", "automation", "codex", "claude", "jarvis")):
        notes.append("AI/otomasyon positioning'i var; Jarvis icerik kumesine alinabilir.")
    if metadata.get("view_count") or metadata.get("like_count"):
        notes.append("Performans metrikleri metadata icinde geldi; benchmark tablosuna yazilabilir.")
    if transcript and transcript.get("ok"):
        notes.append("Transcript bulundu; senaryo ve hook analizi icin metin hazir.")
    elif source_type.startswith("instagram"):
        notes.append("Instagram tarafinda transcript yoksa video indirip gorsel/konusma analizi ikinci asama olmalı.")

    if not notes:
        notes.append("Metadata alindi; derin icerik analizi icin caption/transcript veya video dosyasi gerekir.")
    return notes


def _build_report(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    transcript = payload.get("transcript") if isinstance(payload.get("transcript"), dict) else None
    files = payload.get("files") if isinstance(payload.get("files"), dict) else {}
    notes = payload.get("analysis_notes") if isinstance(payload.get("analysis_notes"), list) else []

    metric_bits = []
    for label, key in (
        ("Izlenme", "view_count"),
        ("Like", "like_count"),
        ("Yorum", "comment_count"),
        ("Paylasim", "repost_count"),
    ):
        value = metadata.get(key)
        if value not in (None, ""):
            metric_bits.append(f"{label}: {value}")

    lines = [
        "# Jarvis Media Intake",
        "",
        f"Kaynak: {metadata.get('source_type') or payload.get('source_type')}",
        f"URL: {metadata.get('url') or payload.get('url')}",
        f"Baslik: {metadata.get('title') or '-'}",
        f"Uretici: {metadata.get('uploader') or '-'}",
    ]
    if metadata.get("duration_seconds") not in (None, ""):
        lines.append(f"Sure: {metadata.get('duration_seconds')} sn")
    if metric_bits:
        lines.append("Metrikler: " + " | ".join(metric_bits))

    description = str(metadata.get("description") or "").strip()
    if description:
        lines.extend(["", "## Caption / Aciklama", _limit(description, 2200)])

    if transcript and transcript.get("ok"):
        lines.extend(["", "## Transcript", _limit(str(transcript.get("summary") or transcript.get("transcript") or ""), 2200)])

    if notes:
        lines.extend(["", "## Jarvis Analiz Notlari"])
        lines.extend(f"- {note}" for note in notes)

    if files:
        lines.extend(["", "## Kayitlar"])
        for key, value in files.items():
            if value:
                lines.append(f"- {key}: {value}")

    lines.append("")
    return "\n".join(lines)


class MediaIntakeSkill:
    def __init__(
        self,
        output_root: str | Path = DEFAULT_OUTPUT_ROOT,
        cookie_file: str | Path | None = None,
        cookies_from_browser: str | None = None,
        extractor: Callable[[str, bool, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.output_root = Path(output_root)
        self.cookie_file = Path(cookie_file).expanduser() if cookie_file else None
        self.cookies_from_browser = (
            str(cookies_from_browser or os.environ.get("JARVIS_YTDLP_COOKIES_FROM_BROWSER") or "").strip()
            or None
        )
        self.extractor = extractor

    def analyze_url(
        self,
        url_or_text: str,
        *,
        download: bool = False,
        write_wiki: bool = True,
    ) -> dict[str, Any]:
        url = extract_first_url(url_or_text) or str(url_or_text or "").strip()
        if not url:
            return {"ok": False, "error": "URL bulunamadi"}

        source_type = detect_source_type(url)
        output_dir = self.output_root / f"{_now_stamp()}_{_slugify(url, source_type)}"
        output_dir.mkdir(parents=True, exist_ok=True)

        payload: dict[str, Any] = {
            "ok": True,
            "url": url,
            "source_type": source_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {},
        }

        if source_type == "pdf":
            pdf_result = _extract_pdf_text(url, output_dir)
            payload["pdf"] = pdf_result
            metadata = {
                "source_type": source_type,
                "url": url,
                "title": Path(urlparse(url).path).name or "PDF kaynak",
                "description": pdf_result.get("text_excerpt", "") if pdf_result.get("ok") else pdf_result.get("error", ""),
            }
            payload["metadata"] = metadata
            payload["analysis_notes"] = ["PDF Jarvis kaynak paketine alindi; wiki/notebook benzeri okuma icin hazir."]
            if pdf_result.get("text_path"):
                payload["files"]["text_path"] = pdf_result["text_path"]
        else:
            metadata = self._extract_video_metadata(url, source_type, output_dir, download=download)
            payload["metadata"] = metadata
            if source_type == "youtube":
                payload["transcript"] = _youtube_transcript(url)
            payload["analysis_notes"] = _build_marketing_notes(metadata, payload.get("transcript"))

        metadata_path = output_dir / "metadata.json"
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["files"]["metadata_path"] = str(metadata_path)

        report = _build_report(payload)
        report_path = output_dir / "report.md"
        report_path.write_text(report, encoding="utf-8")
        payload["files"]["report_path"] = str(report_path)
        payload["report"] = report

        if write_wiki:
            wiki_result = self._write_wiki_note(payload, report)
            if wiki_result:
                payload["wiki"] = wiki_result

        return payload

    def _extract_video_metadata(
        self,
        url: str,
        source_type: str,
        output_dir: Path,
        *,
        download: bool,
    ) -> dict[str, Any]:
        cookie_file = self.cookie_file if self.cookie_file and self.cookie_file.exists() else find_cookie_file(url)
        options = _build_ytdlp_options(
            url=url,
            output_dir=output_dir,
            download=download,
            cookie_file=cookie_file,
            cookies_from_browser=self.cookies_from_browser,
        )

        try:
            if self.extractor is not None:
                raw_info = self.extractor(url, download, options)
            else:
                import yt_dlp

                with yt_dlp.YoutubeDL(options) as ydl:
                    raw_info = ydl.extract_info(url, download=download)
            if not isinstance(raw_info, dict):
                raise RuntimeError("yt-dlp bos sonuc dondu")
            metadata = _normalize_ytdlp_info(raw_info, url, source_type)
            if download:
                requested = raw_info.get("requested_downloads")
                if isinstance(requested, list) and requested:
                    filepath = requested[0].get("filepath")
                    if filepath:
                        metadata["downloaded_media_path"] = filepath
            return metadata
        except Exception as exc:  # noqa: BLE001
            return {
                "source_type": source_type,
                "url": url,
                "title": "Metadata alinamadi",
                "description": str(exc),
                "error": str(exc),
            }

    def _write_wiki_note(self, payload: dict[str, Any], report: str) -> dict[str, Any] | None:
        try:
            try:
                from server.skills.wiki_auto_writer import write_wiki_page
            except Exception:
                from wiki_auto_writer import write_wiki_page  # type: ignore

            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            title = f"Media Intake - {metadata.get('title') or payload.get('source_type')}"
            return write_wiki_page(
                title=title,
                content=report,
                linked_personas=["buse", "eren", "sabrican"],
                source="media_intake",
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}


def format_media_intake_response(result: dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return f"Media intake sonucu: {result}"
    if not result.get("ok"):
        return f"Media intake hatasi: {result.get('error') or 'bilinmeyen hata'}"

    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    files = result.get("files") if isinstance(result.get("files"), dict) else {}
    notes = result.get("analysis_notes") if isinstance(result.get("analysis_notes"), list) else []
    transcript = result.get("transcript") if isinstance(result.get("transcript"), dict) else {}

    lines = [
        "Video/kaynak Jarvis'e alindi.",
        f"Kaynak: {metadata.get('source_type') or result.get('source_type')}",
        f"Baslik: {metadata.get('title') or '-'}",
    ]
    if metadata.get("uploader"):
        lines.append(f"Uretici: {metadata.get('uploader')}")
    metrics = []
    for label, key in (("izlenme", "view_count"), ("like", "like_count"), ("yorum", "comment_count")):
        value = metadata.get(key)
        if value not in (None, ""):
            metrics.append(f"{label}: {value}")
    if metrics:
        lines.append("Metrikler: " + ", ".join(metrics))
    if metadata.get("error"):
        lines.append(f"Not: metadata sinirli alindi ({str(metadata.get('error'))[:120]})")
    if transcript and transcript.get("ok"):
        lines.append(f"Transcript: hazir ({transcript.get('char_count', 0)} karakter)")
    if notes:
        lines.append("Analiz: " + str(notes[0]))
    if files.get("report_path"):
        lines.append(f"Rapor: {files['report_path']}")
    if isinstance(result.get("wiki"), dict) and result["wiki"].get("path"):
        lines.append(f"Wiki: {result['wiki']['path']}")
    return "\n".join(lines)


def check_environment() -> dict[str, Any]:
    return {
        "ok": True,
        "yt_dlp_available": _ytdlp_available(),
        "default_output_root": str(DEFAULT_OUTPUT_ROOT),
        "instagram_cookie_file_found": bool(find_cookie_file("https://www.instagram.com/reel/test/")),
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jarvis media intake")
    parser.add_argument("url", nargs="?", help="Instagram/YouTube/PDF URL")
    parser.add_argument("--download", action="store_true", help="Video dosyasini da indir")
    parser.add_argument("--cookies-from-browser", help="yt-dlp browser cookie kaynagi, ornek: chrome")
    parser.add_argument("--no-wiki", action="store_true", help="Wiki notu yazma")
    parser.add_argument("--check", action="store_true", help="Ortam kontrolu")
    args = parser.parse_args(argv)

    if args.check:
        print(json.dumps(check_environment(), ensure_ascii=False, indent=2))
        return 0
    if not args.url:
        print("Kullanim: python -m server.skills.media_intake_skill <url> [--download]")
        return 2

    result = MediaIntakeSkill(cookies_from_browser=args.cookies_from_browser).analyze_url(
        args.url,
        download=args.download,
        write_wiki=not args.no_wiki,
    )
    print(format_media_intake_response(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
