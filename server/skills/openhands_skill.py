from __future__ import annotations

import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

CONTAINER_NAME = "jarvis-openhands"
OPENHANDS_IMAGE = "docker.all-hands.dev/all-hands-ai/openhands:0.39"
RUNTIME_IMAGE = "docker.all-hands.dev/all-hands-ai/runtime:0.39-nikolaik"
OPENHANDS_PORT = 3000
STATE_DIR = Path.home() / ".openhands-state"

_DOCKER = "docker"


def _docker_available() -> bool:
    try:
        r = subprocess.run([_DOCKER, "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def _container_running() -> bool:
    try:
        r = subprocess.run(
            [_DOCKER, "inspect", "--format", "{{.State.Running}}", CONTAINER_NAME],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() == "true"
    except Exception:
        return False


def _container_exists() -> bool:
    try:
        r = subprocess.run(
            [_DOCKER, "inspect", CONTAINER_NAME],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def _start_container() -> tuple[bool, str]:
    """OpenHands container'ı başlat, (success, message) döndür."""
    if _container_running():
        return True, "Container zaten çalışıyor."

    if _container_exists():
        r = subprocess.run([_DOCKER, "start", CONTAINER_NAME], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return True, "Container yeniden başlatıldı."
        return False, f"Start hatası: {r.stderr[:200]}"

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        _DOCKER, "run", "-d",
        "--name", CONTAINER_NAME,
        "-p", f"{OPENHANDS_PORT}:{OPENHANDS_PORT}",
        "-e", f"SANDBOX_RUNTIME_CONTAINER_IMAGE={RUNTIME_IMAGE}",
        "-e", "LOG_ALL_EVENTS=true",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-v", f"{STATE_DIR}:/.openhands-state",
        "--add-host", "host.docker.internal:host-gateway",
        OPENHANDS_IMAGE,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        return True, f"Container başlatıldı: {r.stdout.strip()[:12]}"
    return False, f"Hata: {r.stderr[:300]}"


def _stop_container() -> tuple[bool, str]:
    if not _container_exists():
        return True, "Container zaten kapalıydı."
    r = subprocess.run([_DOCKER, "stop", CONTAINER_NAME], capture_output=True, text=True, timeout=15)
    if r.returncode == 0:
        return True, "Container durduruldu."
    return False, f"Durdurma hatası: {r.stderr[:200]}"


def _container_status() -> str:
    if not _docker_available():
        return "Docker bulunamadı"
    if _container_running():
        return f"ÇALIŞIYOR — http://localhost:{OPENHANDS_PORT}"
    if _container_exists():
        return "DURDU (yeniden başlatmak için /openhands-baslat)"
    return "YOK (başlatmak için /openhands-baslat)"


def _run_task_background(task: str, notify_fn=None) -> None:
    """Görevi OpenHands'e gönder, sonucu callback ile bildir."""
    import urllib.request
    import urllib.error

    time.sleep(3)  # container warm-up

    payload = json.dumps({"task": task}).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"http://localhost:{OPENHANDS_PORT}/api/conversations",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            conv_id = data.get("conversation_id", "?")
            msg = (
                f"OpenHands görevi alındı!\n"
                f"Conversation ID: {conv_id}\n"
                f"UI: http://localhost:{OPENHANDS_PORT}\n"
                f"Görev: {task[:100]}"
            )
    except urllib.error.URLError:
        msg = (
            f"OpenHands container çalışıyor ama API hazır değil.\n"
            f"Tarayıcıdan aç: http://localhost:{OPENHANDS_PORT}\n"
            f"Görevi manuel gir: {task[:150]}"
        )
    except Exception as e:
        msg = f"OpenHands API hatası: {e}\nUI: http://localhost:{OPENHANDS_PORT}"

    if notify_fn:
        notify_fn(msg)


def run_openhands(args: str = "", notify_fn=None) -> str:
    """
    Ana entry point. args = görev metni.
    notify_fn(str) → arka plan tamamlanınca Telegram'a gönderir.
    """
    if not _docker_available():
        return "Docker bulunamadı. Docker Desktop'ı başlat."

    if not args.strip():
        status = _container_status()
        return (
            f"OpenHands Durumu: {status}\n\n"
            f"Kullanım:\n"
            f"  /openhands [görev] → görevi çalıştır\n"
            f"  /openhands-baslat  → sadece container'ı başlat\n"
            f"  /openhands-durdur  → container'ı durdur\n"
            f"  /openhands-durum   → durum raporu"
        )

    ok, msg = _start_container()
    if not ok:
        return f"Container başlatılamadı: {msg}"

    t = threading.Thread(
        target=_run_task_background,
        args=(args.strip(), notify_fn),
        daemon=True,
        name="openhands_task",
    )
    t.start()

    return (
        f"OpenHands görevi başlatıldı!\n"
        f"Container: {msg}\n"
        f"Görev: {args[:120]}\n"
        f"UI: http://localhost:{OPENHANDS_PORT}\n"
        f"Sonuç gelince Telegram'a bildirim gelecek."
    )


def start_openhands(args: str = "") -> str:
    if not _docker_available():
        return "Docker bulunamadı."
    ok, msg = _start_container()
    if ok:
        return f"OpenHands hazır.\n{msg}\nUI: http://localhost:{OPENHANDS_PORT}"
    return f"Başlatma hatası: {msg}"


def stop_openhands(args: str = "") -> str:
    if not _docker_available():
        return "Docker bulunamadı."
    ok, msg = _stop_container()
    return msg if ok else f"Hata: {msg}"


def status_openhands(args: str = "") -> str:
    if not _docker_available():
        return "Docker bulunamadı."
    return f"OpenHands: {_container_status()}"
