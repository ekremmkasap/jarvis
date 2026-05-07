# Codex Integration Guide — Jarvis Instagram Automation

**Tarih**: 2026-04-15  
**Target**: Codex agent assignments (forge, nexus, spark)  
**Workflow**: Prompt → Codex skill development → Local skill integration → Daily orchestration

---

## Reference Profile: @tenfoldmarc

**Saved Analysis**:
```
Platform: Instagram (@tenfoldmarc)
Bio: "Claude Code builds"
Content: Educational carousels + reels (7 Claude Code skills breakdown)
Cadence: 1-2 reels/day + 3 carousel/week
CTA: "Comment SKILLS for install links"
Engagement: 600-1.1K per post
Monetization: Community (Skool), affiliate
Growth: 22K followers (30 days claimed)

Key insight: Educational + Behind-the-scenes + Community CTA = 2+ engagement multiplier
```

---

## Codex Agent Assignments

### Assignment 1: Codex "forge" (Seda) — Research + Orchestration

**Prompt to Codex**:
```
Task: Build Instagram Daily Research + Skill Development Orchestrator

Context:
- Jarvis AI Instagram account (@jarvis_ai_tr)
- Daily 00:00 UTC trigger
- Input: Empty (daily auto-trigger)
- Output: research_items.json (top 5 trending AI/Claude topics)

Research sources to scrape:
1. GitHub trending (language: Python, topic: AI)
2. Reddit r/claude (top posts, last 24h)
3. Twitter trending (#claude, #claudecode, #ai)
4. Hacker News (search: Claude)

For each item, extract:
- Title
- Source URL
- Why it's trending (votes/engagement)
- Hook for Instagram ("Someone just built...", "Claude now supports...", etc.)

Output structure:
{
  "research_items": [
    {
      "title": "str",
      "source": "str",
      "url": "str",
      "hook": "str",
      "why_trending": "str",
      "engagement_potential": "high|medium|low"
    }
  ],
  "timestamp": "2026-04-15T00:00:00Z",
  "recommended_top_pick": "index"
}

Return a production-ready skill at /skills/instagram_research_daily_skill.py
Use async/await throughout.
Integrate with APScheduler (trigger at daily 00:00 UTC).
Log all scrapes to state/instagram_research.jsonl.
```

**Codex Output Expected**:
```python
# /skills/instagram_research_daily_skill.py
class InstagramDailyResearchSkill:
    async def research_daily(self) -> dict:
        # Scrape GitHub trending
        # Scrape Reddit
        # Scrape Twitter
        # Scrape Hacker News
        # Rank by engagement potential
        # Return research_items.json
```

---

### Assignment 2: Codex "nexus" (Mert) — Content Outline + Video Prompt

**Prompt to Codex**:
```
Task: Build Instagram Content Themer + Video Prompt Generator

Context:
- Input: research_items.json (from forge/Seda)
- Output: content_outline.md + video_prompt.txt (for Kling 3.0)
- Model: @tenfoldmarc (educational + behind-the-scenes)

Content generation flow:
1. Take top research item
2. Extract key insight (1-2 sentences)
3. Break into 5-7 teaching points
4. Add actionable takeaway
5. Generate Instagram caption (150-200 chars)
6. Generate video prompt (for Kling 3.0 generation)

Video prompt style guide:
- Format: "[Scene description]. [Character/elements]. [Animation]. [Text overlay]"
- Duration: 30-60 seconds
- Example: "Split screen showing before/after. Left: manual process (frustrated developer). Right: automated process (celebrating developer). Text overlay: AI accelerates developer efficiency 10x. Trending tech background."

Output structure:
{
  "research_item": {...},
  "content_outline": {
    "headline": "str",
    "key_points": ["str", ...],
    "takeaway": "str"
  },
  "instagram_caption": "str (with emojis + hashtags)",
  "video_prompt": "str (for Kling 3.0)",
  "cta": "Comment [KEYWORD] for [offer]"
}

Return production-ready skill at /skills/instagram_content_themer.py
Handle edge cases (empty research, malformed input, etc.).
```

**Codex Output Expected**:
```python
# /skills/instagram_content_themer.py
class InstagramContentThemer:
    async def generate_content_outline(self, research_item: dict) -> dict:
        # Extract headline
        # Generate 5-7 teaching points
        # Create instagram caption (emoji, hashtags)
        # Generate Kling 3.0 video prompt
        # Return structured output
```

---

### Assignment 3: Codex "spark" (Eren) — Auto Caption + CTA Generator

