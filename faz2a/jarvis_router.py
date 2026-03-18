"""
JarvisRouter - Telegram ↔ CoreAgent köprüsü
Her Telegram mesajını alır, sınıflandırır, doğru agent'a yönlendirir.
"""
import sys
import json
import logging
import datetime
from pathlib import Path

sys.path.insert(0, '/opt/jarvis/core')
from agent import CoreAgent, SubAgent, Task, TaskStatus
from orchestrator import PlannerAgent, ReviewerAgent

sys.path.insert(0, '/opt/jarvis/agents')
from claude_agent import ClaudeAgent
from ollama_agent import OllamaAgent

# Skills
sys.path.insert(0, '/opt/jarvis/skills/execution')
import sunucu_yonet

log = logging.getLogger("jarvis.router")

CHAT_HISTORY_FILE = Path("/opt/jarvis/memory/working_memory/chat_history.jsonl")
MAX_HISTORY = 10

# Selamlama / sohbet → anında cevap, AI beklemez
GREETING_KEYWORDS = [
    "merhaba", "selam", "hey", "hi", "hello", "günaydın", "iyi günler",
    "iyi geceler", "nasılsın", "naber", "ne haber", "iyisin", "nasıl gidiyor",
    "teşekkür", "sağol", "tamam", "anladım", "harika", "süper", "güzel",
    "eyvallah", "tamamdır", "ok", "peki", "görüşürüz", "hoşça kal", "bye"
]

# Karmaşık görev belirtileri → Claude'a git
COMPLEX_KEYWORDS = [
    "yaz", "oluştur", "düzelt", "planla", "analiz", "kod", "script",
    "açıkla", "özetle", "karşılaştır", "tasarla", "geliştir", "implement",
    "write", "create", "fix", "plan", "analyze", "code", "explain", "design",
    "neden", "nasıl yapılır", "ne zaman", "fark nedir", "karşılaştır",
    "örnek ver", "listele", "adım adım", "proje", "hata", "debug", "test"
]

# Sunucu komutları
SERVER_KEYWORDS = [
    "durum", "status", "servis", "service", "başlat", "durdur", "restart",
    "log", "cpu", "ram", "disk", "uptime", "process", "sunucu",
    "çalışıyor", "aktif", "pasif", "memory", "network", "port", "ping"
]

# Anında cevaplar (AI yok, 0ms)
GREETING_RESPONSES = [
    "Merhaba! 👋 Nasıl yardımcı olabilirim?",
    "Selam! Emrindeyim.",
    "Hey! Ne yapmamı istersin?",
]

import random

def _instant_reply(text: str) -> str | None:
    """Selamlama/teşekkür için anında cevap döner. AI değil."""
    lower = text.lower().strip()
    if any(k in lower for k in ["teşekkür", "sağol", "eyvallah"]):
        return "Rica ederim! Başka bir şey var mı?"
    if any(k in lower for k in ["tamam", "anladım", "tamamdır", "ok", "peki"]):
        return "Anlaşıldı. Başka bir isteğin olursa buradayım."
    if any(k in lower for k in ["görüşürüz", "hoşça kal", "bye", "iyi geceler"]):
        return "Görüşürüz! İyi günler. 🙌"
    if any(k in lower for k in GREETING_KEYWORDS):
        return random.choice(GREETING_RESPONSES)
    return None


