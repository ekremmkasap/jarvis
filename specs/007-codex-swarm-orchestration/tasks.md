# TASKS: Codex Multi-Account Swarm Orchestration

**Spec:** 007-codex-swarm-orchestration  
**Plan:** ✅ Ready  
**Status:** TASKED  
**Total Tasks:** 18  
**Est. Duration:** 11 hours  

---

## 🎯 Task Breakdown by Phase

### PHASE 1: Core Orchestrator (4 hours)

**[TASK 1.1] Verify multi_account_swarm.py Completeness** ⏱️ 0.5h
- **Description:** Review `server/multi_account_swarm.py` — ensure all classes complete
- **Action:**
  - [ ] Read QuotaTracker class (line ~80)
  - [ ] Read ParallelCodexDispatcher class (line ~200)
  - [ ] Read VoiceTaskDispatcher class (line ~350)
  - [ ] Check all methods implemented (not TODO)
- **Owner:** Backend Engineer
- **Status:** NOT_STARTED

**[TASK 1.2] Create swarm_skill.py** ⏱️ 1h
- **Description:** Write skills file that bridges `/swarm` command to multi_account_swarm
- **Files Created:**
  - [ ] `server/skills/swarm_skill.py`
- **API:**
  ```python
  def swarm_run(goal: str) -> str:
      """Handle /swarm command"""
      # 1. Detect if parallel keyword
      # 2. If yes: use ParallelCodexDispatcher
      # 3. If no: single task execution
      # 4. Return narrative
  ```
- **Owner:** Backend Engineer
- **Status:** NOT_STARTED
- **Depends On:** 1.1

**[TASK 1.3] Create config/codex_slots.yaml** ⏱️ 0.5h
- **Description:** Define slot configuration (personas, quotas, timeouts)
- **Files Created:**
  - [ ] `config/codex_slots.yaml`
- **Content:**
  ```yaml
  slots:
    forge:
      personas: [seda, mert]
      quota_daily: 100
      timeout_seconds: 120
    nexus:
      personas: [sabrican]
      quota_daily: 100
      timeout_seconds: 120
    # ... (repeat for spark, atlas, shield)
  
  task_decomposition:
    max_tasks: 5
    model: groq/qwen-qwq-32b
    timeout: 30
  ```
- **Owner:** DevOps / Config
- **Status:** NOT_STARTED

**[TASK 1.4] Quota Persistence: Initialize state/codex_quotas.json** ⏱️ 0.5h
- **Description:** Create initial quota state file + ensure daily reset logic
- **Files Created:**
  - [ ] `state/codex_quotas.json` (auto-init on first run)
- **Schema:**
  ```json
  {
    "forge": {
      "calls_today": 0,
      "limit": 100,
      "reset_at": "2026-04-16T00:00:00Z",
      "cooldown_until": null
    },
    // ... (repeat for nexus, spark, atlas, shield)
  }
  ```
- **Owner:** Backend Engineer
- **Status:** NOT_STARTED
- **Depends On:** 1.3

**[TASK 1.5] Task Decomposer Integration** ⏱️ 1h
- **Description:** Integrate LLM-based task decomposition into VoiceTaskDispatcher
- **Changes:**
  - [ ] Modify `VoiceTaskDispatcher._decompose_tasks()` (currently hardcoded)
  - [ ] Use Groq/Gemini to split 1 goal → 5 sub-tasks
  - [ ] Validate output schema (id, prompt, persona, priority)
- **Example Input:** "Paralel olarak 5 tane Python script yaz"
- **Example Output:**
  ```python
  [
    Task(id="t1", prompt="Fibonacci alanındaki hızlı algoritma", persona="seda", priority=1),
    Task(id="t2", prompt="REST API client", persona="seda", priority=2),
    # ... (t3, t4, t5)
  ]
  ```
- **Owner:** Backend Engineer
- **Status:** NOT_STARTED
- **Depends On:** 1.1, 1.2

