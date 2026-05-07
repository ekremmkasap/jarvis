# AI Influencer Mode — Jarvis Sosyal Medya Otomasyonu

**Tarih**: 2026-04-15  
**Durum**: SPECIFICATION  
**Hedef**: Jarvis'i Türkçe market'te AI influencer olarak konumlandır — otonom research + daily posting

---

## Vizyon

Jarvis, kendi Instagram/TikTok/X hesaplarında **günlük** olarak:
1. ✅ Trending topics araştır + AI insights generate et
2. ✅ Competitor posts (100 reference account) analyze et
3. ✅ Content generate et (platform-optimized: 10-50 karakter to 280 char)
4. ✅ Postları schedule et + otomatik publish et
5. ✅ Performance track et + iteratif learn et

**KPI**: 6 ayda 50K followers + 500+ posts (6+ per day)

---

## Architecture: 3 Modül

```
Daily Research Task
  ↓
Content Generator (per platform)
  ↓
Auto-Poster (Instagram API, TikTok API, Twitter API)
  ↓
Analytics + Memory Consolidation
```

---

## Modül 1: Daily Research Task

**Lokasyon**: `server/services/ai_influencer_research.py`

**Görev**: Her 3-4 saatte çalış

```python
class DailyResearchTask:
    """
    Günlük sosyal medya research:
    - Turkish tech/AI trends (Google Trends, Twitter Trending)
    - Competitor posts analysis (100 reference account'lar)
    - User comment sentiment analysis
    - Content idea generation
    """
    
    async def run_daily_research(self) -> dict:
        """
        1. Trending keywords çıkar (Google Trends API)
        2. Reference accounts'tan top posts al
        3. Sentiment analysis + engagement pattern'leri
        4. Content ideas generate et (3-5 idea)
        5. state/research/daily_ideas.json'a kaydet
        """
        
        # Step 1: Trending
        trends = fetch_google_trends('TR', category='Business & Industrial')
        trending_keywords = extract_tech_ai_keywords(trends)
        
        # Step 2: Reference account analysis
        reference_posts = analyze_reference_accounts(
            account_ids=REFERENCE_ACCOUNTS_100,
            limit_per_account=5
        )
        
        engagement_patterns = {
            'high_engagement': extract_top_posts(reference_posts),
            'content_types': categorize_post_types(reference_posts),
            'posting_times': analyze_posting_times(reference_posts)
        }
        
        # Step 3: Content ideas
        ideas = generate_content_ideas(
            trending=trending_keywords,
            patterns=engagement_patterns,
            target_audience='Turkish KOBİ + entrepreneurs'
        )
        
        # Step 4: Save + notify
        save_daily_research(ideas)
        await notify_mert(f"📊 Research complete: {len(ideas)} content ideas")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'trending_keywords': trending_keywords,
            'content_ideas_generated': len(ideas),
            'reference_posts_analyzed': len(reference_posts)
        }
```

**Content Ideas Format**:

```json
{
  "date": "2026-04-15",
  "ideas": [
    {
      "title": "5 Ways Jarvis Saves KOBI Time (vs. Manual)",
      "platforms": ["instagram", "tiktok", "twitter"],
      "angle": "autonomy + business benefit",
      "hook": "5 saat/hafta tasarruf",
      "suggested_visuals": ["screenshot", "infographic", "animation"],
      "estimated_engagement": "2.3x"
    },
    {
      "title": "Eğitimci Görüşü: Jarvis'le Coding Öğretmek",
      "platforms": ["instagram"],
      "angle": "educator credibility (proven high-engagement)",
      "format": "carousel (3 slides)",
      "suggested_visuals": ["laptop_screen", "student_reaction"],
      "estimated_engagement": "2.1x"
    }
  ]
}
```

---

## Modül 2: Content Generator (Platform-Specific)

**Lokasyon**: `server/services/ai_influencer_content.py`

**Format per Platform**:

```python
class ContentGenerator:
    """
    Platform-optimized content:
    - Instagram: 150-2000 char, hook + CTA, emojis, hashtags
    - TikTok: 15-50 sec video, trending sounds, text overlay
    - Twitter/X: 140-280 char, punchy, trending hashtags
    - LinkedIn: 500-1000 char, professional, thought leadership
    """
    
    async def generate_instagram_post(idea: dict) -> dict:
        """
        Carousel post (3-5 slides):
        - Slide 1: Hook + eye-catching visual
        - Slides 2-4: Data/story
        - Slide 5: CTA + link
        """
        
        slides = [
            {
                "text": f"{idea['title']}\n\n💡 {idea['hook']}",
                "visual": generate_visual(idea['suggested_visuals'][0]),
                "caption": "slide_1_hook"
            },
            {
                "text": f"Avantaj #1:\n{benefit_1}",
                "visual": generate_visual(idea['suggested_visuals'][1]),
                "caption": "slide_2_benefit"
            },
            # ... slides 3-5
        ]
        
        full_caption = f"""
        {idea['title']}
        
        {caption_text}
        
        📌 Link profilde (bio)
        
        #Jarvis #AI #Automation #Turkish #KOBI
        """
        
        return {
            'platform': 'instagram',
            'format': 'carousel',
            'slides': slides,
            'caption': full_caption,
            'best_posting_time': calculate_optimal_time('TR', 'afternoon'),
            'estimated_reach': 2000
        }
    
    async def generate_tiktok_post(idea: dict) -> dict:
        """
        15-50 second video:
        - Trending sound
        - Text overlay
        - Quick-cut editing
        """
        return {
            'platform': 'tiktok',
            'format': 'video',
            'duration_seconds': 30,
            'trending_sound': select_trending_sound('AI', 'motivational'),
            'text_overlays': generate_text_overlays(idea),
            'music_beat_sync': True,
            'hashtags': ['#Jarvis', '#AI', '#Technology', '#Turkish', '#Automation']
        }
```

