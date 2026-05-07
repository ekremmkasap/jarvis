from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
OPENCODE_PORT = int(os.environ.get("OPENCODE_PORT", "7080"))
OPENHANDS_PORT = int(os.environ.get("OPENHANDS_PORT", "3000"))
OPENHANDS_CONTAINER = os.environ.get("OPENHANDS_CONTAINER_NAME", "openhands-jarvis")
OPENHANDS_IMAGE = os.environ.get("OPENHANDS_IMAGE", "docker.io/all-hands-ai/openhands:0.43")
OPENHANDS_RUNTIME_IMAGE = os.environ.get(
    "OPENHANDS_RUNTIME_IMAGE",
    "docker.io/nikolaik/python-nodejs:python3.12-nodejs22-slim",
)

_OPENCODE_PROC: subprocess.Popen[str] | None = None


def is_local_port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


def iter_command_candidates(command: str) -> list[str]:
    raw = str(command or "").strip()
    if not raw:
        return []
    if Path(raw).suffix:
        variants = [raw]
    elif os.name == "nt":
        variants = [f"{raw}.cmd", f"{raw}.exe", f"{raw}.bat", raw]
    else:
        variants = [raw]

    candidates: list[str] = []
    seen: set[str] = set()
    for item in variants:
        resolved = shutil.which(item) or item
        key = str(resolved).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append(str(resolved))
    return candidates


