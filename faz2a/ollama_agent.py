"""
Ollama Agent - Jarvis'in hızlı, ücretsiz beyni
Basit sorular ve kısa cevaplar için yerel LLM kullanır
"""
import json
import logging
import urllib.request
import urllib.error
import sys
sys.path.insert(0, '/opt/jarvis/core')
from agent import SubAgent, Task

log = logging.getLogger("agent.ollama")

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "llama3.2"


class OllamaAgent(SubAgent):
    """
    Ollama yerel LLM ile çalışan hızlı agent.
    Basit sorular, durum sorgulama, kısa cevaplar için.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        super().__init__(
            role="ollama",
            permissions=["read", "analyze"]
        )
        self.model = model

    def _is_available(self) -> bool:
        try:
            req = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3)
            return req.status == 200
        except Exception:
            return False

    def run(self, task: Task, context: dict) -> dict:
        goal = task.goal
        chat_history = context.get("chat_history", [])

        if not self._is_available():
            log.warning("Ollama çalışmıyor, Claude'a yönlendir")
            return {"output": None, "error": "ollama_unavailable"}

        # Basit prompt
        history_text = ""
        if chat_history:
            for msg in chat_history[-3:]:
                role = "Kullanıcı" if msg.get("role") == "user" else "Jarvis"
                history_text += f"{role}: {msg.get('content', '')}\n"

        prompt = f"Sen Jarvis'sin. Kısa ve net cevap ver.\n{history_text}\nKullanıcı: {goal}\nJarvis:"

        log.info(f"Ollama'ya gönderiliyor ({self.model}): {goal[:50]}")
        try:
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 500}
            }).encode("utf-8")

            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                output = data.get("response", "").strip()
                log.info(f"Ollama cevabı alındı ({len(output)} karakter)")
                return {"output": output or "(boş cevap)", "error": None, "meta": {"agent": "ollama", "model": self.model}}

        except urllib.error.URLError as e:
            log.error(f"Ollama bağlantı hatası: {e}")
            return {"output": None, "error": "ollama_connection_error"}
        except Exception as e:
            log.error(f"Ollama hatası: {e}")
            return {"output": None, "error": str(e)}
