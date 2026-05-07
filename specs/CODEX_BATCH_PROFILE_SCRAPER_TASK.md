# Codex Görev: Toplu Profil Çekici Becerisi

**Tarih**: 2026-04-15  
**Hedef Persona**: forge/Seda  
**Zorluk**: Orta  
**Tahmini Süre**: 4-6 saat  
**Öncelik**: Yüksek

---

## Görev Özeti

`universal_profile_scraper.py` üzerine inşa ederek, **toplu profil çekici** becerisi yaz. 50+ Instagram/YouTube hesabını paralel olarak scrape et, engagement analizi yap, özet rapor oluştur.

---

## Teknik Temel

### Base Kodu: `/server/services/universal_profile_scraper.py`

**Mevcut Yapı**:
```python
UniversalProfileScraper()
  ├─ .scrape("@handle", platform="instagram")
  └─ .scrape("https://youtube.com/c/Channel", platform="youtube")
  
Çıkış: InstagramProfileData | YouTubeChannelData (Dataclass, JSON)
```

**Örnek Output** (Instagram):
```json
{
  "hesap": "leadgenman",
  "takipci_sayisi": 22000,
  "post_sayisi": 156,
  "ortalama_etkilesim_orani": 2.1,
  "son_postlar": [
    {"begenme": 1200, "yorum": 150, "etkilesim_orani": 2.1}
  ],
  "tahmini_aylik_gelir": "₺50K-100K"
}
```

---

## Yeni Beceri: `batch_profile_scraper_codex.py`

### Giriş (Input)

**Yöntem 1: CSV dosya**
```csv
hesap,platform
@leadgenman,instagram
@alexlindai,instagram
https://youtube.com/c/Channel1,youtube
```

**Yöntem 2: Python List**
```python
hesaplar = ["@leadgenman", "@alexlindai", "https://youtube.com/c/Channel1"]
```

---

### İşlev 1: Paralel Scraping

```python
class BatchProfileScraper:
    def __init__(self, max_concurrent=5, timeout=30):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.scraper = UniversalProfileScraper()
    
    async def scrape_batch(self, hesaplar: List[str]) -> Dict:
        """
        Paralel scrape (5 eş zamanlı)
        
        Input: ["@leadgenman", "@alexlindai", ...]
        Output: {
            "completed": 48,
            "failed": 2,
            "profiles": [...],
            "errors": [...]
        }
        """
```

**Detay**:
- asyncio.Semaphore (5 eş zamanlı max)
- Try/except + error logging
- Başarısız profil retry (2x)
- Timeout koruma (30 sn)

---

### İşlev 2: Engagement Analizi

```python
def analyze_engagement(profiles: List[Dict]) -> Dict:
    """
    Tüm profillerin engagement'ını karşılaştır
    
    Çıkış:
    {
        "instagram_avg_engagement": 2.1,
        "youtube_avg_engagement": 3.2,
        "top_performers": [
            {"hesap": "leadgenman", "etkilesim": 2.8}
        ],
        "benchmarks": {
            "instagram": {
                "min": 0.5,
                "max": 4.2,
                "median": 1.8
            }
        }
    }
    """
```

**Hesapla**:
- Platform'a göre ayrı engagement ortalamaları
- Top 5 best performers
- Benchmark (min/max/median)
- Growth patterns (ay-ay)

---

### İşlev 3: Paraşlandırma Tahmini

```python
def estimate_monetization(profiles: List[Dict]) -> Dict:
    """
    Her profil için aylık gelir tahmini
    
    Sinyaller:
    - has_affiliate_links (2-5x multiplier)
    - has_shopping_feature (1-3x)
    - has_sponsored_posts (1.5-2x)
    - subscriber/follower_count (baseline)
    - avg_engagement_rate (efficiency)
    
    Formül: baseline * (1 + multipliers)
    """
```

**Örnek Hesaplama**:
```
Baseline: takipçi_sayisi * 0.01 (₺/ay)
@leadgenman: 22000 * 0.01 = ₺220

Multipliers:
+ Affiliate: ₺220 * 1.5 = ₺330
+ Shopping: ₺330 * 1.2 = ₺396
+ Sponsor: ₺396 * 1.3 = ₺514

Tahmini Aylık Gelir: ₺50K-100K (range)
```

---

### İşlev 4: Özet Rapor

```python
def generate_summary_report(profiles: List[Dict], analysis: Dict) -> Dict:
    """
    Tüm profillerin özet raporu
    
    Çıkış: ozet_rapor.json
    {
        "tarih": "2026-04-15",
        "toplam_profil": 50,
        "basarili": 48,
        "basarisiz": 2,
        "toplam_takipci": 1250000,
        "ortalama_etkilesim": 2.3,
        "tahmini_toplam_gelir": "₺5M-10M/ay",
        "platform_dagilimi": {
            "instagram": 40,
            "youtube": 8,
            "tiktok": 2
        },
        "en_iyi_10": [
            {"sira": 1, "hesap": "leadgenman", "etkilesim": 2.8, "gelir": "₺50K-100K"}
        ]
    }
    """
```

