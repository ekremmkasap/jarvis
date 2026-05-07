# Tasks: Dijital Ajan V3 — 7 Akıllı Persona + Obsidian + Swarm

**Input**: `specs/004-dijital-ajan-v3-persona-swarm/`
**Branch**: `004-dijital-ajan-v3-persona-swarm`
**Prerequisites**: plan.md ✅ spec.md ✅ data-model.md ✅ research.md ✅ contracts/ ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralel çalışabilir (farklı dosya, bağımlılık yok)
- **[Story]**: US1=Akıllı Persona Yanıtı, US2=Obsidian İkinci Beyin, US3=Alt Ajan Swarm, US4=Ses+Hologram

---

## Phase 1: Setup

**Amaç**: Gerekli ortam değişkenleri, boş modüller, config dosyaları

- [ ] T001 `.env.example` dosyasına `OBSIDIAN_VAULT_PATH=C:/Users/sergen/Documents/ObsidianVault` satırını ekle
- [ ] T002 [P] `server/skills/persona_obsidian_skill.py` dosyasını boş modül olarak oluştur — stub fonksiyonlar: `write_persona_note(persona_id, title, content)`, `read_persona_notes(persona_id, limit)`, `get_persona_context(persona_id)`
- [ ] T003 [P] `server/skills/sub_agent_runner.py` dosyasını boş modül olarak oluştur — stub: `run_sub_agents(persona_id, task, agent_types)`, `_run_web_search(payload)`, `_run_code_analyzer(payload)`, `_run_file_reader(payload)`, `_run_obsidian_writer(payload)`, `_run_summarizer(payload)`

---

## Phase 2: Foundational

**Amaç**: Tüm US'lerden önce tamamlanmalı — system prompt injection + memory isolation

**⚠️ KRITIK**: Bu faz tamamlanmadan US1-US4 başlanamaz.

- [ ] T004 `server/bridge.py` içinde aktif persona system_prompt injection'ı doğrula — `bridge.py:1487` satırını oku; LLM çağrısından önce `get_active_persona()["system_prompt"]` enjekte ediliyorsa ✅, yoksa `_sync_persona_session_for_chat()` çağrısından sonra inject et (APPEND-ONLY, mevcut çağrıları kırma)
- [ ] T005 [P] `server/persona_manager.py` içinde `get_active_persona()` dönüşünün `system_prompt`, `sub_agents`, `obsidian_folder` alanlarını içerdiğini doğrula — `config/agents.yaml` okuyup bu alanları döndürüyorsa ✅, yoksa `_load_agent_config()` return dict'ine ekle
- [ ] T006 [P] `state/agent_memory/` altında persona bazlı dizin yapısının var olduğunu doğrula — `server/persona_memory.py` var ve `state/agent_memory/<persona_id>/` şemasını kullanıyorsa ✅, yoksa `get_memory_path(persona_id)` fonksiyonunu ekle
- [ ] T007 `tests/test_persona_foundation.py` oluştur — `get_active_persona()` test: seda aktifken `system_prompt` boş değil; persona değişince `agent_memory` yolu değişiyor; injection testi: `_sync_persona_session_for_chat()` sonrası ACTIVE_AGENTS dict'inde `system_prompt` var

**Checkpoint**: Foundation ready — US1-US4 paralel başlayabilir.

---

## Phase 3: US1 — Akıllı Persona Yanıtı (Priority: P1) 🎯 MVP

**Hedef**: Her persona kendi uzmanlık alanında farklı ton ve içerikle yanıt üretir; alan dışı sorular yönlendirilir.

**Bağımsız Test**: Seda aktif → "şu Python kodunu incele" → teknik yanıt. Buse aktif → aynı soru → "bu benim alanım değil, Seda'ya sor".

