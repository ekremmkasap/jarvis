from __future__ import annotations
from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis ReleaseAgent.
Prepare releases, draft changelogs, write release notes, coordinate deployments.
Follow:
- keep-a-changelog format for changelogs
- Semantic versioning (semver) for version bumps
- User-friendly language for release notes
Output draft only — never create actual releases without confirmation."""


class ReleaseAgent(RuntimeAgent):
    name = "release"
    description = "Drafts changelogs, release notes, and prepares version releases"
    model_chain = "default"
    risk_level = "medium"

    def execute_task(self, task) -> str:
        self.log.info("Release task: %s", task.goal[:80])
        repo = task.context.get("repo", "unknown")

        prompt = f"""Release Preparation
Task: {task.goal}
Repo: {repo}
Context: {task.context}

Generate:

## Changelog Entry (keep-a-changelog format)
## GitHub Release Notes (user-friendly)
## Upgrade Guide (breaking changes if any)
## Version Bump Recommendation: major/minor/patch — reasoning
## Release Checklist
- [ ] Tests passing
- [ ] Docs updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in package files
- [ ] Migration guide written (if breaking)"""

        return self.llm_call(prompt, system=SYSTEM, max_tokens=2000)
