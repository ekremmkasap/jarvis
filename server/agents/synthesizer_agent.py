from agent import SubAgent, Task


class SynthesizerAgent(SubAgent):
    def __init__(self, llm_call, config: dict):
        super().__init__(role="synthesizer", permissions=["read", "analyze"])
        self.llm_call = llm_call
        self.config = config

    def run(self, task: Task, context: dict) -> dict:
        plan = context.get("plan", [])
        acceptance = context.get("acceptance", [])
        implementation = context.get("implementation", "")
        review = context.get("review", "")
        research = context.get("research", "")
        attempts = context.get("attempts", 1)
        context_packet = context.get("context_packet", "")
        prompt = (
            "Tum uzman ajan ciktilarini tek final rapora donustur. Kisa ama bilgi dolu ol. "
            "Uygulanan is, review sonucu ve sonraki adimlari ayir.\n\n"
            f"GOAL: {task.goal}\n"
            f"ATTEMPTS: {attempts}\n\n"
            f"DEPARTMENT CONTEXT:\n{context_packet[:2000]}\n\n"
            "PLAN:\n" + "\n".join(f"- {item}" for item in plan) + "\n\n"
            "ACCEPTANCE:\n" + "\n".join(f"- {item}" for item in acceptance) + "\n\n"
            "IMPLEMENTATION:\n" + implementation + "\n\n"
            "REVIEW:\n" + review + "\n\n"
            "RESEARCH:\n" + (research or "- Arastirma calismadi veya gerekmedi") + "\n\n"
            "FORMAT:\n"
            "STATUS: ...\n"
            "DELIVERABLES:\n- ...\n"
            "QUALITY:\n- ...\n"
            "NEXT:\n- ..."
        )
        used_fallback = False
        try:
            output = self.llm_call(
                self.config["model"],
                [{"role": "user", "content": prompt}],
                self.config["system_prompt"],
            )
        except Exception:
            output = self._fallback(task.goal, plan, implementation, review, research, attempts)
            used_fallback = True
        return {
            "output": output,
            "error": None,
            "meta": {"agent": "synthesizer", "model": self.config["model"], "fallback": used_fallback},
        }

    def _fallback(self, goal: str, plan: list, implementation: str, review: str, research: str, attempts: int) -> str:
        status = "ready"
        if "FAIL" in review.upper() or "blocked" in review.lower():
            status = "needs_attention"
        lines = [
            f"STATUS: {status}",
            "DELIVERABLES:",
            f"- Goal: {goal}",
            f"- Plan steps: {len(plan)}",
            f"- Attempts: {attempts}",
            "QUALITY:",
            f"- Review: {(review or 'Review yok')[:300]}",
        ]
        if research:
            lines.append(f"- Research: {research[:200]}")
        lines.extend([
            "NEXT:",
            "- Gerekirse artifact'i dosyaya uygula.",
            "- Guard bulgularini kapat ve tekrar dene.",
        ])
        return "\n".join(lines)
