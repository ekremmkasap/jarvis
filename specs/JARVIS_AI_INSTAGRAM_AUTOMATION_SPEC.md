# Jarvis AI Instagram Account — Full Automation Spec

**Tarih**: 2026-04-15  
**Model**: @tenfoldmarc (7 Claude Code skills breakdown - daily educational content)  
**Scope**: Research → Video Generate → Auto-post → Lead capture → Telegram  
**Complexity**: Medium (3-4 weeks implementation) → Deep (6-8 weeks with full Codex)

---

## Reference: @tenfoldmarc Content Strategy

**Content Format**:
```
Post type: Educational carousel (5-8 slides) + video reel
Cadence: 1-2 reels/day + 3 carousel/week
Topic: Claude Code skills breakdown, AI tips, tutorials
CTA: "Comment SKILLS for links" (lead magnet)
Monetization: Community (Skool/paid course), affiliate links (services)
Engagement: 600-1.1K per post
Growth: 0-22K followers in 30 days (claimed)
```

**Content Flow**:
```
1. Research → "7 Claude Code skills that..."
2. Screenshot/design → "Here's skill #1: /spy"
3. Record short video → "This is how /spy works"
4. Post + CTA → "Comment SKILLS for links"
5. DM follow-up → Monetization funnel
```

---

## Architecture: Jarvis AI Instagram Account

### Tier 1: Research + Content Discovery (Light — 1-2 weeks)

**Components**:
```
Daily Trigger (00:00 UTC):
  ├─ ResearchCollector (Codex-powered)
  │  ├─ Scrape: GitHub trending, Reddit r/claude, X trending #claude
  │  ├─ Parse: AI news, new tools, Claude Code features
  │  └─ Output: 5-10 research items (JSON)
  │
  ├─ ContentThemer
  │  ├─ Select top research item
  │  ├─ Generate hook ("Someone just built X with Claude...")
  │  ├─ Outline 5 key points
  │  └─ Output: Content outline (markdown)
  │
  └─ Poster (Manual, 12:00 UTC)
     ├─ Instagram: Post outline (text-only carousel)
     └─ CTA: "Comment RESEARCH for full guide"
```

**File**: `server/services/instagram_research_daily_skill.py`

```python
class DailyInstagramResearchSkill:
    """
    Daily: Research → Hook → Content outline → Post
    Light tier: Text posts only (manual formatting)
    """
    
    async def research_daily(self):
        """
        Daily 00:00 trigger
        """
        # Step 1: Collect research
        research_items = await self.codex_research_collector.fetch_trending(
            sources=[
                "github_trending",
                "reddit:r/claude",
                "twitter:trending #claude",
                "hacker_news"
            ],
            filters=["AI", "Claude", "Automation"],
            limit=10
        )
        
        # Step 2: Rank by engagement potential
        ranked = await self.engagement_ranker.rank_for_instagram(research_items)
        top_item = ranked[0]
        
        # Step 3: Generate hook + outline
        content = {
            "hook": f"Someone just {top_item['action']} with {top_item['tool']}",
            "source": top_item['source'],
            "key_points": await self.content_generator.extract_key_points(top_item),
            "cta": "Comment RESEARCH for full breakdown"
        }
        
        return content
```

---

### Tier 2: Video Generation + Auto-posting (Medium — 3-4 weeks)

**New Components**:
```
Research → Video Generate (Kling 3.0):
  ├─ Input: Research outline
  ├─ Prompt engineering: "Claude Code skill demo video, 30 sec"
  ├─ Model: Kling 3.0 (high quality, Claude Code integration)
  ├─ Output: MP4 (ready for Instagram Reel)
  │
  → Instagram Auto-poster:
     ├─ Video upload (with caption)
     ├─ Optimal time posting (analyze follower timezone)
     └─ CTA carousel comment (auto-reply bot)
```