- [ ] T008 [US1] `config/agents.yaml` her persona için `system_prompt` alanını doğrula — tüm 7 persona (`seda`, `mert`, `buse`, `sabri`, `eren`, `luna`, `sabrican`) için `system_prompt` dolu mu kontrol et; eksik varsa spec `domain_limits.fallback_persona` + `tone_guide` kullanarak ekle
- [ ] T009 [P] [US1] `server/bridge.py` persona handoff reply formatını güncelle — `/api/chat` yanıtı veya Telegram reply başında `"Bağlanıyor: {name}... {greeting}"` formatını `_switch_persona_for_chat()` return'ine ekle (contract: `persona-commands.md#1`)
- [ ] T010 [P] [US1] `server/bridge.py` alan dışı yönlendirme — persona system_prompt'una `domain_limits.restricted_topics` ve `fallback_persona` enjekte edildiğini doğrula; yoksa system_prompt'un sonuna `"Eğer soru {restricted_topics} dışındaysa '{fallback_persona}'ya yönlendir."` cümlesi ekle
- [ ] T011 [US1] `GET /api/persona/active` endpoint'ini doğrula — `bridge.py` içinde bu endpoint'in `id`, `name`, `color`, `voice`, `role`, `skills`, `greeting`, `activated_at` alanlarını döndürdüğünü kontrol et (contract: `persona-api.md#1`); eksik alan varsa `_get_active_persona_payload()` return dict'ine ekle
- [ ] T012 [US1] `tests/test_persona_us1.py` oluştur — `switch_persona("seda")` → `get_active_persona()["system_prompt"]` teknik içerik doğrulama; `switch_persona("buse")` → farklı persona, farklı system_prompt; `GET /api/persona/active` response schema doğrulama

---

## Phase 4: US2 — Obsidian İkinci Beyin (Priority: P2)

**Hedef**: Persona "kaydet" aldığında kendi Obsidian klasörüne yazar; "ne biliyorsun?" aldığında kendi notlarından bağlam üretir.

**Bağımsız Test**: Mert aktif → "bunu kaydet: araştırma notu" → `{VAULT}/personas/mert/YYYY-MM-DD-arastirma-notu.md` oluşur → yeni sorguda "ne biliyorsun?" → yanıt o notu referans alır.

- [ ] T013 [US2] `server/skills/persona_obsidian_skill.py` içinde `write_persona_note(persona_id, title, content)` gerçek implementasyonu — `os.environ["OBSIDIAN_VAULT_PATH"]` + `personas/{persona_id}/` path; `{YYYY-MM-DD}-{slug}.md` dosya adı; frontmatter: `persona_id`, `created_at`, `tags`; path traversal koruması: title içinde `..` veya `/` ignore edilir
- [ ] T014 [P] [US2] `server/skills/persona_obsidian_skill.py` içinde `read_persona_notes(persona_id, limit=5)` implementasyonu — persona klasöründeki `.md` dosyalarını son değiştirilme tarihine göre sıralar, en yeni `limit` adet döner: `[{title, content, date}]`; vault yoksa boş liste
- [ ] T015 [P] [US2] `server/skills/persona_obsidian_skill.py` içinde `get_persona_context(persona_id)` implementasyonu — `read_persona_notes()` çağırır, sonuçları `"[Not: {title} ({date})]\n{content[:300]}"` formatında birleştirir; boş ise `""` döner
- [ ] T016 [US2] `server/bridge.py` içinde Obsidian intent hook'larını APPEND-ONLY ekle — Telegram/chat mesajında `"kaydet"` / `"not al"` / `"obsidian'a yaz"` pattern tespiti → `write_persona_note(active_persona_id, ...)` çağrısı; `"ne biliyorsun"` / `"araştırdıklarımız"` / `"geçen notlarım"` → `get_persona_context()` sonucunu LLM bağlamına ekle (contract: `persona-commands.md#2` ve `#3`)
- [ ] T017 [P] [US2] `server/bridge.py` içinde fleet summary komutu ekle — `/ajanlarin-ozeti` Telegram komutu → her persona için `read_persona_notes(persona_id, limit=1)` → konsolide özet; note yoksa `"{name}: henüz not yok"` (contract: `persona-commands.md#5`)
- [ ] T018 [US2] `tests/test_persona_obsidian.py` oluştur — `write_persona_note("mert", "test", "içerik")` → dosya var; path traversal `../evil` → ignore; `read_persona_notes("mert")` → list döner; vault yokken empty list

---

## Phase 5: US3 — Alt Ajan Swarm (Priority: P2)

