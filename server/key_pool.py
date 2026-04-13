"""
key_pool.py — Otomatik key rotasyon sistemi
Biri tükenince sıradakine geçer. Her yerden key alır.
"""
import os
import time
import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# State dosyası — hangi key tükenmiş, ne zaman reset olur
_STATE_FILE = Path(__file__).parent.parent / "state" / "key_pool_state.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


class KeyPool:
    """
    Kullanım:
        pool = KeyPool("gemini", ["GEMINI_API_KEY", "GEMINI_KEY_SEDA", "GEMINI_KEY_MERT", ...])
        key  = pool.get()        # aktif key
        pool.mark_exhausted(key) # bu key tükendi, sıradakine geç
    """

    def __init__(self, provider: str, env_vars: list[str], cooldown_seconds: int = 3600):
        self.provider = provider
        self.env_vars = env_vars
        self.cooldown = cooldown_seconds

    def _all_keys(self) -> list[str]:
        keys = []
        for var in self.env_vars:
            val = os.getenv(var, "").strip()
            if val:
                keys.append(val)
        return keys

    def get(self) -> Optional[str]:
        """Kullanılabilir ilk key'i döndür."""
        state = _load_state()
        exhausted = state.get(self.provider, {})
        now = time.time()

        for key in self._all_keys():
            key_id = key[-8:]  # son 8 karakter — loga güvenli
            entry = exhausted.get(key_id, {})
            cooldown_until = entry.get("until", 0)

            if now >= cooldown_until:
                return key

        log.warning(f"[KeyPool] {self.provider}: tüm keyler tükendi!")
        return None

    def mark_exhausted(self, key: str, cooldown_seconds: Optional[int] = None):
        """Bu key tükendi — cooldown başlat."""
        state = _load_state()
        if self.provider not in state:
            state[self.provider] = {}

        key_id = key[-8:]
        cd = cooldown_seconds or self.cooldown
        state[self.provider][key_id] = {
            "until": time.time() + cd,
            "marked_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        _save_state(state)
        log.info(f"[KeyPool] {self.provider} key ***{key_id} {cd//60}dk cooldown'a alındı")

    def status(self) -> dict:
        """Hangi keyler aktif, hangileri beklemede."""
        state = _load_state()
        exhausted = state.get(self.provider, {})
        now = time.time()
        result = {"provider": self.provider, "keys": []}

        for key in self._all_keys():
            key_id = key[-8:]
            entry = exhausted.get(key_id, {})
            until = entry.get("until", 0)
            result["keys"].append({
                "id": f"***{key_id}",
                "status": "active" if now >= until else "cooldown",
                "ready_at": time.strftime("%H:%M:%S", time.localtime(until)) if now < until else "now"
            })

        return result


# ── Hazır pool'lar — .env'deki tüm keyleri toplar ──

GEMINI_POOL = KeyPool("gemini", [
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_KEY_SEDA",
    "GEMINI_KEY_MERT",
    "GEMINI_KEY_BUSE",
    "GEMINI_KEY_EREN",
    "GEMINI_KEY_LUNA",
    "GEMINI_KEY_SABRICAN",
    "GEMINI_KEY_SABRI",
])

GROQ_POOL = KeyPool("groq", [
    "GROQ_API_KEY",
    "GROQ_KEY_2",
    "GROQ_KEY_3",
    "GROQ_KEY_4",
    "GROQ_KEY_5",
], cooldown_seconds=86400)  # Groq günlük limit — 24 saat cooldown


def get_gemini_key() -> Optional[str]:
    return GEMINI_POOL.get()


def get_groq_key() -> Optional[str]:
    return GROQ_POOL.get()


def pool_status() -> dict:
    return {
        "gemini": GEMINI_POOL.status(),
        "groq": GROQ_POOL.status(),
    }