**Codex Integration**:
```python
class InstagramVideoAutomationSkill:
    """
    Research → Kling video → Instagram post → Lead capture
    """
    
    async def generate_and_post_daily_reel(self, research_item: dict):
        """
        Medium tier: Full automation
        """
        
        # Step 1: Generate video prompt
        video_prompt = await self.prompt_engineer.generate_video_prompt(
            topic=research_item['topic'],
            format="educational_demo",  # Split screen, annotations, etc.
            duration=30,  # seconds
            style="claude_code_tutorial"
        )
        
        # Step 2: Call Codex for Kling 3.0 video generation
        video_result = await self.codex_client.submit_task(
            task_type="kling/text-to-video",
            params={
                "prompt": video_prompt,
                "duration": 30,
                "quality": "high",
                "style_preset": "technical_tutorial"
            },
            webhook_url=f"{BRIDGE_URL}/instagram/video-ready"  # Callback when done
        )
        
        # Step 3: Wait for video (or poll with callback)
        video_url = await self.wait_for_video(video_result['task_id'])
        
        # Step 4: Generate caption + CTA
        caption = await self.caption_generator.generate_instagram_caption(
            research_item=research_item,
            video_description=video_prompt,
            include_hashtags=True,
            include_cta=True
        )
        
        # Step 5: Upload to Instagram (API or manual queue)
        post = await self.instagram_api.upload_reel(
            video_url=video_url,
            caption=caption,
            publish_time="optimal"  # Based on audience timezone
        )
        
        # Step 6: Log + Track
        await self.tracking_db.log_instagram_post(
            post_id=post['id'],
            video_url=video_url,
            caption=caption,
            research_item=research_item
        )
        
        return post
```

---

### Tier 3: Full Codex Orchestration + Lead Capture (Deep — 6-8 weeks)

