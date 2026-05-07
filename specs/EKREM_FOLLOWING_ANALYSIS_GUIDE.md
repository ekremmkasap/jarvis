# Ekrem Following Analysis — 3 Methods

**Tarih**: 2026-04-15  
**Görev**: Ekrem'in takip ettiği 200 AI account'ı analyze et  
**Status**: 3 method ready

---

## Method 1: Automated (Requires instaloader)

**Prerequisite**: instaloader library + Instagram login

```bash
# Install
pip install instaloader

# Run
python /server/services/ekrem_following_analyzer.py

# Or via Bridge:
/ekrem following-analyze
```

**Pros**: Automated, pulls all 200+ accounts, accurate metadata  
**Cons**: Requires login, may hit rate limits  
**Expected time**: 2-5 minutes

---

## Method 2: Manual Copy-Paste (Fastest)

**Steps**:
1. Open Instagram app (or web)
2. Go to Ekrem's profile: @ekremmkasap
3. Tap "Following" (200+ accounts)
4. Scroll to top (or filter by recently followed)
5. Select all visible handles and copy (Ctrl+A, Ctrl+C)
6. Use this command:

```
/ekrem following-analyze-manual @handle1,@handle2,@handle3,...

Or DM Jarvis with the list and I'll parse it
```

**Pros**: Instant, no login needed  
**Cons**: Manual, need to copy-paste from app  
**Expected time**: 5-10 minutes

---

## Method 3: Instagram Export (Business Account)

**Prerequisites**: Instagram business/creator account + Graph API access

```bash
# Get access token from Meta Developers
# Request: GET /me/following?fields=username,profile_picture_url,biography

curl -X GET "https://graph.instagram.com/me/following?access_token=YOUR_ACCESS_TOKEN"

# Save response to JSON
# Run analyzer on JSON
```

**Pros**: Structured data, accurate  
**Cons**: Requires business account setup  
**Expected time**: 10-15 minutes (one-time setup)

---

## Quick Analysis: Ekrem's Following Patterns

**If Ekrem provides handles**, analyzer will:

✅ **Categorize** accounts into:
- AI-focused (score ≥ 5)
- AI-adjacent (score 2-4)
- Non-AI (score < 2)

✅ **Cluster by purpose**:
- Educators (tutorials, guides)
- Builders (products, tools)
- Researchers (analysis, papers)
- Entrepreneurs (startups, growth)
- Influencers (news, trending)

✅ **Extract insights**:
- Top 20 AI accounts Ekrem follows
- Keyword distribution
- Follower count patterns
- Verification status

✅ **Generate recommendations for Jarvis**:
- Model content after top educators
- Monetization signals (entrepreneur count)
- Collaboration candidates

---

## Expected Output

```json
{
  "analyzed_date": "2026-04-15T...",
  "total_following": 200,
  "summary": {
    "ai_focused_count": 85,
    "ai_percentage": "42.5%",
    "top_topic": "claude"
  },
  "top_20_ai_accounts": [
    {
      "rank": 1,
      "handle": "leadgenman",
      "followers": "22000",
      "ai_score": 8,
      "keywords": "claude, code, automation"
    },
    ...
  ],
  "clusters": {
    "educators": { "count": 32, "top_accounts": [...] },
    "builders": { "count": 28, "top_accounts": [...] },
    "researchers": { "count": 12, "top_accounts": [...] },
    "entrepreneurs": { "count": 8, "top_accounts": [...] },
    "influencers": { "count": 5, "top_accounts": [...] }
  },
  "insights": [
    "Ekrem takip ettiği 85 AI account (%42.5 yoğunluk)",
    "Top cluster: educators (32 account)",
    "Ekrem'in strategy: Mix of educators, builders, researchers",
    "Avg followers (AI accounts): 5,234"
  ],
  "recommendations_for_jarvis": [
    "Model content after top 10 AI educators: @leadgenman, @alexlindai, ...",
    "Monetization insight: 8 entrepreneurs = market demand signal",
    "Collaboration candidates: 28 builders + 12 researchers"
  ]
}
```

---

## Next Step: Send to Codex

**After getting 200 account list:**

```
/instagram analyze-profiles <ekrem's top 50 AI accounts from following>
```

This will:
1. Scrape bios + engagement
2. Compare with general market
3. Generate Jarvis-specific recommendations

---

## Ekrem's Action Required

**Choose one:**

1. **Fastest**: Provide handles via copy-paste (5 min manual work)
   ```
   /ekrem following-analyze-manual @leadgenman,@alexlindai,@ohmo.ai,...
   ```

2. **Automated**: Enable instaloader + login (2-5 min)
   ```
   /ekrem following-analyze
   ```

3. **Batch**: Combine both methods
   - Part 1: Manual top 50
   - Part 2: Automated full 200
   - Then Codex analyze both sets

**Recommendation**: **Start with Method 1** (Instaloader) → Fallback to Method 2 (manual) if it fails.

---

**Kanka, hangisini yapıyalım? 🚀**
