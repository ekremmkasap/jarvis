from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT_DIR / "server" / "config" / "agent_manifests.json"
CANONICAL_TASK_TYPES = {
    "analysis",
    "audit",
    "backend",
    "bridge",
    "deployment_check",
    "desktop_ui",
    "fallback",
    "handoff",
    "hologram",
    "media_runtime",
    "memory",
    "orchestration",
    "policy_check",
    "presentation",
    "redaction",
    "routing",
    "security",
    "shell_check",
    "summary",
    "video",
    "visual",
    "voice",
    "workspace",
    "workspace_media",
}
TASK_TYPE_ALIASES = {
    "analyze": "analysis",
    "deploy": "deployment_check",
    "deployment": "deployment_check",
    "desktop": "desktop_ui",
    "media": "media_runtime",
    "policy": "policy_check",
    "presentation_ui": "presentation",
    "research": "analysis",
    "reel": "video",
    "routing_task": "routing",
    "shell": "shell_check",
    "workspace_trend": "workspace",
}


def _default_manifest(agent_id: str = "") -> dict[str, Any]:
    return {
        "id": agent_id,
        "label": agent_id or "-",
        "role": "unknown",
        "provider": "local",
        "risk_level": "unknown",
        "approval_mode": "auto",
        "allowed_task_types": [],
        "handoff_targets": [],
        "memory_scope": "none",
        "active": False,
    }


def _normalize_manifest(raw: Any) -> dict[str, Any]:
    manifest = _default_manifest(str((raw or {}).get("id") or ""))
    if isinstance(raw, dict):
        manifest.update(raw)
    manifest["id"] = str(manifest.get("id") or "").strip()
    manifest["label"] = str(manifest.get("label") or manifest["id"] or "-").strip() or "-"
    manifest["role"] = str(manifest.get("role") or "unknown").strip() or "unknown"
    manifest["provider"] = str(manifest.get("provider") or "local").strip() or "local"
    manifest["risk_level"] = str(manifest.get("risk_level") or "unknown").strip() or "unknown"
    manifest["approval_mode"] = str(manifest.get("approval_mode") or "auto").strip() or "auto"
    manifest["memory_scope"] = str(manifest.get("memory_scope") or "none").strip() or "none"
    manifest["active"] = bool(manifest.get("active"))
    manifest["allowed_task_types"] = [str(item).strip() for item in (manifest.get("allowed_task_types") or []) if str(item).strip()]
    manifest["handoff_targets"] = [str(item).strip() for item in (manifest.get("handoff_targets") or []) if str(item).strip()]
    manifest["aliases"] = [str(item).strip().lower() for item in (manifest.get("aliases") or []) if str(item).strip()]
    return manifest


def load_agent_manifests() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    manifests = data.get("agents") if isinstance(data, dict) else []
    result: dict[str, dict[str, Any]] = {}
    for item in manifests or []:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_manifest(item)
        if normalized["id"]:
            result[normalized["id"]] = normalized
    return result


def _resolve_agent_id(agent_id: str) -> str:
    key = str(agent_id or "").strip().lower()
    if not key:
        return ""
    manifests = load_agent_manifests()
    if key in manifests:
        return key
    for manifest_id, manifest in manifests.items():
        aliases = [str(item).strip().lower() for item in (manifest.get("aliases") or []) if str(item).strip()]
        if key in aliases:
            return manifest_id
    return key


def normalize_task_type(task_type: str, fallback: str = "summary") -> str:
    task_key = str(task_type or "").strip().lower()
    task_key = TASK_TYPE_ALIASES.get(task_key, task_key)
    if task_key in CANONICAL_TASK_TYPES:
        return task_key
    fallback_key = str(fallback or "summary").strip().lower()
    fallback_key = TASK_TYPE_ALIASES.get(fallback_key, fallback_key)
    if fallback_key in CANONICAL_TASK_TYPES:
        return fallback_key
    return "summary"


def is_known_task_type(task_type: str) -> bool:
    task_key = str(task_type or "").strip().lower()
    return task_key in CANONICAL_TASK_TYPES or task_key in TASK_TYPE_ALIASES


