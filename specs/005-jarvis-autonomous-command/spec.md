# Feature Specification: MARK-XXXXVI — Jarvis Autonomous Command Layer

**Feature Branch**: `005-jarvis-autonomous-command`  
**Created**: 2026-04-14  
**Status**: Draft

---

## Özet

Jarvis artık sadece sohbet eden bir asistan değil — eylem yapan bir komuta merkezi. Ekrem telefonda sesli mesaj atar, Jarvis duyar, PC'de çalıştırır, sonucu sesli geri söyler. Telegram'dan tam yetki kontrol: uygulama aç, dosya gönder, ekran görüntüsü al, AWS'yi yönet. Mesajın içeriğine göre doğru ajan otomatik seçilir. Her konuşma ve eylem Obsidian'a ve wiki'ye yazılır. Jarvis'in belleği kalıcı, komutları güçlü, kontrolü tam.

---

## User Scenarios & Testing

### User Story 1 — Telegram'dan Sesli Komut (Priority: P1)

Ekrem yatakta, telefonu açıp Jarvis Telegram botuna sesli mesaj gönderir: *"Mert, eBay'de iPhone 15 Pro fiyatlarına bak."* Jarvis sesi metne çevirir, Mert'i aktif eder, araştırmayı yapar ve sonucu sesli olarak Telegram'dan geri gönderir.

**Why this priority**: En yüksek "wow" etkisi. Bilgisayar başında olmadan Jarvis'i komuta etmek temel kullanım senaryosu.

**Independent Test**: Telegram botuna sesli mesaj gönder → STT çalışsın → yanıt sesli gelsin. Araştırma yanlış da olsa ses akışı tamamlanmış olmalı.

**Acceptance Scenarios**:

1. **Given** Telegram bota sesli mesaj gönderildi, **When** bot mesajı aldı, **Then** 15 saniye içinde sesli yanıt mesajı geri gelir
2. **Given** Sesli mesaj Türkçe, **When** STT çalışır, **Then** metin doğru anlaşılır (yaygın kelimeler için %85+ doğruluk)
3. **Given** Yanıt üretildi, **When** TTS dönüşümü yapıldı, **Then** Telegram'da dinlenebilir ses mesajı olarak iletilir
4. **Given** STT başarısız, **When** ses anlaşılamadı, **Then** kullanıcıya "Anlamadım, yazarak tekrar eder misin?" metin mesajı gider

---

### User Story 2 — Telegram'dan PC Kontrol (Priority: P1)

Ekrem dışarıda, Telegram'dan yazar: `/ekran-goruntusu` → Jarvis masaüstünün ekran görüntüsünü alır ve Telegram'a gönderir. `/pc-durum` → CPU/RAM/disk bilgisi gelir. `/ac chrome` → Chrome açılır.

**Why this priority**: Uzaktan PC yönetimi günlük operasyonel ihtiyaç. AWS, Codex, Jarvis süreçleri uzaktan izlenebilmeli.

**Independent Test**: `/pc-durum` komutu gönder → CPU/RAM içeren mesaj dön. Başka hiçbir şey çalışmıyor olsa bile bu bağımsız test edilebilir.

**Acceptance Scenarios**:

1. **Given** `/pc-durum` yazıldı, **When** komut işlendi, **Then** CPU yüzdesi, RAM kullanımı, disk alanı içeren mesaj döner
2. **Given** `/ekran-goruntusu` yazıldı, **When** komut işlendi, **Then** anlık masaüstü görüntüsü Telegram'a iletilir
3. **Given** Whitelist dışı komut denendi, **When** komut algılandı, **Then** "Bu komuta izin verilmiyor" mesajı döner, eylem gerçekleşmez
4. **Given** `/ac chrome` yazıldı, **When** Chrome whitelist'teyse, **Then** Chrome açılır ve onay mesajı gelir
5. **Given** `/jarvis-baslat` yazıldı, **When** Jarvis kapalıysa, **Then** sistem ayağa kalkar, "Jarvis başlatıldı" bildirimi gelir
6. **Given** `/dosya-gonder <path>` yazıldı, **When** dosya whitelist klasöründeyse, **Then** dosya Telegram'a iletilir

---

### User Story 3 — Intent Tabanlı Otomatik Ajan Seçimi (Priority: P2)

Ekrem "eBay'de laptop fiyatlarına bak" yazar. Jarvis Mert'i seçer. "şu Python kodunu incele" → Seda seçilir. "Instagram için post yaz" → Buse seçilir. Ekrem persona adı söylemek zorunda değil.

**Why this priority**: Jarvis'i gerçekten akıllı yapan katman. Elle persona seçme zahmetini kaldırır.

**Independent Test**: "araştır ve özetle" mesajı gönder → Mert aktif olsun. "kod analiz et" → Seda aktif. Her senaryo bağımsız test edilebilir.

**Acceptance Scenarios**:

