from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.security.persona_capabilities import (
    ACTION_OPENCLAW_DELIVER,
    ACTION_OPENCLAW_HELPER,
    ACTION_OPERATOR_HIGH,
    ACTION_PC_HIGH,
    ACTION_PC_LOW,
    ACTION_PC_MEDIUM,
    ACTION_SHELL_FULL,
    ACTION_SHELL_SAFE,
    resolve_capability,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
AUDIT_LOG_PATH = ROOT_DIR / "server" / "logs" / "security_policy.jsonl"

SAFE_SHELL_PREFIXES = {
    "dir",
    "echo",
    "ping",
    "ipconfig",
    "tasklist",
    "ollama",
    "python",
    "python3",
    "where",
    "ls",
    "ps",
    "free",
    "df",
}

DENY_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"\bmkfs\b",
    r"\bformat\s+[a-z]:",
    r"del\s+/f\s+/s\s+/q\s+c:\\",
    r"shutdown\s+/s",
    r"curl.+\|\s*(bash|sh)",
    r"wget.+\|\s*(bash|sh)",
]

SENSITIVE_PATTERNS = [
    r"\.env\b",
    r"\bcredential",
    r"\btoken\b",
    r"\bsecret\b",
    r"\bapi[_ -]?key\b",
    r"\bdeploy\b",
    r"\bpayment\b",
    r"\bbridge\.py\b",
    r"\bhey_jarvis\.py\b",
]


@dataclass
class PolicyDecision:
    allowed: bool
    status: str
    risk: str
    reason: str
    action: str
    audit_id: str
    approval_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _compile_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _write_audit(event: dict[str, Any]) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _request_approval(title: str, summary: str, source: str, risk: str) -> dict[str, Any]:
    try:
        from server.skills.approval_skill import create_approval_request
    except Exception:
        from skills.approval_skill import create_approval_request
    return create_approval_request(title=title, summary=summary, source=source, risk=risk)


def _log_decision(decision: PolicyDecision, source: str, target: str, payload: str) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_id": decision.audit_id,
        "source": source,
        "target": target,
        "decision": asdict(decision),
        "payload_preview": payload[:240],
    }
    _write_audit(event)


def _normalize_persona(persona_id: str | None) -> str:
    return str(persona_id or "").strip().lower() or "jarvis"


def _bumped_risk(current: str) -> str:
    if current == "low":
        return "medium"
    return current


def _apply_persona_matrix(
    decision: PolicyDecision,
    *,
    persona_id: str,
    action_class: str,
    approval_title: str,
    approval_summary: str,
    source: str,
) -> PolicyDecision:
    normalized_persona = _normalize_persona(persona_id)
    capability = resolve_capability(normalized_persona, action_class)
    metadata = dict(decision.metadata)
    metadata["persona_id"] = normalized_persona
    metadata["action_class"] = action_class
    metadata["persona_matrix"] = capability

    if decision.status == "denied":
        decision.metadata = metadata
        return decision

    if capability == "allow":
        decision.metadata = metadata
        return decision

    if capability == "deny":
        return PolicyDecision(
            allowed=False,
            status="denied",
            risk=_bumped_risk(decision.risk),
            reason="persona-policy-denied",
            action=decision.action,
            audit_id=decision.audit_id,
            approval_id=None,
            metadata=metadata,
        )

    # capability == "require_approval"
    if decision.status == "approval_required":
        decision.metadata = metadata
        return decision

    approval = _request_approval(
        title=approval_title,
        summary=approval_summary[:400],
        source=source,
        risk=_bumped_risk(decision.risk),
    )
    approval_status = str(approval.get("status") or "pending")
    metadata["approval_status"] = approval_status
    return PolicyDecision(
        allowed=approval_status == "approved",
        status="allowed" if approval_status == "approved" else "approval_required",
        risk=_bumped_risk(decision.risk),
        reason=(
            "approval-granted"
            if approval_status == "approved"
            else "persona-policy-requires-approval"
        ),
        action=decision.action,
        audit_id=decision.audit_id,
        approval_id=str(approval.get("id") or "") or None,
        metadata=metadata,
    )