**Complete System**:
```
┌─────────────────────────────────────────────────────────┐
│ Jarvis AI Instagram Autonomous System                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Daily Trigger (00:00 UTC)                              │
│  ├─ Codex Task 1: DailyResearchCollector               │
│  │  └─ Output: research_items.json                     │
│  │                                                     │
│  ├─ Codex Task 2: ContentThemer                        │
│  │  └─ Input: research_items.json                      │
│  │  └─ Output: content_outline.md + video_prompt.txt   │
│  │                                                     │
│  ├─ Codex Task 3: VideoGenerator (Kling 3.0)           │
│  │  └─ Input: video_prompt.txt                         │
│  │  └─ Output: reel.mp4 (30-60 sec)                    │
│  │                                                     │
│  ├─ Codex Task 4: CaptionGenerator                     │
│  │  └─ Input: content_outline.md                       │
│  │  └─ Output: caption.txt (with emojis + CTA + tags)  │
│  │                                                     │
│  └─ Codex Task 5: InstagramPoster                      │
│     ├─ Input: reel.mp4 + caption.txt                   │
│     ├─ Publish time: Optimal (15:00 UTC for EU/TR)     │
│     └─ Output: post_id (for tracking)                  │
│                                                         │
│ Engagement Tracking (Real-time, 6h loop)              │
│  ├─ Monitor likes, comments, shares                    │
│  ├─ Extract user comments ("Comment RESEARCH for...")  │
│  └─ Auto-reply with Telegram link                      │
│                                                         │
│ Lead Capture Pipeline                                  │
│  ├─ Instagram comment → DM bot message                 │
│  ├─ DM: "✨ Telegram'a gelsene devam edelim..."       │
│  ├─ Listen: DM clicks → Telegram bot                   │
│  └─ CRM: Track lead → Sales follow-up                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Implementation**:
```python
class JarvisInstagramFullAutomation:
    """
    Complete autonomous AI Instagram account
    Codex-powered research → video → posting → lead capture
    """
    
    def __init__(self, instagram_account: str, codex_slots: int = 3):
        self.instagram_account = instagram_account  # @jarvis_ai or simil
        self.codex_slots = codex_slots  # Use 3 out of 5 Codex slots
        self.posting_schedule = {
            "research_reels": "daily",  # 1 reel/day
            "case_study_carousel": "2x/week",  # Tuesday, Friday
            "behind_scenes": "3x/week",  # Mon, Wed, Thu
            "philosophy_thought": "1x/week"  # Saturday (high engagement)
        }
    
    async def orchestrate_daily_cycle(self):
        """
        Full daily automation loop via Codex
        """
        
        # 00:00 UTC: Start research
        research_items = await self.codex_submit_task(
            skill="instagram_research_daily_skill",
            action="research_daily",
            params={}
        )
        
        # 08:00 UTC: Process top 5 items in parallel (Codex slots 1-3 + Jarvis local processing)
        tasks = []
        for i, item in enumerate(research_items[:3]):
            content_task = await self.codex_submit_task(
                skill="instagram_content_themer",
                action="generate_content_outline",
                params={"research_item": item}
            )
            tasks.append(("content", content_task['task_id']))
        
        # 10:00 UTC: Generate videos (Kling 3.0)
        for i, (_, task_id) in enumerate(tasks):
            content_outline = await self.codex_get_result(task_id)
            
            video_task = await self.codex_submit_task(
                skill="kling_video_generator",
                action="generate_video",
                params={
                    "prompt": content_outline['video_prompt'],
                    "format": "instagram_reel",
                    "duration": 30
                }
            )
            
            tasks[i] = ("video", video_task['task_id'])
        
        # 14:00 UTC: Collect videos + generate captions
        for i, (_, task_id) in enumerate(tasks):
            video_url = await self.codex_get_result(task_id)
            content_outline = await self.local_cache.get(f"outline_{i}")
            
            caption_task = await self.codex_submit_task(
                skill="instagram_caption_generator",
                action="generate_caption",
                params={
                    "outline": content_outline,
                    "video_url": video_url,
                    "include_cta": True
                }
            )
            
            tasks[i] = ("caption", caption_task['task_id'])
        
        # 15:00 UTC: Post to Instagram
        for day_of_week, (_, task_id) in enumerate(tasks):
            caption = await self.codex_get_result(task_id)
            
            post_task = await self.codex_submit_task(
                skill="instagram_auto_poster",
                action="post_reel",
                params={
                    "video_url": video_url,
                    "caption": caption,
                    "publish_time": "optimal"
                }
            )
            
            await self.tracking_db.log_scheduled_post(post_task['task_id'])
        
        # 16:00 UTC → 24h: Monitor engagement + capture leads
        while True:
            engagement_data = await self.instagram_api.get_recent_posts_analytics()
            
            for post in engagement_data:
                # Extract comments with CTA
                comments = await self.instagram_api.get_post_comments(post['id'])
                
                for comment in comments:
                    if "RESEARCH" in comment['text'] or "SKILLS" in comment['text']:
                        # Trigger lead capture
                        await self.lead_capture_pipeline.process_comment(
                            comment=comment,
                            post_id=post['id'],
                            instagram_account=self.instagram_account
                        )
            
            # Sleep 6 hours
            await asyncio.sleep(6 * 3600)
```

---

## Codex Integration: 5 Codex Slots Usage

**Current Jarvis Codex Setup**:
- Slot 1: `forge` — Seda (Code implementation)
- Slot 2: `nexus` — Mert (Research)
- Slot 3: `spark` — Eren (Content)
- Slot 4: `atlas` — Sabri (Strategy)
- Slot 5: `shield` — Luna (Security, unused for now)

**For Instagram Automation, Reassign**:
- Slot 1 (`forge`): Instagram automation orchestrator
- Slot 2 (`nexus`): Research collector daily
- Slot 3 (`spark`): Video prompt + caption generator
- (Slot 4-5): Keep for persona work)

**Codex Communication**:
```
Bridge.py → Codex CLI:
  codex "develop" --agent forge --prompt "Script daily research collector"
  codex "develop" --agent nexus --prompt "Implement Kling 3.0 video generator"
  codex "develop" --agent spark --prompt "Build Instagram caption + CTA pipeline"
  
Results:
  ├─ Codex Task 1: /skills/instagram_research_daily_skill.py
  ├─ Codex Task 2: /skills/kling_video_generator.py
  ├─ Codex Task 3: /skills/instagram_caption_generator.py
  └─ Codex Task 4: /skills/instagram_auto_poster.py
