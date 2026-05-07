# Feature Specification: Jarvis Autonomous Research & Personality Agent Sistemi

**Feature Branch**: `002-autonomous-research-agent`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Jarvis Autonomous Research & Personality Agent Sistemi"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sabah Araştırma Briefingi (Priority: P1)

Ekrem sabah uyandığında Jarvis, geceden beri takip ettiği kaynaklardan (GitHub trending, Reddit, X/Twitter) derlediği günlük özeti Telegram üzerinden gönderir. Ekrem hiçbir şey yapmadan günün önemli gelişmelerini öğrenir.

**Why this priority**: Jarvis'in proaktif kişiliğinin en somut göstergesi. Günlük değer üretiyor, kullanıcı aksiyona geçmeden.

**Independent Test**: Sabah 08:00'de Telegram'a bir mesaj geliyor mu? Mesajda GitHub, Reddit veya X içeriği var mı?

**Acceptance Scenarios**:

1. **Given** sistem çalışmakta, **When** saat 08:00 oluyor, **Then** Jarvis Telegram'a GitHub trending + Reddit + X özetini gönderiyor
2. **Given** hiç kaynak bulunamıyor veya API erişimi yok, **When** brief zamanı geliyor, **Then** Jarvis "bugün içerik çekemedim" bilgisi veriyor, sessizce başarısız olmuyor

---

### User Story 2 - Instagram Hesap Takibi (Priority: P2)

Ekrem Jarvis'e bir Instagram hesabı veriyor (`/instagram takip @fatihmakes` gibi). Jarvis o hesabı takip listesine ekliyor ve yeni post/reel geldiğinde Telegram'a bildiriyor.

**Why this priority**: İçerik takibi için doğrudan iş değeri — rakip analizi, ilham kaynağı, trend takibi.

**Independent Test**: `/instagram takip @hesap` komutu verilince hesap listeye ekleniyor mu? Yeni içerik gelince bildirim geliyor mu?

**Acceptance Scenarios**:

1. **Given** Jarvis çalışıyor, **When** `/instagram takip @hesap` komutu verilir, **Then** hesap takip listesine eklenir ve onay mesajı gelir
2. **Given** takip listesinde hesap var, **When** o hesapta yeni post yayınlanır, **Then** Jarvis 30 dakika içinde Telegram'a bildirim gönderir
3. **Given** hesap private veya silinmiş, **When** takip eklenmeye çalışılır, **Then** Türkçe hata mesajı döner

---

### User Story 3 - External Agent Framework Aktivasyonu (Priority: P3)

Ekrem `/crewai` veya `/openhands` komutu ile external-repos altındaki agent framework'lerini Jarvis üzerinden kullanabiliyor. Örneğin `/crewai araştır: Python 2026 trendleri` komutu CrewAI'ı çalıştırıp sonucu döndürüyor.

**Why this priority**: external-repos'taki framework'leri aktif hale getirmek Jarvis'in kapasitesini katlar. Önce temel ikisi (CrewAI + OpenHands) yeterli.

**Independent Test**: `/crewai durum` ve `/openhands durum` komutları çalışıyor mu?

**Acceptance Scenarios**:

1. **Given** external-repos/crewAI mevcut, **When** `/crewai [görev]` komutu verilir, **Then** CrewAI görevi çalıştırır ve sonucu döndürür
2. **Given** framework kurulu değil, **When** komut verilir, **Then** "kurulum gerekiyor: pip install ..." mesajı döner

---

### User Story 4 - Jarvis Kişilik Sistemi (Priority: P4)

Jarvis, soul.md dosyasından okuduğu kişiliğiyle sabah selamlıyor, günlük agenda oluşturuyor ve proaktif öneriler yapıyor.

**Why this priority**: Kullanıcı bağlılığını artırır, Jarvis'i bir araçtan iş ortağına dönüştürür.

**Independent Test**: soul.md düzenlenince Jarvis'in ton ve içeriği değişiyor mu?

**Acceptance Scenarios**:

