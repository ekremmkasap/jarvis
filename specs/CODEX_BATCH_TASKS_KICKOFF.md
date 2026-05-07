# Codex 5-Agent Parallel Kickoff — 48h Instagram Buildout

**Date**: April 15, 2026  
**Goal**: Execute batch scraper, reel analysis, swarm orchestration, QA tests, and CEO strategy in parallel  
**Deadline**: 48 hours  

---

## 📦 Task Inventory (7 Total)

### Block A: Seda (forge) — Batch Scraper Execution
**Task ID**: A1  
**Status**: Ready (code complete, tmp/handles.sample.csv ready)

**Subtasks**:
1. Run batch scraper smoke test: `tmp/handles.sample.csv` (5 handles)
2. Run real batch scrape: Generate 10-15 random Instagram/YouTube handles from instagram_analysis.json
3. Analyze output: Check `ozet_rapor.json`, `engagement_analizi.json`, `monetization_tahminleri.json`
4. Report findings: Save to `outputs/batch_scraper_seda_run1.json`

**Entry Point**:
```python
from server.skills.batch_profile_scraper_codex import BatchProfileScraper

scraper = BatchProfileScraper(max_concurrent=5, timeout=30, max_retries=2)
result = await scraper.batch_scrape_from_csv("tmp/handles.sample.csv")
print(result)
```

**Completion Criteria**:
- ✅ CSV smoke runs without errors
- ✅ Real batch completes (success or detailed failure report)
- ✅ Reports saved to outputs/batch_scrapes/<timestamp>_profiller/
- ✅ Summary JSON with toplam/basarili/basarisiz counts

---

### Block B: Buse (spark) + Eren (spark) — Reel Analysis

**Task B1** (Buse): Reel 021-030 Detailed Analysis  
**Status**: Ready (templates in reel_analiz_log.md)

Subtasks:
1. Parse reel_analiz_log.md Reel 021-030 metadata
2. For each reel:
   - Extract engagement metrics (likes, comments, shares, views, save_rate)
   - Identify creator positioning (open-source, edu, lifestyle, product, other)
   - Analyze CTA effectiveness (comment X, link in bio, DM, none)
   - Map to monetization strategy (affiliate, sponsored, product, none)
3. Generate comparison matrix (CTR × positioning × CTA)
4. Top 3 performing reels analysis
5. Save: `outputs/reel_analiz_buse_021_030.json`

**Task B2** (Eren): Create Batch Analysis Task Spec for Reel 031-065  
**Status**: Ready (templates in reel_analiz_log.md lines 1969+)

Subtasks:
1. Extract handles from Reel 031-065 metadata in reel_analiz_log.md
2. For each handle: map to Instagram profile URL
3. Create batch_handles_031_065.csv: hesap,platform (e.g., @creator_name,instagram)
4. Write task spec: `specs/CODEX_REEL_ANALYSIS_031_065_BATCH.md`
   - Step-by-step engagement analysis instructions
   - Output format: JSON array of {reel_id, creator, positioning, engagement_score}
5. Estimate: ~100-150 lines total across 35 reels

**Completion Criteria (B1+B2)**:
- ✅ Reel 021-030 detailed analysis JSON saved
- ✅ Reel 031-065 batch CSV ready
- ✅ Batch task spec written with clear acceptance criteria
- ✅ Comparison matrix shows top 3 patterns

---

### Block C: Sabrican (nexus) — Swarm Orchestration

**Task C1**: Implement 5-Agent Swarm Coordinator  
**Status**: In-progress (bridge has `/batch-scrape`, need `/swarm` routing)

Subtasks:
1. Define swarm state machine: NEW → RUNNING → COLLECTING → REPORTING → DONE
2. Create `server/orchestrator/swarm_coordinator.py`:
   - Class `SwarmCoordinator` manages 5 Codex slots (forge, nexus, spark×2, atlas)
   - Methods: `assign_task()`, `collect_results()`, `aggregate_reports()`
3. Add bridge command: `/swarm <goal_id> [handles_csv]`
   - Route to `SwarmCoordinator`
   - Return: goal UUID + status link
4. Task bus: Write task definitions for each role
   - Seda (forge): profile scrape + analysis
   - Buse/Eren (spark): content analysis + engagement scoring
   - Sabrican (nexus): orchestration + report aggregation
5. Save: `server/orchestrator/swarm_coordinator.py` + `specs/SWARM_TASK_DEFINITIONS.md`

