import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from claude_wake_runner import run as run_claude_wake
from night_runner import NightRunner
from server.skills.approval_skill import get_autopilot_status, process_pending_auto_approvals


STATE_DIR = ROOT_DIR / "server" / "agent_workspace" / "approval_state"
RUNTIME_PATH = STATE_DIR / "autopilot_runtime.json"
STOP_PATH = STATE_DIR / "autopilot.stop"
PID_PATH = STATE_DIR / "autopilot.pid"
EVENTS_PATH = ROOT_DIR / "server" / "logs" / "agent_os_events.jsonl"


def _record_event(message: str, data: dict | None = None):
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "time": datetime.now().isoformat(),
        "type": "autopilot_runner",
        "message": message,
        "data": data or {},
    }
    with open(EVENTS_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _write_runtime(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now().isoformat()
    RUNTIME_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_state() -> dict:
    return {
        "status": "idle",
        "started_at": datetime.now().isoformat(),
        "last_night_cycle": None,
        "last_claude_wake_check": None,
        "last_auto_approve": None,
        "loop_count": 0,
        "note": "JARVIS autopilot running until stopped.",
    }


def _should_run_night_cycle(state: dict) -> bool:
    now = datetime.now()
    # Run once immediately, then every 45 minutes while autopilot is active.
    if not state.get("last_night_cycle"):
        return True
    last = datetime.fromisoformat(state["last_night_cycle"])
    return now - last >= timedelta(minutes=45)


def _sleep_chunk(seconds: int = 60):
    for _ in range(seconds):
        if STOP_PATH.exists():
            return False
        time.sleep(1)
    return True


def run_forever():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STOP_PATH.unlink(missing_ok=True)
    PID_PATH.write_text(str(__import__("os").getpid()), encoding="utf-8")
    state = _base_state()
    _write_runtime(state)
    _record_event("Autopilot runner started", {"autopilot": get_autopilot_status()})

    while not STOP_PATH.exists():
        state["status"] = "running"
        state["loop_count"] += 1
        _write_runtime(state)

        try:
            process_pending_auto_approvals()
            state["last_auto_approve"] = datetime.now().isoformat()

            wake_result = run_claude_wake()
            state["last_claude_wake_check"] = datetime.now().isoformat()
            _record_event("Claude wake check", {"result": wake_result})

            if _should_run_night_cycle(state):
                _record_event("Night cycle triggered", {"loop": state["loop_count"]})
                runner = NightRunner()
                runner.run_night_cycle()
                state["last_night_cycle"] = datetime.now().isoformat()

        except Exception as exc:
            _record_event("Autopilot loop error", {"error": str(exc)})

        _write_runtime(state)
        if not _sleep_chunk(60):
            break

    state["status"] = "stopped"
    _write_runtime(state)
    _record_event("Autopilot runner stopped")
    PID_PATH.unlink(missing_ok=True)
    STOP_PATH.unlink(missing_ok=True)
    return "Autopilot stopped"


if __name__ == "__main__":
    print(run_forever())
