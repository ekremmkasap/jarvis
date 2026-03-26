from __future__ import annotations
from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis DebugAgent.
Diagnose failures, analyze logs, suggest fixes.
Approach:
1. Root cause (not just symptoms)
2. Exact explanation of why it failed
3. Specific fix with code if applicable
4. Preventive measures
5. Production impact assessment

Be precise and actionable. Format as incident report."""


class DebugAgent(RuntimeAgent):
    name = "debug"
    description = "Diagnoses CI failures, runtime errors, and suggests fixes"
    model_chain = "reasoning"

    def execute_task(self, task) -> str:
        self.log.info("Debugging: %s", task.goal[:80])
        run_id = task.context.get("run_id", "unknown")
        repo = task.context.get("repo", "unknown")

        prompt = f"""Debug Request
Failure: {task.goal}
Repo: {repo}
CI Run ID: {run_id}
Additional Context: {task.context}

Diagnose and resolve:

## Root Cause Analysis
## Error Interpretation
## Proposed Fix
```
[code here if applicable]
```
## Confidence Level: high/medium/low
## Prevention Recommendations
## Monitoring Suggestions"""

        return self.llm_call(prompt, system=SYSTEM, max_tokens=2000)
