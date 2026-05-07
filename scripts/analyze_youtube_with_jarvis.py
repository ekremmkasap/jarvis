from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env_utils import load_env_files
from server.model_router import build_model_router
from server.runtime_config import load_runtime_config


EXTRACTOR_PATH = (
    ROOT / "server" / "agent_prompts" / "wshobson" / "tools" / "yt-design-extractor.py"
)
DEFAULT_OUTPUT_ROOT = ROOT / "temp_videos" / "jarvis-analysis"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download one or more YouTube videos with yt-dlp and analyze them "
            "through Jarvis components."
        )
    )
    parser.add_argument("urls", nargs="+", help="YouTube video URLs or IDs")
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help=f"Root output directory (default: {DEFAULT_OUTPUT_ROOT})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=45,
        help="Seconds between frame captures (default: 45)",
    )
    parser.add_argument(
        "--scene-detect",
        action="store_true",
        help="Also extract scene-change frames",
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
        default=40000,
        help="Max chars from extracted reference sent to Jarvis LLM (default: 40000)",
    )
    parser.add_argument(
        "--route",
        default="",
        help="Force a model-router route, e.g. reasoning or long",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=1800,
        help="Max tokens for final Jarvis analysis (default: 1800)",
    )
    parser.add_argument(
        "--skip-frame-vision",
        action="store_true",
        help="Skip Gemini frame analysis",
    )
    parser.add_argument(
        "--skip-final-analysis",
        action="store_true",
        help="Skip final Jarvis synthesis and only produce intermediate artifacts",
    )
    parser.add_argument(
        "--delete-video",
        action="store_true",
        help="Delete the downloaded video after frame extraction",
    )
    return parser.parse_args()


