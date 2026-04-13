from __future__ import annotations

from typing import Any

from .base import CanonicalAgent, extract_json_payload


class PlannerAgent(CanonicalAgent):
    agent_id = "planner"
    name = "PlannerAgent"
    role = "Goal decomposition and routing"
    model_chain = "reasoning"
    model_preference = "groq/qwen-qwq-32b"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        system = (
            "You are PlannerAgent. Return strict JSON only. "
            "Use Turkish descriptions. "
            "Schema: {"
            '"goals":[str],'
            '"agents_needed":[str],'
            '"steps":[{"title":str,"owner":str,"description":str}],'
            '"estimated_complexity":"low|medium|high",'
            '"priority":"low|medium|high",'
            '"risk_score":int}'
        )
        prompt = (
            f"Goal: {task}\n"
            f"Context: {context}\n"
            "Return the JSON object now."
        )
        response = self._call_llm(prompt, system=system, max_tokens=900)
        parsed = extract_json_payload(response)
        if isinstance(parsed, dict):
            return self._normalize_payload(task, parsed)
        return self._fallback_payload(task)

    def _normalize_payload(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        steps = payload.get("steps")
        normalized_steps: list[dict[str, str]] = []
        if isinstance(steps, list):
            for index, item in enumerate(steps[:6], start=1):
                if isinstance(item, dict):
                    title = str(item.get("title") or f"Adim {index}").strip() or f"Adim {index}"
                    owner = str(item.get("owner") or "developer").strip() or "developer"
                    description = str(item.get("description") or title).strip() or title
                else:
                    title = f"Adim {index}"
                    owner = "developer"
                    description = str(item).strip() or title
                normalized_steps.append(
                    {"title": title, "owner": owner, "description": description}
                )

        if not normalized_steps:
            normalized_steps = self._fallback_payload(task)["steps"]

        goals = payload.get("goals")
        agents_needed = payload.get("agents_needed")
        estimated_complexity = str(payload.get("estimated_complexity") or "").strip().lower()
        priority = str(payload.get("priority") or "").strip().lower()
        risk_score = payload.get("risk_score")

        return {
            "goals": goals if isinstance(goals, list) and goals else [task],
            "agents_needed": agents_needed if isinstance(agents_needed, list) and agents_needed else self._suggest_agents(task),
            "steps": normalized_steps,
            "estimated_complexity": estimated_complexity if estimated_complexity in {"low", "medium", "high"} else self._estimate_complexity(task),
            "priority": priority if priority in {"low", "medium", "high"} else self._estimate_priority(task),
            "risk_score": int(risk_score) if isinstance(risk_score, int) else self._estimate_risk(task),
        }

    def _fallback_payload(self, task: str) -> dict[str, Any]:
        agents_needed = self._suggest_agents(task)
        return {
            "goals": [task],
            "agents_needed": agents_needed,
            "steps": [
                {
                    "title": "Istek analizi",
                    "owner": "planner",
                    "description": "Hedefi, kisitlari ve cikti formatini netlestir.",
                },
                {
                    "title": "Uygulama hazirligi",
                    "owner": agents_needed[0],
                    "description": "Kod, veri veya dokuman baglamini topla ve gerekli degisiklikleri belirle.",
                },
                {
                    "title": "Dogrumala",
                    "owner": "reviewer" if "reviewer" in agents_needed else "mission_control",
                    "description": "Riskleri kontrol et, sonucu test et ve teslim ozetini hazirla.",
                },
            ],
            "estimated_complexity": self._estimate_complexity(task),
            "priority": self._estimate_priority(task),
            "risk_score": self._estimate_risk(task),
        }

    def _suggest_agents(self, task: str) -> list[str]:
        lower = task.lower()
        agents = ["developer"]
        if any(token in lower for token in ("plan", "hedef", "gorev", "roadmap")):
            agents.insert(0, "planner")
        if any(token in lower for token in ("test", "review", "incele", "pr")):
            agents.append("reviewer")
        if any(token in lower for token in ("hata", "debug", "broken", "fix")):
            agents.append("debug")
        if any(token in lower for token in ("readme", "dokum", "docs")):
            agents.append("docs")
        deduped: list[str] = []
        for agent in agents:
            if agent not in deduped:
                deduped.append(agent)
        return deduped

    def _estimate_complexity(self, task: str) -> str:
        lower = task.lower()
        if len(task) > 180 or any(token in lower for token in ("migration", "orchestrator", "bridge", "integration")):
            return "high"
        if len(task) > 80 or any(token in lower for token in ("feature", "refactor", "agent")):
            return "medium"
        return "low"

    def _estimate_priority(self, task: str) -> str:
        lower = task.lower()
        if any(token in lower for token in ("urgent", "acil", "prod", "incident", "hata")):
            return "high"
        if any(token in lower for token in ("release", "roadmap", "integration", "test")):
            return "medium"
        return "low"

    def _estimate_risk(self, task: str) -> int:
        score = 2
        lower = task.lower()
        if any(token in lower for token in ("bridge", "auth", "security", "payment", "voice")):
            score += 3
        if any(token in lower for token in ("prod", "migration", "critical", "incident")):
            score += 3
        if len(task) > 120:
            score += 1
        return min(score, 10)

