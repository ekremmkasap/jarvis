# Evrensel Profil Çekici Becerisi — Tam Rehberi

**Tarih**: 2026-04-15  
**Durum**: Üretim Hazır  
**Platformlar**: Instagram + YouTube (TikTok, Twitter'a genişletilebilir)

---

## Nedir?

Bir Instagram hesabı ya da YouTube kanalı URL'si verilince, o profilin **tüm verisini** çekip JSON formatına dönüştürüyor:
- Takipçi sayısı
- Son postlar/videolar (30 tanesi)
- Etkileşim metrikleri
- Bio, hashtag'ler, içerik temaları
- Paraşlandırma sinyalleri (alışveriş, sponsorlu, vb.)

---

## 3 Kullanım Yöntemi

### Yöntem 1: Bridge Komutu (En Hızlısı)

```
/scrape-profile @leadgenman
/scrape-profile @alexlindai
/scrape-profile https://youtube.com/c/MyCoolChannel
```

**Çıkış**:
```
✅ Profil başarıyla çekildi!

📊 Özet:
  Hesap: @leadgenman
  Takipçiler: 22.000
  Postlar: 30
  Etkileşim: 2.1%

📁 Dosya kaydedildi: /outputs/profile_scrapes/leadgenman_20260415_143022.json
```

**Avantajlar**: Anında, kurulum yok  
**Dezavantajlar**: Bir seferde 1 profil ile sınırlı

---

### Yöntem 2: Beceriyi Doğrudan Çağırma (Programatik)

```python
from server.services.universal_profile_scraper import UniversalProfileScraper

scraper = UniversalProfileScraper()

# Instagram
profile_data = await scraper.scrape("@leadgenman", platform="instagram")

# YouTube
channel_data = await scraper.scrape("https://youtube.com/c/MyCoolChannel", platform="youtube")

# Otomatik algıla
data = await scraper.scrape("@leadgenman")  # Instagram'ı otomatik algılar
```

**Çıkış**: InstagramProfileData ya da YouTubeChannelData (sınıf, JSON-dönüştürülebilir)

**Avantajlar**: Esnek, otomatik platform algılaması  
**Dezavantajlar**: Python ortamı gerektirir

---

### Yöntem 3: Codex Aracı Ataması (Toplu)

```
Codex forge/Seda'ya gönder:

"Instagram ve YouTube profillerini toplu olarak çeken bir beceri yaz.

Giriş: Hesap listesi (CSV)
  @leadgenman
  @alexlindai
  @ohmo.ai
  @tenfoldmarc
  
Çıkış: JSON dosyalarından oluşan klasör (profil başına birer dosya)

universal_profile_scraper.py'yi temel olarak kullan.
Ekle:
- Toplu işleme (paralel)
- Hata kontrolü + yeniden deneme
- CSV ihracatı (isteğe bağlı)
- Rapor oluşturma (özet istatistikleri)

Döndür: /skills/batch_profile_scraper.py
"
```

**Avantajlar**: Otomatik toplu işleme, paralel işlem  
**Dezavantajlar**: Codex becerisi geliştirmesi için 2-3 gün bekleme

---

## Gereksinimler

### Instagram için (instaloader yöntemi):

```bash
pip install instaloader
```

**Not**: Tam erişim için giriş kimlik bilgileri gerekebilir. Kamusal veriler giriş yapılmadan çalışır.

### YouTube için (API yöntemi):

```bash
pip install google-api-python-client
```

**Kurulum**:
1. Google Cloud Console'a git
2. Proje oluştur
3. YouTube Data API v3'ü etkinleştir
4. API anahtarı oluştur
5. `YOUTUBE_API_KEY` ortam değişkenini ayarla

---

## Çıkış Formatı: Instagram Profili

```json
{
  "hesap": "leadgenman",
  "profil_url": "https://instagram.com/leadgenman",
  "tam_ad": "Lead Gen Man",
  "bio": "Claude Code inşaat yapıyo",
  "takipci_sayisi": 22000,
  "takip_ettikleri": 450,
  "post_sayisi": 156,
  "dogrulanmis": true,
  "isletme_hesabi": true,
  "profil_resmi_url": "https://...",
  "website_url": "https://example.com",
  
  "ortalama_etkilesim_orani": 2.1,
  "post_basina_ortalama_begenme": 462,
  "post_basina_ortalama_yorum": 35,
  "son_30_gun_toplam_etkilesim": 14850,
  
  "son_postlar": [
    {
      "post_id": "CXXa1b2c",
      "yazı": "7 Claude Code becerisi...",
      "tarih": "2026-04-15T12:00:00",
      "begenme": 1200,
      "yorum": 150,
      "paylas": 300,
      "etkilesim_orani": 2.1
    }
  ],
  
  "kullanilan_hashtag": {
    "claude": 45,
    "code": 32,
    "ai": 28
  },
  
  "icerik_temalari": ["egitim", "verimlilik", "otomasyon"],
  "haftalik_post_siklik": 4.2,
  "aylik_takipci_buyume": 8.5,
  "alisveris_ozelligi": false,
  "affiliate_baglantisi": true,
  "tahmini_aylik_gelir": "₺50K-100K"
}
```

---

## Çıkış Formatı: YouTube Kanalı

```json
{
  "kanal_id": "UCxxxxxx",
  "kanal_url": "https://youtube.com/channel/UCxxxxxx",
  "kanal_adi": "Harika Kanalım",
  "aciklama": "...",
  "abone_sayisi": 50000,
  "toplam_video": 234,
  "toplam_izlenme": 5000000,
  "dogrulanmis": true,
  
  "video_basina_ortalama_izlenme": 21368,
  "ortalama_etkilesim_orani": 3.2,
  "haftalik_ortalama_yuklemeler": 2.1,
  
  "son_videolar": [
    {
      "video_id": "dQw4w9WgXcQ",
      "baslik": "Claude Code Nasil Kullanilir",
      "yuklenme_tarihi": "2026-04-15T10:00:00",
      "izlenme": 50000,
      "begenme": 2500,
      "yorum": 800,
      "etkilesim_orani": 6.6
    }
  ],
  
  "video_kategorileri": {
    "Egitim": 120,
    "Teknoloji": 80,
    "Oguretim": 34
  },
  
  "aylik_abone_buyume": 12.3,
  "partner_program_uygun": true,
  "super_chat_acik": true,
  "tahmini_aylik_gelir": "₺200K-500K"
}
```

---

## Kullanım Örnekleri

### 1️⃣ Hızlı Profil Kontrolü

```
/scrape-profile @leadgenman
```

Çıkış: Telegram'da özet verisi  
Dosya: İleride kullanmak için kaydedildi

---

### 2️⃣ Kompetitor Analizi (Toplu)

```
20 kompetitor profilini toplu çek
Çıkış: 20 JSON dosyası içeren klasör

Sonra: Codex profil analizirine gönder
Sonuç: Stratejik içgörüler + karşılaştırmalar
```

---

### 3️⃣ AI Takipçi Stratejisi

```
Ekrem'in takip ettiği 10 başarılı hesabı çek:
  @leadgenman
  @alexlindai
  @ohmo.ai
  @tenfoldmarc
  @akinyilmaz.ai
  @mindwired.ai
  @power.ai
  @codingknowledge
  @githubprojects
  @tenfoldmarc

Tüm JSON'ları Codex'e gönder analiz için
Sonuç: "Bu 10 neden kazanıyor + Jarvis ne kopyalamalı"
```

---

### 4️⃣ Derin Profil İncelemesi

```
/scrape-profile @leadgenman
→ 30 son post analiz et
→ Hashtag'leri çıkar (45 #claude, 32 #code)
→ Paraşlandırma sinyallerini kontrol et
→ Bio + bağlantıları gözden geçir

Sonuç: "Bu hesap paraşlandırılıyor mu? Nasıl?"
```

---

## Sonraki: Codex Entegrasyonu

**İleri scraping becerileri oluşturmak için Codex'e gönder**:

```
Görev: Toplu Profil Çekici Becerisi Yaz

Giriş: 50 Instagram/YouTube hesabı (CSV)
Çıkış: 50 JSON dosyası + özet raporu

universal_profile_scraper.py'yi temel al.
Ekle:
- Paralel işleme (5 eş zamanlı)
- Hız sınırı (Instagram/YouTube limitlerini saygıla)
- Hata kurtarışı (başarısız profilləri yeniden dene)
- CSV ihracı (etkileşim karşılaştırmaları)
- Paraşlandırma tahmin modeli

Döndür: /skills/batch_profile_scraper_codex.py
```

---

## Sınırlamalar

### Instagram (instaloader)
- Tam erişim için giriş gerekir
- Hız sınırlı (çok fazla istek sonra Instagram bloke edebilir)
- Özel hesaplar tam scrape olmaz

### YouTube (API)
- API anahtarı + kota gerekir
- Ücretsiz paket: 10K istek/gün (günde ~100 kanal yeter)

### Genel Kurallar
- Sadece etik kullanım (hizmet şartlarına saygılı olmak)
- Spam/taciz için scrape etme
- Gizlilik ayarlarına saygı

---

## Kanka, ne yapıcaz?

1. **Tek profil**: `/scrape-profile @hesap`
2. **Toplu (10+)**: Codex'e beceri yaz, tümünü çek
3. **Gerçek zamanlı takip**: Cron job + günlük scrape
4. **Kompetitor analizi**: Toplu çek + Codex analizi

Hangisini başlatıyoruz? 🚀