**[TASK 1.6] Error Handling: Codex API Wrapper** ⏱️ 0.5h
- **Description:** Create actual Codex API call implementation (currently mocked)
- **Changes:**
  - [ ] Replace `ParallelCodexDispatcher._call_codex_api()` mock
  - [ ] Implement real HTTP POST to GitHub Copilot API (or configured endpoint)
  - [ ] Handle 429 (rate limit) → call `quota.on_rate_limit()`
  - [ ] Handle 401 (auth fail) → rotate to next slot
  - [ ] Add retry with exponential backoff
- **Owner:** Backend Engineer
- **Status:** NOT_STARTED
- **Depends On:** 1.1

---

### PHASE 2: Telegram Integration (3 hours)

**[TASK 2.1] Telegram Command Testing** ⏱️ 1h
- **Description:** Test `/swarm` command end-to-end via Telegram
- **Test Cases:**
  - [ ] `/swarm kod yaz` (single task)
  - [ ] `/swarm paralel 3 görev yaz` (3 tasks)
  - [ ] `/swarm bugün 100 görev` (quota exhaustion)
  - [ ] Verify results aggregated correctly
- **Expected Output:** Telegram message with 5 results or error
- **Owner:** QA
- **Status:** NOT_STARTED
- **Depends On:** 1.2, 1.5

**[TASK 2.2] Progress Reporting (Real-time)** ⏱️ 1h
- **Description:** Send progress updates to Telegram during parallel execution
- **Implementation:**
  - [ ] Create progress webhook endpoint
  - [ ] Poll executor.active_tasks every 1s
  - [ ] Send %progress updates: "✓ 2/5 görev tamamlandı (40%)"
  - [ ] Final summary with all results
- **Owner:** Backend Engineer
- **Status:** NOT_STARTED
- **Depends On:** 1.2

**[TASK 2.3] Error Reporting UI** ⏱️ 1h
- **Description:** Format errors nicely for Telegram
- **Implementation:**
  - [ ] Separate success/failure results
  - [ ] Red flag for rate-limited slots
  - [ ] Suggestion: "Slot `forge` şu an meşgul, ikinci atış yapılıyor..."
  - [ ] Final error summary
- **Owner:** Backend Engineer
- **Status:** NOT_STARTED
- **Depends On:** 1.2, 2.1

---

### PHASE 3: Voice Integration (2 hours)

**[TASK 3.1] Integrate VoiceTaskDispatcher into hey_jarvis.py** ⏱️ 1h
- **Description:** Modify voice loop to detect parallel keywords + use swarm
- **Changes:**
  - [ ] Read `hey_jarvis.py` → locate `voice_loop()`
  - [ ] Add parallel keyword detection (regex: "paralel", "aynı anda", "concurrent")
  - [ ] If parallel: route to `VoiceTaskDispatcher`
  - [ ] If single: route to normal LLM
  - [ ] Collect results + pass to TTS
- **Code Pattern:**
  ```python
  if any(kw in text for kw in ["paralel", "aynı anda"]):
      voice_dispatcher = VoiceTaskDispatcher(dispatcher)
      narrative = await voice_dispatcher.process_voice_command(text)
  else:
      narrative = await single_llm_response(text)
  
  await piper_tts.speak(narrative)
  ```
- **Owner:** Voice Engineer
- **Status:** NOT_STARTED
- **Depends On:** 1.1, 1.2

**[TASK 3.2] TTS Aggregation & Synthesis** ⏱️ 1h
- **Description:** Format parallel results into coherent TTS narrative
- **Implementation:**
  - [ ] Implement `VoiceTaskDispatcher._synthesize_response()` (partially done)
  - [ ] Order results: success first, then errors
  - [ ] Format per-task: "Görev 1 (forge): [100-char summary]..."
  - [ ] Total duration: "Toplam 45 saniyede tamamlandı"
  - [ ] Handle rate limits gracefully: "Forge slot şu an meşgul ama tekrar deneniyor..."
