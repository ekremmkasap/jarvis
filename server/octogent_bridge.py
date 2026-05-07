#!/usr/bin/env python3
"""
Octogent <-> Jarvis bridge helpers.

This is an optional secondary runtime integration. Jarvis does not depend on
Octogent being installed, but Sabrican can inspect and launch it when the
global CLI is available.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
OCTOGENT_REPO_DIR = Path(
    os.environ.get(
        "OCTOGENT_REPO_DIR",
        str(ROOT_DIR / "external-repos" / "octogent"),
    )
).resolve()
OCTOGENT_COMMAND = os.environ.get(
    "OCTOGENT_COMMAND",
    "octogent.cmd" if os.name == "nt" else "octogent",
).strip()
OCTOGENT_API_BASE = os.environ.get("OCTOGENT_API_BASE", "http://127.0.0.1:8787").strip()
OCTOGENT_OWNER_PERSONA = "sabrican"
OCTOGENT_SUB_AGENTS = (
    "tentacle_orchestrator",
    "terminal_supervisor",
    "todo_swarm_manager",
    "channel_messenger",
)
OCTOGENT_SKILL_SURFACES = (
    "tentacle_control",
    "terminal_control",
    "todo_orchestration",
    "channel_messaging",
    "monitor_feed",
)
OCTOGENT_CODEX_SUBAGENTS = (
    "workflow-orchestrator",
    "operations-manager",
    "task-distributor",
    "code-integrator",
)


def _resolve_octogent_command() -> str:
    resolved = shutil.which(OCTOGENT_COMMAND)
    if resolved:
        return resolved
    raw_path = Path(OCTOGENT_COMMAND)
    if raw_path.is_file():
        return str(raw_path)
    return ""


def _resolve_pnpm_command() -> str:
    candidates = ["pnpm.cmd", "pnpm"] if os.name == "nt" else ["pnpm"]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return ""


def _node_snapshot() -> dict[str, Any]:
    resolved = shutil.which("node")
    if not resolved:
        return {"ok": False, "detail": "node-missing", "version": ""}
    try:
        result = subprocess.run(
            [resolved, "-v"],
            capture_output=True,
            text=True,
            timeout=3,
            encoding="utf-8",
            errors="replace",
        )
        version = (result.stdout or result.stderr or "").strip()
        major = 0
        if version.startswith("v"):
            try:
                major = int(version[1:].split(".", 1)[0])
            except ValueError:
                major = 0
        return {
            "ok": major >= 22,
            "detail": "node-supported" if major >= 22 else "node-too-old",
            "version": version,
            "path": resolved,
        }
    except Exception as exc:
        return {"ok": False, "detail": f"node-check-failed:{exc}", "version": ""}


def _probe_octogent_api() -> dict[str, Any]:
    setup_url = f"{OCTOGENT_API_BASE.rstrip('/')}/api/setup"
    try:
        with urllib.request.urlopen(setup_url, timeout=1.5) as response:
            body = response.read(256).decode("utf-8", errors="replace")
            return {
                "ok": True,
                "detail": f"http-{response.status}",
                "status_code": response.status,
                "url": setup_url,
                "preview": body[:120],
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": exc.code < 500,
            "detail": f"http-{exc.code}",
            "status_code": exc.code,
            "url": setup_url,
        }
    except Exception as exc:
        return {
            "ok": False,
            "detail": f"api-unreachable:{exc}",
            "status_code": None,
            "url": setup_url,
        }


def describe_octogent_helper_runtime() -> dict[str, Any]:
    return {
        "id": "octogent",
        "owner_persona": OCTOGENT_OWNER_PERSONA,
        "mode": "helper_only",
        "canonical_runtime": False,
        "bridge_module": "server.octogent_bridge",
        "launch_strategy": "global_cli",
        "repo_path": str(OCTOGENT_REPO_DIR),
        "sub_agents": list(OCTOGENT_SUB_AGENTS),
        "skill_surfaces": list(OCTOGENT_SKILL_SURFACES),
        "codex_subagents": list(OCTOGENT_CODEX_SUBAGENTS),
        "api_base": OCTOGENT_API_BASE,
    }


def build_octogent_health_snapshot() -> dict[str, Any]:
    descriptor = describe_octogent_helper_runtime()
    resolved_command = _resolve_octogent_command()
    node_info = _node_snapshot()
    pnpm_command = _resolve_pnpm_command()
    repo_present = OCTOGENT_REPO_DIR.exists()
    scaffold_path = ROOT_DIR / ".octogent"
    api_info = _probe_octogent_api()

    capabilities = {
        "repo_clone": {
            "ok": repo_present,
            "detail": "repo-present" if repo_present else "repo-missing",
        },
        "node_runtime": {
            "ok": bool(node_info.get("ok")),
            "detail": node_info.get("detail"),
        },
        "package_manager": {
            "ok": bool(pnpm_command),
            "detail": "pnpm-ready" if pnpm_command else "pnpm-missing",
        },
        "cli_ready": {
            "ok": bool(resolved_command),
            "detail": "command-ready" if resolved_command else "command-missing",
        },
        "project_scaffold": {
            "ok": scaffold_path.exists(),
            "detail": "scaffold-present" if scaffold_path.exists() else "scaffold-missing",
        },
        "api_ready": {
            "ok": bool(api_info.get("ok")),
            "detail": api_info.get("detail"),
        },
    }

    if capabilities["api_ready"]["ok"]:
        status = "healthy"
    elif any(item["ok"] for item in capabilities.values()):
        status = "degraded"
    else:
        status = "missing"

    return {
        **descriptor,
        "status": status,
        "command": OCTOGENT_COMMAND,
        "resolved_command": resolved_command,
        "pnpm_command": pnpm_command,
        "repo_present": repo_present,
        "project_root": str(ROOT_DIR),
        "project_scaffold_path": str(scaffold_path),
        "node": node_info,
        "api_probe": api_info,
        "capabilities": capabilities,
        "install_hint": (
            "cd external-repos/octogent && cmd /c pnpm install && cmd /c pnpm build && npm install -g ."
            if os.name == "nt"
            else "cd external-repos/octogent && pnpm install && pnpm build && npm install -g ."
        ),
    }


def run_octogent_cli(args: list[str], timeout: int = 30) -> dict[str, Any]:
    resolved_command = _resolve_octogent_command()
    if not resolved_command:
        return {
            "ok": False,
            "error": "command-missing",
            "snapshot": build_octogent_health_snapshot(),
        }

    cmd = [resolved_command, *[str(item) for item in args]]
    env = os.environ.copy()
    env.setdefault("OCTOGENT_NO_OPEN", "1")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "command": cmd}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "command": cmd}

    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
        "command": cmd,
    }


def start_octogent_dashboard(no_open: bool = True) -> dict[str, Any]:
    resolved_command = _resolve_octogent_command()
    if not resolved_command:
        snapshot = build_octogent_health_snapshot()
        return {
            "ok": False,
            "error": "command-missing",
            "status": snapshot.get("status"),
            "snapshot": snapshot,
        }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "octogent-runtime.log"
    env = os.environ.copy()
    if no_open:
        env["OCTOGENT_NO_OPEN"] = "1"
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            proc = subprocess.Popen(
                [resolved_command],
                cwd=str(ROOT_DIR),
                env=env,
                stdout=handle,
                stderr=handle,
                creationflags=creationflags,
            )
    except Exception as exc:
        return {"ok": False, "error": str(exc), "command": resolved_command}

    return {
        "ok": True,
        "pid": proc.pid,
        "api_base": OCTOGENT_API_BASE,
        "ui_url": OCTOGENT_API_BASE,
        "log_path": str(log_path),
        "command": resolved_command,
    }


class OctogentBridge:
    """Optional helper facade around Octogent commands."""

    def describe_runtime(self) -> dict[str, Any]:
        return describe_octogent_helper_runtime()

    def health_snapshot(self) -> dict[str, Any]:
        return build_octogent_health_snapshot()

    def start(self) -> dict[str, Any]:
        return start_octogent_dashboard()

    def cli(self, *args: str) -> dict[str, Any]:
        return run_octogent_cli(list(args))