def probe_command(command: str, args: list[str] | None = None, timeout: int = 5) -> dict[str, Any]:
    arguments = list(args or [])
    errors: list[str] = []
    for candidate in iter_command_candidates(command):
        try:
            result = subprocess.run(
                [candidate, *arguments],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            continue
        except Exception as exc:
            errors.append(str(exc))
            continue
        message = (result.stdout or result.stderr or "").strip()
        return {
            "ok": result.returncode == 0,
            "command": candidate,
            "message": message or ("ok" if result.returncode == 0 else "probe_failed"),
            "returncode": result.returncode,
        }
    return {
        "ok": False,
        "command": "",
        "message": "; ".join(errors[:2]) if errors else "not_installed",
        "returncode": None,
    }


def _opencode_running() -> bool:
    global _OPENCODE_PROC
    return _OPENCODE_PROC is not None and _OPENCODE_PROC.poll() is None


def get_opencode_status() -> dict[str, Any]:
    probe = probe_command("opencode", ["--version"])
    process_alive = _opencode_running()
    running = is_local_port_busy(OPENCODE_PORT)
    return {
        "ok": bool(running or probe.get("ok")),
        "running": running,
        "process_alive": process_alive,
        "cli_ok": bool(probe.get("ok")),
        "command": str(probe.get("command") or "").strip(),
        "version": str(probe.get("message") or "").strip(),
        "port": OPENCODE_PORT,
        "url": f"http://127.0.0.1:{OPENCODE_PORT}" if running else "",
        "reason": (
            "running"
            if running
            else "starting"
            if process_alive
            else ("cli_ready" if probe.get("ok") else str(probe.get("message") or "cli_unavailable"))
        ),
    }


def start_opencode_serve() -> dict[str, Any]:
    global _OPENCODE_PROC
    status = get_opencode_status()
    if status.get("running"):
        status["started"] = False
        status["reason"] = "already_running"
        return status
    if not status.get("cli_ok"):
        status["ok"] = False
        status["started"] = False
        return status
    try:
        _OPENCODE_PROC = subprocess.Popen(
            [str(status["command"]), "serve", "--port", str(OPENCODE_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT_DIR),
        )
    except Exception as exc:
        status["ok"] = False
        status["started"] = False
        status["reason"] = f"start_failed:{str(exc)[:160]}"
        return status

    refreshed = get_opencode_status()
    for _ in range(16):
        if refreshed.get("running"):
            break
        if _OPENCODE_PROC is not None and _OPENCODE_PROC.poll() is not None:
            break
        time.sleep(0.5)
        refreshed = get_opencode_status()
    refreshed["started"] = bool(refreshed.get("running"))
    refreshed["ok"] = bool(refreshed.get("running"))
    if not refreshed.get("running"):
        if _OPENCODE_PROC is not None and _OPENCODE_PROC.poll() is not None:
            refreshed["reason"] = f"process_exited:{_OPENCODE_PROC.poll()}"
        else:
            refreshed["reason"] = "launch_timeout"
    return refreshed


def format_opencode_status(status: dict[str, Any]) -> str:
    lines = ["OpenCode runtime"]
    if status.get("running"):
        lines.append(f"Serve aktif: {status.get('url') or '-'}")
    else:
        lines.append("Serve kapali")
    if status.get("process_alive") and not status.get("running"):
        lines.append("Process durumu: basliyor veya port acmadi")
    lines.append(f"CLI hazir: {'evet' if status.get('cli_ok') else 'hayir'}")
    if status.get("version"):
        lines.append(f"Version: {status.get('version')}")
    if status.get("command"):
        lines.append(f"Komut: {status.get('command')}")
    return "\n".join(lines)


def get_openhands_runtime_status() -> dict[str, Any]:
    probe = probe_command("docker", ["--version"])
    status = {
        "ok": False,
        "running": False,
        "docker_ok": bool(probe.get("ok")),
        "daemon_available": False,
        "docker_command": str(probe.get("command") or "").strip(),
        "docker_info": str(probe.get("message") or "").strip(),
        "container": OPENHANDS_CONTAINER,
        "port": OPENHANDS_PORT,
        "url": "",
        "status": "",
        "ports": "",
        "workspace": str(ROOT_DIR / "openhands" / "workspace"),
        "config_path": str(ROOT_DIR / "openhands" / "config.toml"),
        "reason": str(probe.get("message") or "docker_cli_unavailable"),
    }
    if not probe.get("ok"):
        return status

    try:
        result = subprocess.run(
            [
                str(status["docker_command"]),
                "ps",
                "--filter",
                f"name={OPENHANDS_CONTAINER}",
                "--format",
                "{{.Names}}\t{{.Status}}\t{{.Ports}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        status["reason"] = f"docker_ps_failed:{str(exc)[:160]}"
        return status

    if result.returncode != 0:
        status["reason"] = (result.stderr or result.stdout or "").strip() or "docker_daemon_unavailable"
        return status

    status["daemon_available"] = True
    output = result.stdout.strip()
    if output:
        parts = output.splitlines()[0].split("\t")
        status["running"] = True
        status["ok"] = True
        status["url"] = f"http://127.0.0.1:{OPENHANDS_PORT}"
        status["status"] = parts[1] if len(parts) > 1 else ""
        status["ports"] = parts[2] if len(parts) > 2 else ""
        status["reason"] = "running"
        return status

    if is_local_port_busy(OPENHANDS_PORT):
        status["running"] = True
        status["ok"] = True
        status["url"] = f"http://127.0.0.1:{OPENHANDS_PORT}"
        status["reason"] = "port_busy"
        return status

    status["reason"] = "stopped"
    return status


def start_openhands_runtime() -> dict[str, Any]:
    status = get_openhands_runtime_status()
    if status.get("running"):
        status["started"] = False
        status["reason"] = "already_running"
        return status
    if not status.get("docker_ok"):
        status["started"] = False
        return status
    if not status.get("daemon_available"):
        status["started"] = False
        return status

    workspace_path = Path(str(status["workspace"]))
    config_path = Path(str(status["config_path"]))
    workspace_path.mkdir(parents=True, exist_ok=True)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    oh_data = str(Path.home() / ".openhands")
    docker_command = str(status["docker_command"] or "docker")

    subprocess.run([docker_command, "rm", "-f", OPENHANDS_CONTAINER], capture_output=True, timeout=10)

    cmd = [
        docker_command,
        "run",
        "-d",
        "--name",
        OPENHANDS_CONTAINER,
        "--pull",
        "never",
        "-e",
        f"SANDBOX_RUNTIME_CONTAINER_IMAGE={OPENHANDS_RUNTIME_IMAGE}",
        "-e",
        "LOG_ALL_EVENTS=true",
        "-v",
        "/var/run/docker.sock:/var/run/docker.sock",
        "-v",
        f"{oh_data}:/.openhands",
        "-v",
        f"{workspace_path}:/opt/workspace_base",
        "-p",
        f"{OPENHANDS_PORT}:{OPENHANDS_PORT}",
        "--add-host",
        "host.docker.internal:host-gateway",
    ]
    if config_path.exists():
        cmd.extend(["-v", f"{config_path}:/.openhands/config.toml"])
    cmd.append(OPENHANDS_IMAGE)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        status["ok"] = False
        status["started"] = False
        status["reason"] = f"start_failed:{str(exc)[:160]}"
        return status

    if result.returncode != 0:
        status["ok"] = False
        status["started"] = False
        status["reason"] = (result.stderr or result.stdout or "").strip() or "docker_run_failed"
        return status

    time.sleep(1)
    refreshed = get_openhands_runtime_status()
    refreshed["started"] = bool(refreshed.get("running"))
    if refreshed.get("started"):
        refreshed["container_id"] = result.stdout.strip()[:12]
    else:
        refreshed["reason"] = "launch_no_port"
    return refreshed


def format_openhands_status(status: dict[str, Any]) -> str:
    lines = ["OpenHands runtime"]
    lines.append(f"Docker hazir: {'evet' if status.get('docker_ok') else 'hayir'}")
    lines.append(f"Daemon hazir: {'evet' if status.get('daemon_available') else 'hayir'}")
    if status.get("running"):
        lines.append(f"UI aktif: {status.get('url') or '-'}")
    else:
        lines.append("UI kapali")
    if status.get("status"):
        lines.append(f"Container durum: {status.get('status')}")
    if status.get("ports"):
        lines.append(f"Portlar: {status.get('ports')}")
    if status.get("docker_info"):
        lines.append(f"Docker: {status.get('docker_info')}")
    return "\n".join(lines)
