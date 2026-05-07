from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env_utils import load_env_files
from server.model_router import build_model_router
from server.runtime_config import load_runtime_config


DEFAULT_OUTPUT_ROOT = ROOT / "temp_videos" / "jarvis-analysis"
WHISPER_MODEL_NAME = os.environ.get("WHISPER_MODEL", "base")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download a web video with yt-dlp and analyze it through Jarvis "
            "using metadata, transcript, frames, and LLM synthesis."
        )
    )
    parser.add_argument("urls", nargs="+", help="Video URLs supported by yt-dlp")
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help=f"Root output directory (default: {DEFAULT_OUTPUT_ROOT})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Seconds between frame captures (default: 2)",
    )
    parser.add_argument(
        "--scene-detect",
        action="store_true",
        help="Also capture frames on scene changes",
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=0.28,
        help="Scene detection threshold (default: 0.28)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=8,
        help="Maximum number of frames to send to Gemini vision (default: 8)",
    )
    parser.add_argument(
        "--transcript-max-chars",
        type=int,
        default=12000,
        help="Maximum transcript chars included in final Jarvis prompt (default: 12000)",
    )
    parser.add_argument(
        "--route",
        default="reasoning",
        help="Jarvis model-router route for the final synthesis (default: reasoning)",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=1800,
        help="Max tokens for the final analysis (default: 1800)",
    )
    parser.add_argument(
        "--keep-video",
        action="store_true",
        help="Keep the downloaded mp4 after analysis",
    )
    parser.add_argument(
        "--skip-frame-vision",
        action="store_true",
        help="Skip Gemini frame-level analysis",
    )
    return parser.parse_args()


def ensure_command(name: str) -> None:
    from shutil import which

    if which(name):
        return
    raise RuntimeError(f"Required command not found on PATH: {name}")


def run_command(cmd: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._-")
    return slug or "video"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_metadata(url: str) -> dict[str, Any]:
    result = run_command(
        ["yt-dlp", "--dump-json", "--no-download", "--no-playlist", url],
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "yt-dlp metadata failed")
    return json.loads(result.stdout)


def download_video(url: str, output_dir: Path) -> Path:
    output_template = str(output_dir / "video.%(ext)s")
    result = run_command(
        [
            "yt-dlp",
            "-f",
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            output_template,
            "--no-playlist",
            url,
        ],
        timeout=900,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "yt-dlp download failed")

    candidates = sorted(output_dir.glob("video.*"))
    for path in candidates:
        if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}:
            return path
    raise RuntimeError("Video download finished but no output file was found")


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    audio_path = output_dir / "audio.wav"
    result = run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(audio_path),
        ],
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[:500] or "ffmpeg audio extraction failed")
    return audio_path


def transcribe_audio(audio_path: Path) -> dict[str, Any]:
    from faster_whisper import WhisperModel

    model = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    items: list[dict[str, Any]] = []
    texts: list[str] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        texts.append(text)
        items.append(
            {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text,
            }
        )
    return {
        "language": getattr(info, "language", ""),
        "language_probability": getattr(info, "language_probability", None),
        "segments": items,
        "text": " ".join(texts).strip(),
    }


def extract_interval_frames(video_path: Path, output_dir: Path, interval: int) -> list[Path]:
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps=1/{interval}",
            "-q:v",
            "2",
            str(frames_dir / "frame_%04d.png"),
        ],
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[:500] or "ffmpeg interval frame extraction failed")
    return sorted(frames_dir.glob("frame_*.png"))


def extract_scene_frames(video_path: Path, output_dir: Path, threshold: float) -> list[Path]:
    frames_dir = output_dir / "frames_scene"
    frames_dir.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-vsync",
            "vfr",
            "-q:v",
            "2",
            str(frames_dir / "scene_%04d.png"),
        ],
        timeout=600,
    )
    if result.returncode != 0:
        return []
    return sorted(frames_dir.glob("scene_*.png"))