1. **Given** "eBay fiyat araştır" mesajı, **When** intent analiz edildi, **Then** Mert aktif olur
2. **Given** "kodu incele" mesajı, **When** intent analiz edildi, **Then** Seda aktif olur
3. **Given** "Instagram post yaz" mesajı, **When** intent analiz edildi, **Then** Buse aktif olur
4. **Given** "EC2 listele" mesajı, **When** intent analiz edildi, **Then** Sabrican aktif olur
5. **Given** Intent belirsiz, **When** eşleşme güven skoru düşük, **Then** mevcut aktif persona devam eder, Ekrem bilgilendirilir
6. **Given** Auto-switch gerçekleşti, **Then** Ekrem'e "Mert'e geçiyorum — araştırma modu" bildirimi gelir

---

### User Story 4 — Obsidian + Wiki Kalıcı Bellek (Priority: P2)

Her önemli konuşma, eylem ve araştırma sonucu Obsidian'a ve wiki'ye otomatik yazılır. "geçen hafta ne araştırdık?" → Jarvis Obsidian'dan çeker. "bu konuyu wiki'ye ekle" → wiki sayfası oluşur.

**Why this priority**: Bellek olmadan Jarvis her oturumda sıfırdan başlar. Kalıcı hafıza Jarvis'i gerçek asistana dönüştürür.

**Independent Test**: Bir araştırma yap → Obsidian vault'ta `personas/mert/` altında dosya oluşsun. Bağımsız kontrol edilebilir.

**Acceptance Scenarios**:

1. **Given** Mert araştırma tamamladı, **When** sonuç üretildi, **Then** 5 saniye içinde `personas/mert/` altında başlıklı markdown oluşur
2. **Given** "bu konuyu wiki'ye ekle" komutu, **When** işlendi, **Then** `wiki/` altında ilgili sayfa oluşur, `wiki/index.md` güncellenir
3. **Given** "geçen araştırmamız neydi?", **When** Obsidian'da ilgili not var, **Then** yanıt o nottan en az bir referans içerir
4. **Given** PC kontrol eylemi gerçekleşti, **When** tamamlandı, **Then** eylem logu `personas/sabrican/actions/` altına yazılır
5. **Given** `wiki/hot.md` güncellemesi, **When** yeni araştırma eklendi, **Then** hot.md son bilgiyle güncellenir
6. **Given** Obsidian vault yolu ayarlı değil, **When** yazma denendi, **Then** kullanıcıya net hata mesajı gelir, sistem çökmez

---

### User Story 5 — Codex Slot Otomatik Dispatch (Priority: P3)

Aktif persona'ya göre Codex slot'u otomatik seçilir. Seda aktifken `/codex-dispatch` → forge slot'una gider. Sabrican aktifken → nexus slot'una. Ekrem slot adı söylemek zorunda değil.

**Why this priority**: Mevcut Codex altyapısını daha akıllı yapar. Operasyonel sürtünmeyi azaltır.

**Independent Test**: Seda aktifken `/codex-dispatch görev` gönder → forge slot'una iş düşsün, nexus'a değil.

**Acceptance Scenarios**:

1. **Given** Seda aktif, `/codex-dispatch "kodu refactor et"`, **Then** forge slot'una iş gider
2. **Given** Sabrican aktif, `/codex-dispatch "EC2 başlat"`, **Then** nexus slot'una iş gider
3. **Given** Slot meşgul, **When** dispatch denendi, **Then** "forge meşgul, sıraya alındı" mesajı gelir
4. **Given** `/codex-durum` yazıldı, **Then** 7 persona + slot eşleşmesi + her slotun durumu döner

---

### User Story 6 — Agent Hafıza Paneli (Priority: P3)

Telegram'dan `/hafiza seda` → Seda'nın son 5 konuşması. `/ajanlarin-ozeti` → tüm 7 ajanın son notu. Web UI'da yan panel aktif persona ve son mesajları canlı gösterir.

**Why this priority**: Operasyonel görünürlük. Jarvis'in ne bildiğini, ne yaptığını görmek güven verir.

**Independent Test**: `/hafiza jarvis` yaz → en az 1 mesaj içeren liste dönsün.

**Acceptance Scenarios**:

1. **Given** `/hafiza seda` yazıldı, **When** Seda'nın geçmişi var, **Then** son 5 mesaj numaralı liste olarak gelir
2. **Given** `/ajanlarin-ozeti` yazıldı, **Then** 7 ajan için son not tarihi veya "henüz not yok" döner
3. **Given** Web UI açık, **When** persona değişti, **Then** yan panel 3 saniye içinde güncellenir

---

### Edge Cases

- Telegram sesli mesaj 60 saniyeyi aşarsa? → Reddet, "Lütfen 60 saniye altında sesli mesaj gönder"
- PC kontrol komutu Jarvis süreci çöküyorsa ne olur? → Watchdog tekrar başlatır, Telegram'a bildirim gider
- Obsidian vault tam disk doluysa? → Yazım fail, kullanıcı bildirilir, sistem çökmez
- Intent confidence 0.7 altındaysa? → Mevcut persona devam eder, Ekrem'e "hangi persona?" sorusu sorulur
- Codex slot'larının tümü meşgulse? → Kuyruk sistemi, kullanıcı tahmini bekleme süresiyle bildirilir

---

## Requirements

### Functional Requirements

