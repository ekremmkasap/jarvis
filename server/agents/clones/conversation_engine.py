"""
conversation_engine.py
Jarvis Swarm — Ajanlar arası sesli diyalog motoru.
CEO bir görev verir → ilgili ajanlar sırayla konuşur → ses çıktısı verir.

KURAL: API key'leri hiçbir zaman loga yazdırma.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx

# ── Proje yolu sabitleri ──────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent.parent.parent  # jarvis-mission-control/
_LOG_DIR = _ROOT / "server" / "logs"
_TMP_DIR = _ROOT / "tmp"
_DIALOGUE_LOG = _LOG_DIR / "swarm_dialogue.jsonl"
_STATE_FILE = _ROOT / "state" / "swarm_speaking_state.json"

_LOG_DIR.mkdir(parents=True, exist_ok=True)
_TMP_DIR.mkdir(parents=True, exist_ok=True)
(_ROOT / "state").mkdir(parents=True, exist_ok=True)

# ── Ajan tanımları ────────────────────────────────────────────────────────────
AGENT_PROFILES: dict[str, dict] = {
    "seda": {
        "name": "Seda",
        "role": "Developer",
        "api_key_env": "GEMINI_KEY_SEDA",
        "voice": "tr-TR-EmelNeural",
        "color": "#00ff88",
        "prompt_file": _ROOT / "server/agents/clones/seda/core/prompt.txt",
    },
    "mert": {
        "name": "Mert",
        "role": "Researcher",
        "api_key_env": "GEMINI_KEY_MERT",
        "voice": "tr-TR-AhmetNeural",
        "color": "#ffdd00",
        "prompt_file": _ROOT / "server/agents/clones/mert/core/prompt.txt",
    },
    "buse": {
        "name": "Buse",
        "role": "Marketer",
        "api_key_env": "GEMINI_KEY_BUSE",
        "voice": "tr-TR-EmelNeural",
        "color": "#ff69b4",
        "prompt_file": _ROOT / "server/agents/clones/buse/core/prompt.txt",
    },
    "eren": {
        "name": "Eren",
        "role": "Analyst",
        "api_key_env": "GEMINI_KEY_EREN",
        "voice": "tr-TR-AhmetNeural",
        "color": "#ff8c00",
        "prompt_file": _ROOT / "server/agents/clones/eren/core/prompt.txt",
    },
    "luna": {
        "name": "Luna",
        "role": "Security",
        "api_key_env": "GEMINI_KEY_LUNA",
        "voice": "tr-TR-EmelNeural",
        "color": "#9b59b6",
        "prompt_file": _ROOT / "server/agents/clones/luna/core/prompt.txt",
    },
    "sabrican": {
        "name": "Sabrican",
        "role": "Ops",
        "api_key_env": "GEMINI_KEY_SABRICAN",
        "voice": "tr-TR-AhmetNeural",
        "color": "#95a5a6",
        "prompt_file": _ROOT / "server/agents/clones/sabrican/core/prompt.txt",
    },
    "sabri": {
        "name": "Sabri",
        "role": "Wildcard",
        "api_key_env": "GEMINI_KEY_SABRI",
        "voice": "tr-TR-AhmetNeural",
        "color": "#e74c3c",
        "prompt_file": _ROOT / "server/agents/clones/sabri/core/prompt.txt",
    },
}

# Anahtar kelime → ajan eşlemesi (CEO'nun otomatik seçimi için)
KEYWORD_MAP: dict[str, list[str]] = {
    "kod": ["seda"],
    "bug": ["seda"],
    "geliştir": ["seda"],
    "araştır": ["mert"],
    "analiz": ["mert", "eren"],
    "rakip": ["mert"],
    "pazarlama": ["buse"],
    "müşteri": ["buse"],
    "landing": ["buse"],
    "güvenlik": ["luna"],
    "risk": ["luna"],
    "deploy": ["sabrican"],
    "sunucu": ["sabrican"],
    "ops": ["sabrican"],
    "özellik": ["seda", "buse"],
    "plan": ["eren"],
}


def _read_prompt(agent_id: str) -> str:
    """Ajan kişilik prompt'unu dosyadan oku."""
    path = AGENT_PROFILES[agent_id]["prompt_file"]
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        p = AGENT_PROFILES[agent_id]
        return f"You are {p['name']}, {p['role']} in Jarvis swarm. Always respond in Turkish."


