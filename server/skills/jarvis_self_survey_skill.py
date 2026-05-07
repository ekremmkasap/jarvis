"""Jarvis self-survey: skill envanteri, scheduler, MCP, OpenClaw subagent snapshot.

Autonomous agent visibility: kendi kapasitesini tarar ve JARVIS-Brain vault'a yazar.
Command: /jarvis-durum
"""
from __future__ import annotations

import ast
import json
import logging
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("jarvis_self_survey")

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
SKILLS_DIR = BASE_DIR / "skills"
VAULT_ROOT = Path(os.getenv("JARVIS_BRAIN_VAULT", r"C:/Users/sergen/Desktop/JARVIS-Brain"))


def _extract_docstring(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return ""
    doc = ast.get_docstring(tree) or ""
    first = doc.strip().splitlines()[0] if doc else ""
    return first[:160]


def survey_skills() -> list[dict]:
    items = []
    if not SKILLS_DIR.exists():
        return items
    for p in sorted(SKILLS_DIR.glob("*.py")):
        if p.name.startswith("_"):
            continue
        items.append({
            "name": p.stem,
            "size_kb": round(p.stat().st_size / 1024, 1),
            "doc": _extract_docstring(p) or "(docstring yok)",
        })
    return items


def survey_schedulers() -> dict[str, Any]:
    state = {"research": "unknown", "instagram": "unknown", "opportunity": "unknown"}
    try:
        from skills import research_scheduler_skill as rs
        state["research"] = rs.get_scheduler_status()
    except Exception as exc:
        state["research"] = f"error: {exc}"
    try:
        from skills import instagram_skill as ig
        if hasattr(ig, "get_scheduler_status"):
            state["instagram"] = ig.get_scheduler_status()
    except Exception as exc:
        state["instagram"] = f"error: {exc}"
    return state


def survey_mcp() -> list[str]:
    cfg = Path.home() / ".claude.json"
    if not cfg.exists():
        return []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    projects = data.get("projects", {})
    project_key = str(REPO_ROOT).replace("\\", "/")
    for k, v in projects.items():
        if k.replace("\\", "/").lower() == project_key.lower():
            return sorted((v.get("mcpServers") or {}).keys())
    return []


def survey_openclaw() -> list[str]:
    try:
        from skills.sabrican_subagent_runner import SUBAGENT_REGISTRY  # type: ignore
        return sorted(SUBAGENT_REGISTRY.keys())
    except Exception:
        return []


def survey_providers() -> list[str]:
    cfg = REPO_ROOT / "config" / "model_router.yml"
    if not cfg.exists():
        return []
    providers: list[str] = []
    try:
        for line in cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("- provider:") or stripped.startswith("provider:"):
                value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                if value and value not in providers:
                    providers.append(value)
    except OSError:
        return []
    return providers


def build_snapshot() -> dict[str, Any]:
    skills = survey_skills()
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "repo_root": str(REPO_ROOT),
        "counts": {
            "skills": len(skills),
            "mcp_servers": len(survey_mcp()),
            "openclaw_subagents": len(survey_openclaw()),
        },
        "skills": skills,
        "schedulers": survey_schedulers(),
        "mcp_servers": survey_mcp(),
        "openclaw_subagents": survey_openclaw(),
        "providers": survey_providers(),
    }


def write_vault_snapshot(snapshot: dict[str, Any]) -> Path | None:
    if not VAULT_ROOT.exists():
        return None
    target_dir = VAULT_ROOT / "04-Dev-Log"
    target_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    target = target_dir / f"self-survey-{date_str}.md"
    lines = [
        "---",
        "tags: [self-survey, autonomy, snapshot]",
        f"date: {date_str}",
        "---",
        "",
        f"# Jarvis Self-Survey — {snapshot['timestamp']}",
        "",
        f"- Platform: `{snapshot['platform']}`",
        f"- Skills: **{snapshot['counts']['skills']}**",
        f"- MCP servers: **{snapshot['counts']['mcp_servers']}**",
        f"- OpenClaw sub-agents: **{snapshot['counts']['openclaw_subagents']}**",
        f"- Providers: {', '.join(snapshot['providers']) or '—'}",
        "",
        "## Scheduler Durumu",
        "```json",
        json.dumps(snapshot["schedulers"], ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## MCP Servers",
    ]
    if snapshot["mcp_servers"]:
        for m in snapshot["mcp_servers"]:
            lines.append(f"- {m}")
    else:
        lines.append("_Yok_")
    lines.append("")
    lines.append("## OpenClaw Sub-agents")
    if snapshot["openclaw_subagents"]:
        for s in snapshot["openclaw_subagents"]:
            lines.append(f"- {s}")
    else:
        lines.append("_Yok_")
    lines.append("")
    lines.append("## Skills Envanteri")
    lines.append("")
    lines.append("| Skill | KB | Açıklama |")
    lines.append("|---|---|---|")
    for sk in snapshot["skills"]:
        doc = sk["doc"].replace("|", "\\|")
        lines.append(f"| `{sk['name']}` | {sk['size_kb']} | {doc} |")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def format_brief(snapshot: dict[str, Any]) -> str:
    c = snapshot["counts"]
    sched = snapshot["schedulers"].get("research")
    sched_running = False
    if isinstance(sched, dict):
        sched_running = bool(sched.get("running"))
    lines = [
        "🧭 Jarvis Self-Survey",
        f"• Skills: {c['skills']}",
        f"• MCP: {c['mcp_servers']} ({', '.join(snapshot['mcp_servers']) or '—'})",
        f"• OpenClaw sub-agents: {c['openclaw_subagents']}",
        f"• Providers: {', '.join(snapshot['providers']) or '—'}",
        f"• Research scheduler: {'çalışıyor ✅' if sched_running else 'kapalı ⏸'}",
    ]
    return "\n".join(lines)


def run_survey() -> dict[str, Any]:
    snap = build_snapshot()
    target = write_vault_snapshot(snap)
    return {
        "ok": True,
        "brief": format_brief(snap),
        "vault_path": str(target) if target else None,
        "snapshot": snap,
    }


__all__ = ["run_survey", "build_snapshot", "format_brief"]
