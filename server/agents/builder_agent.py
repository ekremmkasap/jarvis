from agent import SubAgent, Task


class BuilderAgent(SubAgent):
    def __init__(self, llm_call, config: dict):
        super().__init__(role="builder", permissions=["read", "write", "execute"])
        self.llm_call = llm_call
        self.config = config

    def run(self, task: Task, context: dict) -> dict:
        plan = context.get("plan", [])
        acceptance = context.get("acceptance", [])
        review_feedback = context.get("review_feedback", "")
        task_type = context.get("task_type", "general")
        context_packet = context.get("context_packet", "")
        plan_text = "\n".join(f"- {item}" for item in plan) or "- Net plan verilmedi"
        acceptance_text = "\n".join(f"- {item}" for item in acceptance) or "- Kullanici istegi karsilanmali"
        review_text = review_feedback.strip() or "- Ilk uygulama turu, duzeltme notu yok"
        prompt = (
            "Sen Builder ajanisin. Verilen gorev icin uygulanabilir, net ve dogrudan kullanilabilir cikti uret. "
            "Kod gerekiyorsa dosya bazli ve temiz olsun. Guvenlik kritik alanlarda duzgun varsayimlar sec.\n\n"
            f"TASK TYPE: {task_type}\n"
            f"GOAL: {task.goal}\n\n"
            f"DEPARTMENT CONTEXT:\n{context_packet[:2000]}\n\n"
            f"PLAN:\n{plan_text}\n\n"
            f"ACCEPTANCE:\n{acceptance_text}\n\n"
            f"REVIEW_FEEDBACK:\n{review_text}\n\n"
            "FORMAT:\n"
            "FILES:\n"
            "- path\n"
            "IMPLEMENTATION:\n"
            "<code or artifact>\n"
            "NOTES:\n"
            "- important note"
        )
        used_fallback = False
        try:
            output = self.llm_call(
                self.config["model"],
                [{"role": "user", "content": prompt}],
                self.config["system_prompt"],
            )
        except Exception:
            output = self._fallback(task.goal, task_type, plan, acceptance, review_feedback)
            used_fallback = True
        return {
            "output": output,
            "error": None,
            "meta": {"agent": "builder", "model": self.config["model"], "fallback": used_fallback},
        }

    def _fallback(self, goal: str, task_type: str, plan: list, acceptance: list, review_feedback: str) -> str:
        files = ["response.md"]
        implementation = [
            f"Goal: {goal}",
            f"Task type: {task_type}",
            "Plan:",
            *[f"- {item}" for item in plan[:5]],
        ]
        if acceptance:
            implementation.append("Acceptance:")
            implementation.extend(f"- {item}" for item in acceptance[:5])
        if review_feedback:
            implementation.append("Review feedback:")
            implementation.append(review_feedback[:600])
        if any(keyword in goal.lower() for keyword in ["auth", "login", "register"]):
            files = ["auth_system.py"]
            implementation = [
                "FILES:",
                "- auth_system.py",
                "",
                "IMPLEMENTATION:",
                "- register_user / login_user akisi gerekli.",
                "- Password hashing icin bcrypt veya esdegeri kullanilmali.",
                "- Plaintext password saklanmamali.",
                "- user_repo placeholder arayuzu tanimlanmali.",
                "",
                "NOTES:",
                "- Bu fallback cikti, timeout durumunda asgari uygulanabilir taslaktir.",
            ]
            return "\n".join(implementation)
        return "FILES:\n- " + "\n- ".join(files) + "\n\nIMPLEMENTATION:\n" + "\n".join(implementation) + "\n\nNOTES:\n- Timeout nedeniyle fallback builder kullanildi."