---

## Çıkış (Output)

**Dosya Yapısı**:
```
outputs/batch_scrapes/
├── 2026-04-15_profiller/
│   ├── leadgenman.json
│   ├── alexlindai.json
│   ├── ohmo_ai.json
│   └── ... (48 dosya)
├── ozet_rapor.json
├── engagement_analiyi.json
├── monetization_tahminleri.json
└── hata_log.json
```

**Dosya Boyutları**:
- Her profil JSON: ~5KB
- 50 profil: 250KB
- Raporlar: 50KB total

---

## Bridge Entegrasyonu

### Komut: `/batch-scrape`

```python
# bridge.py'ye ekle (handler)
elif command == "/batch-scrape":
    csv_path = args.strip()  # /outputs/hesaplar.csv
    
    from skills.batch_profile_scraper_codex import BatchProfileScraper
    scraper = BatchProfileScraper(max_concurrent=5)
    
    result = await scraper.batch_scrape_from_csv(csv_path)
    
    return f"""
✅ Toplu Scrape Tamamlandı!

📊 Sonuçlar:
  Toplam: {result['toplam']}
  Başarılı: {result['basarili']}
  Hata: {result['basarisiz']}
  
💰 Tahmini Toplam Gelir: {result['toplam_gelir']}

📁 Dosyalar: {result['output_path']}
    """
```

---

## Gereksinimler

### Kütüphaneler
```python
import asyncio
import csv
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
```

### Mevcut Bağımlılıklar
```python
from server.services.universal_profile_scraper import UniversalProfileScraper
```

---

## Hata Yönetimi

### Başarısız Profil Yeniden Deneme

```python
async def scrape_with_retry(handle: str, max_retries=2):
    for attempt in range(max_retries):
        try:
            profile = await scraper.scrape(handle)
            return profile
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                return {
                    "handle": handle,
                    "error": str(e),
                    "attempted": attempt + 1
                }
```

### Rate Limiting

```python
# Instagram: Max 10 req/min (backoff)
# YouTube: Max 100 req/min (API quota)

async def rate_limited_scrape(handles: List[str]):
    semaphore = asyncio.Semaphore(5)
    
    async def fetch(handle):
        async with semaphore:
            result = await scrape_with_retry(handle)
            await asyncio.sleep(6)  # 6 sn aralık
            return result
    
    tasks = [fetch(h) for h in handles]
    return await asyncio.gather(*tasks)
```

---

## Test Adımları

### 1. Tek Profil Test
```python
scraper = BatchProfileScraper()
result = await scraper.scrape_batch(["@leadgenman"])
assert result['completed'] == 1
assert result['profiles'][0]['hesap'] == 'leadgenman'
```

### 2. 5 Profil Test
```python
result = await scraper.scrape_batch([
    "@leadgenman",
    "@alexlindai",
    "@ohmo.ai",
    "@tenfoldmarc",
    "@akinyilmaz.ai"
])
assert result['completed'] == 5
assert len(result['profiles']) == 5
```

### 3. Engagement Analizi Test
```python
analysis = analyze_engagement(result['profiles'])
assert 'instagram_avg_engagement' in analysis
assert 'top_performers' in analysis
```

### 4. Rapor Oluşturma Test
```python
report = generate_summary_report(result['profiles'], analysis)
assert report['toplam_profil'] == 5
assert 'tahmini_toplam_gelir' in report
```

---

## Deliverable'lar

1. **Dosya**: `/skills/batch_profile_scraper_codex.py`
   - BatchProfileScraper sınıfı
   - 4 ana fonksiyon (paralel, analiz, paraşlandırma, rapor)
   - Bridge integration code

2. **Test Çıkışı**: Örnek `/outputs/batch_scrapes/` klasörü
   - 5 örnek profil JSON
   - Özet rapor
   - Engagement analizi

3. **Döküman**: `/skills/BATCH_SCRAPER_README.md`
   - Kurulum
   - Kullanım örnekleri
   - API referansı

---

## Başarı Kriteri

✅ 50 profili 5 rn içinde paralel çek  
✅ 95% başarı oranı (2+ retry)  
✅ Engagement ortalamaları accuracy ± 5%  
✅ Paraşlandırma tahmini reasonable (expert review)  
✅ Rapor valid JSON, complete metadata  
✅ Bridge komutu working, Telegram'da test  

---

## Notes

- InstaLoader'ın rate limit'i ~ 10 req/min (5 eş zamanlı @ 6 sn = ✅)
- YouTube API quota: 10K/day free (50 channel = 50 units, plenty)
- Hata durumunda failover: silent skip + log (yapıyı bozmaz)
- Monetization tahminleri "estimated range", exact değil (disclaimer)

---

**Ready? Başlatalım mı?** 🚀