- **FR-001**: Sistem Telegram sesli mesajları (.ogg) alıp metne çevirip işleyebilmeli
- **FR-002**: Sistem her yanıt için sesli (.ogg) Telegram mesajı üretebilmeli
- **FR-003**: PC kontrol komutları yalnızca önceden tanımlı whitelist üzerinden çalıştırılabilmeli
- **FR-004**: Tüm PC eylemleri tarih-komut-sonuç triadıyla audit log'a düşmeli
- **FR-005**: Sistem gelen mesajdan intent ve persona çıkarımı yapabilmeli
- **FR-006**: Intent güven skoru eşiğin altındaysa mevcut persona korunmalı
- **FR-007**: Araştırma ve eylem sonuçları aktif persona'nın Obsidian klasörüne otomatik yazılmalı
- **FR-008**: "wiki'ye ekle" intent'i `wiki/` altında sayfa oluşturmalı, `wiki/index.md` ve `wiki/log.md` güncellenmeli
- **FR-009**: `/codex-dispatch` aktif persona'nın slot'una otomatik yönlendirilmeli
- **FR-010**: `/hafiza <persona>` son N konuşmayı Telegram'a iletmeli
- **FR-011**: Web UI yan paneli aktif persona bilgilerini gerçek zamanlı göstermeli

### Key Entities

- **VoiceMessage**: telegram_file_id, duration_seconds, transcription, processed_at
- **PCCommand**: command_key, args, whitelist_approved, result, executed_at, persona_id
- **IntentResult**: raw_message, detected_intent, target_persona, confidence_score, ts
- **ObsidianEntry**: persona_id, vault_folder, title, content_md, created_at, source_type
- **WikiPage**: file_path, title, content_md, updated_at, linked_personas
- **CodexDispatch**: persona_id, resolved_slot, task_description, status, queued_at
- **AgentMemorySnapshot**: persona_id, recent_messages, last_active, obsidian_note_count

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Sesli Telegram mesajından sesli yanıta toplam süre 15 saniyenin altında
- **SC-002**: Türkçe STT doğruluğu günlük kullanım cümlelerinde %85 ve üzeri
- **SC-003**: Intent classifier doğru persona seçimi %80 ve üzeri
- **SC-004**: Whitelist dışı hiçbir PC eylemi gerçekleşmiyor — sıfır tolerans
- **SC-005**: "kaydet" komutundan 5 saniye içinde Obsidian'da dosya oluşuyor
- **SC-006**: Wiki entegrasyonu mevcut `wiki/index.md` yapısını bozmadan çalışıyor
- **SC-007**: `/hafiza` komutu 3 saniye içinde yanıt veriyor
- **SC-008**: Codex dispatch aktif persona slot'una %100 doğrulukla gidiyor
- **SC-009**: Tüm PC eylemleri audit log'a düşüyor, sıfır kayıp

---

## Assumptions

- Groq Whisper API Türkçe ses tanıma için yeterli — ücretsiz tier kota sınırı günlük 100 dakika
- Telegram bot token mevcut ve webhook aktif — `.env`'de `TELEGRAM_BOT_TOKEN` tanımlı
- PC kontrol yalnızca Jarvis'in çalıştığı makinede geçerli (uzak makine scope dışı)
- Obsidian vault Windows'ta erişilebilir — `OBSIDIAN_VAULT_PATH` `.env`'de tanımlı
- Wiki yapısı `wiki/index.md`, `wiki/log.md`, `wiki/hot.md` üçlüsünü kullanıyor (mevcut)
- Web UI real-time güncellemesi polling (3sn) ile yapılır, WebSocket scope dışı
- Codex slot bağlamaları `config/agents.yaml`'a `codex_slot` alanı eklenerek yapılır
- PC whitelist başlangıç: Chrome, VS Code, Notepad, ekran görüntüsü, sistem durumu, Jarvis start/stop, dosya gönderme

---

## Scope Dışı

- Mobil uygulama (Telegram yeterli)
- Çoklu kullanıcı / multi-tenant (tek kullanıcı: Ekrem)
- Gerçek zamanlı ses akışı (push-to-talk) — voice note yeterli
- Uzak makine kontrolü (sadece local PC)
- Obsidian graph view veya plugin entegrasyonu
- Wiki dışında ek dokümantasyon sistemi

---

## Dependencies

| Bağımlılık | Durum | Not |
|-----------|-------|-----|
| `server/bridge.py` | ✅ Mevcut | APPEND-ONLY |
| `server/persona_manager.py` | ✅ Mevcut | |
| `config/agents.yaml` personas | ✅ Mevcut | `codex_slot` alanı eklenecek |
| `OBSIDIAN_VAULT_PATH` env | ⚠️ Kontrol gerekli | `.env.example`'e eklenmeli |
| `TELEGRAM_BOT_TOKEN` env | ✅ Mevcut | `.env`'de kayıtlı |
| Groq API key | ✅ Mevcut | Whisper için kullanılacak |
| `wiki/` dizin yapısı | ✅ Mevcut | `index.md`, `log.md`, `hot.md` |
| `codex_orchestrator.py` | ✅ Mevcut | Slot dispatch için |
