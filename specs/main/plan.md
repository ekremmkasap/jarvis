# Implementation Plan: Persona Switching — "Seda ile Konuş"

**Branch**: `main` | **Date**: 2026-04-13 | **Feature**: Dijital Ajan Persona Switching  
**Input**: Kullanıcı "Seda ile konuş" dediğinde bridge hata veriyor — `persona_manager` modülü eksik

---

## Summary

Kullanıcı bir persona çağırdığında (`"Seda ile konuş"`, `"Buse'yi çağır"`) bridge.py `persona_manager.switch_persona()` fonksiyonunu import etmeye çalışıyor ancak `server/persona_manager.py` dosyası hiç oluşturulmamış. Plan: bu modülü sıfırdan yaz, `state/active_agent.json`'ı yönet, `config/agents.yaml`'a persona profillerini ekle, bridge.py import zincirini düzelt.

---

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: PyYAML (mevcut), json (stdlib)  
**Storage**: `state/active_agent.json` (dosya bazlı)  
**Testing**: pytest  
**Target Platform**: Windows 10, bridge.py HTTP server (port 8081)  
**Project Type**: skill modülü + bridge entegrasyonu  
**Performance Goals**: <50ms persona switch  
**Constraints**: bridge.py backward-safe kalmalı; mevcut Telegram/voice akışı bozulmamalı  
**Scale/Scope**: 7 persona (Seda, Mert, Buse, Eren, Luna, Sabrican, Sabri)

---

## Constitution Check

| Prensip | Durum | Not |
|---------|-------|-----|
| I. Local-First | ✅ | Persona state dosya bazlı, cloud yok |
| II. Spec Before Impl | ✅ | Bu plan o adım |
| III. Security | ✅ | active_agent.json'da credential yok |
| IV. Read Before Write | ✅ | bridge.py okundu, import zinciri analiz edildi |
| V. Verify Before Done | ⬜ | Smoke test tasks'ta tanımlı |

**Gate**: PASS — devam edilebilir.

---

## Project Structure

```text
server/
├── persona_manager.py          # YENİ — switch_persona, get_active_persona, detect_switch_from_text
├── bridge.py                   # DEĞİŞİKLİK — import düzeltmesi (zaten _switch_persona_for_chat var)
config/
├── agents.yaml                 # EKLENİYOR — 7 persona profili (Seda, Mert, Buse, ...)
state/
├── active_agent.json           # YENİ — mevcut aktif persona state dosyası
specs/main/
├── plan.md                     # Bu dosya
├── research.md                 # Phase 0 çıktısı
├── data-model.md               # Phase 1 çıktısı
└── tasks.md                    # /speckit.tasks çıktısı
```

---

## Phase 0: Research

### Mevcut Durum Analizi

**bridge.py'de tespit edilen zincir** (satır 1729–1737):
```python
def _switch_persona_for_chat(chat_id, persona_name):
    try:
        from persona_manager import switch_persona
    except Exception:
        from server.persona_manager import switch_persona  # fallback
    result = switch_persona(persona_name)
    ...
```
→ `persona_manager.py` yoksa her iki import da `ModuleNotFoundError` verir → persona switch tamamen çalışmaz.

**detect_switch_from_text** (satır 3625):
```python
switch_target = detect_switch_from_text(text)
```
→ `detect_switch_from_text` da bridge.py içinde başka bir yerden import ediliyor olmalı veya bridge içinde tanımlı. Kontrol gerekiyor.

**state/active_agent.json** — mevcut değil. Oluşturulmalı.

**config/agents.yaml** — şu an sadece `planner`, `repo_analyst`, `developer`, `reviewer`, `debug` var. Persona profilleri eksik.

### Kararlar

