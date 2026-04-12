from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .base import CanonicalAgent, extract_json_payload


class ReleaseAgent(CanonicalAgent):
    agent_id = "release"
    name = "ReleaseAgent"
    role = "Changelog and semver draft generation"
    model_chain = "default"
    model_preference = "groq/llama-3.3-70b-versatile"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        repo_path = Path(context.get("repo_path") or self.root_dir).resolve()
        current_version = str(context.get("current_version") or "").strip()
        git_log = str(context.get("git_log") or "").strip()
        if not git_log:
            git_log = self._run_command(["git", "log", "--oneline", "-20"], cwd=repo_path)

        response = self._call_llm(
            self._build_prompt(task, git_log, current_version),
            system=(
                "You are ReleaseAgent. Return strict JSON only. "
                "Schema: {"
                '"changelog_entries":[str],'
                '"suggested_version":str,'
                '"breaking_changes":[str],'
                '"highlights":[str]}'
            ),
            max_tokens=1000,
        )
        parsed = extract_json_payload(response)
        if isinstance(parsed, dict):
            return self._normalize_payload(parsed, git_log, current_version)
        return self._fallback_payload(git_log, current_version)

    def _build_prompt(self, task: str, git_log: str, current_version: str) -> str:
        return (
            f"Task: {task}\n"
            f"Current version: {current_version or '(unknown)'}\n"
            f"Git log:\n{git_log[:12000]}\n"
            "Return release draft JSON."
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

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        git_log: str,
        current_version: str,
    ) -> dict[str, Any]:
        changelog_entries = self._normalize_string_list(payload.get("changelog_entries"))
        breaking_changes = self._normalize_string_list(payload.get("breaking_changes"))
        highlights = self._normalize_string_list(payload.get("highlights"))
        if not changelog_entries:
            fallback = self._fallback_payload(git_log, current_version)
            changelog_entries = fallback["changelog_entries"]
        if not highlights:
            highlights = changelog_entries[:3]
        suggested_version = str(payload.get("suggested_version") or "").strip()
        if not suggested_version:
            suggested_version = self._suggest_version(git_log, current_version)
        return {
            "changelog_entries": changelog_entries,
            "suggested_version": suggested_version,
            "breaking_changes": breaking_changes,
            "highlights": highlights,
        }

    def _normalize_string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:10]

    def _fallback_payload(self, git_log: str, current_version: str) -> dict[str, Any]:
        lines = [line.strip() for line in git_log.splitlines() if line.strip()]
        changelog_entries = [self._to_changelog_entry(line) for line in lines[:8]] or ["- No recent commits found."]
        breaking_changes = [
            self._to_changelog_entry(line)
            for line in lines
            if "breaking change" in line.lower() or re.search(r"\bfeat!\b", line.lower())
        ][:5]
        highlights = changelog_entries[:3]
        return {
            "changelog_entries": changelog_entries,
            "suggested_version": self._suggest_version(git_log, current_version),
            "breaking_changes": breaking_changes,
            "highlights": highlights,
        }

    def _to_changelog_entry(self, line: str) -> str:
        cleaned = re.sub(r"^[0-9a-f]{6,}\s+", "", line.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.strip() or "Unlabeled change"
        if not cleaned.startswith("- "):
            cleaned = f"- {cleaned}"
        return cleaned

    def _suggest_version(self, git_log: str, current_version: str) -> str:
        bump = self._classify_bump(git_log)
        if not current_version:
            return bump
        parts = current_version.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            return bump
        major, minor, patch = (int(part) for part in parts)
        if bump == "major":
            return f"{major + 1}.0.0"
        if bump == "minor":
            return f"{major}.{minor + 1}.0"
        return f"{major}.{minor}.{patch + 1}"

    def _classify_bump(self, git_log: str) -> str:
        lower = git_log.lower()
        if "breaking change" in lower or re.search(r"\bfeat!\b", lower):
            return "major"
        if re.search(r"(^|\n)[0-9a-f]{6,}\s+feat(\(|:)", git_log, flags=re.IGNORECASE):
            return "minor"
        return "patch"
