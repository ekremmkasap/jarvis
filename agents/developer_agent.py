from __future__ import annotations
from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis DeveloperAgent powered by Claude Code.
Implement features, fix bugs, write tests, refactor code.
Always:
- Write clean, production-ready code
- Include error handling and edge cases
- Suggest tests alongside implementations
- Output complete, runnable code (not pseudocode)
- Note any breaking changes"""


class DeveloperAgent(RuntimeAgent):
    name = "developer"
    description = "Implements features, fixes bugs, writes tests via Claude Code"
    model_chain = "code"
    risk_level = "medium"

    def execute_task(self, task) -> str:
        self.log.info("Developer task: %s", task.goal[:80])

        if task.dry_run:
            return f"[DRY RUN] Would implement: {task.goal}"

        prompt = f"""Development Task: {task.goal}

Repository: {task.context.get('repo', 'local')}
Context: {task.context}

Implement the solution:
1. Complete implementation code with docstrings
2. Unit tests
3. Design decisions explained briefly
4. Migration / upgrade notes if applicable

Output as markdown with fenced code blocks."""

        return self.llm_call(prompt, system=SYSTEM, max_tokens=3000)