1. **Given** soul.md'de kişilik tanımlı, **When** Jarvis sabah briefingi yapıyor, **Then** mesaj soul.md'deki tona uygun Türkçe yazılmış
2. **Given** günlük agenda oluşturuluyor, **When** Ekrem "bugün ne var?" diye soruyor, **Then** Jarvis araştırmadan gelen önemlileri özetliyor

---

### Edge Cases

- Instagram rate limit aşılırsa ne olur? (instaloader bekleme mekanizması)
- X/Twitter API ücretsiz tier'da çok kısıtlı — scraping fallback'e düşülecek mi?
- GitHub API limiti (60 req/saat unauthenticated) — token yoksa nasıl davranır?
- CrewAI / OpenHands kurulu değilse sessiz fail mi, hata mı?
- Sabah briefingi Jarvis kapalıyken gelirse scheduler ne yapar?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistem MUST her gün belirlenen saatte GitHub trending, Reddit ve X kaynaklarından içerik toplayıp özet üretmeli
- **FR-002**: Sistem MUST üretilen özeti Telegram bot üzerinden belirlenen chat_id'ye göndermeli
- **FR-003**: Kullanıcı MUST `/instagram takip @hesap` komutuyla takip listesine hesap ekleyebilmeli
- **FR-004**: Sistem MUST takip listesindeki Instagram hesaplarını periyodik kontrol edip yeni içerik varsa Telegram bildirimi göndermeli
- **FR-005**: Takip listesi MUST kalıcı olarak saklanmalı (restart'ta silinmemeli)
- **FR-006**: Sistem MUST `/crewai` ve `/openhands` komutlarını bridge.py üzerinden yönlendirmeli
- **FR-007**: Her external framework skill'i MUST kurulum kontrolü yapmalı, kurulu değilse kullanıcıya yönlendirici mesaj vermeli
- **FR-008**: soul.md dosyası MUST Jarvis'in tonunu, sabah selamlama stilini ve günlük agenda formatını tanımlamalı
- **FR-009**: Tüm araştırma ve takip işlemleri MUST arka planda çalışmalı, bridge.py ana döngüsünü bloklamamalı
- **FR-010**: API key, token ve credential'lar MUST loga veya Telegram mesajlarına sızdırılmamalı

### Key Entities

- **ResearchReport**: Kaynak (GitHub/Reddit/X/Instagram), içerik başlığı, URL, özet, tarih
- **WatchedAccount**: Platform (instagram), hesap adı, son kontrol tarihi, son post ID
- **DailyBrief**: Tarih, kaynak listesi, özet metin, gönderildi mi
- **AgentFramework**: İsim (crewai/openhands), repo yolu, kurulum durumu, bridge komutu

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Jarvis her sabah 08:00'de (±5 dakika) Telegram'a günlük özet gönderiyor
- **SC-002**: Instagram takipçi ekleme komutu 5 saniyede tamamlanıyor ve onay mesajı geliyor
- **SC-003**: Takip edilen hesaplarda yeni içerik 30 dakika içinde tespit ediliyor
- **SC-004**: `/crewai durum` ve `/openhands durum` komutları 10 saniyede yanıt veriyor
- **SC-005**: Mevcut Jarvis komutlarının hiçbirinin davranışı değişmiyor (sıfır regresyon)
- **SC-006**: Tüm araştırma işlemleri arka planda çalışıyor, Jarvis'in normal komutlara yanıt süresi etkilenmiyor

## Assumptions

- GitHub, Reddit API'leri ücretsiz tier'da yeterli kota sağlıyor (token ile artırılabilir)
- X/Twitter için resmi API yerine başlangıçta nitter proxy veya web scraping kullanılabilir
- Instagram takibi için instaloader kullanılıyor, login gerektiren özellikler opsiyonel
- Sabah briefingi saati varsayılan 08:00, .env üzerinden değiştirilebilir
- CrewAI ve OpenHands external-repos altında zaten clone'lanmış durumda
- Jarvis Windows 10'da çalışıyor, scheduler için APScheduler kullanılacak
- soul.md dosyası server/ veya config/ altında tutulacak
- Tüm bildirimler mevcut Telegram bot üzerinden gidecek (yeni bot token gerekmez)