class JarvisRouter:
    def __init__(self):
        self.core = CoreAgent()

        # Sub-agent'ları kaydet
        self.core.register_agent(PlannerAgent())
        self.core.register_agent(ReviewerAgent())
        self.core.register_agent(ClaudeAgent())
        self.core.register_agent(OllamaAgent())

        log.info("JarvisRouter hazır. Agents: %s", list(self.core.sub_agents.keys()))

    def _load_history(self) -> list:
        """Son N konuşmayı yükle"""
        if not CHAT_HISTORY_FILE.exists():
            return []
        try:
            lines = CHAT_HISTORY_FILE.read_text(encoding="utf-8").strip().split("\n")
            history = [json.loads(l) for l in lines if l.strip()]
            return history[-MAX_HISTORY:]
        except Exception:
            return []

    def _save_history(self, role: str, content: str):
        """Konuşmayı kaydet, 50 mesajı geçince otomatik sıkıştır"""
        try:
            CHAT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "role": role,
                "content": content,
                "time": datetime.datetime.utcnow().isoformat()
            }
            with open(CHAT_HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._maybe_compact()
        except Exception as e:
            log.error(f"Geçmiş kaydedilemedi: {e}")

    def _maybe_compact(self):
        """50 mesajı geçince memory_compactor.py'yi subprocess ile çalıştır"""
        import subprocess
        try:
            if not CHAT_HISTORY_FILE.exists():
                return
            line_count = CHAT_HISTORY_FILE.read_text(encoding="utf-8").count("\n")
            if line_count < 50:
                return
            log.info(f"Compaction tetiklendi ({line_count} mesaj)")
            subprocess.Popen(
                ["python3", "/opt/jarvis/skills/cognitive/memory_compactor.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            log.error(f"Compaction başlatılamadı: {e}")

    def _classify(self, text: str) -> str:
        """
        Mesajı sınıflandır:
        - 'greeting' → anında cevap, AI yok (0ms)
        - 'server'   → sunucu yönetimi skill
        - 'claude'   → karmaşık, Claude AI
        - 'ollama'   → basit soru, Ollama
        """
        lower = text.lower().strip()

        # Önce greeting kontrolü (hızlı, AI beklemez)
        if len(text) <= 60 and any(k in lower for k in GREETING_KEYWORDS):
            return "greeting"

        if any(k in lower for k in SERVER_KEYWORDS):
            return "server"

        if any(k in lower for k in COMPLEX_KEYWORDS) or len(text) > 120:
            return "claude"

        return "ollama"

    def handle(self, user_message: str) -> str:
        """Ana giriş noktası: mesaj al, cevap dön"""
        if not user_message.strip():
            return "Merhaba! Ben Jarvis. Sana nasıl yardımcı olabilirim?"

        log.info(f"Mesaj: {user_message[:80]}")

        # Greeting → anında cevap, geçmişe yazma bile gerek yok
        instant = _instant_reply(user_message)
        if instant:
            log.info("Kategori: greeting (instant)")
            self._save_history("user", user_message)
            self._save_history("assistant", instant)
            return instant

        history = self._load_history()
        self._save_history("user", user_message)

        category = self._classify(user_message)
        log.info(f"Kategori: {category}")

        response = ""

        # --- Sunucu Yönetimi ---
        if category == "server":
            response = self._handle_server(user_message)

        # --- Claude (karmaşık) ---
        elif category == "claude":
            claude = self.core.sub_agents.get("claude")
            if claude:
                task = Task(goal=user_message)
                result = claude.run(task, {"chat_history": history})
                response = result.get("output") or "Claude cevap veremedi."
                if result.get("error") == "claude_timeout":
                    log.warning("Claude timeout, Ollama'ya fallback")
                    response = self._try_ollama(user_message, history)
            else:
                response = "Claude agent kayıtlı değil."

        # --- Ollama (basit) ---
        else:
            response = self._try_ollama(user_message, history)

        self._save_history("assistant", response)
        return response

    def _try_ollama(self, message: str, history: list) -> str:
        """Ollama ile cevap dene, olmayınca Claude'a git"""
        ollama = self.core.sub_agents.get("ollama")
        if ollama:
            task = Task(goal=message)
            result = ollama.run(task, {"chat_history": history})
            if result.get("output") and not result.get("error"):
                return result["output"]
            log.warning(f"Ollama başarısız: {result.get('error')}, Claude'a geçiliyor")

        # Ollama yoksa veya hata varsa Claude
        claude = self.core.sub_agents.get("claude")
        if claude:
            task = Task(goal=message)
            result = claude.run(task, {"chat_history": history})
            return result.get("output") or "Yanıt üretilemedi."

        return "AI servisi şu an kullanılamıyor."

    def _handle_server(self, message: str) -> str:
        """Sunucu yönetimi komutlarını işle"""
        lower = message.lower()

        # Hangi işlem?
        if any(k in lower for k in ["durum", "status", "bilgi", "nasıl", "ne durumda"]):
            r = sunucu_yonet.run("durum")
            return f"Sunucu Durumu:\n{r['result']}"

        if any(k in lower for k in ["log", "loglar"]):
            service = "gateway"
            for svc in ["gateway", "openclaw", "ollama"]:
                if svc in lower:
                    service = svc
                    break
            r = sunucu_yonet.run("log", service)
            return f"{service} logları:\n{r['result'][:800]}"

        if any(k in lower for k in ["yeniden başlat", "restart"]):
            service = "gateway"
            for svc in ["gateway", "openclaw", "ollama"]:
                if svc in lower:
                    service = svc
                    break
            r = sunucu_yonet.run("yeniden-baslat", service)
            return f"{service} yeniden başlatıldı: {'✅' if r['success'] else '❌'}"

        if any(k in lower for k in ["process", "processler", "çalışan"]):
            r = sunucu_yonet.run("ps")
            return f"Çalışan processler:\n{r['result'][:600]}"

        # Genel sunucu sorusu → durum göster
        r = sunucu_yonet.run("durum")
        return f"Sunucu Durumu:\n{r['result']}"

    def get_memory_summary(self) -> str:
        """Son konuşmaları özet olarak dön"""
        history = self._load_history()
        if not history:
            return "Henüz konuşma geçmişi yok."
        lines = []
        for msg in history[-6:]:
            role = "Sen" if msg["role"] == "user" else "Jarvis"
            lines.append(f"{role}: {msg['content'][:80]}")
        return "\n".join(lines)

    def get_tasks_summary(self) -> str:
        """Son görevleri listele"""
        tasks = self.core.task_history[-5:]
        if not tasks:
            return "Henüz görev yok."
        lines = []
        for t in tasks:
            lines.append(f"[{t.id}] {t.status.value.upper()} - {t.title}")
        return "\n".join(lines)


# Singleton
_router = None

def get_router() -> JarvisRouter:
    global _router
    if _router is None:
        _router = JarvisRouter()
    return _router


if __name__ == "__main__":
    router = JarvisRouter()
    print("JarvisRouter test:")
    tests = [
        "sunucu durumu nedir?",
        "merhaba nasılsın",
        "agent.py dosyasını açıkla",
    ]
    for msg in tests:
        print(f"\n> {msg}")
        resp = router.handle(msg)
        print(f"Jarvis: {resp[:200]}")
