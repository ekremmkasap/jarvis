from __future__ import annotations
from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis DocsAgent.
Write and update technical documentation: README, AGENTS.md, RUNBOOK, API docs.
Rules:
- Clear, concise, developer-friendly
- Proper markdown with headings and code examples
- Include prerequisites, setup, usage, troubleshooting
- Never fabricate API details — mark unknowns with [TODO]"""


class DocsAgent(RuntimeAgent):
    name = "docs"
    description = "Writes and updates README, AGENTS.md, RUNBOOK, and API documentation"
    model_chain = "default"

    def execute_task(self, task) -> str:
        self.log.info("Docs task: %s", task.goal[:80])
        doc_type = task.context.get("doc_type", "general")
        repo = task.context.get("repo", "unknown")

        prompt = f"""Documentation Task
Request: {task.goal}
Repo: {repo}
Doc Type: {doc_type}

Write production-ready documentation including:
1. Clear title and one-sentence description
2. Prerequisites / installation
3. Usage examples with code blocks
4. Configuration reference (all options)
5. Troubleshooting section
6. Contributing guidelines (if applicable)

Output as complete markdown document."""

        return self.llm_call(prompt, system=SYSTEM, max_tokens=2500)
