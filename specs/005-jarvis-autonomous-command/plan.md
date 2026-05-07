# Implementation Plan: MARK-XXXXVI — Jarvis Autonomous Command Layer

**Branch**: `005-jarvis-autonomous-command` | **Date**: 2026-04-14 | **Spec**: `specs/005-jarvis-autonomous-command/spec.md`

## Summary

Jarvis'e 6 yeni katman ekleniyor: Telegram sesli mesaj (STT/TTS), whitelist-gated PC kontrol, intent tabanlı otomatik persona seçimi, Obsidian+Wiki otomatik bellek yazımı, Codex slot auto-dispatch ve agent hafıza API'si. Tüm değişiklikler mevcut altyapı üzerine APPEND-ONLY — `bridge.py` geriye dönük uyumlu kalır.

## Technical Context

**Language/Version**: Python 3.11, TypeScript/Next.js (web-ui panel)  
**Primary Dependencies**: python-telegram-bot (mevcut), groq SDK (mevcut), edge-tts (mevcut), pyautogui (mevcut), psutil (yeni), Pydantic (mevcut)  
**Storage**: `state/agent_memory/<persona_id>/` (JSONL), Obsidian markdown (OBSIDIAN_VAULT_PATH), `wiki/` dizini  
**Testing**: pytest  
**Target Platform**: Windows 10, local  
**Project Type**: Desktop AI asistan  
**Performance Goals**: Ses → yanıt < 15sn, PC komut < 3sn, intent < 2sn  
**Constraints**: bridge.py backward-safe, credentials loga sızmaz, PC whitelist sıfır tolerans

## Constitution Check

| Prensip | Durum | Not |
|---------|-------|-----|
| I. Local-First | ✅ | Groq Whisper ücretsiz, STT/TTS local altyapı |
| II. Spec Before Impl | ✅ | spec → research → plan sırası takip edildi |
| III. Security/Redaction | ✅ | PC whitelist, audit log, credentials .env'de |
| IV. Read Before Write | ✅ | bridge.py, intent_skill.py, computer_control_skill.py okundu |
| V. Verify Before Done | ✅ | Her faz sonunda smoke test |

**GATE**: Tüm prensipler geçiyor.

## Project Structure

```text
server/skills/
├── telegram_voice_handler.py    # YENİ: .ogg download → whisper_skill → text
├── telegram_tts_reply.py        # YENİ: text → edge-tts → .ogg → send_voice
├── pc_control_gateway.py        # YENİ: whitelist check + dispatch + audit log
├── intent_persona_router.py     # YENİ: intent → persona auto-switch
├── obsidian_auto_writer.py      # YENİ: araştırma/eylem sonucu → Obsidian
├── wiki_auto_writer.py          # YENİ: wiki intent → wiki/ yazım
└── agent_memory_skill.py        # YENİ: /hafiza + /ajanlarin-ozeti

config/
├── pc_control_whitelist.yaml    # YENİ: komut → eylem → izin map
└── agents.yaml                  # GÜNCELLEME: codex_slot alanı ekle

server/bridge.py                 # APPEND-ONLY: yeni handler'lar
apps/web-ui/src/components/
└── AgentMemoryPanel.tsx         # YENİ: aktif persona + son mesajlar

tests/
├── test_telegram_voice.py
├── test_pc_control_gateway.py
├── test_intent_persona_router.py
├── test_obsidian_auto_writer.py
└── test_agent_memory_skill.py
```

## Mevcut Altyapı (Değiştirilmeyecek)

| Bileşen | Dosya | Kullanım |
|---------|-------|---------|
| Whisper STT | `server/skills/whisper_skill.py` | `transcribe_audio(path)` çağrısı |
| send_voice | `server/bridge.py:4505` | `self.send_voice(chat_id, audio_path)` |
| Intent classifier | `server/skills/intent_skill.py` | `classify_intent()` + `handle_with_intent()` genişletilir |
| PC control | `server/skills/computer_control_skill.py` | Gateway üzerinden çağrılır |
| Wiki komutları | `server/bridge.py:6668` | `_handle_wiki_command()` var, intent hook eklenir |
| Obsidian skill | `server/skills/persona_obsidian_skill.py` | 004 feature'dan, auto-writer kullanır |
| Codex orchestrator | `codex_orchestrator.py` | Slot dispatch zaten var |
| Vision analyzer | `server/agents/vision_analyzer.py` | Screenshot analizi için kullanılabilir |

---

## Phase 0: Research

Tüm kararlar `research.md`'de alındı. Öne çıkan bulgular:

| Karar | Seçim | Gerekçe |
|-------|-------|---------|
| STT | Groq Whisper API | Mevcut key, Türkçe destekli, ücretsiz |
| TTS reply | edge-tts + send_voice | bridge.py zaten var |
| PC güvenlik | YAML whitelist | Minimal, okunabilir, değiştirilebilir |
| Intent routing | intent_skill.py genişletme | Sıfırdan yazmaya gerek yok |
| Obsidian auto | persona_obsidian_skill.py hook | 004 altyapısı |
| Wiki auto | obsidian_sync_skill genişletme | run_wiki() zaten var |
| Codex slot | agents.yaml codex_slot alanı | Minimal değişiklik |

---

## Phase 1: Design & Contracts

### Data Model → `data-model.md` ✅

**Kritik varlıklar**:
- `VoiceMessage` — Telegram .ogg → STT metni
- `PCCommand` — whitelist check + audit
- `IntentResult` — intent + confidence + auto_switch
- `PCControlWhitelist` — YAML config
- `CodexPersonaSlotMap` — agents.yaml eklentisi
- `AgentMemorySnapshot` — API response şeması

