# PLAN: Codex Multi-Account Swarm Orchestration

**Spec:** 007-codex-swarm-orchestration  
**Date:** 2026-04-15  
**Status:** PLANNING  

---

## 🎯 Technical Architecture

### Core Design Decisions

| Decision | Rationale | Implementation |
|----------|-----------|-----------------|
| **Async/Await** | Concurrent task execution | asyncio.Task pool |
| **Quota Tracking** | 429 Prevention | state/codex_quotas.json + in-memory cache |
| **Task Decomposition** | Multi-task support | LLM prompt → 5 sub-prompts |
| **Slot Routing** | Load balancing | Priority-based assignment + fallback |
| **Progress Reporting** | Real-time feedback | Polling every 1s (vs. webhook) |
| **Error Recovery** | Resilience | Exponential backoff + slot rotation |

### Architecture Diagram

```
                    ┌──────────────────┐
                    │  Voice/Telegram  │
                    │  Input Handler   │
                    └────────┬─────────┘
                             │ "paralel 5 görev"
                             ▼
                    ┌──────────────────┐
                    │ Intent Detector  │ (regex + LLM)
                    └────────┬─────────┘
                             │ is_parallel=true
                             ▼
                    ┌──────────────────────────┐
                    │ Task Decomposer (LLM)    │ ← Groq/Gemini
                    └────────┬─────────────────┘
                             │ [Task1, Task2, ..., Task5]
                             ▼
               ┌─────────────────────────────────┐
               │  ParallelCodexDispatcher        │
               │  ┌────────────────────────────┐ │
               │  │ SlotAssigner               │ │ (Priority-based)
               │  └───────┬────────────────────┘ │
               │          │                      │
               │  ┌───────▼────────────────────┐ │
               │  │ QuotaTracker Check         │ │
               │  │ - calls_today < limit?     │ │
               │  │ - in_cooldown? No          │ │
               │  └───────┬────────────────────┘ │
               │          │                      │
        ┌──────┼──────────┼──────────┬──────────┼───────┐
        │      │          │          │          │       │
        ▼      ▼          ▼          ▼          ▼       │
    FORGE   NEXUS      SPARK       ATLAS     SHIELD    │
    (Task1) (Task2)   (Task3)    (Task4)   (Task5)    │
        │      │          │          │          │       │
        │ ConcurrentWorkflow Pattern            │
        │ - async.create_task() for each       │
        │ - asyncio.gather() results           │
        │ - 1s polling per slot                │
        │      │          │          │          │       │
        └──────┼──────────┼──────────┼──────────┼───────┘
               │ Results merged every 1s
               ▼
        ┌────────────────────────┐
        │ ResultAggregator       │ ← Error handling, synthesis
        └────────┬───────────────┘
                 │
        ┌────────▼────────────┐
        │ TTS Narrative Gen   │ ← "Görev 1: bitti. Sonuç..."
        └────────┬────────────┘
                 │
             Piper tr_TR / edge-tts
```

---

## 🛠️ Implementation Modules

### Module 1: QuotaTracker (READY)

**File:** `server/multi_account_swarm.py::QuotaTracker`
**Status:** ✅ Code complete
**API:**
```python
tracker = QuotaTracker(daily_limit=100)
slot = tracker.get_available_slot()  # → CodexSlot or None
tracker.mark_used(slot)  # increment counter
tracker.on_rate_limit(slot, wait_seconds=60)  # set cooldown
```

### Module 2: ParallelCodexDispatcher (READY)

**File:** `server/multi_account_swarm.py::ParallelCodexDispatcher`
**Status:** ✅ Code complete
**API:**
```python
dispatcher = ParallelCodexDispatcher(quota_tracker)
results = await dispatcher.dispatch_parallel([Task(...), ...])
# → {task_id: TaskResult, ...}
```

### Module 3: VoiceTaskDispatcher (READY)

**File:** `server/multi_account_swarm.py::VoiceTaskDispatcher`
**Status:** ✅ Code complete (partial)
**API:**
```python
voice = VoiceTaskDispatcher(dispatcher)
narrative = await voice.process_voice_command("paralel 5 görev")
```

### Module 4: SwarmSkill (TODO)

**File:** `server/skills/swarm_skill.py`
**Status:** ❌ Template only
**API:**
```python
def swarm_run(goal: str) -> str:
    # Called by: bridge.py _handle_swarm_command()
    # 1. Check if parallel keyword
    # 2. Decompose
    # 3. Dispatch
    # 4. Poll results
    # 5. Return narrative
```

### Module 5: Voice Integration (TODO)

**File:** `server/voice/voice_swarm_dispatcher.py`
**Status:** ❌ Not created
**Integration:**
- Modify `hey_jarvis.py` to detect parallel keywords
- Route to `VoiceTaskDispatcher` instead of LLM
- Play aggregated TTS output

