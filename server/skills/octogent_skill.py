"""
Jarvis Skill — Octogent
Optional multi-agent Claude Code orchestration runtime.
"""

from __future__ import annotations

import json

try:
    from server.octogent_bridge import (
        build_octogent_health_snapshot,
        run_octogent_cli,
        start_octogent_dashboard,
    )
except Exception:
    from octogent_bridge import (  # type: ignore
        build_octogent_health_snapshot,
        run_octogent_cli,
        start_octogent_dashboard,
    )


def _usage() -> str:
    return (
        "Kullanim: /octogent [durum|start|init|projects]\n"
        "- /octogent durum -> runtime snapshot\n"
        "- /octogent start -> dashboard/API baslat\n"
        "- /octogent init -> mevcut proje icin .octogent scaffold olustur\n"
        "- /octogent projects -> kayitli Octogent projeleri"
    )


def octogent_status() -> str:
    snapshot = build_octogent_health_snapshot()
    caps = snapshot.get("capabilities", {})
    node = snapshot.get("node", {})
    lines = [
        "Octogent durum",
        f"Durum: {snapshot.get('status', '?')}",
        f"Komut: {snapshot.get('resolved_command') or snapshot.get('command') or '-'}",
        f"Repo: {snapshot.get('repo_path', '-')} ({caps.get('repo_clone', {}).get('detail', '-')})",
        f"Node: {node.get('version') or '-'} ({caps.get('node_runtime', {}).get('detail', '-')})",
        f"pnpm: {snapshot.get('pnpm_command') or '-'} ({caps.get('package_manager', {}).get('detail', '-')})",
        f"Scaffold: {snapshot.get('project_scaffold_path', '-')} ({caps.get('project_scaffold', {}).get('detail', '-')})",
        f"API: {snapshot.get('api_base', '-')} ({caps.get('api_ready', {}).get('detail', '-')})",
        "Komutlar: /octogent start | /octogent init | /octogent projects | /octogent-health",
    ]
    if not caps.get("cli_ready", {}).get("ok"):
        lines.extend(["", "Kurulum notu:", snapshot.get("install_hint", "-")])
    return "\n".join(lines)


def run_octogent(query: str) -> str:
    payload = str(query or "").strip()
    if not payload:
        return octogent_status()

    action, _, remainder = payload.partition(" ")
    action_key = action.strip().lower()
    rest = remainder.strip()

    if action_key in {"durum", "status", "health"}:
        return octogent_status()
    if action_key in {"yardim", "help"}:
        return _usage()
    if action_key in {"start", "baslat"}:
        result = start_octogent_dashboard(no_open=True)
        if result.get("ok"):
            return (
                "Octogent baslatildi\n"
                f"PID: {result.get('pid')}\n"
                f"UI: {result.get('ui_url')}\n"
                f"Log: {result.get('log_path')}"
            )
        return "Octogent baslatilamadi\n" + json.dumps(result, ensure_ascii=False, indent=2)[:1400]
    if action_key == "init":
        result = run_octogent_cli(["init"] + ([rest] if rest else []), timeout=45)
        label = "ok" if result.get("ok") else "hata"
        return f"Octogent init ({label})\n" + json.dumps(result, ensure_ascii=False, indent=2)[:1400]
    if action_key in {"projects", "projeler"}:
        result = run_octogent_cli(["projects"], timeout=20)
        label = "ok" if result.get("ok") else "hata"
        return f"Octogent projects ({label})\n" + json.dumps(result, ensure_ascii=False, indent=2)[:1400]
    return _usage()