**Generated Content Storage**:

```
state/content_queue/
  ├── scheduled_2026-04-15.json  (publish ready)
  ├── drafts_2026-04-15.json     (pending review)
  └── published_archive/
```

---

## Modül 3: Auto-Poster + API Integration

**Lokasyon**: `server/services/ai_influencer_poster.py`

**Platform APIs**:

| Platform | API | Capability |
|----------|-----|-----------|
| Instagram | Instaloader + Graph API | Post scheduling, analytics |
| TikTok | TikTok API (creator) | Video upload, scheduling |
| Twitter/X | X API v2 | Tweet posting, scheduling |
| LinkedIn | LinkedIn API | Professional content |

```python
class AutoPoster:
    """
    Multiple platform'a otonom posting:
    - Content scheduling (optimal time per platform)
    - Multi-part series posting (carousel support)
    - Performance tracking (likes, comments, shares)
    """
    
    async def schedule_post(
        content: dict,
        platforms: List[str],
        publish_time: Optional[datetime] = None
    ) -> dict:
        """
        Post'u platform'lara schedule et.
        
        Instagram: Carousel push (up to 10 slides)
        TikTok: Video upload → schedule draft
        Twitter: Tweet + thread
        """
        
        results = {}
        
        for platform in platforms:
            if platform == 'instagram':
                # Instagram API
                post_id = await instagram_api.post_carousel(
                    slides=content['slides'],
                    caption=content['caption'],
                    scheduled_publish_time=publish_time
                )
                results['instagram'] = {
                    'status': 'scheduled',
                    'post_id': post_id,
                    'scheduled_time': publish_time
                }
            
            elif platform == 'tiktok':
                # TikTok API
                video_url = await generate_video(content)
                draft_id = await tiktok_api.create_draft(
                    video_url=video_url,
                    caption=content['caption'],
                    sounds=[content['trending_sound']]
                )
                results['tiktok'] = {
                    'status': 'draft',
                    'draft_id': draft_id,
                    'scheduled_time': publish_time
                }
            
            elif platform == 'twitter':
                # X API
                tweet_id = await twitter_api.post_tweet(
                    text=content['text'],
                    reply_settings='everyone',
                    scheduled_at=publish_time
                )
                results['twitter'] = {
                    'status': 'scheduled',
                    'tweet_id': tweet_id,
                    'scheduled_time': publish_time
                }
        
        return {
            'content_id': content['id'],
            'scheduled_posts': results,
            'total_platforms': len(platforms),
            'estimated_combined_reach': sum_estimated_reach(results)
        }
    
    async def post_now(content: dict, platforms: List[str]) -> dict:
        """Anonim publish — optimize edilebilir test için"""
        return await self.schedule_post(content, platforms, publish_time=datetime.now())
```

---

## Modül 4: Analytics + Memory Learning