- **Expected Output:** Turkish-proper, TTS-friendly (no URLs, no JSON)
- **Owner:** Voice Engineer
- **Status:** NOT_STARTED
- **Depends On:** 1.3

---

### PHASE 4: Testing & Hardening (2 hours)

**[TASK 4.1] Unit Tests: QuotaTracker** ⏱️ 0.5h
- **Description:** Write pytest tests for quota tracking
- **Test File:**
  - [ ] `tests/test_quota_tracker.py`
- **Test Cases:**
  - [ ] `test_init_fresh_quota()`
  - [ ] `test_mark_used_increments()`
  - [ ] `test_quota_exhausted()`
  - [ ] `test_cooldown_expiration()`
  - [ ] `test_daily_reset()` (time-based)
- **Owner:** QA
- **Status:** NOT_STARTED
- **Depends On:** 1.1

**[TASK 4.2] Unit Tests: ParallelCodexDispatcher** ⏱️ 0.5h
- **Description:** Write pytest tests for parallel execution
- **Test File:**
  - [ ] `tests/test_parallel_dispatcher.py`
- **Test Cases:**
  - [ ] `test_dispatch_5_tasks_concurrently()`
  - [ ] `test_slot_assignment_priority()`
  - [ ] `test_rate_limit_recovery()`
  - [ ] `test_task_timeout_handling()`
  - [ ] `test_result_aggregation()`
- **Owner:** QA
- **Status:** NOT_STARTED
- **Depends On:** 1.1

**[TASK 4.3] Integration Test: Telegram → Codex → Result** ⏱️ 0.5h
- **Description:** End-to-end test via Telegram
- **Test Scenario:**
  - [ ] Send `/swarm paralel 3 kisan`
  - [ ] Verify 3 tasks dispatched to 3 different slots
  - [ ] Verify results returned in <30s
  - [ ] Verify quota incremented correctly
- **Owner:** QA
- **Status:** NOT_STARTED
- **Depends On:** 2.1, 2.2

**[TASK 4.4] Load Test: 10 Concurrent Users** ⏱️ 0.5h
- **Description:** Stress test parallel dispatcher
- **Test:**
  - [ ] Spawn 10 concurrent /swarm requests
  - [ ] Verify slot rotation (not all to forge)
  - [ ] Verify quota tracking stays consistent
  - [ ] Verify no race conditions
- **Owner:** DevOps
- **Status:** NOT_STARTED
- **Depends On:** 2.1

---

## 🧩 Task Dependency Graph

```
1.1 (Verify)
  ↓
1.2 (swarm_skill)  ←  1.1
  ↓
1.3 (config)
  ↓
1.4 (state)  ←  1.3
  ↓
1.5 (decomposer)  ←  1.2
  ↓
1.6 (API wrapper)  ←  1.1
  ↓
2.1 (Telegram test)  ←  1.2, 1.5
  ↓
2.2 (Progress)  ←  1.2
  ↓
2.3 (Error UI)  ←  1.2, 2.1
  ↓
3.1 (Voice)  ←  1.1, 1.2
  ↓
3.2 (TTS)  ←  1.3
  ↓
4.1 (Unit: Quota)  ←  1.1
4.2 (Unit: Dispatcher)  ←  1.1
4.3 (Integration)  ←  2.1, 2.2
4.4 (Load test)  ←  2.1
```

---

## 📋 Checklist

### PRE-DEVELOPMENT
- [ ] Spec + Plan reviewed by Ekrem
- [ ] Codex API endpoint URL confirmed
- [ ] Telegram bot token ready
- [ ] GitHub access for Codex API

### BUILD (Tasks 1-4)
- [ ] All 4 phases complete
- [ ] Code review passed
- [ ] Tests: 90%+ coverage
- [ ] No linting errors (`ruff check`, `mypy`)

### DEPLOYMENT
- [ ] Merged to main branch
- [ ] Deployed to production
- [ ] Monitored for 24h (no critical errors)
- [ ] Ekrem verified end-to-end

---

**Next:** `/speckit.implement` → Codex goes to work!