**Prompt to Codex**:
```
Task: Build Instagram Caption Generator + CTA Pipeline

Context:
- Input: content_outline.md + video_url (from nexus/Mert)
- Output: instagram_caption.txt (ready to post)
- Model: High engagement CTAs (@tenfoldmarc pattern)

Caption generation flow:
1. Read content outline
2. Add emoji to each key point
3. Craft story hook (3-5 sentences max)
4. Add call-to-action (Comment X for Y)
5. Add relevant hashtags (#claude #ai #tutorial #automation)
6. Brand it with Jarvis voice (Türkçe + educational + autonomy narrative)

CTA patterns (test multiple):
- "Comment RESEARCH for full breakdown 👇"
- "Comment TOOLS for complete list 🔗"
- "Şu skill'i kullan et! Ama önce comment SKILLS 👀"
- "Bunu internalize et, sonra comment DEEP for advanced"

Engagement optimization:
- First line: Hook (why should they care)
- Middle: Value (what they'll learn)
- CTA: Specific action (comment + keyword)
- Hashtags: 8-12 relevant tags

Output structure:
{
  "caption": "str (300-500 chars)",
  "visual_description": "str",
  "estimated_engagement": "low|medium|high",
  "cta_keyword": "str",
  "suggested_posting_time": "str (HH:MM UTC)"
}

Return production-ready skill at /skills/instagram_caption_generator.py
Include optimization for emoji placement and hashtag ordering.
```

**Codex Output Expected**:
```python
# /skills/instagram_caption_generator.py
class InstagramCaptionGenerator:
    async def generate_caption(self, outline: dict, video_url: str) -> dict:
        # Generate engaging caption
        # Add emojis + hashtags
        # Create CTA
        # Estimate engagement potential
        # Return structured caption
```

---

### Assignment 4: Jarvis Local — Video Generation (Kling 3.0)

**Why local (not Codex)**:
- Kling API integration stable (documented)
- Video generation = wait time 5-10 minutes
- Async pattern already proven in hey_jarvis.py TTSing

**Implementation**:
```python
# /server/services/kling_video_generator.py

class KlingVideoGenerator:
    def __init__(self, api_key: str):
        self.api_key = os.environ.get("KLING_API_KEY")
        self.api_url = "https://api.klingai.com/v1/videos/text2video"
    
    async def generate_instagram_video(self, prompt: str, duration: int = 30) -> str:
        """
        Input: video_prompt from Codex (nexus/Mert)
        Output: video_url (MP4 ready for Instagram)
        """
        
        payload = {
            "model": "kling-v1",
            "prompt": prompt,
            "duration": duration,
            "size": "1080x1920",  # Instagram vertical
            "quality": "high"
        }
        
        # Submit job
        response = await self.http_client.post(
            self.api_url,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        task_id = response.json()['task_id']
        
        # Poll for completion (async)
        while True:
            status = await self.check_status(task_id)
            if status['state'] == 'COMPLETED':
                return status['video_url']
            elif status['state'] == 'FAILED':
                raise Exception(f"Video generation failed: {status['error']}")
            
            await asyncio.sleep(5)  # Poll every 5s
```

---

## Orchestration: Daily Automation Flow

**Master trigger** (in `master_launcher.py` or `bridge.py`):

```python
# APScheduler setup
scheduler = AsyncIOScheduler()

# 00:00 UTC: Daily research
@scheduler.scheduled_job('cron', hour=0, minute=0)
async def daily_instagram_automation():
    try:
        # Step 1: Research (Codex forge/Seda)
        research_skill = await load_skill('instagram_research_daily_skill')
        research_items = await research_skill.research_daily()
        
        # Step 2: Select top item + generate outline (Codex nexus/Mert)
        themer_skill = await load_skill('instagram_content_themer')
        outline = await themer_skill.generate_content_outline(
            research_items[0]
        )
        
        # Step 3: Generate video (Local Kling)
        kling = KlingVideoGenerator()
        video_url = await kling.generate_instagram_video(outline['video_prompt'])
        
        # Step 4: Generate caption (Codex spark/Eren)
        caption_skill = await load_skill('instagram_caption_generator')
        caption_data = await caption_skill.generate_caption(outline, video_url)
        
        # Step 5: Schedule post (15:00 UTC for EU/TR timezone optimal)
        await schedule_instagram_post(
            video_url=video_url,
            caption=caption_data['caption'],
            cta_keyword=caption_data['cta_keyword'],
            publish_time="15:00"
        )
        
        # Step 6: Track for monitoring
        await tracking_db.log_daily_automation({
            'research_items_count': len(research_items),
            'top_pick': outline['headline'],
            'video_url': video_url,
            'caption_keyword': caption_data['cta_keyword'],
            'scheduled_time': '15:00 UTC'
        })
        
        logger.info("✓ Daily Instagram automation completed")
    
    except Exception as e:
        logger.error(f"Daily automation failed: {e}")
        await send_telegram_alert(f"Instagram automation error: {str(e)[:200]}")

scheduler.start()
```

---

## Setup: Ekrem Provides Codex Agent Access

**Prerequisites**:
1. Codex account with 3+ slots available
2. Agents assigned: `forge`, `nexus`, `spark`
3. Kling API key (video generation)
4. Instagram business account + API credentials

**Step 1: Assign Codex Agents**

