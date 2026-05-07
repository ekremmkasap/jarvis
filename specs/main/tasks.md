# Tasks: Persona Switching — "Seda ile Konuş"

**Feature**: Dijital Ajan V2 — PersonaManager  
**Branch**: main | **Date**: 2026-04-13 | **Status**: ✅ TAMAMLANDI

## Phase 1: Setup

- [x] T001 `state/active_agent.json` oluşturuldu — default Jarvis profili

## Phase 2: Foundational

- [x] T002 `config/agents.yaml`'a `personas:` bloğu eklendi — 7 persona tam profil

## Phase 3: US1 — PersonaManager Modülü

- [x] T003 [US1] `server/persona_manager.py` — `load_personas()` ✅
- [x] T004 [US1] `server/persona_manager.py` — `get_active_persona()` ✅
- [x] T005 [US1] `server/persona_manager.py` — `detect_switch_from_text()` ✅
- [x] T006 [US1] `server/persona_manager.py` — `switch_persona()` ✅
- [x] T007 [P] [US1] `server/persona_manager.py` — `list_personas()` ✅

## Phase 4: US2 — Bridge Endpoint

- [x] T008 [US2] `server/bridge.py` — `GET /api/persona/active` eklendi ✅
- [x] T009 [P] [US2] `server/bridge.py` — `/kim-aktif` zaten mevcuttu ✅

## Phase 5: Polish

- [x] T010 Smoke test PASS — switch_persona, detect_switch, get_active, list_personas ✅
- [x] T011 Bridge import test PASS ✅

---

## Sonuç

- "Seda ile konuş" → Telegram'a `"Baglaniyor: Seda... Merhaba, Seda burada. Hangi kodla başlıyoruz?"` gelir
- `GET /api/persona/active` → aktif persona JSON döner (hologram için)
- 7 persona aktif: Seda, Mert, Buse, Eren, Luna, Sabrican, Sabri