def validate_agent_manifests() -> dict[str, Any]:
    manifests = load_agent_manifests()
    invalid_task_types: list[dict[str, str]] = []
    missing_handoffs: list[str] = []
    inactive_agents: list[str] = []
    empty_allowed_types: list[str] = []
    unknown_handoff_targets: list[dict[str, str]] = []
    approval_consistency_warnings: list[dict[str, str]] = []
    role_consistency_warnings: list[dict[str, str]] = []

    all_agent_ids = set(manifests.keys())

    for agent_id, manifest in manifests.items():
        risk_level = str(manifest.get("risk_level") or "").strip().lower()
        approval_mode = str(manifest.get("approval_mode") or "").strip().lower()
        role = str(manifest.get("role") or "").strip().lower()
        if not bool(manifest.get("active")):
            inactive_agents.append(agent_id)

        if risk_level == "high" and approval_mode != "always":
            approval_consistency_warnings.append({
                "agent": agent_id,
                "risk_level": risk_level,
                "approval_mode": approval_mode or "-",
                "reason": "high risk icin approval_mode=always beklenir",
            })
        elif risk_level == "low" and approval_mode in {"review_required", "always"}:
            approval_consistency_warnings.append({
                "agent": agent_id,
                "risk_level": risk_level,
                "approval_mode": approval_mode,
                "reason": "low risk icin daha hafif approval mode beklenir",
            })

        allowed = manifest.get("allowed_task_types") or []
        allowed_set = {normalize_task_type(str(item), fallback="summary") for item in allowed}
        if not allowed:
            empty_allowed_types.append(agent_id)

        if role == "reviewer" and any(task in allowed_set for task in {"backend", "bridge", "deployment_check", "shell_check", "voice", "video", "workspace"}):
            role_consistency_warnings.append({
                "agent": agent_id,
                "role": role,
                "reason": "reviewer rolu write/execute agir task type tasiyor",
            })
        if role == "curator" and any(task in allowed_set for task in {"bridge", "deployment_check", "shell_check", "voice", "hologram"}):
            role_consistency_warnings.append({
                "agent": agent_id,
                "role": role,
                "reason": "curator rolu memory disi operasyonel task type tasiyor",
            })
        if role == "operator" and not any(task in allowed_set for task in {"voice", "hologram", "desktop_ui", "media_runtime"}):
            role_consistency_warnings.append({
                "agent": agent_id,
                "role": role,
                "reason": "operator rolu icin beklenen runtime task type eksik",
            })

        for raw_task_type in allowed:
            normalized = normalize_task_type(str(raw_task_type), fallback="summary")
            raw_key = str(raw_task_type or "").strip().lower()
            if raw_key not in CANONICAL_TASK_TYPES and normalized == "summary" and raw_key != "summary":
                invalid_task_types.append({"agent": agent_id, "task_type": raw_key})

        targets = [str(item).strip().lower() for item in (manifest.get("handoff_targets") or []) if str(item).strip()]
        if not targets:
            missing_handoffs.append(agent_id)
        else:
            for target in targets:
                if target and target not in all_agent_ids:
                    unknown_handoff_targets.append({"agent": agent_id, "unknown_target": target})

    return {
        "ok": not invalid_task_types and not empty_allowed_types and not missing_handoffs,
        "total_agents": len(manifests),
        "invalid_task_types": invalid_task_types,
        "missing_handoffs": missing_handoffs,
        "inactive_agents": inactive_agents,
        "empty_allowed_task_types": empty_allowed_types,
        "unknown_handoff_targets": unknown_handoff_targets,
        "approval_consistency_warnings": approval_consistency_warnings,
        "role_consistency_warnings": role_consistency_warnings,
    }


def get_agent_manifest(agent_id: str) -> dict[str, Any] | None:
    key = _resolve_agent_id(agent_id)
    if not key:
        return None
    return load_agent_manifests().get(key)


