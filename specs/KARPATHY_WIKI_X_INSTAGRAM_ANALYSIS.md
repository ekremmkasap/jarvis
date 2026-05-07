# Karpathy LLM Wiki × Instagram Lead Generation — Comparative Analysis

**Tarih**: 15.04.2026 / 08:45  
**Context**: Ekrem'in isteği — "karpathy-llm-wiki-rehberi işstersen kankam bunuda incele"  
**Amaç**: İki sistem arasında parallel patterns bulup, Jarvis'e uygulanacak learning'ler çıkarmak

---

## 📊 Sistem Karşılaştırması

### **Giriş Tablosu**
| Boyut | Karpathy LLM Wiki | Instagram Lead Gen |
|-------|------------------|-------------------|
| **Input** | Raw unstructured data (PDF, video, articles) | Raw followers (public profiles) |
| **Processing** | Claude LLM organize | Rules-based filter (keywords, count) |
| **Storage** | Markdown files (~500 char/page avg) | Structured Excel (19 columns) |
| **Output** | Interconnected wiki pages (graph) | Segmented leads (qualification tiers) |
| **Scaling** | More docs → broader knowledge | More accounts → more leads |
| **Maintenance** | hot.md refresh (daily summary) | progress.json dedup (no re-scrape) |

---

## 🔄 Parallel Processing Patterns

### **Pattern 1: Layered Input Architecture**

#### **Karpathy Wiki**
```
raw/
├── makale.md         (article #1)
├── video_transcript/ (YouTube #1-N)
├── notes/            (personal notes)
└── competitor/       (external research)

↓ [Claude processes]

wiki/
├── [topic_1].md      (organized page)
├── [topic_2].md      (linked concepts)
└── [relationship].md (concept A ← → B)
```

#### **Instagram Lead Gen**
```
seeds.txt
├── @rootaccount_1
├── @rootaccount_2
└── @rootaccount_N

↓ [instagrapi scrapes]

results.csv
├── profile_id | username | followers | bio | email (19 cols)
├── [lead_1]   (50K+ tier)
├── [lead_2]   (5K-50K tier)
└── [lead_N]   (low-tier or no email)
```

**INSIGHT**: Both start with **raw seed data** (docs for wiki, accounts for IG) → progressively filter/organize

---

### **Pattern 2: Quality Gating (Filtering Rules)**

#### **Karpathy Wiki Filter**
- ✅ Include: Information appears 2+ sources (consensus)
- ❌ Exclude: Outdated info (>6 months old)
- ⚠️ Flag: Contradictions (needs resolution)

#### **Instagram Lead Gen Filter**
- ✅ Include: `followers > min_followers` AND `bio keyword match` AND `public`
- ❌ Exclude: Private accounts
- ⚠️ Flag: Email not found (lower tier)

**INSIGHT**: Both use **multi-condition gates** (must pass ALL to qualify)

---

### **Pattern 3: Segmentation & Tiering**

#### **Karpathy Wiki Output**
```
wiki/hot.md (500 words) ← Fast summary
wiki/index.md (links)   ← Navigation
wiki/[topic].md (detail) ← Full research
wiki/log.md (history)   ← Trail
```

#### **Instagram Lead Gen Output**
```
FA Leads Email.xlsx
├── EXPORT (ready to send) ← Hottest leads
├── DATA (50K+)            ← High authority
├── Data10-70K (5K-50K)    ← Mid tier
```

**INSIGHT**: Both **tier outputs** (hottest first, detail available deeper)

---

## 🎯 Integration Opportunities for Jarvis

### **Opportunity 1: Wiki-Based Lead Knowledge Base**

**Current state**: Instagram scraper outputs `results.csv` → leads lost in Excel

**Proposed**: 
```
leads-wiki/
├── raw/
│   └── instagram_scrape_2026_04_15.csv
│   
└── wiki/
    ├── [lead_id_001].md
    │   - Name: John Doe
    │   - IG: @johndoe
    │   - Bio keywords: coaching, fitness
    │   - Followers: 12,000
    │   - Email: john@gmail.com
    │   - Related: [[lead_id_002]], [[competitor_xyz]]
    │
    ├── [niche_fitness].md
    │   - Leads in this niche: [link], [link], [link]
    │   - Common email providers: gmail (60%), yahoo (20%)
    │   - Peak engagement hours: 7-9 AM
    │
    ├── index.md
    │   - Total leads: 1,423
    │   - By niche: [fitnessleads] [coachleads] [agencyeleads]
    │   - By tier: [highauth] [research] [lowauth]
    │
    └── hot.md
        - THIS WEEK: 47 new leads scraped
        - Top country: Turkey (%68)
        - Top niche: Fitness coaching (%34)
        - Email success rate: %72
```

**Benefit**: Leads become **discoverable & contextualized** (not just a row in Excel)

---

### **Opportunity 2: multi-Account Coordination (Wiki-style)**

**Current Instagram system**: 
- Single config file → All accounts same keywords
- Long lead time to test new strategies

**Wiki-style approach**:
```
accounts-wiki/
├── [account_1].md         # Persona, performance, focus niche
├── [account_2].md         # Activity log, leads generated
├── [strategy_fitness].md  # Shared keywords, seed accounts
├── [strategy_coaching].md # Niche-specific approach
└── [experiment_logs]/     # "Try X, result Y" trail
    ├── 2026_04_01_reduced_delay.md
    ├── 2026_04_08_add_proxy_rotation.md
    └── 2026_04_15_keyword_v3.md
```

