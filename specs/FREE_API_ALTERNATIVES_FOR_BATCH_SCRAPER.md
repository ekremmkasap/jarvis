# Free API Alternatifleri — Batch Profile Scraper

**Araştırma Kaynağı**: github.com/public-apis/public-apis (422k stars)

---

## 📊 Instagram Çekimi Seçenekleri

### Option 1: instaloader (Mevcut - Login with env)
- **Status**: ✅ Implemented
- **Authentication**: INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD (env)
- **Fallback**: Public data (login olmadan)
- **Pros**: Detaylı veri (followers, engagement, posts)
- **Cons**: Instagram rate-limit, login gerekli
- **Usage**: Already in `server/services/universal_profile_scraper.py`

### Option 2: HunterIO (Development kategori)
- **Status**: 🔄 Alternative
- **API Type**: Email + profile lookup
- **Rate**: Free tier: 100/month
- **Pros**: Email finder, profile enrichment
- **Cons**: Email-focused, Instagram data sınırlı
- **Cost**: freemium

### Option 3: Web Scraping APIs (Public data)
- **Options**:
  - `ScrapingDog` (apiKey | Yes)
  - `ScraperApi` (apiKey | Yes)
  - `ZenRows` (apiKey | Yes)
  - `ProxyCrawl` (apiKey | Yes)
- **Pros**: Anti-bot bypass, rotation proxies
- **Cons**: Free tier 100 req/month
- **Use Case**: Public profile pages, posts

---

## 🎥 YouTube Çekimi (Ready)

### Option 1: YouTube Data API v3 (Mevcut - Ready)
- **Status**: ✅ Implemented
- **Key**: REDACTED (in .env)
- **Rate**: 10,000 units/day (free)
- **Data**: Channel info, videos, stats, comments
- **Integration**: Already in `server/services/universal_profile_scraper.py`

### Option 2: SocialBlade (Analytics alternative)
- **Status**: 🔄 Alternative
- **API**: No official API (can scrape)
- **Data**: Channel growth, analytics
- **Use**: Engagement analytics alongside YouTube API

---

## 🔄 Fallback Strategy (Implemented)

```python
# Current flow in universal_profile_scraper.py:

# Instagram:
try:
    return await _scrape_with_instaloader(handle)      # Primary
except:
    try:
        return await _scrape_with_graph_api(handle)    # Fallback (public)
    except:
        return None                                      # Fail gracefully

# YouTube:
if YOUTUBE_API_KEY:
    return await scrape_youtube_api(channel)           # Primary
else:
    return await scrape_youtube_fallback(channel)      # Public page
```

---

## 💾 Credential Configuration

### Current State
```env
YOUTUBE_API_KEY=REDACTED ✅
INSTAGRAM_USER=REDACTED ✅
INSTAGRAM_PASS=                                         ❌ (empty)
```

### Code Flexibility
- ✅ `INSTAGRAM_USERNAME` **OR** `INSTAGRAM_USER` (both supported)
- ✅ `INSTAGRAM_PASSWORD` **OR** `INSTAGRAM_PASS` (both supported)
- ✅ Public-only fallback (login optional)

---

## 🚀 Next Steps (When Ekrem Adds Sources)

**Expected additions:**
1. Additional YouTube API keys
2. HunterIO API key (optional, enrichment)
3. Web scraper API key (optional, backup)
4. Alternative Instagram session/token

**Integration Plan:**
- Add to `.env` following existing pattern
- Update `universal_profile_scraper.py` to use alternatives
- Test with batch scraper (tmp/handles.sample.csv)
- Measure response times + success rates

---

## 📈 Performance Targets

| Source | Concurrent | Timeout | Success Rate |
|--------|-----------|---------|--------------|
| Instagram | 5 | 30s | 70% (no login), 95% (with login) |
| YouTube | 5 | 30s | 98% (with API key) |
| Fallback | 5 | 30s | 40% |

**Current batch:** 5 max concurrent, 30s timeout, 2 retries

---

## 🔗 References

- **Repo**: https://github.com/public-apis/public-apis
- **Categories Used**: Development, Social, Photography, Text Analysis
- **Last Updated**: 422k stars, 46k forks, 1.2k PRs