### Contracts → `contracts/` ✅

- `telegram-commands.md` — Sesli mesaj, PC kontrol, hafıza, codex dispatch komutları
- `http-api.md` — `/api/persona/{id}/memory`, `/api/agents/summary`, `/api/pc/status`

---

## Implementation Phases

### Faz 1: Telegram Ses Kanalı (US1)

**Yeni**: `server/skills/telegram_voice_handler.py`
```python
async def handle_voice_message(update, context) -> str:
    """Telegram .ogg indir → geçici path → whisper_skill.transcribe_audio() → metin"""

async def send_voice_reply(chat_id: int, text: str, voice: str = None) -> None:
    """text → edge-tts .mp3 → bridge.send_voice(chat_id, path) → cleanup"""
```

`bridge.py` APPEND: Telegram handler'a `voice` message type handler ekle → `handle_voice_message()` çağır.

### Faz 2: PC Kontrol Gateway (US2)

**Yeni**: `server/skills/pc_control_gateway.py`
```python
def check_whitelist(command_key: str, args: str = None) -> bool:
    """config/pc_control_whitelist.yaml okur, komut + args doğrular"""

def execute_pc_command(command_key: str, args: str, persona_id: str, chat_id: int) -> str:
    """whitelist_check → computer_control_skill dispatch → audit_log → ObsidianAutoEntry"""

def get_system_status() -> dict:
    """psutil: cpu_percent, ram, disk → dict"""

def take_screenshot() -> str:
    """pyautogui.screenshot() → geçici path → döner"""
```

`bridge.py` APPEND: `/pc-durum`, `/ekran-goruntusu`, `/ac`, `/dosya-gonder`, `/jarvis-baslat`, `/jarvis-kapat`

**Yeni config**: `config/pc_control_whitelist.yaml`

### Faz 3: Intent → Persona Router (US3)

**Yeni**: `server/skills/intent_persona_router.py`
```python
PERSONA_INTENTS = {
    "research": "mert",
    "code": "seda",
    "social": "buse",
    "aws": "sabrican",
    "youtube": "eren",
    "strategy": "sabri",
    "security": "luna",
}

def route_to_persona(intent_result: dict, current_persona: str, chat_id: int) -> str | None:
    """intent + confidence → persona switch veya None"""
```

`intent_skill.py` APPEND: `PERSONA_INTENTS` routing ekle, `bridge.py:4225`'deki intent hook'u genişlet.

### Faz 4: Obsidian + Wiki Otomatik Yazım (US4)

**Yeni**: `server/skills/obsidian_auto_writer.py`
```python
def auto_write_research(persona_id: str, query: str, result: str) -> None:
    """Araştırma tamamlandığında → persona_obsidian_skill.write_persona_note()"""

def auto_write_pc_action(command: str, result: str) -> None:
    """PC eylem logu → personas/sabrican/actions/"""
```

**Yeni**: `server/skills/wiki_auto_writer.py`
```python
def write_wiki_page(title: str, content: str, linked_personas: list[str]) -> str:
    """wiki/{slug}.md yaz → index.md + log.md güncelle"""

def update_hot_md(summary: str) -> None:
    """wiki/hot.md son ~500 kelimelik özeti güncelle"""
```

`intent_skill.py` APPEND: "wiki'ye ekle" intent → `write_wiki_page()`

### Faz 5: Codex Slot Auto-Dispatch (US5)

`config/agents.yaml` GÜNCELLEME: Her persona'ya `codex_slot` alanı ekle.

`bridge.py /codex-dispatch` GÜNCELLEME: `get_active_persona()["codex_slot"]` → slot parametresi.

### Faz 6: Agent Hafıza Paneli (US6)

**Yeni**: `server/skills/agent_memory_skill.py`
```python
def get_persona_memory(persona_id: str, limit: int = 5) -> AgentMemorySnapshot:
    """state/agent_memory/{id}/ JSONL okur → son N mesaj"""

def get_all_agents_summary() -> list[dict]:
    """Tüm 7 persona için memory snapshot + obsidian_note_count"""
```

`bridge.py` APPEND: `/hafiza`, `/ajanlarin-ozeti` Telegram komutları + `GET /api/persona/{id}/memory` + `GET /api/agents/summary` + `GET /api/pc/status`

**Web UI**: `apps/web-ui/src/components/AgentMemoryPanel.tsx` — polling 3sn, aktif persona + son mesajlar.

---

## Verification Plan

| Test | Yöntem |
|------|--------|
| Sesli mesaj STT | Telegram'a .ogg gönder → `transcription` metin döner |
| TTS reply | `send_voice_reply()` → chat'te ses mesajı gelir |
| PC whitelist geçer | `/pc-durum` → CPU/RAM bilgisi döner |
| PC whitelist reddeder | `/komut evil` → "izin verilmiyor" mesajı |
| Intent routing | "eBay araştır" → Mert aktif |
| Obsidian auto-write | Araştırma tamamla → vault'ta dosya var |
| Wiki intent | "wiki'ye ekle" → `wiki/yeni-sayfa.md` oluşur |
| Codex auto-dispatch | Seda aktif → forge slot'una iş gider |
| Memory API | `GET /api/persona/seda/memory` → messages listesi |
| Hafıza komutu | `/hafiza seda` → son 5 mesaj Telegram'da |

```bash
python -m pytest tests/test_telegram_voice.py tests/test_pc_control_gateway.py tests/test_intent_persona_router.py tests/test_obsidian_auto_writer.py tests/test_agent_memory_skill.py -q
```

---

## Complexity Tracking

Constitution gate ihlali yok.
