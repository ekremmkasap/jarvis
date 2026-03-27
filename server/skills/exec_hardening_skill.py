"""
Jarvis - Exec Hardening Skill
"""
import re, json
from pathlib import Path
from datetime import datetime

AUDIT_PATH = Path(__file__).parent.parent / "logs" / "security_audit.jsonl"

FORBIDDEN_SUBSTRINGS = [
    "rm -rf", "del /f", "format c:", "shutdown", ":(){:|:&};:",
    "dd if=", "mkfs", "wget http", "curl http", "> /dev/sd",
]

FORBIDDEN_REGEX = [
    r"os\.system",
    r"subprocess\.call.*shell=True",
    r"eval\(",
    r"exec\(",
    r"__import__",
]

def is_safe_command(command: str) -> bool:
    cmd = command.lower()
    for sub in FORBIDDEN_SUBSTRINGS:
        if sub in cmd:
            return False
    for pat in FORBIDDEN_REGEX:
        if re.search(pat, command):
            return False
    return True

def is_safe_path(path: str) -> bool:
    blocked = ["system32", "windows", "/etc/passwd", "/etc/shadow", "ntuser"]
    p = path.lower().replace("\\", "/")
    return not any(b in p for b in blocked)

def harden_exec_request(command: str, path_value: str = "") -> dict:
    safe = is_safe_command(command) and (not path_value or is_safe_path(path_value))
    if not safe:
        record_security_event("blocked_exec", {"command": command[:200], "path": path_value})
        return {"allowed": False, "reason": "Blocked by exec hardening"}
    return {"allowed": True}

def record_security_event(event_type: str, detail: dict):
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": datetime.utcnow().isoformat(), "event": event_type, **detail}
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + chr(10))