| Karar | Seçim | Gerekçe |
|-------|-------|---------|
| Persona state formatı | JSON dosya | Mevcut bridge state pattern'ı ile uyumlu |
| Persona config kaynağı | `config/agents.yaml` personas bölümü | Tek config dosyası prensibi |
| Trigger tespiti | Regex + fuzzy isim eşleşmesi | Türkçe çekim ekleri için gerekli |
| Greeting kaynağı | config'deki `greeting` alanı | Hardcode yok |

---

## Phase 1: Design & Contracts

### Data Model — `state/active_agent.json`

```json
{
  "id": "jarvis",
  "name": "Jarvis",
  "color": "#00d4ff",
  "voice": "AhmetNeural",
  "role": "genel asistan",
  "skills": ["genel", "kod", "arama"],
  "greeting": "Merhaba, Jarvis burada.",
  "activated_at": 1713000000.0
}
```

### Persona Config — `config/agents.yaml` personas bölümü

```yaml
personas:
  seda:
    name: Seda
    role: "kod/debug/PR uzmanı"
    color: "#00ff88"
    voice: AhmetNeural
    skills: [kod, debug, pr, refactor]
    greeting: "Merhaba, Seda burada. Hangi kodla başlıyoruz?"
    triggers: [seda, "sedaya", "seda'ya", "seda ile"]
  mert:
    name: Mert
    role: "araştırma/rakip analizi"
    color: "#ffdd00"
    voice: AhmetNeural
    skills: [arastirma, rakip, pazar, trend]
    greeting: "Mert hazır. Ne araştırıyoruz?"
    triggers: [mert, "merte", "mert'e", "mert ile"]
  buse:
    name: Buse
    role: "pazarlama/landing"
    color: "#ff69b4"
    voice: EmelNeural
    skills: [pazarlama, landing, kopya, sosyal]
    greeting: "Selam! Buse burada. Bugün ne satıyoruz?"
    triggers: [buse, "buseyi", "buse'yi", "buse ile"]
  eren:
    name: Eren
    role: "veri/dashboard"
    color: "#ff8c00"
    voice: AhmetNeural
    skills: [veri, dashboard, grafik, analiz]
    greeting: "Eren bağlandı. Hangi veriyi analiz ediyoruz?"
    triggers: [eren, "erene", "eren'e", "eren ile"]
  luna:
    name: Luna
    role: "güvenlik/audit"
    color: "#9b59b6"
    voice: EmelNeural
    skills: [guvenlik, audit, pentest, log]
    greeting: "Luna aktif. Sistemi tarayalım mı?"
    triggers: [luna, "lunaya", "luna'ya", "luna ile"]
  sabrican:
    name: Sabrican
    role: "deploy/ops"
    color: "#95a5a6"
    voice: AhmetNeural
    skills: [deploy, ops, docker, ci]
    greeting: "Sabrican hazır. Neyi deploy ediyoruz?"
    triggers: [sabrican, "sabricana", "sabrican ile"]
  sabri:
    name: Sabri
    role: "wildcard/yaratıcı"
    color: "#e74c3c"
    voice: AhmetNeural
    skills: [yaratici, fikir, strateji, wildcard]
    greeting: "Sabri burada. Bugün neyi icat ediyoruz?"
    triggers: [sabri, "sabriye", "sabri'ye", "sabri ile"]
```

### Interface Contract — `server/persona_manager.py`

```python
def switch_persona(name: str) -> dict:
    """
    Returns: {"ok": True, "name": "Seda", "greeting": "...", "color": "#00ff88"}
          or {"ok": False, "error": "Persona bulunamadı: xyz"}
    """

def get_active_persona() -> dict:
    """Returns current active_agent.json content. Default: jarvis."""

def detect_switch_from_text(text: str) -> str | None:
    """
    Input: "Seda ile konuş" / "Buse'yi çağır"
    Returns: persona_id ("seda") or None
    """
```

---

## Complexity Tracking

Yok — kapsam tek modül + config değişikliği, constitution gate'leri geçiyor.

---

## Sonraki Adım

`/speckit.tasks` → görev listesi üret → `/speckit.implement`
