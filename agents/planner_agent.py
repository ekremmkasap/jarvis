from __future__ import annotations
from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis PlannerAgent.
Given a goal, produce a structured execution plan:
1. Numbered steps with clear descriptions
2. Assigned agent per step (planner/repo_analyst/developer/reviewer/debug/release/docs/mission_control)
3. Dependencies between steps
4. Risk assessment per step (low/medium/high)
5. Overall complexity estimate

Output valid JSON with fields: steps[], summary, total_risk, recommended_first_agent."""


class PlannerAgent(RuntimeAgent):
    name = "planner"
    description = "Breaks goals into structured plans and dispatches to specialized agents"
    model_chain = "reasoning"

    def execute_task(self, task) -> str:
        self.log.info("Planning: %s", task.goal[:80])
        prompt = f"""Goal: {task.goal}

Context: {task.context}

Create a detailed execution plan. Output as JSON:
{{
  "steps": [
    {{"step": 1, "description": "...", "agent": "...", "depends_on": [], "risk": "low"}}
  ],
  "summary": "one sentence",
  "total_risk": "low|medium|high",
  "recommended_first_agent": "agent_name"
}}"""
        return self.llm_call(prompt, system=SYSTEM, max_tokens=1500)