def can_accept_task(agent_id: str, task_type: str) -> bool:
    manifest = get_agent_manifest(agent_id)
    if not manifest or not manifest.get("active"):
        return False
    task_key = normalize_task_type(task_type)
    allowed = [str(item).strip().lower() for item in (manifest.get("allowed_task_types") or [])]
    return bool(task_key and task_key in allowed)


def can_handoff(from_agent: str, to_agent: str) -> bool:
    manifest = get_agent_manifest(from_agent)
    if not manifest or not manifest.get("active"):
        return False
    target = _resolve_agent_id(to_agent)
    targets = [str(item).strip().lower() for item in (manifest.get("handoff_targets") or [])]
    return bool(target and target in targets)


def requires_approval(agent_id: str, task_type: str) -> bool:
    manifest = get_agent_manifest(agent_id)
    if not manifest:
        return True
    mode = str(manifest.get("approval_mode") or "auto").strip().lower()
    task_key = normalize_task_type(task_type)
    if mode == "always":
        return True
    if mode == "review_required":
        return task_key not in {"summary", "analysis", "policy_check"}
    return False


def dispatch_policy_check(from_agent: str, to_agent: str, task_type: str) -> dict[str, Any]:
    source = _resolve_agent_id(from_agent)
    target = _resolve_agent_id(to_agent)
    task_key = normalize_task_type(task_type)
    manifest = get_agent_manifest(target)

    result = {
        "from_agent": source or "-",
        "to_agent": target or "-",
        "task_type": task_key or "-",
        "has_manifest": bool(manifest),
        "active": bool((manifest or {}).get("active")),
        "accepted": can_accept_task(target, task_key),
        "handoff_ok": can_handoff(source, target),
        "approval_needed": requires_approval(target, task_key),
        "policy_status": "ok",
        "blocking_reason": "",
        "warning_reasons": [],
    }

    if not result["has_manifest"]:
        result["policy_status"] = "blocked"
        result["blocking_reason"] = "manifest yok"
        return result
    if not result["active"]:
        result["policy_status"] = "blocked"
        result["blocking_reason"] = "agent aktif degil"
        return result
    if not result["handoff_ok"]:
        result["policy_status"] = "blocked"
        result["blocking_reason"] = "handoff izni yok"
        return result
    if not result["accepted"]:
        result["policy_status"] = "blocked"
        result["blocking_reason"] = f"task_type uyumsuz: {task_key or '-'}"
        return result
    if result["approval_needed"]:
        result["warning_reasons"].append("onay onerilir")
    if result["warning_reasons"]:
        result["policy_status"] = "warn"
    return result


def build_agent_policy_report() -> str:
    manifests = load_agent_manifests()
    if not manifests:
        return "AGENT POLITIKA\n\nManifest bulunamadi."

    validation = validate_agent_manifests()

    lines = [
        "AGENT POLITIKA",
        f"Toplam agent: {len(manifests)}",
        f"Validation: {'TEMIZ' if validation.get('ok') else 'UYARI_VAR'}",
    ]

    invalid = validation.get("invalid_task_types") or []
    empty = validation.get("empty_allowed_task_types") or []
    missing = validation.get("missing_handoffs") or []
    unknown = validation.get("unknown_handoff_targets") or []
    approval_warnings = validation.get("approval_consistency_warnings") or []
    role_warnings = validation.get("role_consistency_warnings") or []
    inactive = validation.get("inactive_agents") or []

    if invalid:
        lines.append(f"  [!] invalid_task: {len(invalid)}")
        for item in invalid[:3]:
            lines.append(f"      - {item.get('agent', '-')} -> {item.get('task_type', '-')}")
    if empty:
        lines.append(f"  [!] empty_allowed: {len(empty)}")
        for agent in empty[:3]:
            lines.append(f"      - {agent}")
    if missing:
        lines.append(f"  [!] missing_handoff: {len(missing)}")
        for agent in missing[:3]:
            lines.append(f"      - {agent}")
    if unknown:
        lines.append(f"  [!] unknown_target: {len(unknown)}")
        for item in unknown[:3]:
            lines.append(f"      - {item.get('agent', '-')} -> {item.get('unknown_target', '-')}")
    if inactive:
        lines.append(f"  [i] inactive: {len(inactive)} -> {', '.join(inactive)}")

    lines.append("")
    lines.append(f"[CANONICAL TASK TYPES] -> {len(CANONICAL_TASK_TYPES)}")
    lines.append(f"  {', '.join(sorted(CANONICAL_TASK_TYPES))}")
    lines.append("")
    lines.append("[ AGENT DETAY ]")

    for agent_id, item in sorted(manifests.items(), key=lambda entry: entry[0]):
        status = "ACTIVE" if item["active"] else "INACTIVE"
        lines.append(f"- {item['label']} ({agent_id}) [{status}]")
        lines.append(f"  rol: {item['role']} | risk: {item['risk_level']} | onay: {item['approval_mode']}")
        lines.append(f"  provider: {item['provider']} | memory: {item['memory_scope']}")
        lines.append(f"  task_types: {', '.join(item['allowed_task_types']) or '-'}")
        lines.append(f"  handoff: {', '.join(item['handoff_targets']) or '-'}")
        lines.append("")

    return "\n".join(lines).rstrip()


