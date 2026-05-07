from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import CanonicalAgent


class RepoAnalystAgent(CanonicalAgent):
    agent_id = "repo_analyst"
    name = "RepoAnalystAgent"
    role = "Repository health analysis"
    model_chain = "code"
    model_preference = "groq/moonshotai/kimi-k2-5"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        repo_path = Path(context.get("repo_path") or self.root_dir).resolve()
        recent_commits_raw = self._run_command(["git", "log", "--oneline", "-5"], cwd=repo_path)
        staged_diff_raw = self._run_command(["git", "diff", "--stat", "--cached"], cwd=repo_path)
        working_diff_raw = self._run_command(["git", "diff", "--stat"], cwd=repo_path)

        recent_commits = [line.strip() for line in recent_commits_raw.splitlines() if line.strip()]
        changed_files = self._parse_changed_files("\n".join([staged_diff_raw, working_diff_raw]))
        warnings = self._build_warnings(recent_commits, changed_files, staged_diff_raw, working_diff_raw)
        recommendations = self._build_recommendations(warnings)
        health_score = self._score_repo(warnings, changed_files)

        report_path = self._write_report(
            repo_path=repo_path,
            task=task,
            recent_commits=recent_commits,
            changed_files=changed_files,
            warnings=warnings,
            recommendations=recommendations,
            health_score=health_score,
        )

        return {
            "recent_commits": recent_commits,
            "changed_files": changed_files,
            "health_score": health_score,
            "warnings": warnings,
            "recommendations": recommendations,
            "report_path": str(report_path),
        }

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
        if result.returncode != 0:
            return (result.stderr or result.stdout or "").strip()
        return (result.stdout or "").strip()

    def _parse_changed_files(self, diff_stat: str) -> list[str]:
        files: list[str] = []
        for line in diff_stat.splitlines():
            cleaned = line.strip()
            if "|" not in cleaned:
                continue
            file_name = cleaned.split("|", 1)[0].strip()
            if file_name and file_name not in files:
                files.append(file_name)
        return files

    def _build_warnings(
        self,
        recent_commits: list[str],
        changed_files: list[str],
        staged_diff: str,
        working_diff: str,
    ) -> list[str]:
        warnings: list[str] = []
        if not recent_commits:
            warnings.append("No recent git commits were found.")
        if len(changed_files) > 20:
            warnings.append("Large working set detected; review scope may be too broad.")
        if staged_diff and not working_diff:
            warnings.append("Only staged changes detected; verify unstaged review coverage if expected.")
        if working_diff.count("\n") > 25:
            warnings.append("Working tree diff is noisy; risk of incidental changes is elevated.")
        if not warnings:
            warnings.append("No critical repo health issues detected in the sampled git signals.")
        return warnings

    def _build_recommendations(self, warnings: list[str]) -> list[str]:
        if any("Large working set" in warning for warning in warnings):
            return [
                "Split the change set into smaller reviewable batches.",
                "Run targeted tests around modified paths before merge.",
            ]
        if any("No recent git commits" in warning for warning in warnings):
            return [
                "Confirm the repository checkout is valid and has visible history.",
                "Collect CI and ownership context before further automation.",
            ]
        return [
            "Keep review scoped to changed files and run focused regression checks.",
            "Update docs or release notes if the modified paths are operator-facing.",
        ]

    def _score_repo(self, warnings: list[str], changed_files: list[str]) -> int:
        score = 92
        score -= min(len(changed_files), 20)
        score -= max(len(warnings) - 1, 0) * 8
        return max(score, 40)

    def _write_report(
        self,
        *,
        repo_path: Path,
        task: str,
        recent_commits: list[str],
        changed_files: list[str],
        warnings: list[str],
        recommendations: list[str],
        health_score: int,
    ) -> Path:
        report_dir = self.root_dir / "outputs" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"repo_analyst_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        commit_lines = [f"- {line}" for line in recent_commits] or ["- None"]
        file_lines = [f"- {line}" for line in changed_files] or ["- None"]
        warning_lines = [f"- {line}" for line in warnings]
        recommendation_lines = [f"- {line}" for line in recommendations]
        report = [
            "# Repo Analyst Report",
            "",
            f"- Task: {task}",
            f"- Repository: {repo_path}",
            f"- Health Score: {health_score}",
            "",
            "## Recent Commits",
            *commit_lines,
            "",
            "## Changed Files",
            *file_lines,
            "",
            "## Warnings",
            *warning_lines,
            "",
            "## Recommendations",
            *recommendation_lines,
        ]
        report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
        return report_path
