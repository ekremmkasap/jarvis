from __future__ import annotations

import re
from typing import Any

try:
    from server.openclaw_bridge import normalize_dream_phase, read_dream_report
except Exception:
    from openclaw_bridge import normalize_dream_phase, read_dream_report  # type: ignore

try:
    from server.persona_manager import get_active_persona, recall, remember, resolve_persona_name
except Exception:
    from persona_manager import (  # type: ignore
        get_active_persona,
        recall,
        remember,
        resolve_persona_name,
    )


THEME_LINE_RE = re.compile(
    r"^- Theme:\s+`?(?P<theme>[^`]+?)`?\s+kept surfacing across\s+(?P<count>\d+)\s+memories\.$"
)


def _target_persona_id(persona_id: str | None = None) -> str:
    if persona_id:
        resolved = resolve_persona_name(persona_id, include_internal=True)
        if resolved:
            return resolved
        normalized = str(persona_id).strip().lower()
        if normalized:
            return normalized

    active = get_active_persona()
    return str(active.get("id") or "jarvis").strip().lower() or "jarvis"


def parse_dream_report(report_text: str) -> dict[str, Any]:
    themes: list[dict[str, Any]] = []
    lasting_truths: list[str] = []
    section = ""

    for raw_line in str(report_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "### Reflections":
            section = "reflections"
            continue
        if line == "### Possible Lasting Truths":
            section = "truths"
            continue
        if section == "reflections":
            match = THEME_LINE_RE.match(line)
            if match:
                themes.append(
                    {
                        "theme": match.group("theme").strip(),
                        "count": int(match.group("count")),
                    }
                )
            continue
        if section == "truths" and line.startswith("- "):
            truth = line[2:].strip()
            if truth and truth.lower() != "no strong candidate truths surfaced.":
                lasting_truths.append(truth)

    return {
        "themes": themes,
        "lasting_truths": lasting_truths,
    }


def get_dream_report(phase: str = "rem") -> dict[str, Any]:
    return read_dream_report(normalize_dream_phase(phase))


def capture_dream_snapshot(persona_id: str | None = None) -> dict[str, Any]:
    target_persona = _target_persona_id(persona_id)
    report = get_dream_report("rem")
    result: dict[str, Any] = {
        "status": "ok",
        "target_persona": target_persona,
        "phase": report.get("phase") or "rem",
        "report_path": report.get("path"),
        "themes_captured": 0,
        "lasting_truths": 0,
        "memory_entries_written": 0,
        "themes": [],
    }

    if not report.get("exists"):
        result["status"] = "missing_report"
        return result

    parsed = parse_dream_report(str(report.get("content") or ""))
    memory_entries_written = 0

    for theme in parsed["themes"]:
        remember(
            target_persona,
            f"[dream-theme] {theme['theme']}: {theme['count']} kez",
        )
        memory_entries_written += 1

    for truth in parsed["lasting_truths"]:
        remember(target_persona, f"[dream-truth] {truth}")
        memory_entries_written += 1

    result["themes_captured"] = len(parsed["themes"])
    result["lasting_truths"] = len(parsed["lasting_truths"])
    result["memory_entries_written"] = memory_entries_written
    result["themes"] = [item["theme"] for item in parsed["themes"]]
    return result


def restore_from_dream(persona_id: str | None = None, top_k: int = 10) -> int:
    target_persona = _target_persona_id(persona_id)
    restored = recall(
        target_persona,
        "dream-theme dream-truth dusler rem deep light",
        top_k=top_k,
    )
    return len(restored)