**Integration**: Memory Consolidation Service (from Quick Win #3)

```python
class InfluencerAnalytics:
    """
    Post performance tracking + learning:
    - Which content types get 2.3x engagement?
    - Best posting times per platform?
    - Which reference accounts have highest engagement signals?
    - What's the ROI: followers + engagement gain vs. content generation cost?
    """
    
    async def track_post_performance(post_id: str, platform: str) -> dict:
        """
        24-48 saat sonra post'un performance'ını track et:
        - Likes, comments, shares
        - Save rate
        - Click-through rate (if applicable)
        - Sentiment of comments
        - Follower growth
        """
        metrics = await fetch_platform_analytics(platform, post_id)
        
        # Calculate "win score"
        win_score = calculate_engagement_score(metrics)
        
        # Save to consolidated learnings
        await save_to_memory_consolidation({
            'post_id': post_id,
            'platform': platform,
            'content_angle': detect_angle(post_id),
            'engagement_2h': metrics['engagement_2h'],
            'engagement_24h': metrics['engagement_24h'],
            'win_score': win_score,
            'timestamp': datetime.now().isoformat()
        })
        
        return metrics
    
    async def generate_weekly_report(self) -> dict:
        """
        Weekly influencer report:
        - Total posts: X
        - Average engagement: Ye%
        - Top performing content: [angles, formats]
        - Trending with audience: [topics]
        - Next week recommendations: [strategic adjustments]
        """
        pass
```

---

## Reference Account Tracking: 100 Accounts

**Initial List** (Ekrem format'ında sağlayacaksınız):

```json
[
  {
    "username": "mindwired.ai",
    "platform": "instagram",
    "category": "AI news",
    "tracked_since": "2026-04-15"
  },
  {
    "username": "esadcom",
    "platform": "instagram",
    "category": "Turkish entrepreneur",
    "tracked_since": "2026-04-15",
    "notes": "Autonomy + freedom narrative, high engagement"
  },
  // ... 98 more accounts
]
```

**Data Collected per Account**:
- Top 5 posts (last 30 days)
- Posting frequency
- Engagement rate
- Audience demographics (if available)
- Content angles that perform
- Optimal posting times

---

## Daily Workflow

### 08:00 — Research Task

```
/research start
  ├─ Fetch Google Trends
  ├─ Analyze reference accounts
  ├─ Generate 3-5 content ideas
  └─ Notify: "📊 Research complete"
```

### 10:00 — Content Generation

```
/influencer generate-content
  ├─ Instagram: 1-2 carousel posts
  ├─ TikTok: 1 video
  ├─ Twitter: 2-3 tweets
  └─ Review queue: 5-6 pending
```

### 12:30, 18:00, 21:00 — Auto-Posting (x3/day)

```
/influencer publish
  ├─ Schedule Instagram → 13:00 (optimal time)
  ├─ Schedule TikTok → 18:30 (peak hours)
  ├─ Schedule Twitter → 21:00 (evening engagement)
  └─ Notify: "📱 6 posts scheduled today"
```

### 20:00 — Analytics + Next-Day Planning

```
/influencer track-performance
  ├─ Fetch yesterday's post metrics
  ├─ Update win scores
  ├─ Save patterns to memory
  └─ Generate: "Top content: [angle], forecast engagement: 2.3x"
```

---

## Implementation Roadmap

### Phase 1 (này): Research + Content Gen (3-4 weeks)

- [ ] `ai_influencer_research.py` — Daily research scheduler
- [ ] Google Trends API integration
- [ ] Reference account analyzer
- [ ] Content idea generator
- [ ] Mert persona: daily research notifications

### Phase 2: Auto-Posting (2-3 weeks)

- [ ] Instagram API (Graph API auth)
- [ ] TikTok Creator API integration
- [ ] X/Twitter API v2 integration
- [ ] Scheduler + queue management

### Phase 3: Analytics + Learning (1-2 weeks)

- [ ] Performance tracker
- [ ] Memory consolidation integration
- [ ] Weekly reports
- [ ] Iterative improvement loop

### Phase 4: Scale (2-4 weeks)

- [ ] 100 reference accounts tracking
- [ ] Video generation (Remotion / FFmpeg)
- [ ] Multi-language support (en, tr)
- [ ] Subscriber program (pay-per-post)

---

## API Keys Required

```bash
# .env
INSTAGRAM_GRAPH_API_TOKEN=<token>
INSTAGRAM_BUSINESS_ACCOUNT_ID=<id>
TIKTOK_ACCESS_TOKEN=<token>
TIKTOK_CREATOR_ID=<id>
TWITTER_API_KEY=<key>
TWITTER_API_SECRET=<secret>
TWITTER_BEARER_TOKEN=<token>
GOOGLE_TRENDS_API_KEY=<key>
```

---

## Success Metrics

| Metrik | Target (6 month) |
|--------|------------------|
| **Followers** | 50K |
| **Posts / Month** | 180+ (6/day) |
| **Avg Engagement Rate** | 3-5% |
| **Conversion (click-through)** | 2-3% |
| **Community Growth Rate** | 10-15% MoM |

---

## Key Insight: Why This Works

Your earlier research showed:
- **Educator credibility + autonomy narrative = 2.0-2.43x engagement**
- **Direct CTAs + feature lists = 0.01-0.10x (FAIL)**

AI Influencer Mode applies this:
- Public persona = "Türkçe KOBİ'lerin otonom asistanı"
- Content = autonomy stories + real trader solutions + educator partnerships
- Posting = data-driven (not hype)
- Engagement = community + trust → conversion

---

## Timeline: Start This Week

- [ ] Monday: Reference accounts list (100 URLs)
- [ ] Tuesday-Wednesday: Phase 1 implementation (research + content gen)
- [ ] Thursday: Testing + optimization
- [ ] Friday: Deploy + first daily research run

---

## Files to Create

1. `server/services/ai_influencer_research.py` — Daily research
2. `server/services/ai_influencer_content.py` — Content generator
3. `server/services/ai_influencer_poster.py` — Auto-poster
4. `server/services/ai_influencer_analytics.py` — Performance tracking
5. `config/reference_accounts_100.json` — Reference account list
6. `specs/ai_influencer_roadmap.md` — Detailed implementation guide

---

**Status**: ✅ READY FOR REQUIREMENTS

100 reference account'ları gönder, başlayalım.
