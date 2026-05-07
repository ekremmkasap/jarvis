# Instagram Lead Generation System — Detaylı Araştırma Raporu

**Tarih**: 15.04.2026  
**Kaynak**: `Instagram Müşteri Sistemi.pdf` (8 sayfa, İngilizce + Türkçe)  
**Ekrem Links**: 
- https://www.instagram.com/p/DXJkcPtgiMN/
- https://www.instagram.com/reel/DXJfNSujy4O/

---

## 📋 PDF İçeriği Özeti

### **Sistem Adı**
Automatic Instagram Lead Generation System (Otomatik Instagram Potansiyel Müşteri Üretim Sistemi)

### **Ana Amaç**
- Hedef müşterinin takip ettiği hesapları tarama
- Bio keyword'lerine göre filtre (coach, trainer, fitness, etc.)
- Takipçi sayısına göre segment
- E-posta adreslerini extraction
- Günlük 30-500 qualified lead üretme

---

## 🔧 Teknik Stack

### **Kullanılan Teknolojiler**
| Bileşen | Araç | Açıklama |
|---------|------|---------|
| **Language** | Python | Otomasyon motoru |
| **Instagram API** | `instagrapi` (unofficial) | Profil scraping, session mgmt |
| **Data** | `openpyxl` | Excel dosyası yönetimi |
| **Proxy** | IPRoyal / Smartproxy | Optional - ban prevention |
| **Database** | CSV + Excel | Lead storage |
| **Rate Limiting** | 2-5s delay | Ban prevention |

### **Required Files**
```
leadgen/
├── scraper.py           (main engine)
├── importer.py          (Excel export)
├── config.json          (settings + keywords)
├── seeds.txt            (target accounts to scrape from)
└── results.csv          (auto-generated output)
```

---

## ⚙️ config.json Yapısı

```json
{
  "accounts": [
    {"username": "ig_account_1", "password": "pass_1"},
    {"username": "ig_account_2", "password": "pass_2"}
  ],
  "proxies": [],
  "min_followers": 5000,
  "delay_min": 2.0,
  "delay_max": 5.0,
  "save_every": 50,
  "keywords": [
    "coach", "trainer", "coaching", "fitness", "nutrition",
    "certified", "online coach", "transformation", "results"
  ]
}
```

### **Parametreler**
- `accounts`: 3-5 tane scraping hesabı (main account değil!)
- `min_followers`: Minimum takipçi sayısı (5K default)
- `delay`: Her profile check arasında 2-5s delay (ban prevention)
- `save_every`: 50 profile sonra progress kaydı
- `keywords`: Bio'da en az biri olmalı

---

## 🎯 Lead Qualification Logic

### **Lead Sayılma Şartları (ALL TRUE olması gerekir)**
1. ✅ Followers > min_followers (ör. 5,000)
2. ✅ Bio'da en az 1 keyword
3. ✅ Hesap public (not private)

### **Email Detection**
- Public email field scanning
- Bio text regex search ("email me: john@gmail.com" gibi)
- Auto-extraction + Excel EXPORT sekmesine yazma

---

## 📊 Output Structure (Excel)

### **FA Leads IG.xlsx**
| Sheet | Takipçi Range | Amaç |
|-------|----------|------|
| DATA | 50K+ | High-authority leads |
| Data 10 to 70K | 5K-50K | Mid-tier leads |

### **FA Leads Email.xlsx**
| Sheet | Kullanım |
|-------|---------|
| DATA | Tüm leads (50K+) |
| Data10-70K | Mid-tier (5K-50K) |
| EXPORT | Email olanlar (Instantly/Lemlist için) |

### **Header Columns (19 fields)**
```
number | ig_user_id | avatar | profile | username | full_name | 
followed_by_you | is_verified | followers_count | following_count | 
posts_count | email | phone | city | biography | address_street | 
is_private | is_business | external_url
```

---

## 📈 Scalability & Performance

### **Leads Per Day (Based on Configuration)**
```
Configuration          | Leads/Day Range | Factor
---------------------------------------------------
5 accounts, no proxy   | 30-50           | Baseline
5 accounts + proxy     | 100-200         | 2-4x
10+ accounts + proxy   | 300-500         | 6-10x
```

