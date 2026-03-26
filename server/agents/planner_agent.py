import re

from agent import SubAgent, Task


class PlannerAgent(SubAgent):
    def __init__(self, llm_call, config: dict):
        super().__init__(role="planner", permissions=["read", "analyze"])
        self.llm_call = llm_call
        self.config = config

    def run(self, task: Task, context: dict) -> dict:
        goal = context.get("goal", task.goal)
        task_type = context.get("task_type", "general")
        context_packet = context.get("context_packet", "")
        prompt = (
            "Kullanici istegini uygulama plani haline getir. "
            "En fazla 5 adim yaz. Her adim uygulanabilir olsun. "
            "Ayrica acceptance criteria ve riskler cikar.\n\n"
            f"TASK TYPE: {task_type}\n"
            f"GOAL: {goal}\n\n"
            f"DEPARTMENT CONTEXT:\n{context_packet[:2000]}\n\n"
            "FORMAT:\n"
            "PLAN:\n"
            "- ...\n"
            "ACCEPTANCE:\n"
            "- ...\n"
            "RISKS:\n"
            "- ..."
        )
        used_fallback = False
        try:
            output = self.llm_call(
                self.config["model"],
                [{"role": "user", "content": prompt}],
                self.config["system_prompt"],
            )
            parsed = self._parse(output)
        except Exception:
            parsed = self._fallback(goal, task_type)
            used_fallback = True
        return {
            "output": parsed,
            "error": None,
            "meta": {"agent": "planner", "model": self.config["model"], "fallback": used_fallback},
        }

    def _fallback(self, goal: str, task_type: str) -> dict:
        compact_goal = goal.strip() or "Genel gorev"
        plan = [
            f"Istek siniflandirilir ve hedef netlestirilir ({task_type}).",
            "Uygulanabilir artifact veya cevap taslagi uretilir.",
            "Guvenlik ve mantik kontrolu yapilir.",
            "Final sonuc tek raporda birlestirilir.",
        ]
        acceptance = [
            "Kullanici istegine dogrudan cevap verilmeli.",
            "Cikti uygulanabilir ve acik olmali.",
        ]
        risks = [
            "Harici model gecikmesi veya timeout riski.",
            "Guvenlik kritik isteklerde ek review gerekebilir.",
        ]
        if "auth" in compact_goal.lower() or "login" in compact_goal.lower() or "register" in compact_goal.lower():
            plan.insert(1, "Auth akisi icin register/login ve password handling tasarlanir.")
            acceptance.append("Password hashing ve generic error handling dikkate alinmali.")
        return {"plan": plan[:5], "acceptance": acceptance[:4], "risks": risks[:4]}

    def _parse(self, text: str) -> dict:
        current = None
        sections = {"plan": [], "acceptance": [], "risks": []}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            upper = line.upper().rstrip(":")
            if upper == "PLAN":
                current = "plan"
                continue
            if upper == "ACCEPTANCE":
                current = "acceptance"
                continue
            if upper == "RISKS":
                current = "risks"
                continue
            if current:
                cleaned = re.sub(r"^[-*\d.)\s]+", "", line).strip()
                if cleaned:
                    sections[current].append(cleaned)
        if not sections["plan"]:
            fallback = [re.sub(r"^[-*\d.)\s]+", "", line).strip() for line in text.splitlines() if line.strip()]
            sections["plan"] = fallback[:5] or ["Gorevi analiz et ve uygulanabilir cikti uret"]
        return sections
