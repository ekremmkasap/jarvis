"""
zeynep_security_skill.py — Zeynep (defensive security / KVKK persona).

Hepsi read-only audit. Offensive işlemler yok.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT_DIR / "server" / "logs" / "zeynep_security.jsonl"
MAX_FILES_PER_SCAN = 2000
MAX_FINDINGS = 200
BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".exe", ".dll",
               ".mp3", ".mp4", ".wav", ".woff", ".woff2", ".ttf", ".otf", ".sqlite", ".db"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build",
             ".pytest_cache", ".ruff_cache", ".mypy_cache", "state", "logs"}


TC_KIMLIK_RE = re.compile(r"\b[1-9]\d{10}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_TR_RE = re.compile(r"\b(?:\+?90|0)?\s*[\(\s]?5\d{2}[\)\s]?\s*\d{3}\s*\d{2}\s*\d{2}\b")
IBAN_TR_RE = re.compile(r"\bTR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b")

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key",   re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key",   re.compile(r"(?i)aws(.{0,20})?(secret|sk).{0,5}['\"=:]\s*['\"]?[A-Za-z0-9/+]{40}['\"]?")),
    ("stripe_live",      re.compile(r"\bsk_live_[0-9a-zA-Z]{24,}\b")),
    ("stripe_test",      re.compile(r"\bsk_test_[0-9a-zA-Z]{24,}\b")),
    ("openai_key",       re.compile(r"\bsk-[A-Za-z0-9\-_]{20,}\b")),
    ("anthropic_key",    re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    ("google_api",       re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("github_token",     re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("telegram_bot",     re.compile(r"\b\d{8,11}:[A-Za-z0-9_-]{30,}\b")),
    ("slack_token",      re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("generic_bearer",   re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}")),
    ("jwt",              re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("password_assign",  re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]")),
]

LOG_ANOMALY_PATTERNS = [
    ("auth_fail",         re.compile(r"(?i)(auth fail|authentication failed|401 unauthor|invalid token)")),
    ("permission_denied", re.compile(r"(?i)(permission denied|403 forbidden|access denied)")),
    ("exception",         re.compile(r"(?i)(traceback|exception|error:|\berror\b.{0,80}at line)")),
    ("rate_limit",        re.compile(r"(?i)(rate limit|429|too many requests)")),
    ("crash",             re.compile(r"(?i)(segfault|crash|panic|core dumped)")),
]


def _log_event(action: str, payload: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "persona": "zeynep",
        "action": action,
        "payload": payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _redact(match_text: str, keep_prefix: int = 4, keep_suffix: int = 0) -> str:
    value = str(match_text or "")
    if len(value) <= keep_prefix + keep_suffix + 3:
        return "[REDACTED]"
    return value[:keep_prefix] + "…[REDACTED]…" + (value[-keep_suffix:] if keep_suffix else "")


def _walk_text_files(root: Path, max_files: int = MAX_FILES_PER_SCAN) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if len(files) >= max_files:
            break
        if not path.is_file():
            continue
        parts = set(path.parts)
        if parts & SKIP_DIRS:
            continue
        if path.suffix.lower() in BINARY_EXTS:
            continue
        try:
            if path.stat().st_size > 2_000_000:  # 2MB skip
                continue
        except OSError:
            continue
        files.append(path)
    return files


def _safe_resolve(project_path: str) -> Path | None:
    try:
        resolved = Path(project_path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        return None
    if not resolved.exists():
        return None
    return resolved


def zeynep_kvkk_audit(project_path: str) -> dict[str, Any]:
    """PII pattern tarama (TC kimlik, e-posta, telefon, IBAN)."""
    root = _safe_resolve(project_path or ".")
    if root is None:
        return {"ok": False, "error": "invalid_path", "message": f"Geçerli path değil: {project_path}"}
    if not root.is_dir():
        return {"ok": False, "error": "not_a_directory", "message": f"Klasör değil: {root}"}

    findings: list[dict[str, Any]] = []
    checks = [
        ("tc_kimlik", TC_KIMLIK_RE, "high",   3, 0),
        ("email",     EMAIL_RE,     "medium", 2, 0),
        ("telefon",   PHONE_TR_RE,  "medium", 2, 0),
        ("iban",      IBAN_TR_RE,   "high",   4, 0),
    ]

    scanned = 0
    for file in _walk_text_files(root):
        scanned += 1
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            for name, pattern, severity, keep_prefix, keep_suffix in checks:
                for match in pattern.finditer(line):
                    findings.append({
                        "type": name,
                        "severity": severity,
                        "file": str(file.relative_to(root).as_posix()),
                        "line": line_no,
                        "sample": _redact(match.group(0), keep_prefix, keep_suffix),
                    })
                    if len(findings) >= MAX_FINDINGS:
                        break
                if len(findings) >= MAX_FINDINGS:
                    break
            if len(findings) >= MAX_FINDINGS:
                break
        if len(findings) >= MAX_FINDINGS:
            break

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

    result = {
        "ok": True,
        "scope": "read-only / audit",
        "root": str(root),
        "scanned_files": scanned,
        "total_findings": len(findings),
        "by_severity": severity_counts,
        "findings": findings,
    }
    _log_event("kvkk_audit", {"root": str(root), "findings": len(findings)})
    return result


def zeynep_secret_scan(path: str = ".") -> dict[str, Any]:
    """API key / token / password pattern tarama (redacted)."""
    root = _safe_resolve(path or ".")
    if root is None:
        return {"ok": False, "error": "invalid_path", "message": f"Geçerli path değil: {path}"}
    if not root.is_dir():
        return {"ok": False, "error": "not_a_directory", "message": f"Klasör değil: {root}"}

    findings: list[dict[str, Any]] = []
    scanned = 0
    for file in _walk_text_files(root):
        scanned += 1
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            for name, pattern in SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    findings.append({
                        "type": name,
                        "severity": "high",
                        "file": str(file.relative_to(root).as_posix()),
                        "line": line_no,
                        "sample": _redact(match.group(0), keep_prefix=4, keep_suffix=0),
                    })
                    if len(findings) >= MAX_FINDINGS:
                        break
                if len(findings) >= MAX_FINDINGS:
                    break
            if len(findings) >= MAX_FINDINGS:
                break
        if len(findings) >= MAX_FINDINGS:
            break

    result = {
        "ok": True,
        "scope": "read-only / audit",
        "root": str(root),
        "scanned_files": scanned,
        "total_findings": len(findings),
        "findings": findings,
    }
    _log_event("secret_scan", {"root": str(root), "findings": len(findings)})
    return result


def zeynep_log_review(log_path: str = "", since_hours: int = 24) -> dict[str, Any]:
    """Son N saatteki log dosyalarında anomali pattern'lerini topla."""
    base = _safe_resolve(log_path) if log_path else (ROOT_DIR / "server" / "logs")
    if base is None or not base.exists():
        return {"ok": False, "error": "invalid_path", "message": f"Log path bulunamadı: {log_path}"}

    try:
        hours = max(1, int(since_hours))
    except (TypeError, ValueError):
        hours = 24
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

    candidates = [base] if base.is_file() else list(base.rglob("*.log")) + list(base.rglob("*.jsonl"))
    candidates = [p for p in candidates if p.is_file()][:200]

    counters: dict[str, int] = {name: 0 for name, _ in LOG_ANOMALY_PATTERNS}
    samples: dict[str, list[str]] = {name: [] for name, _ in LOG_ANOMALY_PATTERNS}
    scanned = 0

    for file in candidates:
        try:
            mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if mtime < threshold:
            continue
        scanned += 1
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line in content.splitlines()[-500:]:
            for name, pattern in LOG_ANOMALY_PATTERNS:
                if pattern.search(line):
                    counters[name] += 1
                    if len(samples[name]) < 3:
                        samples[name].append(line[:200])

    result = {
        "ok": True,
        "scope": "read-only / audit",
        "root": str(base),
        "since_hours": hours,
        "scanned_files": scanned,
        "anomaly_counts": counters,
        "samples": samples,
    }
    _log_event("log_review", {"root": str(base), "counts": counters})
    return result


