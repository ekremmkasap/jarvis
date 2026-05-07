from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from server.skills.luna_scan_skill import parse_foxguard_output, run_foxguard_scan


ROOT_DIR = Path(__file__).resolve().parents[2]
LUNA_TARGETS_PATH = ROOT_DIR / "config" / "luna_targets.yaml"
LUNA_AUDIT_LOG_PATH = ROOT_DIR / "server" / "logs" / "luna_audit.jsonl"


class LunaAgentError(RuntimeError):
    pass


class TargetNotAuthorizedError(LunaAgentError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_target_id(target_id: str) -> str:
    return str(target_id or "").strip().lower()


def _targets_path() -> Path:
    override = os.environ.get("LUNA_TARGETS_PATH", "").strip()
    return Path(override).expanduser() if override else LUNA_TARGETS_PATH


def _audit_log_path() -> Path:
    override = os.environ.get("LUNA_AUDIT_LOG_PATH", "").strip()
    return Path(override).expanduser() if override else LUNA_AUDIT_LOG_PATH


def _load_authorized_targets() -> list[dict[str, Any]]:
    path = _targets_path()
    if not path.exists():
        return []
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []

    if isinstance(payload, list):
        raw_targets = payload
    elif isinstance(payload, dict):
        raw_targets = payload.get("targets") or payload.get("authorized_targets") or []
    else:
        raw_targets = []

    targets: list[dict[str, Any]] = []
    for item in raw_targets:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        normalized["id"] = _normalize_target_id(item.get("id", ""))
        targets.append(normalized)
    return [item for item in targets if item.get("id")]


def is_authorized(target_id: str) -> dict[str, Any]:
    normalized_target_id = _normalize_target_id(target_id)
    for target in _load_authorized_targets():
        if target.get("id") == normalized_target_id:
            return target
    raise TargetNotAuthorizedError(f"Target yetkili degil: {target_id}")


def audit_log(
    action: str,
    target: str,
    finding: str | None = None,
    severity: str | None = None,
    notes: str = "",
) -> None:
    try:
        path = _audit_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": _now_iso(),
            "persona": "luna",
            "target": str(target or "").strip(),
            "action": str(action or "").strip(),
            "finding_id": str(finding).strip() if finding else None,
            "severity": str(severity).strip().lower() if severity else None,
            "notes": str(notes or "").strip(),
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


def _resolve_scan_path(target: dict[str, Any]) -> Path:
    raw_path = str(target.get("scan_path") or target.get("path") or ".").strip()
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (ROOT_DIR / path).resolve(strict=False)
    return path


def scan_target(target_id: str) -> dict[str, Any]:
    target = is_authorized(target_id)
    scan_path = _resolve_scan_path(target)
    if not scan_path.exists():
        result = {
            "ok": False,
            "target_id": target["id"],
            "error": "scan_path_missing",
            "path": str(scan_path),
            "findings": [],
        }
        audit_log("scan", target["id"], notes=f"scan_path_missing:{scan_path}")
        return result

    try:
        raw_result = run_foxguard_scan(scan_path)
        if not raw_result.get("ok"):
            error = str(raw_result.get("error") or "scan_failed")
            audit_log("scan", target["id"], notes=error)
            return {
                "ok": False,
                "target_id": target["id"],
                "error": error,
                "path": str(scan_path),
                "findings": [],
                "raw_result": raw_result,
            }

        findings = parse_foxguard_output(raw_result)
        for finding in findings:
            audit_log(
                "scan_finding",
                target["id"],
                finding=finding.get("id"),
                severity=finding.get("severity"),
                notes=finding.get("title") or finding.get("description") or "",
            )
        audit_log("scan", target["id"], notes=f"ok:{len(findings)}")
        return {
            "ok": True,
            "target_id": target["id"],
            "path": str(scan_path),
            "findings": findings,
            "raw_result": raw_result,
        }
    except Exception as exc:
        audit_log("scan", target["id"], notes=f"exception:{exc}")
        return {
            "ok": False,
            "target_id": target["id"],
            "error": "scan_exception",
            "details": str(exc),
            "path": str(scan_path),
            "findings": [],
        }


def run_luna_task(
    task_type: str,
    target_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task_name = str(task_type or "").strip().lower()
    if task_name == "scan":
        return scan_target(target_id)
    return {
        "ok": False,
        "target_id": _normalize_target_id(target_id),
        "error": "unsupported_task",
        "task_type": task_name,
        "payload": dict(payload or {}),
    }