def evenly_sample(items: list[Path], max_items: int) -> list[Path]:
    if len(items) <= max_items:
        return items
    if max_items <= 1:
        return items[:1]
    sampled: list[Path] = []
    step = (len(items) - 1) / (max_items - 1)
    for index in range(max_items):
        sampled.append(items[math.floor(index * step)])
    deduped: list[Path] = []
    seen: set[Path] = set()
    for item in sampled:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def select_frames(interval_frames: list[Path], scene_frames: list[Path], max_frames: int) -> list[Path]:
    return evenly_sample(scene_frames + interval_frames, max_frames)


def build_router():
    runtime = load_runtime_config(ROOT, ROOT / "server")
    return build_model_router(
        root_dir=ROOT,
        default_ollama_url=runtime.ollama_url,
        request_timeout=runtime.request_timeout,
    )


def build_frame_analyzer():
    import google.generativeai as genai

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is required for frame analysis")
    genai.configure(api_key=api_key)
    return {
        "genai": genai,
        "model": genai.GenerativeModel("gemini-2.5-flash"),
    }


def analyze_frames(selected_frames: list[Path], skip_frame_vision: bool) -> list[dict[str, Any]]:
    if skip_frame_vision or not selected_frames:
        return []

    analyzer = build_frame_analyzer()
    uploads = [
        analyzer["genai"].upload_file(str(frame_path), mime_type="image/png")
        for frame_path in selected_frames
    ]
    frame_names = [frame_path.name for frame_path in selected_frames]
    prompt = (
        "You will receive multiple frames from the same short-form social video. "
        "Analyze each frame in Turkish. Return exactly one line per frame, in the same order, "
        "using this format only:\n"
        "frame_name || concise analysis\n\n"
        f"Frame order: {', '.join(frame_names)}"
    )
    try:
        response = analyzer["model"].generate_content([prompt, *uploads])
        raw_text = (response.text or "").strip() if response else ""
    finally:
        for uploaded in uploads:
            try:
                analyzer["genai"].delete_file(uploaded.name)
            except Exception:
                pass

    parsed: dict[str, str] = {}
    for line in raw_text.splitlines():
        if "||" not in line:
            continue
        left, right = line.split("||", 1)
        parsed[left.strip()] = right.strip()

    results: list[dict[str, Any]] = []
    for frame_path in selected_frames:
        results.append(
            {
                "frame": str(frame_path),
                "analysis": parsed.get(frame_path.name, raw_text),
            }
        )
    return results


def summarize_frame_analyses(frame_analyses: list[dict[str, Any]]) -> str:
    if not frame_analyses:
        return "No frame analyses were generated."
    lines = []
    for item in frame_analyses:
        frame_name = Path(item["frame"]).name
        lines.append(f"- {frame_name}: {item['analysis']}")
    return "\n".join(lines)


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[truncated]"


def synthesize_with_jarvis(
    router: Any,
    *,
    url: str,
    metadata: dict[str, Any],
    transcript_text: str,
    transcript_segments: list[dict[str, Any]],
    frame_analyses: list[dict[str, Any]],
    route_name: str,
    max_output_tokens: int,
) -> tuple[str, dict[str, Any]]:
    comments = metadata.get("comments") or []
    description = metadata.get("description") or ""
    comment_text = "\n".join(
        f"- {item.get('author', 'unknown')}: {item.get('text', '').strip()}"
        for item in comments[:5]
        if item.get("text")
    )
    segment_text = "\n".join(
        f"- {item['start']:.2f}s-{item['end']:.2f}s: {item['text']}"
        for item in transcript_segments[:20]
    )

    system_prompt = (
        "Sen Jarvis icin calisan bir video analiz ajanisin. "
        "Sadece verilen metadata, transkript ve frame gozlemlerine dayan. "
        "Kanitlanmayan seyi kesinmis gibi yazma. Cevabi Turkce ve Markdown ver."
    )
    user_prompt = f"""
Video URL: {url}
Baslik: {metadata.get('title', '')}
Kanal: {metadata.get('channel') or metadata.get('uploader') or ''}
Sure: {metadata.get('duration', 0)} saniye
Açiklama: {description}

Top comment / sinyal:
{comment_text or 'No comment data'}

Transkript segmentleri:
{segment_text or 'No transcript segments'}

Tam transkript:
{transcript_text or 'No spoken transcript found'}

Frame gozlemleri:
{summarize_frame_analyses(frame_analyses)}

Bu reel icin su basliklarla net bir analiz yaz:
1. Reel Ozeti
2. Zaman Cizelgesi
3. Ana Mesaj ve Vaat
4. Gorsel Akis ve Gosterilen Araclar
5. Icerik Formulu
6. Guclu Yanlar
7. Riskli veya Belirsiz Noktalar
8. Bunu yeniden uretmek isteyen biri icin adimlar
""".strip()

    response, trace = router.chat(
        route_name=route_name,
        primary_model="",
        fallback_model=None,
        extra_fallback_models=None,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
        max_tokens=max_output_tokens,
        num_ctx=32768,
    )
    return response, trace


