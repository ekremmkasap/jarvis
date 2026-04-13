from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .base import CanonicalAgent, extract_json_payload


SEVERITIES = ("critical", "major", "minor")


class ReviewerAgent(CanonicalAgent):
    agent_id = "reviewer"
    name = "ReviewerAgent"
    role = "Read-only code and diff review"
    model_chain = "code"
    model_preference = "groq/llama-3.3-70b-versatile"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        repo_path = Path(context.get("repo_path") or self.root_dir).resolve()
        diff_text = str(context.get("diff_text") or "").strip()
        if not diff_text:
            diff_text = self._run_command(["git", "diff", "--cached"], cwd=repo_path)
        if not diff_text.strip():
            diff_text = self._run_command(["git", "diff"], cwd=repo_path)

        response = self._call_llm(
            self._build_prompt(task, diff_text),
            system=(
                "You are ReviewerAgent. Return strict JSON only. "
                "Schema: {"
                '"issues":[{"severity":"critical|major|minor","file":str,"title":str,"details":str}],'
                '"suggestions":[str],'
                '"severity_counts":{"critical":int,"major":int,"minor":int},'
                '"overall_verdict":"approve|request_changes|comment"}'
            ),
            max_tokens=1000,
        )
        parsed = extract_json_payload(response)
        if isinstance(parsed, dict):
            return self._normalize_payload(parsed)
        return self._fallback_payload(diff_text)

    def _build_prompt(self, task: str, diff_text: str) -> str:
        snippet = diff_text[:12000] if diff_text else "(no diff)"
        return (
            f"Task: {task}\n"
            "Review the diff and return a JSON report.\n"
            f"Diff:\n{snippet}"
        )

    def _run_command(self, args: list[str], cwd: Path) -> str:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        return (result.stdout or result.stderr or "").strip()

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        issues = self._normalize_issues(payload.get("issues"))
        suggestions = self._normalize_suggestions(payload.get("suggestions"), issues)
        severity_counts = self._count_severities(issues, payload.get("severity_counts"))
        verdict = str(payload.get("overall_verdict") or "").strip().lower()
        if verdict not in {"approve", "request_changes", "comment"}:
            verdict = self._verdict_from_counts(severity_counts)
        return {
            "issues": issues,
            "suggestions": suggestions,
            "severity_counts": severity_counts,
            "overall_verdict": verdict,
        }

    def _normalize_issues(self, raw_issues: Any) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        if isinstance(raw_issues, list):
            for item in raw_issues[:10]:
                if isinstance(item, dict):
                    severity = str(item.get("severity") or "minor").strip().lower()
                    title = str(item.get("title") or "Review issue").strip() or "Review issue"
                    file_name = str(item.get("file") or "unknown").strip() or "unknown"
                    details = str(item.get("details") or title).strip() or title
                else:
                    severity = "minor"
                    title = "Review issue"
                    file_name = "unknown"
                    details = str(item).strip() or title
                if severity not in SEVERITIES:
                    severity = "minor"
                normalized.append(
                    {
                        "severity": severity,
                        "file": file_name,
                        "title": title,
                        "details": details,
                    }
                )
        return normalized

    def _normalize_suggestions(self, raw_suggestions: Any, issues: list[dict[str, str]]) -> list[str]:
        if isinstance(raw_suggestions, list):
            cleaned = [str(item).strip() for item in raw_suggestions if str(item).strip()]
            if cleaned:
                return cleaned[:5]
        if issues:
            return [
                "Address the flagged issues before approval.",
                "Run focused regression checks on touched files.",
            ]
        return ["No blocking issues detected in the reviewed diff."]

    def _count_severities(self, issues: list[dict[str, str]], raw_counts: Any) -> dict[str, int]:
        counts = {severity: 0 for severity in SEVERITIES}
        if isinstance(raw_counts, dict):
            for severity in SEVERITIES:
                value = raw_counts.get(severity)
                if isinstance(value, int) and value >= 0:
                    counts[severity] = value
        if not any(counts.values()):
            for issue in issues:
                counts[issue["severity"]] += 1
        return counts

    def _verdict_from_counts(self, counts: dict[str, int]) -> str:
        if counts["critical"] or counts["major"]:
            return "request_changes"
        if counts["minor"]:
            return "comment"
        return "approve"

    def _fallback_payload(self, diff_text: str) -> dict[str, Any]:
        issues: list[dict[str, str]] = []
        lower = diff_text.lower()
        added_lines = [
            line[1:]
            for line in diff_text.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]

        for line in added_lines:
            lowered = line.lower()
            if any(token in lowered for token in ("api_key", "secret", "password", "authorization", "token")):
                issues.append(
                    {
                        "severity": "critical",
                        "file": self._extract_file_name(diff_text),
                        "title": "Potential secret exposure",
                        "details": "Added line appears to include a secret-bearing token or credential field.",
                    }
                )
                break

        for line in added_lines:
            lowered = line.lower()
            if "verify=false" in lowered or ("subprocess" in lowered and "shell=true" in lowered):
                issues.append(
                    {
                        "severity": "major",
                        "file": self._extract_file_name(diff_text),
                        "title": "Risky execution or transport change",
                        "details": "Added code disables verification or enables shell execution without review context.",
                    }
                )
                break

        for line in added_lines:
            lowered = line.lower()
            if "todo" in lowered or "fixme" in lowered or "console.log" in lowered or "print(" in lowered:
                issues.append(
                    {
                        "severity": "minor",
                        "file": self._extract_file_name(diff_text),
                        "title": "Temporary debug or unfinished marker",
                        "details": "Added line contains a TODO/FIXME or debug print that may need cleanup.",
                    }
                )
                break

        severity_counts = self._count_severities(issues, None)
        return {
            "issues": issues,
            "suggestions": self._normalize_suggestions(None, issues),
            "severity_counts": severity_counts,
            "overall_verdict": self._verdict_from_counts(severity_counts),
        }

    def _extract_file_name(self, diff_text: str) -> str:
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                return line.replace("+++ b/", "", 1).strip() or "unknown"
        return "unknown"