**Benefit**: Run A/B tests, track what works, compose new strategies from old experiments

---

### **Opportunity 3: Recursive Lead Enrichment (Like Wiki Linking)**

**Current**: Lead = single row (username, followers, email)

**Wiki-style enrich**:
```
lead_enrichment/
├── @leadperson_001.md
│   - Primary bio: "Online coach"
│   - URL: leads-to → [blog_url_001].md
│   - Engagement: ~300 likes/post
│   - Follower composition: %60 female, %40 male (estimated)
│   - Cross-posts with: [[coach_002]], [[coach_003]]
│   - Similar to: [[persona_fitness_coach]]
│
├── [blog_url_001].md
│   - Topic: "Transformation stories"
│   - Leads to: 23 other coaches
│   - Authority markers: ~50k backlinks (ahrefs)
│
└── [persona_fitness_coach].md
    - Average followers: 8000-15000
    - Engagement rate: 4-6%
    - Bio keywords (frequency): coaching (90%), transformation (85%), results (72%)
```

**Benefit**: Opens **follower-of-followers** discovery (like Instagram's system, but with persistence)

---

## 💡 Architectural Parallel

### **Karpathy Wiki = Knowledge Graph in Markdown**
- Nodes: Individual wiki pages
- Edges: `[[cross-links]]` between concepts
- Query: Start at hot.md → follow links → discover relationships
- **Cost**: Just markdown files (~no compute, just LLM for initial ingest)

### **Instagram Lead Gen = Social Graph in Excel**
- Nodes: Individual profiles (users)
- Edges: Follower relationships (implicit in seed → followers)
- Query: Start at seed account → fetch followers → filter by rules
- **Cost**: High (API calls, rate limits, proxy costs)

### **Hybrid Potential: Lead Graph as Wiki**
Combine both:
1. **Scrape** Instagram followers → raw CSV
2. **Ingest** into wiki (Claude organize by niche/persona/region)
3. **Store** relationships as markdown links
4. **Query** via "Which fitness coaches are connected to @leadgenman?"

---

## 🚀 Actionable Tasks for Jarvis

### **Phase 1: Wiki Infrastructure (1-2 days)**
```
[ ] Create leads-wiki/ folder structure
[ ] Update batch_profile_scraper.py to export leads as markdown
[ ] Write wiki ingestion script (CSV → individual .md files)
[ ] Add hot.md auto-generation (weekly summary)
```

### **Phase 2: Lead Linking (2-3 days)**
```
[ ] Map lead relationships (followers of followers)
[ ] Add cross-reference links ([[lead_id]], [[niche_topic]])
[ ] Build "related leads" sections in each profile page
[ ] Create niche summary pages (aggregate insights)
```

### **Phase 3: Multi-Account Wiki (3-5 days)**
```
[ ] Create accounts-wiki/ for IG account coordination
[ ] Track A/B test results as markdown logs
[ ] Build strategy composition system (test results → new strategy)
[ ] Implement experiment dashboard (hot.md shows latest tests)
```

---

## 📈 Metrics: Before vs After

### **Current State (Instagram → Excel)**
- Lead discovery: Linear (manual search through rows)
- Relationship mapping: Manual (copy-paste between sheets)
- Strategy testing: Slow (results buried in separate files)
- Knowledge reuse: Low (each campaign starts from scratch)
- **Total setup time**: 1-2 hours per campaign

### **Proposed State (Instagram → Lead Graph Wiki)**
- Lead discovery: Graph traversal (click links, find adjacent niches)
- Relationship mapping: Automatic (wiki links generated)
- Strategy testing: Fast (experiment logs accessible, trends visible)
- Knowledge reuse: High (templates from past campaigns)
- **Total setup time**: 15 min per campaign (copy template, adjust)

---

## 🔗 Integration with Batch Scraper

**Current file**: `server/skills/batch_profile_scraper_codex.py`

**Enhancement opportunity**:
```python
# Instead of just JSON output
results = {
    "engagement_analizi.json": {...},      # Current
    "monetization_tahminleri.json": {...}, # Current
    "leads_wiki_export/": {                # NEW
        "raw/": "batch_2026_04_15.csv",    # Input
        "wiki/": {
            "[lead_001].md": "Profile page with links",
            "[niche_fitness].md": "Niche summary page",
            "index.md": "Lead index",
            "hot.md": "Weekly summary",
            "log.md": "Scrape history"
        }
    }
}
```

**Command**: `/batch-scrape --output wiki` → generates leads-wiki/ automatically

---

## 📌 Key Insight: Wiki as Competitive Moat

**Karpathy says**: "Your wiki becomes your brain"  
**For Jarvis**: "Your leads wiki becomes your audience map"

- Competitors: Scrape once, forget (Google Sheets)
- Jarvis with wiki: Scrape daily, **learn** (relationships compound over time)
- After 90 days: Jarvis knows which coaches are connected to which ones
- After 1 year: Jarvis can predict which new coaches will match your niche

---

## 🎯 Next Step

**Awaiting Ekrem's decision**:
1. Should we implement leads wiki? (Phase 1-3 roadmap)
2. Which phase first? (Infrastructure vs Linking vs Experiment tracking)
3. Proxy keys? (For real scale testing)

**Status**: Analysis complete. Ready to build.