**Hedef**: 3+ adımlı görevler otomatik adımlara bölünür, sıralı (bağımsızsa paralel) çalışır, tek persona yanıtı olarak döner.

**Bağımsız Test**: Seda aktif → "şu repoyu analiz et, hataları listele, refactor öner" → 3 adım çalışır → birleşik rapor.

- [ ] T019 [US3] `server/skills/sub_agent_runner.py` içinde complexity_detector implementasyonu — `is_multi_step(message)` fonksiyonu: `["adım adım", "önce...sonra", "analiz et ve", "oku.*listele", "araştır ve", "dosyaları.*hata"]` regex pattern'leri; True/False döner
- [ ] T020 [P] [US3] `server/skills/sub_agent_runner.py` içinde `_run_web_search(payload)` implementasyonu — `payload["query"]` ile `server/skills/mert_skill.py` içindeki `web_search_deep()` veya Groq search çağrısı; sonuç string döner
- [ ] T021 [P] [US3] `server/skills/sub_agent_runner.py` içinde `_run_code_analyzer(payload)` implementasyonu — `payload["path"]` dosyasını okur, LLM'e `"Kod analizi yap:"` prefix ile gönderir; sonuç string döner; dosya yoksa graceful fail
- [ ] T022 [P] [US3] `server/skills/sub_agent_runner.py` içinde `_run_file_reader(payload)` implementasyonu — `payload["path"]` dosyasını okur, içeriği döner; max 2000 karakter truncate
- [ ] T023 [P] [US3] `server/skills/sub_agent_runner.py` içinde `_run_obsidian_writer(payload)` implementasyonu — `persona_obsidian_skill.write_persona_note()` çağrısı; başarı/fail mesajı döner
- [ ] T024 [P] [US3] `server/skills/sub_agent_runner.py` içinde `_run_summarizer(payload)` implementasyonu — `payload["text"]` LLM'e `"Özetle:"` prefix ile gönderir; Groq llama-3.3-70b kullan (openai SDK)
- [ ] T025 [US3] `server/skills/sub_agent_runner.py` içinde `run_sub_agents(persona_id, task, agent_types)` orkestrasyon implementasyonu — görevi adımlara böler (her `agent_type` bir adım); sıralı çalışır; her adım fail olursa `"[{type}] adımda sorun çıktı: {err}"` eklenir; tüm sonuçlar birleştirilir; sistem çökmez
- [ ] T026 [US3] `server/bridge.py` içinde swarm intent hook'unu APPEND-ONLY ekle — `is_multi_step(message)` True ise `run_sub_agents(active_persona_id, message, persona["sub_agents"])` çağrısı; sonucu LLM yanıtına prefix olarak ekle (contract: `persona-commands.md#4`)
- [ ] T027 [US3] `tests/test_sub_agent_runner.py` oluştur — `is_multi_step("analiz et ve özetle")` True; `is_multi_step("merhaba")` False; `_run_file_reader({"path": "nonexistent"})` graceful fail; `run_sub_agents()` bir adım fail → diğerleri çalışmaya devam

---

## Phase 6: US4 — Ses + Hologram Kimlik Katmanı (Priority: P3)

**Hedef**: Persona değişince TTS sesi değişir, hologram rengi geçiş yapar, persona sesli karşılar.

**Bağımsız Test**: "Buse ile konuş" → hologram `#ff69b4`, TTS EmelNeural, "Selam! Buse burada." sesli duyulur.

