from __future__ import annotations
from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis RepoAnalystAgent.
Analyze GitHub repositories and codebases. Provide:
- Architecture overview
- Health metrics (open issues, PR velocity, CI pass rate)
- Risk areas (stale code, missing tests, large files)
- Actionable recommendations
Be specific, data-driven, and concise. Format output as markdown."""


class RepoAnalystAgent(RuntimeAgent):
    name = "repo_analyst"
    description = "Analyzes repository health, architecture, and code quality"
    model_chain = "code"

    def execute_task(self, task) -> str:
        self.log.info("Analyzing: %s", task.goal[:80])
        repo = task.context.get("repo", "unknown")
        report_type = task.context.get("report_type", "general")

        prompt = f"""Repository Analysis Request
Repo: {repo}
Report Type: {report_type}
Task: {task.goal}

Provide comprehensive analysis:
1. Repository health summary (score 0-10)
2. Recent activity patterns
3. Critical issues requiring immediate attention
4. Code quality observations
5. Security hotspots if any
6. Recommended automated Jarvis actions

Format as markdown report with sections."""

        return self.llm_call(prompt, system=SYSTEM, max_tokens=2000)
