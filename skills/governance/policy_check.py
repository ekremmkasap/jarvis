"""
Skill: policy_check
Kategori: governance
j.txt Section 5 & 7 - Policy gate, audit trail
"""
import logging
import datetime
import json
from pathlib import Path

log = logging.getLogger("skill.policy_check")

MANIFEST = {
    "name": "policy_check",
    "version": "1.0",
    "category": "governance",
    "inputs": {"action": "str", "agent_role": "str", "context": "dict"},
    "outputs": {"allowed": "bool", "reason": "str", "audit_id": "str"},
    "permissions": ["read", "audit_write"],
    "failure_modes": ["policy_violation", "unknown_agent"],
    "logs": ["action", "agent_role", "allowed", "reason"]
}

AUDIT_LOG = Path("/opt/jarvis/logs/audit.jsonl")

# j.txt Section 7 - capability-based permissions
ROLE_PERMISSIONS = {
    "planner":     ["read", "analyze"],
    "implementer": ["read", "write", "execute"],
    "reviewer":    ["read"],
    "curator":     ["read", "memory_write"],
    "operator":    ["read", "execute", "system"],
    "core":        ["read", "write", "execute", "memory_write", "audit_write", "system"],
}

# Yasakli eylemler
FORBIDDEN_ACTIONS = ["delete_all", "drop_database", "format_disk", "rm_rf_root"]


def run(action: str, agent_role: str, context: dict = None) -> dict:
    import uuid
    audit_id = str(uuid.uuid4())[:8]
    context = context or {}

    # 1. Bilinmeyen rol kontrolu
    if agent_role not in ROLE_PERMISSIONS:
        reason = f"Unknown agent role: {agent_role}"
        _audit(audit_id, action, agent_role, False, reason)
        return {"allowed": False, "reason": reason, "audit_id": audit_id}

    # 2. Yasakli eylem kontrolu
    for forbidden in FORBIDDEN_ACTIONS:
        if forbidden in action.lower():
            reason = f"Forbidden action: {forbidden}"
            _audit(audit_id, action, agent_role, False, reason)
            return {"allowed": False, "reason": reason, "audit_id": audit_id}

    # 3. Yetki kontrolu
    role_perms = ROLE_PERMISSIONS[agent_role]
    required_perm = _infer_permission(action)
    if required_perm and required_perm not in role_perms:
        reason = f"Role '{agent_role}' lacks permission '{required_perm}' for action '{action}'"
        _audit(audit_id, action, agent_role, False, reason)
        return {"allowed": False, "reason": reason, "audit_id": audit_id}

    reason = "ok"
    _audit(audit_id, action, agent_role, True, reason)
    return {"allowed": True, "reason": reason, "audit_id": audit_id}


def _infer_permission(action: str) -> str:
    action = action.lower()
    if any(w in action for w in ["write", "create", "update", "save"]):
        return "write"
    if any(w in action for w in ["execute", "run", "start", "stop"]):
        return "execute"
    if any(w in action for w in ["delete", "remove"]):
        return "write"
    return "read"


def _audit(audit_id: str, action: str, role: str, allowed: bool, reason: str):
    entry = {
        "audit_id": audit_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "agent_role": role,
        "action": action,
        "allowed": allowed,
        "reason": reason
    }
    log.info(f"[AUDIT {audit_id}] {role} -> {action} | allowed={allowed} | {reason}")
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.error(f"Audit write failed: {e}")


if __name__ == "__main__":
    tests = [
        ("read_file", "reviewer", {}),
        ("write_file", "reviewer", {}),    # blocked - reviewer sadece okur
        ("execute_command", "implementer", {}),
        ("delete_all", "core", {}),        # blocked - forbidden
        ("analyze_code", "planner", {}),
    ]
    for action, role, ctx in tests:
        r = run(action, role, ctx)
        status = "IZIN VERILDI" if r["allowed"] else "ENGELLENDI"
        print(f"{status}: [{role}] -> {action} | {r['reason']}")
