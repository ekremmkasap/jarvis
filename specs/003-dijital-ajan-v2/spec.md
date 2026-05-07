# Feature Specification: Dijital Ajan Dünyası V2 — PersonaManager

**Feature Branch**: `003-dijital-ajan-v2`  
**Created**: 2026-04-13  
**Status**: Draft  
**Priority**: Çok Yüksek

---

## Özet

Jarvis'e 7 lazy persona (Seda, Mert, Buse, Eren, Luna, Sabrican, Sabri) eklenir. "Buse ile konuş" komutuyla aktif persona değişir: hologram rengi değişir, kişiye özel sesli selamlama gelir, mesajlar o kişinin kimliğiyle yanıtlanır. Personalar lazy — yalnızca aktif edilince devreye girer, arka planda çalışan process yoktur.

---

## User Scenarios & Testing

### User Story 1 — Persona Değiştirme: Sesli + Telegram (Priority: P1)

Ekrem "Buse ile konuş" veya "Buseyi çağır" dediğinde Jarvis aktif personayı Buse'ye çevirir, Buse'nin sesiyle "Bağlanıyor: Buse..." selamlama yapar ve Telegram'a da bildirir.

**Independent Test**: bridge.py + state/active_agent.json + hey_jarvis.py TTS ayakta iken "Buse ile konuş" komutu işlenip ses çıktısı alınabilir.

**Acceptance Scenarios**:

1. **Given** Jarvis çalışıyor, **When** "Buse ile konuş" komutu gelir (Telegram veya ses), **Then** `state/active_agent.json` `"buse"` olur, EmelNeural TTS ile "Baglaniyor: Buse" duyulur.
2. **Given** aktif persona Buse, **When** "kim aktif?" sorusu gelir, **Then** "Şu an Buse aktif — Pazarlama & Landing" yanıtı döner.
3. **Given** bilinmeyen bir isim söylenir ("Arif ile konuş"), **When** komut işlenir, **Then** "Bu isimde bir ajan tanımlamadım, mevcut ajanlar: Seda, Mert, Buse..." yanıtı döner.
4. **Given** herhangi bir persona aktifken, **When** Telegram'dan mesaj gelir, **Then** yanıt o personanın adı ve kimliğiyle başlar ("Buse: ...").

---

### User Story 2 — Hologram Renk Geçişi (Priority: P2)

Persona değiştiğinde hologram glow rengi ve animasyon o personanın rengine geçer (fade animasyonuyla).

**Independent Test**: Electron uygulaması çalışırken `/api/persona/active` endpoint'i farklı persona döndürdüğünde hologram DOM'da yeni renk sınıfını alır.

**Acceptance Scenarios**:

1. **Given** hologram açık ve Jarvis aktif, **When** "Seda ile konuş" komutu gelir, **Then** hologram 1 saniye içinde `#00ff88` (Seda yeşili) renkte parlar.
2. **Given** "Luna aktif" iken, **Then** hologram `#9b59b6` mor tondadır.
3. **Given** persona değişimi sırasında, **Then** fade geçiş animasyonu 600ms sürer, ani kesme olmaz.

---

### User Story 3 — Per-Persona Skill Routing (Priority: P2)

Her persona, kendine atanmış skill seti ve sistem promptuyla çalışır. Buse'ye "landing page yaz" denmesi, Seda'ya aynı komutu vermekten farklı bir yanıt üretir.

**Independent Test**: bridge.py çalışırken `/agent` endpoint'i `{"agent":"buse","task":"landing yazalım"}` alıp Buse kimliğiyle yanıt dönebilir.

**Acceptance Scenarios**:

1. **Given** Buse aktif, **When** "Instagram içeriği hazırla" komutu gelir, **Then** Buse'nin pazarlama sistem promptuyla yanıt döner.
2. **Given** Seda aktif, **When** "şu kodu incele" gelir, **Then** Seda'nın code-review sistem promptuyla yanıt döner.
3. **Given** aktif persona değişti, **When** yeni komut gelir, **Then** önceki personanın sistem promptu kullanılmaz.

---

### User Story 4 — Persona Hafızası (Priority: P3)

Her personanın `state/agent_memory/<persona>/` altında kalıcı hafızası vardır. "Buse geçen hafta ne önermişti?" sorusuna Buse'nin kendi hafızasından yanıt alınır.

**Independent Test**: `remember("Buse", "Landing A/B test sonucu: kırmızı buton %12 daha iyi")` çağrısı sonrası `recall("Buse", "landing")` bu kaydı döner.

**Acceptance Scenarios**:

1. **Given** Buse bir öneri yapar, **When** hafıza kaydedilir, **Then** sonraki konuşmada "geçen konuşmanda şunu söylemiştin..." bağlamı sağlanır.
2. **Given** Seda'nın hafıza dizini boş, **When** recall çağrılır, **Then** [] döner, hata fırlatmaz.

---

### Edge Cases

- İki persona aynı anda aktif edilmeye çalışılırsa? → İkinci aktif olur, birinci pasife geçer; "Seda kapandı, Buse bağlandı" mesajı.
- Hologram kapalıyken persona değişirse? → state güncellenir, hologram açıldığında doğru rengi alır; hata yok.
- TTS servisi çalışmıyorsa? → Sessiz geçiş, Telegram bildirimi yeterli.
- config/agents.yaml bozulursa? → Fallback: Jarvis (varsayılan), hata logu.

---

## Persona Profilleri

| ID | Ad | Rol | Renk | Ses |
|----|----|-----|------|-----|
| seda | Seda | Kod / Debug / PR | #00ff88 | AhmetNeural |
| mert | Mert | Araştırma / Rakip | #ffdd00 | AhmetNeural |
| buse | Buse | Pazarlama / Landing | #ff69b4 | EmelNeural |
| eren | Eren | Veri / Dashboard | #ff8c00 | AhmetNeural |
| luna | Luna | Güvenlik / Audit | #9b59b6 | EmelNeural |
| sabrican | Sabrican | Deploy / Ops | #95a5a6 | AhmetNeural |
| sabri | Sabri | Wildcard / Yaratıcı | #e74c3c | AhmetNeural |
