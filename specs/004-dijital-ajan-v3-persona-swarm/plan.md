# Implementation Plan: Dijital Ajan V3 — 7 Akıllı Persona + Obsidian + Swarm

**Branch**: `004-dijital-ajan-v3-persona-swarm` | **Date**: 2026-04-14 | **Spec**: `specs/004-dijital-ajan-v3-persona-swarm/spec.md`

## Summary

7 persona (Seda, Mert, Buse, Eren, Luna, Sabrican, Sabri) sistem prompt motoru ile gerçek uzman yanıtları üretir, Obsidian kasasına kendi klasöründen okur/yazar, karmaşık görevleri alt ajanlara bölerek orkestre eder. Ses + hologram kimlik katmanı mevcut altyapı üzerine eklenir. Luna küçük bir sub-feature: lab-only Foxguard/CAI tarama + audit logging.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript/Next.js (web-ui)
**Primary Dependencies**: FastAPI/aiohttp (bridge.py), PyYAML, edge-tts, groq SDK, gemini SDK
**Storage**: `state/agent_memory/<persona_id>/` (konuşma geçmişi), Obsidian markdown dosyaları (OBSIDIAN_VAULT_PATH)
**Testing**: pytest (`tests/`)
**Target Platform**: Windows 10, local (bridge.py port 8081)
**Project Type**: Desktop AI asistan
**Performance Goals**: Persona geçişi < 2sn, hologram renk değişimi < 1sn
**Constraints**: Backward-safe (bridge.py mevcut komutlar kırılmaz), credentials loga sızmaz, Luna lab_only

## Constitution Check

| Prensip | Durum | Not |
|---------|-------|-----|
| I. Local-First | ✅ | Tüm değişiklikler local; cloud LLM çağrısı mevcut altyapı üzerinden |
| II. Spec Before Impl | ✅ | Bu plan spec'ten sonra geliyor |
| III. Security/Redaction | ✅ | Luna audit log redaction, credentials .env'de kalır |
| IV. Read Before Write | ✅ | bridge.py, hey_jarvis.py, agents.yaml okundu |
| V. Verify Before Done | ✅ | Her faz sonunda smoke test |

**GATE**: Tüm prensipler geçiyor. Implementasyona devam edilebilir.

## Project Structure

```text
server/
├── bridge.py                        # Mevcut — yeni komutlar APPEND-ONLY
├── persona_manager.py               # Mevcut — değiştirilmeyecek
├── skills/
│   ├── obsidian_persona_skill.py    # YENİ: persona-aware Obsidian okuma/yazma
│   ├── sub_agent_runner.py          # YENİ: sub-agent orkestrasyon
│   ├── luna_scan_skill.py           # YENİ: Foxguard scanner wrapper
│   ├── luna_browser_skill.py        # YENİ: browser-use scope crawler
│   └── luna_report_skill.py         # YENİ: finding → Obsidian + Telegram
├── services/
│   └── luna_agent.py                # YENİ: Luna task orchestrator
└── logs/
    └── luna_audit.jsonl             # YENİ: append-only audit log

config/
├── agents.yaml                      # Mevcut — system_prompt/sub_agents/obsidian_folder ZATEN DOLU
└── luna_targets.yaml                # YENİ: authorized targets whitelist

state/
└── agent_memory/
    └── <persona_id>/                # Mevcut dizin yapısı, persona isolation hazır

tests/
├── test_obsidian_persona_skill.py   # YENİ
├── test_sub_agent_runner.py         # YENİ
└── test_luna_agent.py               # YENİ
```

## Mevcut Altyapı (Değiştirilmeyecek)

| Bileşen | Dosya | Durum |
|---------|-------|-------|
| System prompt injection | `bridge.py:1487` | ✅ Çalışıyor |
| Voice okuma | `hey_jarvis.py:227 _current_voice_name()` | ✅ Çalışıyor |
| Persona switch | `server/persona_manager.py switch_persona()` | ✅ Çalışıyor |
| Hologram polling | `apps/desktop-hologram/renderer.js` | ✅ Çalışıyor |
| agents.yaml yapısı | `config/agents.yaml` | ✅ system_prompt + sub_agents + obsidian_folder dolu |

---

## Phase 0: Research

**Araştırma soruları**:

1. **Obsidian dosya sistemi**: OBSIDIAN_VAULT_PATH altında markdown yaz/oku — `pathlib.Path` yeterli, API yok.
2. **Sub-agent tipleri**: `web_search`, `code_analyzer`, `file_reader`, `obsidian_writer`, `summarizer` — her biri tek bir fonksiyon, sıralı çalışır (paralel ileriki fazda).
3. **Luna toolchain**: `foxguard` binary opsiyonel — yüklü değilse graceful fail. CAI aynı şekilde.

**Kararlar**:

| Karar | Seçim | Gerekçe |
|-------|-------|---------|
| Obsidian erişim | Direkt dosya sistemi | API yok, markdown sync otomatik |
| Sub-agent execution | Sıralı, aynı process | Spec scope: paralel ileriki faz |
| Luna tool absent | Graceful fail + log | Binary opsiyonel, sistem çökmemeli |
| Memory isolation | `state/agent_memory/<id>/` | Zaten dizin yapısı var |

---

## Phase 1: Design & Contracts

### Data Model

