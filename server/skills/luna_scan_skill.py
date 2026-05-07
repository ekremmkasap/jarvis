from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _normalize_severity(value: object) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"critical", "crit", "sev0", "p0"}:
        return "critical"
    if raw in {"high", "sev1", "p1"}:
        return "high"
    if raw in {"medium", "moderate", "med", "sev2", "p2"}:
        return "medium"
    if raw in {"low", "sev3", "p3"}:
        return "low"
    return "info"


def _coerce_issue_list(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("findings", "issues", "results", "alerts", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [payload] if payload else []


def run_foxguard_scan(path: str | Path) -> dict:
    scan_path = Path(path).expanduser()
    foxguard_bin = shutil.which("foxguard")
    if not foxguard_bin:
        return {
            "ok": False,
            "error": "foxguard_not_installed",
            "path": str(scan_path),
        }

    try:
        completed = subprocess.run(
            [foxguard_bin, "scan", "--path", str(scan_path), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": "foxguard_execution_failed",
            "path": str(scan_path),
            "details": str(exc),
        }

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        return {
            "ok": False,
            "error": "foxguard_scan_failed",
            "path": str(scan_path),
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    return {
        "ok": True,
        "path": str(scan_path),
        "raw": stdout,
        "stderr": stderr,
    }


def parse_foxguard_output(raw: object) -> list[dict]:
    payload = raw
    if isinstance(raw, dict) and "raw" in raw:
        payload = raw.get("raw", "")

    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return []
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []

    findings: list[dict] = []
    for index, issue in enumerate(_coerce_issue_list(payload), start=1):
        severity = _normalize_severity(
            issue.get("severity")
            or issue.get("level")
            or issue.get("priority")
        )
        rule_id = str(
            issue.get("rule_id")
            or issue.get("rule")
            or issue.get("id")
            or f"foxguard-{index}"
        )
        title = str(
            issue.get("title")
            or issue.get("message")
            or issue.get("description")
            or rule_id
        ).strip()
        description = str(issue.get("description") or title).strip()
        location = issue.get("location") or issue.get("path") or issue.get("file") or ""
        findings.append(
            {
                "id": rule_id,
                "severity": severity,
                "type": str(issue.get("type") or "foxguard").strip() or "foxguard",
                "title": title,
                "description": description,
                "evidence": str(location).strip(),
                "status": "new",
                "found_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )
    return findings