def load_extractor_module():
    spec = importlib.util.spec_from_file_location("yt_design_extractor", EXTRACTOR_PATH)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load extractor module from {EXTRACTOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def choose_route(explicit_route: str, reference_text: str) -> str:
    if explicit_route.strip():
        return explicit_route.strip()
    return "long" if len(reference_text) > 20000 else "reasoning"


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
    preferred = scene_frames + interval_frames
    return evenly_sample(preferred, max_frames)


def build_router():
    runtime = load_runtime_config(ROOT, ROOT / "server")
    return build_model_router(
        root_dir=ROOT,
        default_ollama_url=runtime.ollama_url,
        request_timeout=runtime.request_timeout,
    )


def build_frame_analyzer():
    from server.agents.vision_analyzer import VisionAnalyzer

    return VisionAnalyzer()


def analyze_frame(frame_path: Path, analyzer: Any) -> dict[str, Any]:
    image_data = analyzer._load_image_data(image_path=str(frame_path))
    prompt = (
        "Analyze this video frame in Turkish. Focus on what is visually happening, "
        "what kind of scene this is, notable text or UI if visible, camera/composition "
        "cues, and why this frame matters inside the larger video. Keep it concise."
    )
    response = analyzer.model.generate_content([prompt, image_data])
    text = (response.text or "").strip() if response else ""
    return {
        "frame": str(frame_path),
        "analysis": text,
    }


def analyze_frames(selected_frames: list[Path], skip_frame_vision: bool) -> list[dict[str, Any]]:
    if skip_frame_vision or not selected_frames:
        return []

    analyzer = build_frame_analyzer()
    results: list[dict[str, Any]] = []
    for frame_path in selected_frames:
        results.append(analyze_frame(frame_path, analyzer))
    return results


def summarize_frame_analyses(frame_analyses: list[dict[str, Any]]) -> str:
    if not frame_analyses:
        return "No frame analyses were generated."
    lines: list[str] = []
    for item in frame_analyses:
        lines.append(f"- {Path(item['frame']).name}: {item['analysis']}")
    return "\n".join(lines)


def synthesize_with_jarvis(
    router: Any,
    *,
    url: str,
    metadata: dict[str, Any],
    reference_text: str,
    frame_analyses: list[dict[str, Any]],
    route_name: str,
    max_output_tokens: int,
) -> tuple[str, dict[str, Any]]:
    title = metadata.get("title", "Unknown title")
    channel = metadata.get("channel") or metadata.get("uploader") or "Unknown channel"
    duration = metadata.get("duration") or 0
    chapters = metadata.get("chapters") or []

    system_prompt = (
        "Sen Jarvis video analiz ajanisin. Sadece verilen metadata, transcript ve "
        "gorsel gozlemlerden yararlan. Bilmedigin bir seyi uydurma. Cevabi Turkce "
        "ve Markdown olarak ver."
    )
    user_prompt = f"""
Video URL: {url}
Baslik: {title}
Kanal: {channel}
Sure (saniye): {duration}
Bolum sayisi: {len(chapters)}

Asagidaki veriye dayanarak detayli ama oz bir video analizi cikar.

Zorunlu basliklar:
1. Genel Ozet
2. Ana Temalar
3. Anlati ve Aks
4. Gorsel Dil ve Kurgu
5. Hedef Kitle ve Amac
6. Dikkat Ceken Anlar
7. Uygulanabilir Icgoruler
8. Belirsiz Noktalar

Frame gozlemleri:
{summarize_frame_analyses(frame_analyses)}

Extracted reference:
{reference_text}
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
    extractor: Any,
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
    skip_frame_vision: bool,
    skip_final_analysis: bool,
    delete_video: bool,
) -> dict[str, Any]:
    video_id = extractor.extract_video_id(url)
    video_dir = output_root / video_id
    video_dir.mkdir(parents=True, exist_ok=True)

    metadata = extractor.get_video_metadata(url)
    transcript_entries = extractor.get_transcript(video_id)

    write_json(video_dir / "metadata.json", metadata)
    write_json(video_dir / "transcript.json", transcript_entries or [])

    print(f"[jarvis] Downloading video for {video_id} ...")
    video_path = extractor.download_video(url, video_dir)
    interval_frames = extractor.extract_frames_interval(video_path, video_dir, interval=interval)
    scene_frames: list[Path] = []
    if scene_detect:
        scene_frames = extractor.extract_frames_scene(video_path, video_dir, threshold=scene_threshold)

    if delete_video:
        video_path.unlink(missing_ok=True)

    reference_path = extractor.build_markdown(
        metadata,
        transcript_entries,
        interval_frames,
        scene_frames,
        video_dir,
        interval,
    )

    selected_frames = select_frames(interval_frames, scene_frames, max_frames)
    frame_analyses = analyze_frames(selected_frames, skip_frame_vision=skip_frame_vision)
    write_json(video_dir / "frame_analyses.json", frame_analyses)

    reference_text = reference_path.read_text(encoding="utf-8", errors="replace")
    if len(reference_text) > transcript_max_chars:
        reference_text = reference_text[:transcript_max_chars] + "\n\n[truncated]"

    final_analysis_path = video_dir / "jarvis_analysis.md"
    trace_path = video_dir / "jarvis_route_trace.json"
    chosen_route = choose_route(route, reference_text)

    llm_trace: dict[str, Any] | None = None
    if skip_final_analysis:
        final_analysis = "Final Jarvis synthesis was skipped."
    else:
        print(f"[jarvis] Running final synthesis for {video_id} via route '{chosen_route}' ...")
        final_analysis, llm_trace = synthesize_with_jarvis(
            router,
            url=url,
            metadata=metadata,
            reference_text=reference_text,
            frame_analyses=frame_analyses,
            route_name=chosen_route,
            max_output_tokens=max_output_tokens,
        )
        write_json(trace_path, llm_trace)

    final_analysis_path.write_text(final_analysis, encoding="utf-8")

    result = {
        "url": url,
        "video_id": video_id,
        "title": metadata.get("title", ""),
        "output_dir": str(video_dir),
        "video_path": str(video_path) if video_path.exists() else "",
        "reference_path": str(reference_path),
        "frame_count": len(interval_frames) + len(scene_frames),
        "selected_frame_count": len(selected_frames),
        "final_analysis_path": str(final_analysis_path),
        "route": chosen_route,
        "trace_path": str(trace_path) if llm_trace else "",
    }
    write_json(video_dir / "run_summary.json", result)
    return result


def main() -> int:
    args = parse_args()
    load_env_files(ROOT / ".env", ROOT / "server" / ".env")

    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    extractor = load_extractor_module()
    router = build_router()

    results: list[dict[str, Any]] = []
    for url in args.urls:
        results.append(
            analyze_url(
                extractor,
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
                skip_frame_vision=args.skip_frame_vision,
                skip_final_analysis=args.skip_final_analysis,
                delete_video=args.delete_video,
            )
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