```

---

## Implementation Depth Comparison

| Parameter | Light (1-2w) | Medium (3-4w) | Deep (6-8w) |
|-----------|--------------|---------------|------------|
| **Daily posts** | Text only | 1 reel + 2 posts | 2 reels + 3 posts |
| **Video generation** | Manual (Kling) | Codex + Kling | Codex + Kling + style variation |
| **Lead capture** | Manual DM | Instagram CTA → Telegram | Full pipeline + CRM |
| **Codex involvement** | 0 slots | 1 slot (research) | 3 slots (research, video, posting) |
| **Expected folower/week** | 50-100 | 200-400 | 500-1000+ |
| **Expected MRR** | ₺0 (awareness) | ₺5K-10K | ₺20K-50K |

---

## Files to Create / Modify

### New Skills (Codex-generated):
1. `server/services/instagram_research_daily_skill.py`
   - Research trending AI/Claude topics
   - Generate daily content ideas

2. `server/services/instagram_content_themer.py`
   - Convert research → content outline
   - Generate video prompts

3. `server/services/kling_video_generator.py`
   - Call Kling 3.0 API
   - Generate 30-60 sec educational videos

4. `server/services/instagram_caption_generator.py`
   - Auto-generate captions (emojis + CTA + hashtags)
   - Brand voice consistency

5. `server/services/instagram_auto_poster.py`
   - Schedule posts via Instagram API
   - Track post IDs for monitoring

6. `server/services/instagram_lead_capture.py`
   - Monitor comments
   - DM auto-replies
   - Telegram link integration

### Modified:
- `bridge.py`: Add `/instagram auto-post-setup` command
- `master_launcher.py`: Register daily 00:00 UTC trigger

---

## Setup: Ekrem's Account Creation

**Step 1**: Create Instagram account
```
Handle: @jarvis_ai_tr (or @jarvisai_official)
Bio: "Otomatik araştırma. AI news. Claude Code tutorials. Türkçe + English"
Profile pic: Jarvis hologram avatar
```

**Step 2**: Connect to Jarvis backend
```
Environment variables:
  INSTAGRAM_USERNAME=<handle>
  INSTAGRAM_PASSWORD=<app-specific-password>
  INSTAGRAM_BUSINESS_ACCOUNT_ID=<meta-graph-id>
  KLING_API_KEY=<kling-api-key>  # For video generation
  CODEX_AGENT_slots=["forge", "nexus", "spark"]
```

**Step 3**: Initialize automation
```
Bridge command:
  /instagram auto-post-setup medium
  
Bridge creates:
  - Daily 00:00 UTC trigger
  - Codex agent assignments (3 slots)
  - Instagram API authentication
  - Telegram lead capture webhook
```

**Step 4**: Monitor (first 3 days manual)
```
Day 1-3: Review auto-generated content before posting
Day 4+: Full automation (no manual review)
```

---

## Expected Results (3-Month Projection)

| Metric | Light | Medium | Deep |
|--------|-------|--------|------|
| **Followers** | 200-500 | 2K-5K | 10K-25K |
| **Avg engagement** | 50-100 | 200-500 | 800-1.5K |
| **Lead captures** | 10-20 | 50-100 | 200-500 |
| **MRR** | ₺0 | ₺5K-10K | ₺20K-50K |
| **Content pieces** | 90 | 180+ | 300+ |

---

## Risk Assessment

**Low Risk**:
- Research automation (already proven with daily summaries)
- Text posting (already doing)

**Medium Risk**:
- Video generation (Kling integration new, but stable API)
- Instagram API authentication (Meta business account required)

**High Risk**:
- Account suspension (if too aggressive with CTAs — mitigate with human review Day 1-3)
- Lead quality (raw Instagram comments may not convert)

**Mitigation**:
- Start Medium tier (3-4 weeks)
- Monitor daily engagement/comments
- Adjust CTA frequency based on response rate
- Keep human in loop for caption review (Week 1-2)

---

## Ekrem's Next Step

**Choose your depth**:
1. **Light**: Text-only daily posts (minimal Codex)
2. **Medium**: 1 reel/day + CTAs ( recommended starting point)
3. **Deep**: Full 24/7 automation + lead capture (3-month commitment)

Recommend: **Start Medium (3-4 weeks)** → Prove model → Upgrade to Deep (6-8 weeks)

Başlıyalım mı?
