# Feature Specification: Dijital Ajan V3 — 7 Akıllı Persona + Obsidian İkinci Beyin + Alt Ajan Swarm

**Feature Branch**: `004-dijital-ajan-v3-persona-swarm`  
**Created**: 2026-04-13  
**Status**: Draft  

---

## Özet

Jarvis'in 7 dijital ajanı (Seda, Mert, Buse, Eren, Luna, Sabrican, Sabri) artık birer karakter değil — birer **akıllı uzman**. Her ajan kendi kişiliğiyle LLM'den gerçek cevap üretiyor, Obsidian kasasına erişip bilgi okuyor/yazıyor ve kendi uzmanlık alanında alt görevleri yönetiyor. Ekrem "Seda ile konuş" dediğinde gerçekten bir kıdemli yazılım mühendisiyle konuşuyor gibi hissediyor.

---

## User Scenarios & Testing

### User Story 1 — Akıllı Persona Yanıtı (Priority: P1)

Ekrem bir persona çağırır ve o persona'nın uzmanlık alanında soru sorar. Persona gerçek bir uzman gibi kendi sesiyle, kendi bakış açısıyla yanıt verir.

**Why this priority**: Temel vaad. Persona switching çalışıyor ama zeka yok. Bu eklenmeden diğer her şey anlamsız.

**Independent Test**: Seda aktif → "şu Python kodunu incele" → teknik, debug odaklı yanıt. Buse aktif → aynı soru → "bu benim alanım değil, Seda'ya sor" yanıtı.

**Acceptance Scenarios**:

1. **Given** Seda aktif, **When** kod sorusu sorulur, **Then** yanıt teknik ve debug odaklı gelir, Seda'nın kişiliğiyle
2. **Given** Buse aktif, **When** "landing page nasıl olsun?" diye sorulur, **Then** pazarlama diliyle, CTA odaklı yanıt gelir
3. **Given** Persona kendi alanı dışında soru alır, **Then** "bu benim alanım değil, [X persona]'ya sor" der
4. **Given** Persona değiştirilir, **When** yeni mesaj gelir, **Then** yeni persona aktif, önceki konuşma geçmişi korunur

---

### User Story 2 — Obsidian İkinci Beyin (Priority: P2)

Her persona Obsidian kasasındaki kendi klasörüne yazar ve okur. "Bunu kaydet" → Obsidian'a not. "Ne biliyorsun?" → Obsidian notlarını bağlam olarak kullanır.

**Why this priority**: Personaları kalıcı bellekli yapar. Konuşmalar arası bilgi taşınır.

**Independent Test**: Mert aktif → "bunu Obsidian'a kaydet" → `personas/mert/` altında dosya oluşur → yeni oturumda "geçen araştırmamız" → Mert o notu okuyup özetler.

**Acceptance Scenarios**:

1. **Given** Mert aktif ve Obsidian bağlı, **When** "kaydet" komutu, **Then** `personas/mert/` altında başlıklı markdown oluşur
2. **Given** Seda aktif, **When** "bu konuda ne biliyorsun?" sorulur, **Then** Seda kendi Obsidian klasörünü okur, ilgili notları bağlam olarak kullanır
3. **Given** Persona değiştirilir, **Then** yeni persona sadece kendi klasörüne erişir (izolasyon)
4. **Given** "tüm ajanların özetini ver", **Then** Jarvis her persona klasöründen son notu okur, konsolide özet sunar

---

### User Story 3 — Alt Ajan Swarm (Priority: P2)

Her persona karmaşık görevleri alt ajanlara böler. Seda bir repo analizi yaparken "kod oku", "hataları listele", "refactor öner" adımlarını sırayla çalıştırır.

**Why this priority**: Personaların gerçek iş yapmasını sağlar. Tek LLM çağrısı yerine orkestrasyon.

**Independent Test**: Seda'ya "şu repo'yu analiz et" → Seda görevi 3 alt adıma böler → sırayla işler → birleşik rapor sunar.

**Acceptance Scenarios**:

1. **Given** Seda ve 3+ adımlı bir görev, **When** görev verilir, **Then** Seda adımları listeler ve sırayla işler
2. **Given** Mert araştırma görevi alır, **When** "araştır ve özetle", **Then** web search + Obsidian okuma + özetleme sırayla çalışır
3. **Given** Alt görev başarısız olur, **Then** persona "şu adımda sorun çıktı" raporlar, sistem çökmez
4. **Given** Bağımsız alt görevler, **Then** mümkünse paralel çalışır

---

### User Story 4 — Ses + Hologram Kimlik Katmanı (Priority: P3)

Persona değişince TTS sesi değişir, hologram rengi değişir, persona kendini sesli karşılar.

**Why this priority**: Deneyim katmanı. Görsel/işitsel kimlik çalışan sistemin üstüne eklenir.

