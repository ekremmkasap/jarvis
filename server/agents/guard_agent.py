import re

from agent import SubAgent, Task


SEVERITIES = ("critical", "high", "medium", "low")


class GuardAgent(SubAgent):
    def __init__(self, llm_call, config: dict):
        super().__init__(role="guard", permissions=["read", "analyze"])
        self.llm_call = llm_call
        self.config = config

    def run(self, task: Task, context: dict) -> dict:
        implementation = context.get("implementation", "")
        plan = context.get("plan", [])
        task_type = context.get("task_type", "general")
        context_packet = context.get("context_packet", "")
        prompt = (
            "Sen Guard ajanisin. Verilen artifacti guvenlik, mantik hatasi ve uygulanabilirlik acisindan denetle. "
            "Riskleri severity ile belirt ve gerekiyorsa Builder icin duzeltme notlari yaz.\n\n"
            f"TASK TYPE: {task_type}\n"
            f"GOAL: {task.goal}\n\n"
            f"DEPARTMENT CONTEXT:\n{context_packet[:2000]}\n\n"
            "PLAN:\n"
            + "\n".join(f"- {item}" for item in plan)
            + "\n\nARTIFACT:\n"
            + implementation
            + "\n\nFORMAT:\n"
            + "SECURITY STATUS:\n- ...\n"
            + "FINDINGS:\n- [Severity: High] ...\n"
            + "FIXES:\n- ...\n"
            + "FINAL VERDICT:\n- PASS or FAIL"
        )
        used_fallback = False
        try:
            output = self.llm_call(
                self.config["model"],
                [{"role": "user", "content": prompt}],
                self.config["system_prompt"],
            )
        except Exception:
            output = self._fallback(implementation, task_type)
            used_fallback = True
        counts = self._extract_counts(output)
        fail_on = {item.lower() for item in self.config.get("fail_on_severity", [])}
        passed = not any(counts.get(level, 0) for level in fail_on)
        return {
            "output": output,
            "error": None,
            "passed": passed,
            "meta": {
                "agent": "guard",
                "model": self.config["model"],
                "severity_counts": counts,
                "fallback": used_fallback,
            },
        }

    def _extract_counts(self, text: str) -> dict:
        counts = {level: 0 for level in SEVERITIES}
        for match in re.findall(r"severity\s*:\s*(critical|high|medium|low)", text, re.IGNORECASE):
            counts[match.lower()] += 1
        return counts

    def _fallback(self, implementation: str, task_type: str) -> str:
        findings = []
        lowered = implementation.lower()
        if task_type == "code" and any(token in lowered for token in ["auth", "login", "register"]) and "bcrypt" not in lowered:
            findings.append("- [Severity: High] Password hashing icin bcrypt benzeri guclu mekanizma gorunmuyor.")
        if task_type == "code" and any(token in lowered for token in ["auth", "login", "register"]) and "invalid credentials" not in lowered and "generic" not in lowered:
            findings.append("- [Severity: Medium] Login hata mesajlari enumeration riskine acik olabilir.")
        if not findings:
            findings.append("- [Severity: Low] Timeout nedeniyle temel heuristik review uygulandi.")
        verdict = "PASS" if not any("High" in item or "Critical" in item for item in findings) else "FAIL"
        return (
            "SECURITY STATUS:\n"
            "- Fallback guard review tamamlandi.\n"
            "FINDINGS:\n"
            + "\n".join(findings)
            + "\nFIXES:\n- Production kullanimi oncesi tam security review onerilir.\n"
            f"FINAL VERDICT:\n- {verdict}"
        )