def analyze_url(
    router: Any,
    *,
    url: str,
    output_root: Path,
    interval: int,
    scene_detect: bool,
    scene_threshold: float,
    max_frames: int,
    transcript_max_chars: int,
    route: str,
    max_output_tokens: int,
    keep_video: bool,
    skip_frame_vision: bool,
) -> dict[str, Any]:
    metadata = fetch_metadata(url)
    video_id = safe_slug(str(metadata.get("id") or metadata.get("display_id") or metadata.get("title") or "video"))
    output_dir = output_root / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    write_json(output_dir / "metadata.json", metadata)

    print(f"[jarvis] Downloading {video_id} ...")
    video_path = download_video(url, output_dir)
    audio_path = extract_audio(video_path, output_dir)
    transcript = transcribe_audio(audio_path)
    write_json(output_dir / "transcript.json", transcript)

    interval_frames = extract_interval_frames(video_path, output_dir, interval)
    scene_frames = extract_scene_frames(video_path, output_dir, scene_threshold) if scene_detect else []
    selected_frames = select_frames(interval_frames, scene_frames, max_frames)
    frame_analyses = analyze_frames(selected_frames, skip_frame_vision=skip_frame_vision)
    write_json(output_dir / "frame_analyses.json", frame_analyses)

    transcript_text = truncate_text(transcript.get("text", ""), transcript_max_chars)
    final_analysis, trace = synthesize_with_jarvis(
        router,
        url=url,
        metadata=metadata,
        transcript_text=transcript_text,
        transcript_segments=transcript.get("segments", []),
        frame_analyses=frame_analyses,
        route_name=route,
        max_output_tokens=max_output_tokens,
    )

    analysis_path = output_dir / "jarvis_analysis.md"
    analysis_path.write_text(final_analysis, encoding="utf-8")
    write_json(output_dir / "jarvis_route_trace.json", trace)

    summary = {
        "url": url,
        "video_id": video_id,
        "title": metadata.get("title", ""),
        "duration_seconds": metadata.get("duration", 0),
        "output_dir": str(output_dir),
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "frame_count": len(interval_frames) + len(scene_frames),
        "selected_frame_count": len(selected_frames),
        "analysis_path": str(analysis_path),
        "route": route,
    }
    write_json(output_dir / "run_summary.json", summary)

    if not keep_video:
        video_path.unlink(missing_ok=True)

    return summary


def main() -> int:
    args = parse_args()
    load_env_files(ROOT / ".env", ROOT / "server" / ".env")
    ensure_command("yt-dlp")
    ensure_command("ffmpeg")

    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    router = build_router()

    results: list[dict[str, Any]] = []
    for url in args.urls:
        results.append(
            analyze_url(
                router,
                url=url,
                output_root=output_root,
                interval=args.interval,
                scene_detect=args.scene_detect,
                scene_threshold=args.scene_threshold,
                max_frames=args.max_frames,
                transcript_max_chars=args.transcript_max_chars,
                route=args.route,
                max_output_tokens=args.max_output_tokens,
                keep_video=args.keep_video,
                skip_frame_vision=args.skip_frame_vision,
            )
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
