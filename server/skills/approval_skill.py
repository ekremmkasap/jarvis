import json
import uuid
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT_DIR / "server" / "agent_workspace" / "approval_state"
QUEUE_PATH = STATE_DIR / "approval_queue.json"
CLAUDE_PATH = STATE_DIR / "claude_resume.json"
AUTOPILOT_PATH = STATE_DIR / "autopilot.json"


def _ensure_state():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not QUEUE_PATH.exists():
        QUEUE_PATH.write_text(json.dumps({"items": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not CLAUDE_PATH.exists():
        CLAUDE_PATH.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "resume_at": "09:02",
                    "updated_at": datetime.now().isoformat(),
                    "notes": "",
                    "last_task": "",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if not AUTOPILOT_PATH.exists():
        AUTOPILOT_PATH.write_text(
            json.dumps(
                {
                    "enabled": True,
                    "mode": "sleep",
                    "auto_approve_risks": ["low", "medium"],
                    "blocked_patterns": [
                        "bridge.py",
                        "hey_jarvis.py",
                        ".env",
                        "credentials",
                        "token",
                        "payment",
                        "deploy",
                    ],
                    "updated_at": datetime.now().isoformat(),
                    "note": "Uyku modu acik. Kritik olmayan isler otomatik onaylanir."
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def _load_queue() -> dict:
    _ensure_state()
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def _save_queue(data: dict):
    QUEUE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_claude() -> dict:
    _ensure_state()
    return json.loads(CLAUDE_PATH.read_text(encoding="utf-8"))


def _save_claude(data: dict):
    data["updated_at"] = datetime.now().isoformat()
    CLAUDE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_autopilot() -> dict:
    _ensure_state()
    return json.loads(AUTOPILOT_PATH.read_text(encoding="utf-8"))


def _save_autopilot(data: dict):
    data["updated_at"] = datetime.now().isoformat()
    AUTOPILOT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_approval_request(title: str, summary: str = "", source: str = "jarvis", risk: str = "medium") -> str:
    queue = _load_queue()
    item_id = str(uuid.uuid4())[:8]
    autopilot = _load_autopilot()
    status = "pending"
    decision_note = ""
    if should_auto_approve(title=title, summary=summary, risk=risk, source=source):
        status = "approved"
        decision_note = f"Autopilot auto-approved ({autopilot.get('mode', 'sleep')})"
    queue["items"].append(
        {
            "id": item_id,
            "title": title.strip(),
            "summary": summary.strip(),
            "source": source,
            "risk": risk,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "decision_at": datetime.now().isoformat() if status != "pending" else None,
            "decision_note": decision_note,
        }
    )
    _save_queue(queue)
    if status == "approved":
        return f"Onay istegi otomatik kabul edildi: #{item_id} - {title.strip()}"
    return f"Onay istegi eklendi: #{item_id} - {title.strip()}"


def list_approval_requests(status: str = "pending") -> str:
    queue = _load_queue()
    items = [item for item in queue["items"] if status == "all" or item["status"] == status]
    if not items:
        return "Bekleyen onay istegi yok."
    lines = ["Onay kuyruğu:"]
    for item in items[:20]:
        lines.append(
            f"- #{item['id']} [{item['status']}] ({item['risk']}) {item['title']} | kaynak: {item['source']}"
        )
        if item.get("summary"):
            lines.append(f"  {item['summary'][:140]}")
    return "\n".join(lines)


def decide_approval(item_id: str, decision: str, note: str = "") -> str:
    queue = _load_queue()
    for item in queue["items"]:
        if item["id"] == item_id:
            item["status"] = "approved" if decision == "approve" else "rejected"
            item["decision_at"] = datetime.now().isoformat()
            item["decision_note"] = note.strip()
            _save_queue(queue)
            return f"#{item_id} {item['status']} olarak işaretlendi."
    return f"Onay isteği bulunamadı: #{item_id}"


def schedule_claude_resume(resume_at: str = "09:02", notes: str = "", last_task: str = "") -> str:
    state = _load_claude()
    state["status"] = "scheduled"
    state["resume_at"] = resume_at.strip() or "09:02"
    state["notes"] = notes.strip()
    if last_task.strip():
        state["last_task"] = last_task.strip()
    _save_claude(state)
    return f"Claude uyandırma planlandı: {state['resume_at']}"


def get_claude_resume_status() -> str:
    state = _load_claude()
    lines = [
        "Claude resume durumu:",
        f"- durum: {state.get('status', 'idle')}",
        f"- saat: {state.get('resume_at', '09:02')}",
    ]
    if state.get("last_task"):
        lines.append(f"- son görev: {state['last_task']}")
    if state.get("notes"):
        lines.append(f"- not: {state['notes']}")
    return "\n".join(lines)


def set_autopilot(enabled: bool, mode: str = "sleep", note: str = "") -> str:
    data = _load_autopilot()
    data["enabled"] = enabled
    data["mode"] = mode
    if note.strip():
        data["note"] = note.strip()
    _save_autopilot(data)
    return f"Autopilot {'aktif' if enabled else 'pasif'}: {mode}"


def get_autopilot_status() -> str:
    data = _load_autopilot()
    return "\n".join(
        [
            "Autopilot durumu:",
            f"- aktif: {'evet' if data.get('enabled') else 'hayir'}",
            f"- mod: {data.get('mode', 'sleep')}",
            f"- riskler: {', '.join(data.get('auto_approve_risks', [])) or 'none'}",
            f"- not: {data.get('note', '')}",
        ]
    )


def should_auto_approve(title: str = "", summary: str = "", risk: str = "medium", source: str = "jarvis") -> bool:
    data = _load_autopilot()
    if not data.get("enabled"):
        return False
    if risk.lower() not in {item.lower() for item in data.get("auto_approve_risks", [])}:
        return False
    haystack = f"{title} {summary} {source}".lower()
    for pattern in data.get("blocked_patterns", []):
        if pattern.lower() in haystack:
            return False
    return True


def process_pending_auto_approvals() -> str:
    queue = _load_queue()
    changed = 0
    for item in queue["items"]:
        if item["status"] != "pending":
            continue
        if should_auto_approve(item.get("title", ""), item.get("summary", ""), item.get("risk", "medium"), item.get("source", "jarvis")):
            item["status"] = "approved"
            item["decision_at"] = datetime.now().isoformat()
            item["decision_note"] = "Autopilot batch approval"
            changed += 1
    _save_queue(queue)
    return f"Autopilot {changed} bekleyen isi onayladi."


def run(args: str, context: dict = None) -> str:
    context = context or {}
    text = (args or "").strip()
    if not text or text == "list":
        return list_approval_requests()
    if text.startswith("add "):
        payload = text[4:]
        title, _, summary = payload.partition("|")
        return add_approval_request(title, summary, source=context.get("source", "jarvis"))
    if text.startswith("approve "):
        payload = text[8:]
        item_id, _, note = payload.partition("|")
        return decide_approval(item_id.strip(), "approve", note)
    if text.startswith("reject "):
        payload = text[7:]
        item_id, _, note = payload.partition("|")
        return decide_approval(item_id.strip(), "reject", note)
    if text.startswith("wake "):
        payload = text[5:]
        resume_at, _, note = payload.partition("|")
        return schedule_claude_resume(resume_at.strip(), note)
    if text == "status":
        return get_claude_resume_status()
    if text == "autopilot":
        return get_autopilot_status()
    if text.startswith("sleep on"):
        note = text.partition("|")[2]
        return set_autopilot(True, "sleep", note)
    if text.startswith("sleep off"):
        note = text.partition("|")[2]
        return set_autopilot(False, "manual", note)
    if text == "auto-approve":
        return process_pending_auto_approvals()
    return (
        "Kullanim:\n"
        "- list\n"
        "- add Baslik | Ozet\n"
        "- approve ID | not\n"
        "- reject ID | not\n"
        "- wake 09:02 | not\n"
        "- status\n"
        "- autopilot\n"
        "- sleep on | not\n"
        "- sleep off | not\n"
        "- auto-approve"
    )