def build_manifest_validation_report() -> str:
    validation = validate_agent_manifests()
    lines = [
        "AGENT MANIFEST VALIDATION",
        f"Toplam agent: {validation.get('total_agents', 0)}",
        f"Genel durum: {'TEMIZ' if validation.get('ok') else 'UYARI_VAR'}",
        "",
    ]

    invalid = validation.get("invalid_task_types") or []
    empty = validation.get("empty_allowed_task_types") or []
    missing = validation.get("missing_handoffs") or []
    inactive = validation.get("inactive_agents") or []
    unknown = validation.get("unknown_handoff_targets") or []
    approval_warnings = validation.get("approval_consistency_warnings") or []
    role_warnings = validation.get("role_consistency_warnings") or []

    lines.append(f"[INVALID TASK TYPES] -> {len(invalid)}")
    for item in invalid[:5]:
        lines.append(f"  - {item.get('agent', '-')} -> {item.get('task_type', '-')}")
    if not invalid:
        lines.append("  (yok)")

    lines.append("")
    lines.append(f"[EMPTY ALLOWED_TASK_TYPES] -> {len(empty)}")
    for agent in empty[:5]:
        lines.append(f"  - {agent}")
    if not empty:
        lines.append("  (yok)")

    lines.append("")
    lines.append(f"[MISSING HANDOFFS] -> {len(missing)}")
    for agent in missing[:5]:
        lines.append(f"  - {agent}")
    if not missing:
        lines.append("  (yok)")

    lines.append("")
    lines.append(f"[INACTIVE AGENTS] -> {len(inactive)}")
    for agent in inactive[:5]:
        lines.append(f"  - {agent}")
    if not inactive:
        lines.append("  (yok)")

    lines.append("")
    lines.append(f"[UNKNOWN HANDOFF TARGETS] -> {len(unknown)}")
    for item in unknown[:5]:
        lines.append(f"  - {item.get('agent', '-')} -> {item.get('unknown_target', '-')}")
    if not unknown:
        lines.append("  (yok)")

    lines.append("")
    lines.append(f"[APPROVAL CONSISTENCY WARNINGS] -> {len(approval_warnings)}")
    for item in approval_warnings[:5]:
        lines.append(f"  - {item.get('agent', '-')} -> {item.get('reason', '-')}")
    if not approval_warnings:
        lines.append("  (yok)")

    lines.append("")
    lines.append(f"[ROLE CONSISTENCY WARNINGS] -> {len(role_warnings)}")
    for item in role_warnings[:5]:
        lines.append(f"  - {item.get('agent', '-')} -> {item.get('reason', '-')}")
    if not role_warnings:
        lines.append("  (yok)")

    lines.append("")
    lines.append(f"[CANONICAL TASK TYPES] -> {len(CANONICAL_TASK_TYPES)}")
    lines.append(f"  {', '.join(sorted(CANONICAL_TASK_TYPES))}")

    return "\n".join(lines)