**Completion Criteria**:
- ✅ SwarmCoordinator class instantiable
- ✅ `/swarm test-goal-1` command runs without errors
- ✅ Task definitions for all 5 roles documented
- ✅ Results aggregation working

---

### Block D: QA (any slot) — Validation

**Task D1**: Test `/scrape-profile` Bridge Command  
Subtasks:
1. Run: `/scrape-profile @leadgenman`
2. Verify: Returns profile data (followers, engagement, bio, etc.)
3. Run: `/scrape-profile https://youtube.com/c/TestChannel`
4. Verify: YouTube profile data returns correctly
5. Log results: `outputs/qa_scrape_profile_results.json`

**Task D2**: Test `/swarm` End-to-End Flow  
Subtasks:
1. Define small test goal: scrape 3 handles + analyze
2. Run: `/swarm test-goal-qa [3_handles.csv]`
3. Wait for completion (track via `/swarm-status <goal_uuid>`)
4. Verify: All 5 agents executed, results aggregated
5. Log: `outputs/qa_swarm_e2e_results.json`

**Completion Criteria**:
- ✅ Both `/scrape-profile` tests pass
- ✅ `/swarm` e2e test completes without errors
- ✅ QA report saved with PASS/FAIL

---

### Block E: Sabri (atlas) — CEO Strategy Goal

**Task E1**: 48-Hour Instagram Buildout Strategy  
**Status**: Ready (batch scraper, reel analysis, swarm ready)

Subtasks:
1. Define KPI dashboard: followers gained, engagement rate, content quality score
2. Set 48h targets:
   - 15-20 new creator partnerships identified
   - 50+ reel analysis completed
   - Top 10 monetization opportunities discovered
   - 3 go-to-market strategies proposed
3. Coordinate swarm execution:
   - Hour 0-12: Reel 021-065 batch analysis
   - Hour 12-24: Parallel batch scraper (100+ profiles)
   - Hour 24-36: Top opportunity deep dives
   - Hour 36-48: Strategy synthesis + proposal deck
4. Save: `outputs/ceo_48h_buildout_strategy.md`

**Completion Criteria**:
- ✅ KPI dashboard initialized
- ✅ Swarm parallelism coordinated
- ✅ Strategy proposal completed
- ✅ Go-to-market recommendations documented

---

## 🎯 Execution Plan

### Phase 1: Launch (Hour 0-2)
- **Seda**: Start A1.1 (CSV smoke)
- **Buse**: Start B1 (Reel 021-030 analysis)
- **Eren**: Start B2 (Reel 031-065 batch prep)
- **Sabrican**: Start C1 (Swarm coordinator code)
- **Sabri**: Initialize E1 (KPI setup)

### Phase 2: Parallel Execution (Hour 2-24)
- **Seda**: A1.2-A1.4 (Real batch scrape + analysis)
- **Buse**: B1 completion
- **Eren**: B2 completion
- **Sabrican**: C1 completion
- **QA**: Run D1 (scrape-profile test)

### Phase 3: Integration (Hour 24-36)
- **Sabrican**: Coordinate swarm
- **QA**: D2 (e2e swarm test)
- **Sabri**: Process results, update strategy

### Phase 4: Completion (Hour 36-48)
- **Sabri**: Strategy synthesis + recommendations
- **All**: Final report aggregation

---

## 📊 Outputs

All results saved to `outputs/`:

```
outputs/
├── batch_scrapes/<timestamp>_profiller/
│   ├── profile1.json
│   ├── ozet_rapor.json
│   ├── engagement_analizi.json
│   ├── monetization_tahminleri.json
│   └── hata_log.json
├── reel_analiz_buse_021_030.json
├── batch_handles_031_065.csv
├── qa_scrape_profile_results.json
├── qa_swarm_e2e_results.json
└── ceo_48h_buildout_strategy.md
```

---

## 🚀 Ready to Execute?

- [x] Batch scraper code: READY
- [x] Reel templates: READY
- [x] Bridge scaffolding: READY (batch_scraper_codex.py + /batch-scrape + /scrape-profile)
- [ ] Swarm coordinator: TO IMPLEMENT
- [ ] QA tests: TO IMPLEMENT
- [ ] CEO strategy: TO SYNTHESIZE

**Next**: Codex agents execute parallel blocks. Sabri coordinates 48h goal.