### Module 6: Configuration (TODO)

**File:** `config/codex_slots.yaml`
**Status:** ❌ Not created
**Contains:**
- Slot definitions (forge/nexus/spark/atlas/shield)
- Persona → slot mapping
- Daily quota limits
- Timeout values

---

## 🔌 Integration Points

### 1. Bridge.py → SwarmSkill

**Current:**
```python
elif command == "/swarm":
    return _handle_swarm_command(args)

def _handle_swarm_command(args: str) -> str:
    from swarm_skill import swarm_run
    return swarm_run(args.strip())
```

**Required:** Nothing (already wired!)

**Test:** `/swarm paralel 3 python script yaz`

### 2. Hey_jarvis.py → Voice Dispatcher

**Current:** Sequential LLM response

**Required Modification:**
```python
# In voice_loop()
if "paralel" in text or "aynı anda" in text:
    voice_dispatcher = VoiceTaskDispatcher(dispatcher)
    narrative = await voice_dispatcher.process_voice_command(text)
else:
    narrative = await normal_llm_call(text)
```

### 3. TTS Output Handling

**How:** Piper tr_TR voice line-by-line (no TTS cut mid-sentence)

**Implementation:**
```python
def split_tts_safe(narrative: str) -> List[str]:
    # Split on "." "?" "!" but not mid-sentence
    parts = narrative.split(". ")
    return parts
```

---

## 🧪 Testing Strategy

### Unit Tests (test_swarm_orchestration.py)

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| Parallel dispatch | 5 tasks | All execute concurrently | ❌ TODO |
| Quota tracking | 100 calls | calls_today increments | ❌ TODO |
| Rate limit recovery | 429 error | Exponential backoff + retry | ❌ TODO |
| Task decomposition | Text input | 5 valid sub-tasks | ❌ TODO |
| Voice intent | "paralel 3 görev" | is_parallel=true, len=3 | ❌ TODO |
| Slot assignment | Priorities | High priority → preferred slot | ❌ TODO |

### Integration Tests

| Test | Scenario | Expected |
|------|----------|----------|
| End-to-end Telegram | `/swarm kod yaz 5 tur` | 5 results aggregated |
| End-to-end Voice | "Paralel 5 yapı yaz" | Voice output heard |
| Quota exhaustion | 100 calls + 1 | 101st → rate limit echo |
| Multi-slot failure | 2 slots down | Tasks routed to 3 active |

---

## 🔐 Security & Edge Cases

### Risks

| Risk | Handling |
|------|----------|
| **Codex API key leak** | `.env` gitignore, never log |
| **Task injection** | LLM decomposer validates schema |
| **Rate limit abuse** | Rate limit detection + cooldown |
| **Concurrent slot collision** | Mutex-based slot reservation |

### Edge Cases

| Case | Handling |
|------|----------|
| **All slots exhausted** | Return "Quota exhausted, try later" |
| **Single vs. Parallel** | Single task → direct route (no decompose) |
| **Slot down** | Route to next available |
| **Task timeout** | Mark as "timeout", continue others |

---

## 📊 Performance Targets

| Metric | Target | Implementation |
|--------|--------|-----------------|
| **Parallelization overhead** | <200ms | async/await (no thread overhead) |
| **Single slot → multi-slot** | +50% throughput | 5x concurrent capacity |
| **Result aggregation** | <500ms | No-wait gather() |
| **Quota check** | O(1) | In-memory cache |

---

## 🚀 Deployment Strategy

### Phases

**Phase 1: Core (4 hours)**
- ✅ QuotaTracker
- ✅ ParallelCodexDispatcher
- ✅ VoiceTaskDispatcher
- ✅ SwarmSkill

**Phase 2: Telegram (3 hours)**
- `/swarm` command tests
- Progress reporting
- Error handling UI

**Phase 3: Voice (2 hours)**
- hey_jarvis.py integration
- Parallel keyword detection
- TTS aggregation

**Phase 4: QA (2 hours)**
- Load testing (5 concurrent tasks)
- Quota edge cases
- Failure recovery scenarios

---

## 🎯 Definition of Done

- [ ] All 4 core modules production-ready
- [ ] Unit tests: 90%+ coverage
- [ ] Integration tests pass
- [ ] Quota tracking persisted + verified
- [ ] TTS output coherent + Turkish-proper
- [ ] Error handling for all edge cases
- [ ] Deployed to production
- [ ] Telegram `/swarm` tested
- [ ] Voice `/paralel` tested
- [ ] Codex quota dashboard shows 5 slots

---

**Next:** `/speckit.tasks` → actionable checklist

