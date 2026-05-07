from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

try:
    import psutil as _psutil
except Exception:  # pragma: no cover - optional dependency
    _psutil = None


SERVER_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = SERVER_DIR.parent
LOG_DIR = SERVER_DIR / "logs"
OPS_LOG_PATH = LOG_DIR / "sabrican_ops.jsonl"
BRIDGE_DIR = SERVER_DIR
BRIDGE_SCRIPT = BRIDGE_DIR / "bridge.py"
BRIDGE_HEALTH_URL = "http://127.0.0.1:8081/health"
OLLAMA_HEALTH_URL = "http://127.0.0.1:11434/api/tags"
HOLOGRAM_PROCESS_NAMES = [
    "electron.exe",
    "electron",
    "desktop-hologram.exe",
    "jarvis-hologram.exe",
]
HOLOGRAM_CMD_TERMS = [
    "desktop-hologram",
    "jarvis hologram",
    "hologram",
]
ALLOWED_RESTART_SERVICES = {"bridge", "ollama"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _audit(action: str, service: str, payload: dict[str, Any]) -> None:
    _append_jsonl(
        OPS_LOG_PATH,
        {
            "ts": _now_iso(),
            "action": action,
            "service": service,
            "payload": payload,
        },
    )


def _normalize_service_name(service_name: str) -> str:
    return str(service_name or "").strip().lower()


def _strip_to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return default


def _parse_kv_block(stdout: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in str(stdout or "").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            parsed[key] = value
    return parsed


def _safe_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        json.dumps(payload, ensure_ascii=False)
        return payload
    except Exception:
        return {"ok": False, "error": "non_serializable_payload"}


def _http_probe(url: str, timeout: int = 5) -> tuple[bool, int | None, str | None]:
    started_at = time.perf_counter()
    try:
        request = Request(
            str(url).strip(),
            headers={"User-Agent": "Jarvis-Sabrican/1.0"},
            method="GET",
        )
        with urlopen(request, timeout=timeout) as response:
            response.read(128)
        return True, int((time.perf_counter() - started_at) * 1000), None
    except Exception as exc:
        return False, None, str(exc)


def _process_matches_psutil(
    process_names: list[str],
    cmd_terms: list[str],
) -> bool:
    if _psutil is None:
        return False

    expected_names = {item.lower() for item in process_names}
    lowered_terms = [item.lower() for item in cmd_terms]
    for proc in _psutil.process_iter(["name", "cmdline"]):
        try:
            name = str(proc.info.get("name") or "").strip().lower()
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
        except Exception:
            continue
        if name in expected_names:
            return True
        if cmdline and any(term in cmdline for term in lowered_terms):
            return True
    return False


def _process_matches_tasklist(process_names: list[str]) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        expected_names = {item.lower() for item in process_names}
        reader = csv.reader(result.stdout.splitlines())
        for row in reader:
            if not row:
                continue
            image_name = str(row[0] or "").strip().strip('"').lower()
            if image_name in expected_names:
                return True
        return False

    result = subprocess.run(
        ["ps", "-A", "-o", "comm="],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    expected_names = {item.lower() for item in process_names}
    for raw_line in result.stdout.splitlines():
        process_name = Path(raw_line.strip()).name.lower()
        if process_name in expected_names:
            return True
    return False


def _check_process_health(
    process_names: list[str],
    cmd_terms: list[str] | None = None,
) -> bool:
    terms = cmd_terms or []
    if _psutil is not None:
        return _process_matches_psutil(process_names, terms)
    return _process_matches_tasklist(process_names)


def _read_windows_metrics_fallback() -> tuple[float, float, float]:
    cpu_pct = 0.0
    ram_pct = 0.0
    disk_pct = 0.0

    try:
        result = subprocess.run(
            ["wmic", "cpu", "get", "loadpercentage", "/value"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        cpu_pct = _strip_to_float(_parse_kv_block(result.stdout).get("LoadPercentage"))
    except Exception:
        cpu_pct = 0.0

    try:
        result = subprocess.run(
            [
                "wmic",
                "OS",
                "get",
                "FreePhysicalMemory,TotalVisibleMemorySize",
                "/value",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        values = _parse_kv_block(result.stdout)
        free_kb = _strip_to_float(values.get("FreePhysicalMemory"))
        total_kb = _strip_to_float(values.get("TotalVisibleMemorySize"))
        if total_kb > 0:
            ram_pct = round(((total_kb - free_kb) / total_kb) * 100, 2)
    except Exception:
        ram_pct = 0.0

    drive = os.environ.get("SystemDrive", "C:").rstrip("\\")
    try:
        result = subprocess.run(
            [
                "wmic",
                "logicaldisk",
                "where",
                f"DeviceID='{drive}'",
                "get",
                "FreeSpace,Size",
                "/value",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        values = _parse_kv_block(result.stdout)
        free_space = _strip_to_float(values.get("FreeSpace"))
        total_size = _strip_to_float(values.get("Size"))
        if total_size > 0:
            disk_pct = round(((total_size - free_space) / total_size) * 100, 2)
    except Exception:
        disk_pct = 0.0

    return float(cpu_pct), float(ram_pct), float(disk_pct)


def _read_system_metrics() -> tuple[float, float, float]:
    if _psutil is not None:
        try:
            cpu_pct = float(_psutil.cpu_percent(interval=0.1))
            ram_pct = float(_psutil.virtual_memory().percent)
            disk_target = os.environ.get("SystemDrive", "C:")
            if os.name == "nt":
                disk_target = f"{disk_target}\\"
            else:
                disk_target = "/"
            disk_pct = float(_psutil.disk_usage(disk_target).percent)
            return round(cpu_pct, 2), round(ram_pct, 2), round(disk_pct, 2)
        except Exception:
            pass

    if os.name == "nt":
        return _read_windows_metrics_fallback()
    return 0.0, 0.0, 0.0


def _detached_creation_flags() -> int:
    return int(getattr(subprocess, "DETACHED_PROCESS", 0)) | int(
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    )


def _schedule_bridge_restart() -> dict[str, Any]:
    python_executable = sys.executable or "python"
    if not BRIDGE_SCRIPT.exists():
        return {
            "ok": False,
            "service": "bridge",
            "status": "down",
            "error": "bridge_script_missing",
        }

    if os.name == "nt":
        command = (
            f"ping 127.0.0.1 -n 3 >nul "
            f"&& taskkill /PID {os.getpid()} /F >nul 2>&1 "
            f"&& ping 127.0.0.1 -n 2 >nul "
            f'&& start "Jarvis-Bridge" "{python_executable}" "{BRIDGE_SCRIPT.name}"'
        )
        subprocess.Popen(
            ["cmd.exe", "/c", command],
            cwd=str(BRIDGE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_detached_creation_flags(),
        )
    else:
        command = (
            f"sleep 2; "
            f"kill -TERM {os.getpid()}; "
            f"sleep 1; "
            f'nohup "{python_executable}" "{BRIDGE_SCRIPT}" >/dev/null 2>&1 &'
        )
        subprocess.Popen(
            ["sh", "-c", command],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return {
        "ok": True,
        "service": "bridge",
        "status": "scheduled",
        "error": None,
    }


def _schedule_ollama_restart() -> dict[str, Any]:
    ollama_binary = shutil.which("ollama")
    if not ollama_binary:
        return {
            "ok": False,
            "service": "ollama",
            "status": "down",
            "error": "ollama_not_installed",
        }

    if os.name == "nt":
        command = (
            "taskkill /IM ollama.exe /F >nul 2>&1 "
            "&& ping 127.0.0.1 -n 2 >nul "
            f'&& start "Ollama" "{ollama_binary}" serve'
        )
        subprocess.Popen(
            ["cmd.exe", "/c", command],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_detached_creation_flags(),
        )
    else:
        command = (
            f'pkill -f ollama || true; sleep 1; nohup "{ollama_binary}" serve >/dev/null 2>&1 &'
        )
        subprocess.Popen(
            ["sh", "-c", command],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return {
        "ok": True,
        "service": "ollama",
        "status": "scheduled",
        "error": None,
    }


def check_service_health(service_name: str, url: str | None = None) -> dict[str, Any]:
    service = _normalize_service_name(service_name)
    result: dict[str, Any]

    if not service:
        result = {
            "ok": False,
            "service": "",
            "status": "unknown",
            "latency_ms": None,
            "error": "missing_service_name",
        }
        _audit("check_service_health", service or "unknown", _safe_json_payload(result))
        return result

    if url:
        ok, latency_ms, error = _http_probe(url, timeout=5)
        result = {
            "ok": ok,
            "service": service,
            "status": "up" if ok else "down",
            "latency_ms": latency_ms,
            "error": error,
            "url": str(url).strip(),
        }
        _audit("check_service_health", service, _safe_json_payload(result))
        return result

    if service == "bridge":
        ok, latency_ms, error = _http_probe(BRIDGE_HEALTH_URL, timeout=5)
        result = {
            "ok": ok,
            "service": service,
            "status": "up" if ok else "down",
            "latency_ms": latency_ms,
            "error": error,
            "url": BRIDGE_HEALTH_URL,
        }
    elif service == "ollama":
        ok, latency_ms, error = _http_probe(OLLAMA_HEALTH_URL, timeout=5)
        result = {
            "ok": ok,
            "service": service,
            "status": "up" if ok else "down",
            "latency_ms": latency_ms,
            "error": error,
            "url": OLLAMA_HEALTH_URL,
        }
    elif service == "hologram":
        is_running = _check_process_health(
            HOLOGRAM_PROCESS_NAMES,
            cmd_terms=HOLOGRAM_CMD_TERMS,
        )
        result = {
            "ok": is_running,
            "service": service,
            "status": "up" if is_running else "down",
            "latency_ms": None,
            "error": None if is_running else "process_not_found",
        }
    else:
        result = {
            "ok": False,
            "service": service,
            "status": "unknown",
            "latency_ms": None,
            "error": "unknown_service",
        }

    _audit("check_service_health", service, _safe_json_payload(result))
    return result


def get_system_status() -> dict[str, Any]:
    services = [
        check_service_health("bridge"),
        check_service_health("ollama"),
        check_service_health("hologram"),
    ]
    cpu_pct, ram_pct, disk_pct = _read_system_metrics()
    result = {
        "services": services,
        "cpu_pct": float(cpu_pct),
        "ram_pct": float(ram_pct),
        "disk_pct": float(disk_pct),
    }
    _audit("get_system_status", "system", _safe_json_payload(result))
    return result


def docker_status() -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except FileNotFoundError:
        payload = {
            "ok": False,
            "containers": [],
            "error": "docker_not_installed",
        }
        _audit("docker_status", "docker", payload)
        return payload
    except Exception as exc:
        payload = {
            "ok": False,
            "containers": [],
            "error": str(exc),
        }
        _audit("docker_status", "docker", payload)
        return payload

    if result.returncode != 0:
        payload = {
            "ok": False,
            "containers": [],
            "error": (result.stderr or result.stdout or "docker_unavailable").strip(),
        }
        _audit("docker_status", "docker", payload)
        return payload

    containers: list[dict[str, Any]] = []
    stdout = str(result.stdout or "").strip()
    if stdout:
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                if line.startswith("["):
                    try:
                        parsed = json.loads(line)
                    except Exception:
                        parsed = {"raw": line}
                else:
                    parsed = {"raw": line}
            if isinstance(parsed, list):
                containers.extend(item for item in parsed if isinstance(item, dict))
            elif isinstance(parsed, dict):
                containers.append(parsed)

    payload = {
        "ok": True,
        "containers": containers,
        "count": len(containers),
        "error": None,
    }
    _audit("docker_status", "docker", _safe_json_payload(payload))
    return payload


def restart_service(service_name: str) -> dict[str, Any]:
    service = _normalize_service_name(service_name)

    if service not in ALLOWED_RESTART_SERVICES:
        payload = {
            "ok": False,
            "service": service,
            "status": "unknown",
            "error": "not_allowed",
        }
        _audit("restart_service", service or "unknown", payload)
        return payload

    if service == "bridge":
        payload = _schedule_bridge_restart()
    else:
        payload = _schedule_ollama_restart()

    _audit("restart_service", service, _safe_json_payload(payload))
    return payload