def evaluate_shell_command(
    command: str,
    *,
    full_access: bool,
    source: str = "bridge",
    persona_id: str = "jarvis",
) -> PolicyDecision:
    audit_id = str(uuid.uuid4())[:10]
    normalized = str(command or "").strip()
    lowered = normalized.lower()
    first_token = normalized.split(maxsplit=1)[0].lower() if normalized else ""
    action_class = ACTION_SHELL_FULL if full_access else ACTION_SHELL_SAFE
    action_label = "shell_full" if full_access else "shell_safe"

    if not normalized:
        decision = PolicyDecision(
            allowed=False,
            status="denied",
            risk="low",
            reason="empty-command",
            action=action_label,
            audit_id=audit_id,
        )
    elif _compile_any(DENY_PATTERNS, lowered):
        decision = PolicyDecision(
            allowed=False,
            status="denied",
            risk="critical",
            reason="dangerous-pattern",
            action=action_label,
            audit_id=audit_id,
        )
    elif not full_access:
        if first_token not in SAFE_SHELL_PREFIXES:
            decision = PolicyDecision(
                allowed=False,
                status="denied",
                risk="medium",
                reason="not-in-safe-allowlist",
                action=action_label,
                audit_id=audit_id,
                metadata={"first_token": first_token},
            )
        else:
            decision = PolicyDecision(
                allowed=True,
                status="allowed",
                risk="low",
                reason="safe-allowlist",
                action=action_label,
                audit_id=audit_id,
                metadata={"first_token": first_token},
            )
    else:
        risk = "high" if _compile_any(SENSITIVE_PATTERNS, lowered) else "medium"
        approval = _request_approval(
            title=f"Shell komutu icin onay gerekli: {first_token or 'shell'}",
            summary=normalized[:400],
            source=source,
            risk=risk,
        )
        status = str(approval.get("status") or "pending")
        decision = PolicyDecision(
            allowed=status == "approved",
            status="allowed" if status == "approved" else "approval_required",
            risk=risk,
            reason=(
                "full-shell-requires-approval" if status != "approved" else "approval-granted"
            ),
            action=action_label,
            audit_id=audit_id,
            approval_id=str(approval.get("id") or "") or None,
            metadata={"approval_status": status, "first_token": first_token},
        )

    decision = _apply_persona_matrix(
        decision,
        persona_id=persona_id,
        action_class=action_class,
        approval_title=f"Shell komutu (persona) icin onay gerekli: {first_token or 'shell'}",
        approval_summary=normalized,
        source=source,
    )
    _log_decision(decision, source, "shell", normalized)
    return decision


def evaluate_openclaw_task(
    task: str,
    *,
    deliver: bool,
    source: str = "openclaw_bridge",
    runtime_warnings: list[str] | None = None,
    persona_id: str = "sabrican",
) -> PolicyDecision:
    audit_id = str(uuid.uuid4())[:10]
    normalized = str(task or "").strip()
    lowered = normalized.lower()
    warnings = [str(item) for item in (runtime_warnings or []) if str(item)]
    action_class = ACTION_OPENCLAW_DELIVER if deliver else ACTION_OPENCLAW_HELPER

    if not normalized:
        decision = PolicyDecision(
            allowed=False,
            status="denied",
            risk="low",
            reason="empty-task",
            action="openclaw_agent_run",
            audit_id=audit_id,
        )
    elif _compile_any(DENY_PATTERNS, lowered):
        decision = PolicyDecision(
            allowed=False,
            status="denied",
            risk="critical",
            reason="dangerous-pattern",
            action="openclaw_agent_run",
            audit_id=audit_id,
            metadata={"runtime_warnings": warnings},
        )
    elif deliver or _compile_any(SENSITIVE_PATTERNS, lowered):
        risk = "high" if _compile_any(SENSITIVE_PATTERNS, lowered) else "medium"
        approval = _request_approval(
            title="OpenClaw agent gorevi icin onay gerekli",
            summary=normalized[:400],
            source=source,
            risk=risk,
        )
        approval_status = str(approval.get("status") or "pending")
        decision = PolicyDecision(
            allowed=approval_status == "approved",
            status="allowed" if approval_status == "approved" else "approval_required",
            risk=risk,
            reason=(
                "approval-granted"
                if approval_status == "approved"
                else "openclaw-task-requires-approval"
            ),
            action="openclaw_agent_run",
            audit_id=audit_id,
            approval_id=str(approval.get("id") or "") or None,
            metadata={
                "runtime_warnings": warnings,
                "approval_status": approval_status,
                "deliver": deliver,
            },
        )
    else:
        decision = PolicyDecision(
            allowed=True,
            status="allowed",
            risk="low",
            reason="helper-task-allowed",
            action="openclaw_agent_run",
            audit_id=audit_id,
            metadata={"runtime_warnings": warnings, "deliver": deliver},
        )

    decision = _apply_persona_matrix(
        decision,
        persona_id=persona_id,
        action_class=action_class,
        approval_title="OpenClaw agent (persona) icin onay gerekli",
        approval_summary=normalized,
        source=source,
    )
    _log_decision(decision, source, "openclaw_agent", normalized)
    return decision