- [ ] T028 [US4] `hey_jarvis.py` içinde `_current_voice_name()` fonksiyonunu doğrula — `hey_jarvis.py:227` satırını oku; `get_active_persona()["voice"]` → edge-tts'e `tr-TR-{voice}` formatında geçiliyor mu; geçiliyorsa ✅; değilse `_current_voice_name()` içinde `persona.get("voice", "AhmetNeural")` fix et
- [ ] T029 [P] [US4] `hey_jarvis.py` içinde persona greeting TTS hook ekle — `switch_persona()` çağrısından sonra (veya `_apply_persona_to_chat()` sonrası) `persona["greeting"]` TTS ile bir kez oynat; tekrar tetiklenmeyi önlemek için `_last_greeted_persona` module-level variable kullan; spam koruması: aynı persona → greeting yok
- [ ] T030 [P] [US4] `apps/desktop-hologram/renderer.js` içinde renk geçişini doğrula — `/api/persona/active` polling sonucu `color` field'ı CSS glow variable'a uygulanıyor mu; `#00ff88` → `--glow-color: #00ff88` şeklinde CSS variable set ediliyorsa ✅; yoksa polling callback'ine `document.documentElement.style.setProperty('--glow-color', data.color)` ekle
- [ ] T031 [P] [US4] `apps/desktop-hologram/renderer.js` CSS transition doğrula — `.hologram-container` veya glow elementinde `transition: all 0.6s ease` var mı; yoksa CSS'e ekle
- [ ] T032 [US4] Manuel smoke test talimatı — `tests/smoke_persona_voice.md` oluştur: "Buse aktif yap → hologram rengi #ff69b4 olmalı → TTS EmelNeural sesi duyulmalı → Seda aktif yap → hologram #00ff88 → TTS AhmetNeural"

---

## Phase 7: Polish

**Amaç**: Cross-cutting concerns, hata mesajları, final doğrulama

- [ ] T033 [P] `OBSIDIAN_VAULT_PATH` env yokken tüm Obsidian fonksiyonlarının graceful fail verdiğini doğrula — `write_persona_note()`, `read_persona_notes()`, `get_persona_context()` içine `if not os.environ.get("OBSIDIAN_VAULT_PATH"): return None / []` guard ekle; kullanıcıya "OBSIDIAN_VAULT_PATH ayarlı değil" mesajı
- [ ] T034 [P] Luna `lab_only` hard-reject doğrulama — `server/bridge.py` içinde `/luna-tara`, `/luna-kapsam`, `/luna-analiz` komutları Luna persona dışından çağrıldığında `"Bu komut sadece Luna aktifken kullanılabilir"` döner; `config/agents.yaml` Luna `domain_limits.lab_only: true` set
- [ ] T035 [P] `config/agents.yaml` eksik persona alanları — her 7 persona için `greeting`, `triggers`, `handoff_targets`, `domain_limits.fallback_persona` alanlarını kontrol et; eksik varsa spec `data-model.md` şemasından doldur
- [ ] T036 Final smoke test — `python -m pytest tests/test_persona_foundation.py tests/test_persona_us1.py tests/test_persona_obsidian.py tests/test_sub_agent_runner.py -q` çalıştır; tüm testler pass

---

## Dependencies

```
Phase 1 (Setup)
  └─► Phase 2 (Foundation) — T004-T007
        ├─► Phase 3 (US1) — T008-T012   [MVP]
        ├─► Phase 4 (US2) — T013-T018   [Phase 3 sonrası veya paralel]
        ├─► Phase 5 (US3) — T019-T027   [Phase 3 sonrası veya paralel]
        └─► Phase 6 (US4) — T028-T032   [bağımsız, paralel başlayabilir]
              └─► Phase 7 (Polish) — T033-T036
```

US2, US3, US4 birbirinden bağımsız — Phase 2 bitince paralel çalışabilir.

## Paralel Çalışma

Phase 2 sonrası aynı anda çalışabilecekler:
- T008-T012 (US1) + T013-T015 (US2 stub) + T028-T031 (US4 doğrulama)

Phase 3 sonrası:
- T013-T018 (US2) + T019-T027 (US3) birlikte

## Implementation Strategy (MVP First)

| Faz | Teslim | Değer |
|-----|--------|-------|
| Phase 1-3 | T001-T012 | MVP: Personalar gerçek uzman yanıtı üretiyor, handoff çalışıyor |
| + Phase 4 | T013-T018 | Obsidian bellek: "kaydet" / "ne biliyorsun?" çalışıyor |
| + Phase 5 | T019-T027 | Swarm: karmaşık görevler alt ajanlara bölünüyor |
| + Phase 6-7 | T028-T036 | Ses + hologram kimlik + polish |

**Önerilen MVP**: Phase 1 + Phase 2 + Phase 3 (T001-T012) — 12 task, çalışan akıllı persona sistemi.
