"""
Claude Agent - Jarvis'in güçlü beyni
Karmaşık görevler için Claude CLI'yi çağırır (sunucuda kurulu, Pro plan bağlı)
"""
import subprocess
import logging
import sys
sys.path.insert(0, '/opt/jarvis/core')
from agent import SubAgent, Task

log = logging.getLogger("agent.claude")

CLAUDE_BIN = "/home/userk/.npm-global/bin/claude"


class ClaudeAgent(SubAgent):
    """
    Claude Pro plan ile çalışan güçlü AI agent.
    Karmaşık görevler, kod yazma, çok adımlı planlama için.
    """

    def __init__(self):
        super().__init__(
            role="claude",
            permissions=["read", "write", "analyze", "execute"]
        )

    def run(self, task: Task, context: dict) -> dict:
        goal = task.goal
        plan = context.get("plan", [])
        inputs = context.get("inputs") or {}
        chat_history = context.get("chat_history", [])

        # Prompt oluştur
        system_ctx = "Sen Jarvis'in AI beynisisin. Türkçe veya kullanıcının dilinde kısa, net, işe yarar cevaplar ver."

        history_text = ""
        if chat_history:
            history_text = "\n\nÖnceki konuşma:\n"
            for msg in chat_history[-5:]:
                role = "Kullanıcı" if msg.get("role") == "user" else "Jarvis"
                history_text += f"{role}: {msg.get('content', '')}\n"

        plan_text = ""
        if plan:
            plan_text = f"\nPlan: {chr(10).join(plan)}"

        prompt = f"{system_ctx}{history_text}\n\nGörev: {goal}{plan_text}"

        log.info(f"Claude'a gönderiliyor: {goal[:60]}")
        try:
            result = subprocess.run(
                [CLAUDE_BIN, "-p", prompt],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace"
            )
            output = result.stdout.strip()
            if not output and result.stderr:
                output = result.stderr.strip()

            log.info(f"Claude cevabı alındı ({len(output)} karakter)")
            return {"output": output or "(boş cevap)", "error": None, "meta": {"agent": "claude"}}

        except subprocess.TimeoutExpired:
            log.error("Claude timeout")
            return {"output": None, "error": "claude_timeout"}
        except Exception as e:
            log.error(f"Claude hatası: {e}")
            return {"output": None, "error": str(e)}