def evaluate_channel_delivery(
    channel: str,
    payload_preview: str,
    *,
    source: str = "openclaw_bridge",
) -> PolicyDecision:
    audit_id = str(uuid.uuid4())[:10]
    normalized_channel = str(channel or "").strip().lower()
    preview = str(payload_preview or "").strip()

    if normalized_channel != "telegram":
        decision = PolicyDecision(
            allowed=False,
            status="denied",
            risk="low",
            reason="unsupported-channel",
            action="channel_delivery",
            audit_id=audit_id,
        )
        _log_decision(decision, source, normalized_channel or "channel", preview)
        return decision

    if _compile_any(DENY_PATTERNS, preview.lower()):
        decision = PolicyDecision(
            allowed=False,
            status="denied",
            risk="high",
            reason="dangerous-pattern",
            action="channel_delivery",
            audit_id=audit_id,
        )
        _log_decision(decision, source, normalized_channel, preview)
        return decision

    decision = PolicyDecision(
        allowed=True,
        status="allowed",
        risk="low",
        reason="channel-allowlisted",
        action="channel_delivery",
        audit_id=audit_id,
        metadata={"channel": normalized_channel},
    )
    _log_decision(decision, source, normalized_channel, preview)
    return decision


def _pc_action_class(action: str, key: str, args: str) -> str:
    normalized_action = str(action or "").strip().lower()
    normalized_key = str(key or "").strip().lower()
    lowered_args = str(args or "").strip().lower()

    if normalized_action in {"sleep_pc", "stop_jarvis", "send_file"}:
        return ACTION_PC_HIGH
    if normalized_action == "open_app":
        app_name = lowered_args or normalized_key
        if app_name in {"terminal", "cmd", "powershell"}:
            return ACTION_PC_HIGH
        return ACTION_PC_LOW
    if normalized_action == "clipboard_read":
        return ACTION_PC_MEDIUM
    if normalized_action in {"lock_screen", "clipboard_clear", "type_text"}:
        return ACTION_PC_MEDIUM
    if normalized_action in {"open_url", "web_search"} and _compile_any(
        SENSITIVE_PATTERNS, lowered_args
    ):
        return ACTION_PC_MEDIUM
    return ACTION_PC_LOW