def zeynep_hardening_check(project_path: str = "") -> dict[str, Any]:
    """Temel güvenlik hijyeni kontrol listesi."""
    root = _safe_resolve(project_path or str(ROOT_DIR))
    if root is None or not root.is_dir():
        return {"ok": False, "error": "invalid_path", "message": "Geçerli proje klasörü gerekli."}

    checks: list[dict[str, Any]] = []

    env_file = root / ".env"
    gitignore = root / ".gitignore"
    env_in_gitignore = False
    if gitignore.exists():
        try:
            env_in_gitignore = ".env" in gitignore.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            env_in_gitignore = False
    checks.append({
        "id": "env_in_gitignore",
        "ok": env_in_gitignore or not env_file.exists(),
        "severity": "high",
        "note": ".env dosyası .gitignore içinde olmalı." if env_file.exists() else ".env yok, kontrol geçerli değil.",
    })

    example_env = root / ".env.example"
    checks.append({
        "id": "env_example_present",
        "ok": example_env.exists(),
        "severity": "low",
        "note": ".env.example şablon olarak repo'da tutulmalı.",
    })

    readme = root / "README.md"
    checks.append({
        "id": "readme_present",
        "ok": readme.exists(),
        "severity": "low",
        "note": "README.md mevcut (credential policy dokümantasyonu için yer).",
    })

    claude_md = root / "CLAUDE.md"
    checks.append({
        "id": "claude_md_present",
        "ok": claude_md.exists(),
        "severity": "low",
        "note": "CLAUDE.md mevcut (ajans davranış kuralları).",
    })

    logs_dir = root / "server" / "logs"
    checks.append({
        "id": "logs_dir_writable",
        "ok": logs_dir.exists() or logs_dir.parent.exists(),
        "severity": "low",
        "note": "server/logs mevcut veya yazılabilir.",
    })

    pass_count = sum(1 for c in checks if c["ok"])
    total = len(checks)
    result = {
        "ok": True,
        "scope": "read-only / audit",
        "root": str(root),
        "checks": checks,
        "pass_count": pass_count,
        "total_checks": total,
        "score_pct": round((pass_count / total) * 100, 1) if total else 0.0,
    }
    _log_event("hardening_check", {"root": str(root), "score_pct": result["score_pct"]})
    return result


__all__ = [
    "zeynep_kvkk_audit",
    "zeynep_secret_scan",
    "zeynep_log_review",
    "zeynep_hardening_check",
]
