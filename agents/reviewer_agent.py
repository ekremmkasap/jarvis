from __future__ import annotations
from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis ReviewerAgent — senior engineer code reviewer.
Check for:
- Logic bugs and edge cases
- Security vulnerabilities (OWASP Top 10)
- Performance issues
- Code style and maintainability
- Missing tests and documentation

Rate issues: CRITICAL / MAJOR / MINOR / SUGGESTION
Always end with: APPROVE | REQUEST_CHANGES | COMMENT"""


class ReviewerAgent(RuntimeAgent):
    name = "reviewer"
    description = "Reviews PRs and code for quality, security, and correctness"
    model_chain = "code"

    def execute_task(self, task) -> str:
        self.log.info("Reviewing: %s", task.goal[:80])
        pr_num = task.context.get("pr_number", "unknown")
        repo = task.context.get("repo", "unknown")

        prompt = f"""Code Review Request
PR: #{pr_num} in {repo}
Description: {task.goal}

Provide structured review:
## Executive Summary
[APPROVE | REQUEST_CHANGES | COMMENT]

## Critical Issues (Blockers)
## Major Concerns
## Minor Suggestions
## Security Observations
## Test Coverage Assessment
## Recommended Next Steps"""

        return self.llm_call(prompt, system=SYSTEM, max_tokens=2000)
