from agent import SubAgent, Task


class ResearchAgent(SubAgent):
    def __init__(self, llm_call, config: dict):
        super().__init__(role="research", permissions=["read", "analyze"])
        self.llm_call = llm_call
        self.config = config

    def run(self, task: Task, context: dict) -> dict:
        task_type = context.get("task_type", "general")
        context_packet = context.get("context_packet", "")
        prompt = (
            "Sen Research ajanisin. Gerektiginde teknoloji, mimari, paket ve workflow secenekleri sun. "
            "En fazla 3 secenek ver ve net oneride bulun.\n\n"
            f"TASK TYPE: {task_type}\n"
            f"GOAL: {task.goal}\n\n"
            f"DEPARTMENT CONTEXT:\n{context_packet[:2000]}\n\n"
            "FORMAT:\n"
            "OPTIONS:\n- ...\n"
            "RECOMMENDATION:\n- ...\n"
            "RATIONALE:\n- ..."
        )
        used_fallback = False
        try:
            output = self.llm_call(
                self.config["model"],
                [{"role": "user", "content": prompt}],
                self.config["system_prompt"],
            )
        except Exception:
            output = self._fallback(task.goal, task_type)
            used_fallback = True
        return {
            "output": output,
            "error": None,
            "meta": {"agent": "research", "model": self.config["model"], "fallback": used_fallback},
        }

    def _fallback(self, goal: str, task_type: str) -> str:
        return (
            "OPTIONS:\n"
            "- Hedefe gore mevcut local modellerle hizli akisi kullan\n"
            "- Kod agir islerde builder+guard adimlarini koru\n"
            "- Buyuk mimari islerde research'i manuel tetikle\n"
            "RECOMMENDATION:\n"
            f"- {task_type} gorevi icin once hizli local workflow kullan\n"
            "RATIONALE:\n"
            f"- Timeout durumunda bile hedef ({goal}) icin sistem cevap verebilmeli"
        )