**PersonaProfile** (config/agents.yaml'dan okunur):
```yaml
id: seda
name: Seda
color: "#00ff88"
voice: AhmetNeural
role: "Senior Yazılım Mühendisi"
system_prompt: "..."
sub_agents: [code_analyzer, file_reader, obsidian_writer, summarizer]
obsidian_folder: "personas/seda"
```

**ObsidianNote** (dosya sistemi):
```
{OBSIDIAN_VAULT_PATH}/personas/{persona_id}/{YYYY-MM-DD}-{slug}.md
---
persona_id: seda
created_at: 2026-04-14T10:30:00
tags: [seda, not]
---
{content}
```

**SubAgentTask** (runtime, in-memory):
```python
@dataclass
class SubAgentTask:
    id: str
    type: str  # web_search | code_analyzer | file_reader | obsidian_writer | summarizer
    payload: dict
    status: str  # pending | running | done | failed
    result: str | None
```

**LunaFinding** (audit + report):
```python
@dataclass
class LunaFinding:
    finding_id: str
    target_id: str
    severity: str  # critical | high | medium | low | info
    title: str
    description: str
    evidence: str
    ts: str
```

### Bridge Contracts (Yeni Telegram Komutları)

| Komut | Format | Açıklama |
|-------|--------|---------|
| `/luna-tara` | `/luna-tara <target_id>` | Foxguard scan, audit log, Telegram rapor |
| `/luna-kapsam` | `/luna-kapsam <program_url>` | Browser crawl → luna_targets.yaml güncelle |
| `/luna-analiz` | `/luna-analiz <target_id> <görev>` | CAI lab-only analiz |

> Not: Obsidian kaydetme/okuma komutları Telegram formatı değil, LLM niyeti tespiti ile çalışır (bridge.py intent parser).

---

## Implementation Phases

### Faz 1: Obsidian Persona Skill (FR-2, FR-3)

**Dosya**: `server/skills/obsidian_persona_skill.py`

```python
def write_persona_note(persona_id: str, title: str, content: str) -> str:
    """OBSIDIAN_VAULT_PATH/personas/{persona_id}/{date}-{slug}.md yazar"""

def read_persona_notes(persona_id: str, limit: int = 5) -> list[dict]:
    """Persona klasöründeki son N notu döner (title, content, date)"""

def get_persona_context(persona_id: str) -> str:
    """LLM bağlamı için son notları özetler"""
```

Bridge.py'a 2 intent hook eklenir (APPEND-ONLY):
- "kaydet" / "not al" / "Obsidian'a yaz" → `write_persona_note()`
- "ne biliyorsun" / "araştırdıklarımız" → `read_persona_notes()` → system context'e ekle

### Faz 2: Sub-Agent Runner (FR-4)

**Dosya**: `server/skills/sub_agent_runner.py`

```python
def run_sub_agents(persona_id: str, task_description: str, agent_types: list[str]) -> str:
    """Görevi adımlara böler, her sub_agent tipi için runner çağırır, sonuçları birleştirir"""

def _run_web_search(payload: dict) -> str: ...
def _run_code_analyzer(payload: dict) -> str: ...
def _run_file_reader(payload: dict) -> str: ...
def _run_obsidian_writer(payload: dict) -> str: ...
def _run_summarizer(payload: dict) -> str: ...
```

3+ adımlı görev tespiti: mesaj "adım adım", "önce...sonra...", "analiz et ve özetle" pattern'leri.

### Faz 3: Luna Cyber Stack (US1-US5)

**Dosya**: `server/services/luna_agent.py`, `server/skills/luna_*.py`

Zincir:
```
/luna-tara jarvis-bridge
  → is_authorized("jarvis-bridge")  # luna_targets.yaml'dan
  → run_foxguard_scan(path)          # subprocess, graceful fail
  → parse_foxguard_output(raw)       # LunaFinding listesi
  → audit_log(action, target, ...)   # luna_audit.jsonl
  → Telegram rapor
```

**Güvenlik gate'leri** (hiçbiri atlanamaz):
1. `is_authorized()` → whitelist kontrolü
2. `_is_lab_target()` → CAI için zorunlu
3. `audit_log()` → her işlem kayıt altına alınır

### Faz 4: Ses + Hologram Doğrulama (FR-5)

Mevcut altyapı zaten çalışıyor. Doğrulama:
- `hey_jarvis.py:_current_voice_name()` persona voice'u okur → edge-tts'e verir
- `renderer.js` `/api/persona/active` poll eder → color → CSS glow
- Test: Buse aktif yap → hologram `#ff69b4`, TTS EmelNeural doğrula

---

## Verification Plan

| Test | Yöntem |
|------|--------|
| System prompt injection | Seda aktif → Telegram mesaj → yanıt teknik dil içermeli |
| Obsidian yazma | `/luna-not yaz` → `{VAULT}/personas/seda/*.md` dosya oluşmalı |
| Obsidian okuma | "ne biliyorsun?" → yanıt Obsidian referansı içermeli |
| Memory isolation | Seda → Buse geç → Buse Seda'nın konuşmasını bilmemeli |
| Luna Foxguard | Binary yoksa → graceful fail mesajı |
| Luna authorization | Bilinmeyen target → TargetNotAuthorizedError |
| Hologram renk | `switch_persona("buse")` → renderer color `#ff69b4` |
| TTS ses | Buse aktif → edge-tts EmelNeural kullanılıyor |

```bash
# Smoke test suite
python -m pytest tests/test_obsidian_persona_skill.py -q
python -m pytest tests/test_sub_agent_runner.py -q
python -m pytest tests/test_luna_agent.py -q
```

---

## Complexity Tracking

Tüm Constitution gate'leri geçti — yok.