def evaluate_pc_action(
    command_key: str,
    *,
    action: str,
    args: str = "",
    persona_id: str = "jarvis",
    chat_id: int = 0,
    rule: dict[str, Any] | None = None,
    source: str = "pc_control_gateway",
) -> PolicyDecision:
    audit_id = str(uuid.uuid4())[:10]
    normalized_key = str(command_key or "").strip().lower()
    normalized_action = str(action or "").strip().lower()
    normalized_args = str(args or "").strip()
    lowered_args = normalized_args.lower()
    rule = rule if isinstance(rule, dict) else {}
    action_class = _pc_action_class(normalized_action, normalized_key, normalized_args)

    if _compile_any(DENY_PATTERNS, lowered_args):
        decision = PolicyDecision(
            allowed=False,
            status="denied",
            risk="critical",
            reason="dangerous-pattern",
            action=normalized_action or normalized_key or "pc_action",
            audit_id=audit_id,
            metadata={"persona_id": persona_id, "chat_id": chat_id},
        )
        decision = _apply_persona_matrix(
            decision,
            persona_id=persona_id,
            action_class=action_class,
            approval_title=f"PC komutu (persona) icin onay gerekli: {normalized_key or normalized_action}",
            approval_summary=normalized_args or normalized_action,
            source=source,
        )
        _log_decision(decision, source, normalized_key or "pc_control", normalized_args)
        return decision

    requires_confirmation = bool(rule.get("requires_confirmation"))
    risk = "low"
    require_approval = False

    if normalized_action in {"sleep_pc", "stop_jarvis"}:
        risk = "high"
        require_approval = True
    elif normalized_action in {"send_file", "clipboard_read"}:
        risk = "high" if normalized_action == "send_file" else "medium"
        require_approval = True
    elif normalized_action == "open_app":
        app_name = lowered_args or normalized_key
        if app_name in {"terminal", "cmd", "powershell"}:
            risk = "high"
            require_approval = True
        else:
            risk = "low"
    elif normalized_action in {"lock_screen", "clipboard_clear", "type_text"}:
        risk = "medium"
    elif normalized_action in {"open_url", "web_search"} and _compile_any(
        SENSITIVE_PATTERNS, lowered_args
    ):
        risk = "medium"
        require_approval = True

    if requires_confirmation:
        require_approval = True
        if risk == "low":
            risk = "medium"

    if require_approval:
        approval = _request_approval(
            title=f"PC komutu icin onay gerekli: {normalized_key or normalized_action}",
            summary=normalized_args[:400] or normalized_action,
            source=source,
            risk=risk,
        )
        approval_status = str(approval.get("status") or "pending")
        decision = PolicyDecision(
            allowed=approval_status == "approved",
            status="allowed" if approval_status == "approved" else "approval_required",
            risk=risk,
            reason=(
                "approval-granted"
                if approval_status == "approved"
                else "pc-action-requires-approval"
            ),
            action=normalized_action or normalized_key or "pc_action",
            audit_id=audit_id,
            approval_id=str(approval.get("id") or "") or None,
            metadata={
                "persona_id": persona_id,
                "chat_id": chat_id,
                "approval_status": approval_status,
                "command_key": normalized_key,
            },
        )
    else:
        decision = PolicyDecision(
            allowed=True,
            status="allowed",
            risk=risk,
            reason="pc-action-allowed",
            action=normalized_action or normalized_key or "pc_action",
            audit_id=audit_id,
            metadata={
                "persona_id": persona_id,
                "chat_id": chat_id,
                "command_key": normalized_key,
            },
        )

    decision = _apply_persona_matrix(
        decision,
        persona_id=persona_id,
        action_class=action_class,
        approval_title=f"PC komutu (persona) icin onay gerekli: {normalized_key or normalized_action}",
        approval_summary=normalized_args or normalized_action,
        source=source,
    )
    _log_decision(decision, source, normalized_key or "pc_control", normalized_args)
    return decision


def evaluate_operator_action(
    action_name: str,
    payload_preview: str = "",
    *,
    source: str = "bridge",
    risk: str = "medium",
    require_approval: bool = False,
    persona_id: str = "jarvis",
    action_class: str | None = None,
) -> PolicyDecision:
    audit_id = str(uuid.uuid4())[:10]
    normalized_action = str(action_name or "").strip() or "operator_action"
    preview = str(payload_preview or "").strip()

    if _compile_any(DENY_PATTERNS, preview.lower()):
        decision = PolicyDecision(
            allowed=False,
            status="denied",
            risk="critical",
            reason="dangerous-pattern",
            action=normalized_action,
            audit_id=audit_id,
        )
    elif require_approval:
        approval = _request_approval(
            title=f"Operator aksiyonu icin onay gerekli: {normalized_action}",
            summary=preview[:400] or normalized_action,
            source=source,
            risk=risk,
        )
        approval_status = str(approval.get("status") or "pending")
        decision = PolicyDecision(
            allowed=approval_status == "approved",
            status="allowed" if approval_status == "approved" else "approval_required",
            risk=risk,
            reason=(
                "approval-granted"
                if approval_status == "approved"
                else "operator-action-requires-approval"
            ),
            action=normalized_action,
            audit_id=audit_id,
            approval_id=str(approval.get("id") or "") or None,
            metadata={"approval_status": approval_status},
        )
    else:
        decision = PolicyDecision(
            allowed=True,
            status="allowed",
            risk=risk,
            reason="operator-action-allowed",
            action=normalized_action,
            audit_id=audit_id,
        )

    decision = _apply_persona_matrix(
        decision,
        persona_id=persona_id,
        action_class=str(action_class or ACTION_OPERATOR_HIGH),
        approval_title=f"Operator aksiyonu (persona) icin onay gerekli: {normalized_action}",
        approval_summary=preview or normalized_action,
        source=source,
    )
    _log_decision(decision, source, normalized_action, preview)
    return decision


def format_policy_block_message(decision: PolicyDecision) -> str:
    if decision.status == "approval_required" and decision.approval_id:
        return (
            f"Bu eylem policy gate tarafindan beklemeye alindi. "
            f"Onay kodu: #{decision.approval_id} | risk: {decision.risk} | neden: {decision.reason}"
        )
    return f"Bu eylem policy gate tarafindan engellendi. risk: {decision.risk} | neden: {decision.reason}"