### **Scale Factors**
- More scraping accounts = parallel requests
- Residential proxy = ban prevention (same IP không repeat)
- Longer runtime = more profiles scanned
- Low delay = faster pero higher ban risk

---

## 🔄 Daily Routine

### **Morning**
```bash
open terminal
cd Desktop/leadgen
python -u scraper.py          # Start scraping
# minimize window, work on other tasks
```

### **Evening**
```bash
# In terminal
Ctrl+C                        # Stop scraper
python -u importer.py         # Export to Excel
# Upload EXPORT sheet to Instantly / Lemlist
```

### **Automation**
- `progress.json` = tracks scraped profiles (prevents re-scraping)
- Can resume mid-run (Ctrl+C → python scraper.py again)
- New leads accumulated daily

---

## ⚠️ Risk Management

### **Ban Prevention Strategy**
| Tactic | Implementation |
|--------|-----------------|
| Fresh accounts | Use 3-5 new IG accounts (not main) |
| Rate limiting | 2-5s delay between checks |
| Proxy rotation | IPRoyal/Smartproxy for IP rotation |
| Progress tracking | progress.json prevents duplicates |
| Account rotation | Replace banned account + continue |

### **If Account Gets Banned**
1. Replace in `config.json`
2. Restart scraper
3. progress.json preserves progress (no re-scraping)

---

## 🌐 Integration Points (For Batch Scraper)

### **How This Relates to Our System**

| Component | Our System | Instagram Scraper |
|-----------|-----------|------------------|
| **Profile URLs** | /scrape-profile @handle | ← Uses similar API |
| **Batch input** | /batch-scrape CSV | ← Takes URLs from seeds.txt |
| **Email extraction** | Bio + profile fields | ↓ Same logic |
| **Excel export** | Reports + analysis | ← Identical output format |
| **Proxy support** | Optional | ✅ YES (IPRoyal/Smartproxy) |

### **Direct Compatibility**
- `instagrapi` (their tool) = same library we're using
- Email regex parsing = we already have this
- Excel export = openpyxl (same)
- Delay/retry logic = same pattern

---

## 🚀 Instagram Links (Ekrem Provided)

### **Link 1: Post**
https://www.instagram.com/p/DXJkcPtgiMN/

### **Link 2: Reel**
https://www.instagram.com/reel/DXJfNSujy4O/

**Status**: Can be crawled with:
- `scraper.py` (extract profile data from engagers)
- `instagrapi` (get post comments → profile URLs)
- Our batch scraper (add URLs to seeds.txt)

---

## 📋 Actionable Next Steps

### **For Jarvis Batch Scraper**
1. ✅ PDF system studied — confirmed compatibility
2. ✅ instagrapi library available (already in use)
3. 🔄 Add proxy support (IPRoyal/Smartproxy keys)
4. 🔄 Add seed file support (seeds.txt parser)
5. 🔄 Add progress tracking (progress.json clone)

### **For Ekrem**
1. Instagram linkleri işlemi başlatmak için kullan
2. Batch scraper ile compatibility check
3. Proxy keys ekle (optional but recommended for scale)
4. Test: 5 seed account → daily lead target

---

## 🎯 Integration Summary

**Ekrem's Instagram Scraper System** ← Can be integrated into:

1. **Batch Profile Scraper** (already built)
   - seeds.txt → batch_handles_031_065.csv
   - Keywords → engagement filter
   - Excel output → same format

2. **Codex Swarm**
   - Buse (spark): Add keyword scoring to reel analysis
   - Eren (spark): Add engagement trend extraction
   - Seda (forge): Handle proxy + account rotation

3. **Lead Gen Pipeline**
   - Scrape → Bio extraction → Email pull → Excel export
   - 100-500 leads/day (with proxy)
   - Auto-resume on ban

---

## 📌 Key Files & Links

- **PDF**: `C:\Users\sergen\Downloads\Instagram Müşteri Sistemi.pdf`
- **Library**: `instagrapi` (https://github.com/adw0rd/instagrapi)
- **Proxy**: IPRoyal / Smartproxy (residential)
- **Email Tool**: Instantly / Lemlist (downstream)

**Status**: System ready for integration. Awaiting Ekrem's proxy keys + additional resources.