```bash
# Terminal: Configure Codex slots for Instagram

codex config set-agent forge instagram_research
codex config set-agent nexus instagram_themer
codex config set-agent spark instagram_caption

# Verify
codex config list-agents
# Output:
# forge: instagram_reserarch
# nexus: instagram_themer
# spark: instagram_caption
```

**Step 2: Initialize Jarvis Integration**

```bash
# Bridge command
curl -X POST http://localhost:8081/instagram/auto-post-setup \
  -H "Content-Type: application/json" \
  -d '{
    "account_handle": "@jarvis_ai_tr",
    "codex_slots": ["forge", "nexus", "spark"],
    "depth_tier": "medium",
    "daily_trigger": "00:00 UTC"
  }'

# Response:
# {
#   "status": "ready",
#   "instagram_account": "@jarvis_ai_tr",
#   "codex_agents": ["forge/seda", "nexus/mert", "spark/eren"],
#   "first_automation": "2026-04-16T00:00:00Z"
# }
```

**Step 3: Test (Day 1)**

```
Manual trigger to test:
  /instagram auto-post-test

Output:
  ✓ Research fetched: 5 items
  ✓ Top pick: "Claude Code now supports MCP"
  ✓ Content outline generated
  ✓ Video prompt: "Split screen demo..."
  ✓ Video queued (Kling task_id: xyz)
  ✓ Caption generated: "Someone just..."
  ✓ Post scheduled for 15:00 UTC

Review output → approve → go live
```

**Step 4: Monitor (Week 1)**

```
Daily check:
  /instagram analytics

Output:
  Post 1: 234 likes, 45 comments (avg 1.2% engagement)
  Top comment: "Comment RESEARCH" (32 responses)
  Leading: Comment rate vs likes (engagement quality)

Adjustment:
  - If engagement high: Keep cadence
  - If engagement low: Adjust video style / CTA wording
  - If comments low: A/B test different CTAs
```

---

## Codex Prompt Templates (Copy-Paste)

### Prompt 1: Research Skill (for forge/Seda)
```
Task: Build Instagram Daily Research Skill

Build a Python async skill for Jarvis AI Instagram automation.

Daily trigger: 00:00 UTC
Input: None (auto-trigger)
Output: JSON with top 5 trending AI/Claude topics

Scrape:
1. GitHub trending (Python + AI)
2. Reddit r/claude (top 24h posts)
3. Twitter (#claude #ai #claudecode)
4. Hacker News search "Claude"

For each result extract:
- title, url, source, engagement_level, hook_for_instagram

Return skill file: /skills/instagram_research_daily_skill.py
Use async/await.
Log to state/instagram_research.jsonl.

Personality: Professional researcher, captures "why this matters" for Instagram.
```

### Prompt 2: Content Themer (for nexus/Mert)
```
Task: Build Instagram Content Outline Generator

Build a Python async skill for Jarvis AI Instagram automation.

Input: research_item (dict with title, url, why_trending)
Output: content_outline with headline + 5 teaching points + video_prompt

Research Model: @tenfoldmarc (educational, behind-the-scenes, practical tips)

For video prompt:
- Format: "[Scene]. [Elements]. [Text overlay]"
- Duration: 30-60 seconds
- Include: Before/after, trending context, actionable takeaway

Return skill file: /skills/instagram_content_themer.py
Use async/await.

Personality: Creative content strategist, turns research into engaging Instagram ideas.
```

### Prompt 3: Caption Generator (for spark/Eren)
```
Task: Build Instagram Caption Generator

Build a Python async skill for Jarvis AI Instagram automation.

Input: content_outline (dict with headline + teaching points) + video_url
Output: Instagram-ready caption (250-400 chars) + CTA + hashtags + engagement_estimate

Caption style: @tenfoldmarc (educational focus, Türkçe+English mix, community-driven)

CTA patterns to test:
- "Comment RESEARCH for full breakdown 👇"
- "Bunu internalize et, sonra comment for deeper insights 🔗"
- "Sizce hangisi daha useful? Comment your favorite! 🎯"

Add 8-12 relevant hashtags.
Estimate engagement potential (low/medium/high).

Return skill file: /skills/instagram_caption_generator.py
Use async/await.

Personality: Community builder, writes CTAs that drive engagement + lead capture.
```

---

## Success Metrics (After 1 week)

| Metric | Target | Signal |
|--------|--------|--------|
| **Posts scheduled** | 7 | Automation is working |
| **Avg engagement** | 0.5-1.0% | On par with cold start |
| **Comment rate** | 5-10% of likes | CTA is resonating |
| **Lead captures** | 5-10 | Telegram link clicks from DMs |

---

## Next: Ekrem Provides Codex Access

Ready to:
1. Send Codex prompts to agents (forge, nexus, spark)
2. Wait 2-3 days for skill development
3. Test local integration
4. Launch daily automation (00:00 UTC trigger)

Ekrem'in Codex slot'ları hazır mı?
