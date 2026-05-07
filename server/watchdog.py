from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BRIDGE = ROOT / "bridge.py"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
HEARTBEAT = DATA / "bridge_heartbeat.json"
WATCHDOG_LOG = DATA / "watchdog.log"
LOCK_FILE = DATA / "bridge.lock"

HEARTBEAT_TIMEOUT = 30
RESTART_BACKOFF = 3
STARTUP_GRACE = 45


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(message: str) -> None:
    line = f"{_now()} [watchdog] {message}"
    print(line, flush=True)
    try:
        with WATCHDOG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def _load_heartbeat() -> dict:
    try:
        return json.loads(HEARTBEAT.read_text(encoding="utf-8")) if HEARTBEAT.exists() else {}
    except Exception:
        return {}


def _coerce_pid(value: object) -> int | None:
    try:
        pid = int(value or 0)
    except Exception:
        return None
    return pid if pid > 0 else None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, SystemError):
        return False


def _lock_pid() -> int | None:
    try:
        if not LOCK_FILE.exists():
            return None
        return _coerce_pid(LOCK_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _heartbeat_age_seconds() -> float:
    data = _load_heartbeat()
    updated_at = str(data.get("updated_at") or "").strip()
    if not updated_at:
        return 9999.0
    try:
        ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds())
    except Exception:
        return 9999.0


def _heartbeat_matches_pid(pid: int) -> bool:
    return _coerce_pid(_load_heartbeat().get("pid")) == pid


def _cleanup_bridge_state_for_pid(pid: int) -> None:
    heartbeat_pid = _coerce_pid(_load_heartbeat().get("pid"))
    if heartbeat_pid == pid and HEARTBEAT.exists():
        try:
            HEARTBEAT.unlink()
            _log(f"Eski heartbeat dosyasi silindi (PID {pid} oldu)")
        except Exception as exc:
            _log(f"Heartbeat cleanup hatasi: {exc}")

    lock_pid = _lock_pid()
    if lock_pid == pid and LOCK_FILE.exists():
        try:
            LOCK_FILE.unlink()
            _log(f"Eski lock dosyasi silindi (PID {pid} oldu)")
        except Exception as exc:
            _log(f"Lock cleanup hatasi: {exc}")


def _cleanup_stale_bridge_state() -> None:
    old_lock_pid = _lock_pid()
    try:
        if old_lock_pid and not _pid_alive(old_lock_pid) and LOCK_FILE.exists():
            LOCK_FILE.unlink()
            _log(f"Eski lock dosyasi silindi (PID {old_lock_pid} olu)")
    except Exception as exc:
        _log(f"Lock cleanup hatasi: {exc}")

    heartbeat_pid = _coerce_pid(_load_heartbeat().get("pid"))
    try:
        if heartbeat_pid and not _pid_alive(heartbeat_pid) and HEARTBEAT.exists():
            HEARTBEAT.unlink()
            _log(f"Eski heartbeat dosyasi silindi (PID {heartbeat_pid} olu)")
    except Exception as exc:
        _log(f"Heartbeat cleanup hatasi: {exc}")


def _spawn_bridge() -> subprocess.Popen:
    _log("bridge baslatiliyor")
    return subprocess.Popen([sys.executable, str(BRIDGE)], cwd=str(ROOT.parent))


def _is_port_busy(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()


def _restart_bridge(proc: subprocess.Popen, reason: str) -> subprocess.Popen:
    _log(reason)
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    _cleanup_bridge_state_for_pid(proc.pid)
    time.sleep(RESTART_BACKOFF)
    return _spawn_bridge()


def main() -> int:
    if not BRIDGE.exists():
        _log(f"bridge.py bulunamadi: {BRIDGE}")
        return 1

    _cleanup_stale_bridge_state()

    if _is_port_busy(8081):
        _log("8081 zaten dolu; watchdog ikinci bridge baslatmayacak")
        return 0

    proc = _spawn_bridge()
    started_at = time.time()

    while True:
        time.sleep(3)

        if proc.poll() is not None:
            _cleanup_bridge_state_for_pid(proc.pid)
            _log("bridge sureci sonlandi, yeniden baslatiliyor")
            time.sleep(RESTART_BACKOFF)
            proc = _spawn_bridge()
            started_at = time.time()
            continue

        if time.time() - started_at < STARTUP_GRACE:
            continue

        if not _heartbeat_matches_pid(proc.pid):
            proc = _restart_bridge(proc, "heartbeat pid eslesmiyor, bridge yeniden baslatiliyor")
            started_at = time.time()
            continue

        age = _heartbeat_age_seconds()
        if age > HEARTBEAT_TIMEOUT:
            proc = _restart_bridge(proc, f"heartbeat stale ({int(age)}s), bridge yeniden baslatiliyor")
            started_at = time.time()
            continue


if __name__ == "__main__":
    raise SystemExit(main())