def _update_speaking_state(
    speaking: Optional[str],
    text: str,
    participants: list[str],
    dialogue_active: bool,
    ceo_phase: str = "thinking",
) -> None:
    """state/swarm_speaking_state.json'u güncelle — hologram pencereler bunu okur."""
    payload = {
        "speaking": speaking,
        "text": text[:60],
        "participants": participants,
        "dialogue_active": dialogue_active,
        "ceo_phase": ceo_phase,
        "updated_at": time.time(),
    }
    try:
        _STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _log_turn(agent_id: str, turn: int, text: str) -> None:
    """Diyalog turunu JSONL log dosyasına yaz. Ses yolu veya key yok."""
    entry = {
        "ts": time.time(),
        "agent": agent_id,
        "turn": turn,
        "text": text,
    }
    try:
        with _DIALOGUE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


async def _call_gemini(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int = 180) -> str:
    """Gemini Flash API'yi çağır. api_key asla loglara gitmez."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.85,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        # key'i asla yazdırma
        return f"[{e.__class__.__name__}: API yanıt vermedi]"


async def _tts_generate(agent_id: str, text: str, turn: int) -> Optional[Path]:
    """edge_tts ile mp3 üret. Yoksa None döner."""
    try:
        import edge_tts  # type: ignore
    except ImportError:
        return None

    voice = AGENT_PROFILES[agent_id]["voice"]
    out = _TMP_DIR / f"{agent_id}_{turn}.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out))
        return out
    except Exception:
        return None


async def _play_audio(audio_file: Optional[Path]) -> None:
    """Ses dosyasını çal (pygame fallback playsound)."""
    if not audio_file or not audio_file.exists():
        return
    try:
        import pygame  # type: ignore
        pygame.mixer.init()
        pygame.mixer.music.load(str(audio_file))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        return
    except Exception:
        pass
    try:
        from playsound import playsound  # type: ignore
        await asyncio.get_event_loop().run_in_executor(None, playsound, str(audio_file))
    except Exception:
        pass


def route_keywords(topic: str) -> list[str]:
    """
    Topic'e göre ajan seç.
    'all' veya 'swarm' geçiyorsa → tüm 7 ajan.
    Yoksa keyword eşleşmesi + eksikler tamamlanır → max 7.
    """
    topic_lower = topic.lower()
    all_agents = list(AGENT_PROFILES.keys())  # 7 ajan sırası

    # Swarm / tüm ajan modu
    if any(w in topic_lower for w in ("all", "swarm", "tümü", "hepsi", "herkes", "genel")):
        return all_agents

    seen: list[str] = []
    for kw, agents in KEYWORD_MAP.items():
        if kw in topic_lower:
            for a in agents:
                if a not in seen:
                    seen.append(a)

    # Keyword eşleşmesi yoksa tüm ajanlar katılır
    if not seen:
        return all_agents

    # Eksik ajanları sırayla tamamla — minimum 7
    for a in all_agents:
        if a not in seen:
            seen.append(a)

    return seen  # tüm 7 ajan


class ConversationEngine:
    """
    Ajanlar arası sesli diyalog motoru.
    CEO bir görev verir → ilgili ajanlar sırayla konuşur → ses çıktısı verir.
    """

    async def dialogue(
        self,
        topic: str,
        participants: list[str],
        rounds: int = 2,
    ) -> list[dict]:
        """
        Dönüş:
        [
          {"agent": "seda", "text": "...", "audio_file": "tmp/seda_0.mp3"},
          ...
        ]
        """
        # katılımcıları doğrula
        valid = [p for p in participants if p in AGENT_PROFILES]
        if not valid:
            valid = ["seda", "mert"]

        _update_speaking_state(
            speaking=None,
            text=f"Diyalog başlıyor: {topic[:40]}",
            participants=valid,
            dialogue_active=True,
            ceo_phase="thinking",
        )

        history: list[dict] = []
        results: list[dict] = []
        global_turn = 0

        for round_idx in range(rounds):
            for agent_id in valid:
                profile = AGENT_PROFILES[agent_id]
                api_key = os.getenv(profile["api_key_env"], "")

                # Önceki konuşmaları context olarak derle
                context_lines = [
                    f"{h['agent'].capitalize()}: {h['text']}"
                    for h in history[-6:]  # son 6 mesaj
                ]
                context_str = "\n".join(context_lines) if context_lines else "(ilk konuşma)"

                system_prompt = _read_prompt(agent_id)
                user_prompt = (
                    f"Konu: {topic}\n\n"
                    f"Diyalog geçmişi:\n{context_str}\n\n"
                    f"Şimdi {profile['name']} olarak kısa (1-2 cümle) Türkçe yanıt ver. "
                    f"Kendi rolüne ({profile['role']}) uygun konuş."
                )

                # State güncelle — hologram "konuşuyor" görecek
                _update_speaking_state(
                    speaking=agent_id,
                    text=f"{profile['name']} düşünüyor...",
                    participants=valid,
                    dialogue_active=True,
                    ceo_phase="thinking",
                )

                if api_key:
                    text = await _call_gemini(api_key, system_prompt, user_prompt)
                else:
                    text = self._mock_response(agent_id, topic, round_idx)

                text = text.strip()
                short_text = text[:60]

                # State: şu an konuşuyor
                _update_speaking_state(
                    speaking=agent_id,
                    text=short_text,
                    participants=valid,
                    dialogue_active=True,
                    ceo_phase="speaking",
                )

                # TTS üret
                audio_file = await _tts_generate(agent_id, text, global_turn)

                # Log (sadece metin, key yok)
                _log_turn(agent_id, global_turn, text)

                # Ses çal
                await _play_audio(audio_file)

                entry = {
                    "agent": agent_id,
                    "text": text,
                    "audio_file": str(audio_file) if audio_file else None,
                    "turn": global_turn,
                    "round": round_idx,
                }
                history.append({"agent": agent_id, "text": text})
                results.append(entry)
                global_turn += 1

                # Kısa bekleme — konuşmalar arasında nefes
                await asyncio.sleep(0.4)

        # Diyalog bitti
        _update_speaking_state(
            speaking=None,
            text="Diyalog tamamlandı.",
            participants=valid,
            dialogue_active=False,
            ceo_phase="idle",
        )

        return results

    def _mock_response(self, agent_id: str, topic: str, round_idx: int) -> str:
        """Test modunda gerçek API çağrısı yapmadan yanıt üret."""
        profile = AGENT_PROFILES[agent_id]
        templates = {
            "seda": [
                f"Şöyle bir şey var ki, '{topic}' konusunda kodu inceliyorum.",
                "Birinci turda bulguları aldım, şimdi implementasyona geçiyorum.",
            ],
            "mert": [
                f"'{topic}' için rakip analizi başlattım, ilk bulgular ilginç.",
                "Araştırmam tamamlandı, en iyi pattern'i raporluyorum.",
            ],
            "buse": [
                f"Müşteri perspektifinden '{topic}' öncelikli görünüyor.",
                "Mert'in bulguları harika, landing page'e de yansıtalım.",
            ],
            "eren": [
                f"'{topic}' verisini analiz ediyorum, trend pozitif.",
                "İkinci tur analizim hazır, dashboard'a ekledim.",
            ],
            "luna": [
                f"'{topic}' için güvenlik taraması başlattım, risk düşük.",
                "Güvenlik raporu hazır, onaylıyorum.",
            ],
            "sabrican": [
                f"'{topic}' deploy pipeline'ını hazırlıyorum.",
                "Sistem stabil, production'a geçebiliriz.",
            ],
            "sabri": [
                f"'{topic}' için alternatif bir yaklaşım öneririm.",
                "Joker kart: Herkese yardım etmeye hazırım.",
            ],
        }
        lines = templates.get(agent_id, [f"{profile['name']} konuşuyor."])
        return lines[round_idx % len(lines)]

    def _mock_dialogue(self, topic: str, participants: list[str], rounds: int = 1) -> list[dict]:
        """Senkron test yardımcısı — gerçek API çağırmaz."""
        results = []
        for turn, agent_id in enumerate(participants * rounds):
            text = self._mock_response(agent_id, topic, turn // len(participants))
            results.append({"agent": agent_id, "text": text, "audio_file": None, "turn": turn})
        return results
