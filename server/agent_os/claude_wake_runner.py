import json
import sys
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server.skills.approval_skill import _load_claude, _save_claude, add_approval_request


EXCHANGE_DIR = ROOT_DIR / "server" / "agent_workspace" / "exchange" / "claude" / "incoming"
EVENTS_PATH = ROOT_DIR / "server" / "logs" / "agent_os_events.jsonl"


def _record_event(message: str, data: dict | None = None):
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "time": datetime.now().isoformat(),
        "type": "claude_resume",
        "message": message,
        "data": data or {},
    }
    with open(EVENTS_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _is_due(resume_at: str) -> bool:
    now = datetime.now()
    hour, minute = [int(part) for part in resume_at.split(":", 1)]
    return (now.hour, now.minute) >= (hour, minute)


def run() -> str:
    state = _load_claude()
    if state.get("status") not in {"scheduled", "cooldown"}:
        return "Claude wake runner: planlanmis resume yok."
    resume_at = state.get("resume_at", "09:02")
    if not _is_due(resume_at):
        return f"Claude wake runner: saat henuz gelmedi ({resume_at})."

    EXCHANGE_DIR.mkdir(parents=True, exist_ok=True)
    package = {
        "created_at": datetime.now().isoformat(),
        "resume_at": resume_at,
        "last_task": state.get("last_task", "Claude collaboration protocol"),
        "notes": state.get("notes", "Claude limiti yenilendi, kaldigin yerden devam et."),
        "source_of_truth": [
            "server/agent_os/night_runner.py",
            "server/bridge.py",
            "server/logs/night_reports/",
            "server/agent_workspace/staging/",
        ],
        "instruction": "Kaldigin yerden devam et. Koddan once mimari/protocol/pattern analizi uret.",
    }
    out_path = EXCHANGE_DIR / f"claude_resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")

    state["status"] = "resumed"
    _save_claude(state)
    add_approval_request(
        "Claude resume package hazir",
        f"Claude için devam paketi uretildi: {out_path.name}",
        source="claude_wake_runner",
        risk="low",
    )
    _record_event("Claude resume package generated", {"package": str(out_path)})
    return f"Claude resume paketi hazirlandi: {out_path}"


if __name__ == "__main__":
    print(run())
