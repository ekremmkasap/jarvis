"""
Mission Control Orchestrator (j.txt Section 1-A)
Kullanicidan gelen istegi Task'a cevirir, CoreAgent'i calistirir,
sonucu geri iletir.
"""
import json
import logging
from pathlib import Path
from agent import CoreAgent, SubAgent, Task

log = logging.getLogger("orchestrator")


# --- Sub-Agent Implementasyonlari (j.txt Section 4) ---

class PlannerAgent(SubAgent):
    """Hedef -> adimlar -> bagimliliklar -> riskler (j.txt Section 4.1)"""

    def __init__(self):
        super().__init__(role="planner", permissions=["read", "analyze"])

    def run(self, task: Task, context: dict) -> dict:
        goal = context.get("goal", task.goal)
        steps = [
            f"1. Gereksinimler analiz edildi: '{goal[:50]}'",
            "2. Alt gorevler belirlendi",
            "3. Bagimliliklar haritasi olusturuldu",
            "4. Riskler degerlendirildi",
            "5. Uygulama icin implementer'a gonderilmeye hazir",
        ]
        return {
            "output": steps,
            "error": None,
            "meta": {"agent": "planner", "steps_count": len(steps)}
        }


class ImplementerAgent(SubAgent):
    """Plani uygular, kod/konfig/cikti uretir (j.txt Section 4.2)"""

    def __init__(self):
        super().__init__(role="implementer", permissions=["read", "write", "execute"])

    def run(self, task: Task, context: dict) -> dict:
        plan = context.get("plan", [])
        summary = f"Plan uygulandı ({len(plan)} adım). Görev: {task.goal[:60]}"
        return {
            "output": summary,
            "error": None,
            "meta": {"agent": "implementer", "plan_steps": len(plan)}
        }


class ReviewerAgent(SubAgent):
    """Kalite kontrol, eksik/celişki bulma (j.txt Section 4.3) - SADECE OKUR"""

    def __init__(self):
        super().__init__(role="reviewer", permissions=["read"])  # yazma yok (j.txt Section 7)

    def run(self, task: Task, context: dict) -> dict:
        artifacts = context.get("artifacts", [])
        issues = []

        if not artifacts:
            issues.append("Hicbir artifact uretilmedi.")
        if not task.plan:
            issues.append("Plan bos.")

        if issues:
            return {
                "output": f"REVIEW: {len(issues)} sorun bulundu: " + "; ".join(issues),
                "error": None,
                "passed": False
            }
        return {
            "output": f"REVIEW: Kalite kontrol gecildi. {len(artifacts)} artifact incelendi.",
            "error": None,
            "passed": True
        }


# --- Orchestrator ---

class Orchestrator:
    def __init__(self):
        self.core = CoreAgent()
        # Sub-agent'lari kaydet
        self.core.register_agent(PlannerAgent())
        self.core.register_agent(ImplementerAgent())
        self.core.register_agent(ReviewerAgent())
        log.info("Orchestrator hazir. Registered: %s", list(self.core.sub_agents.keys()))

    def handle(self, user_input: str, constraints: list = None) -> str:
        """Kullanicidan gelen metni isle, sonucu string olarak dondur."""
        if not user_input.strip():
            return "Bos istek. Lutfen bir gorev tanimlayin."

        log.info(f"Yeni istek: {user_input[:80]}")
        result = self.core.run(goal=user_input, constraints=constraints)

        status = result.get("status")
        task_id = result.get("task_id")

        if status == "done":
            r = result.get("result", {})
            review = r.get("review", "")
            plan = r.get("plan", [])
            plan_text = "\n".join(plan) if isinstance(plan, list) else str(plan)
            return (
                f"[{task_id}] Gorev tamamlandi.\n\n"
                f"Plan:\n{plan_text}\n\n"
                f"Review: {review}"
            )
        elif status == "failed":
            return f"[{task_id}] Gorev basarisiz: {result.get('reason')}"
        elif status == "blocked":
            return f"[{task_id}] Gorev bloke: {result.get('reason')}"
        else:
            return f"[{task_id}] Durum: {status}"

    def get_status(self) -> str:
        return json.dumps(self.core.status(), indent=2, ensure_ascii=False)


# --- CLI Test ---
if __name__ == "__main__":
    orch = Orchestrator()

    print("\n=== Mission Control Orchestrator ===")
    print("Komut girin (cikis icin 'exit'):\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCikiliyor...")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            break
        if user_input.lower() == "status":
            print(orch.get_status())
            continue
        if not user_input:
            continue

        response = orch.handle(user_input)
        print(f"\n{response}\n")