**Independent Test**: "Buse ile konuş" → hologram pembe (#ff69b4), TTS EmelNeural → "Selam! Buse burada." sesli duyulur.

**Acceptance Scenarios**:

1. **Given** Persona değiştirilir, **Then** hologram 0.6 saniyede yeni renge geçer
2. **Given** Yeni persona aktif, **Then** greeting cümlesi o persona'nın TTS sesiyle okunur
3. **Given** Jarvis → persona geçişi, **Then** "Jarvis'ten [persona]'ya bağlanıyorum" sesli duyulur

---

## Functional Requirements

### FR-1: Persona System Prompt Motoru
- Her persona'nın `config/agents.yaml`'da `system_prompt` alanı olur
- Aktif persona system prompt'u LLM çağrısının başına enjekte edilir
- System prompt: kişilik, uzmanlık, konuşma tonu, alan dışı yönlendirme kuralı
- Model değişmez (Groq/Gemini/Ollama), sadece system prompt eklenir

### FR-2: Persona Hafıza İzolasyonu
- Her persona `state/agent_memory/<persona_id>/` altında ayrı konuşma geçmişi
- Persona değişince aktif hafıza değişir, önceki korunur
- Obsidian: her persona `obsidian/personas/<persona_id>/` klasörüne yazar/okur

### FR-3: Obsidian İkinci Beyin Köprüsü
- "kaydet" / "not al" / "Obsidian'a yaz" → aktif persona klasörüne markdown yazar
- "ne biliyorsun" / "araştırdıklarımız" → persona kendi Obsidian klasörünü bağlam olarak okur
- `OBSIDIAN_VAULT_PATH` env değişkeninden kasanın yolu alınır
- Her not: başlık, tarih, persona_id, içerik

### FR-4: Alt Ajan Orkestrasyon
- `config/agents.yaml`'da her persona için `sub_agents` listesi
- 3+ adım gerektiren görevler otomatik alt ajanlara bölünür
- Alt ajan tipleri: `web_search`, `code_analyzer`, `file_reader`, `obsidian_writer`, `summarizer`
- Sonuçlar persona'ya döner, persona kendi sesiyle özetler

### FR-5: Ses + Hologram Kimlik
- Persona geçişinde `hey_jarvis.py` yeni voice değerini okur
- `apps/desktop-hologram/renderer.js` her 3 saniyede `/api/persona/active` poll eder, color'a göre glow rengini değiştirir
- Geçiş: 0.6 saniye CSS transition

---

## Success Criteria

1. Seda ile Buse'ye aynı soru sorulunca yanıtlar birbirinden açıkça ayrışır (teknik vs pazarlama)
2. "Bunu kaydet" komutundan 5 saniye içinde Obsidian'da dosya oluşur
3. "Ne biliyorsun?" sorusuna yanıt Obsidian notlarından en az 1 referans içerir
4. Karmaşık görevlerin yüzde 90'ında alt ajan zinciri başarıyla tamamlanır
5. Persona değişiminden 2 saniye içinde doğru TTS sesi aktif olur
6. Persona değişiminden 1 saniye içinde hologram yeni renge geçer
7. Persona A'nın söyledikleri Persona B'nin yanıtlarında sızmaz (hafıza izolasyonu)

---

## Key Entities

| Varlık | Açıklama |
|--------|---------|
| `PersonaProfile` | id, name, color, voice, role, skills, system_prompt, sub_agents, obsidian_folder |
| `PersonaMemory` | persona_id, messages[], last_active |
| `ObsidianNote` | persona_id, title, content, created_at, tags |
| `SubAgentTask` | id, type, payload, status, result, created_by_persona |
| `ActivePersonaState` | id, name, color, voice, activated_at |

---

## Assumptions

1. Obsidian kasası `OBSIDIAN_VAULT_PATH` env'den alınır (Windows path)
2. TTS: edge-tts veya Piper; voice değişimi runtime'da mümkün
3. Alt ajan sistemi şimdilik aynı process içinde sıralı çalışır
4. Obsidian API yok — doğrudan dosya sistemi (Obsidian markdown takip eder)
5. LLM model değişmez, sadece system prompt eklenir

---

## Scope Dışı

- Personalar arası gerçek anlık mesajlaşma
- Codex slot binding (Faz 4 — ayrı feature)
- Web UI persona chat ekranı (ayrı feature)
- Obsidian graph view entegrasyonu

---

## Dependencies

- `server/persona_manager.py` ✅ mevcut
- `state/active_agent.json` ✅ mevcut
- `config/agents.yaml` personas bloğu ✅ mevcut
- `server/bridge.py` `/api/persona/active` ✅ mevcut
- `OBSIDIAN_VAULT_PATH` — `.env`'e eklenmeli
- `hey_jarvis.py` — voice override hook gerekiyor
- `apps/desktop-hologram/renderer.js` — persona color polling gerekiyor
