# SPEC: Codex Multi-Account Swarm Orchestration

**Feature ID:** 007  
**Title:** 5 Codex Hesabı Paralel Çalışması + Sesli/Telegram Integration  
**Owner:** Ekrem  
**Status:** SPECIFIED  
**Priority:** CRITICAL (15+ gün bekleyen feature)  
**Date:** 2026-04-15  

---

## 🎯 Requirements (Ekrem'in Sözleri)

> "Ben Jarvis'le sesli konuşacağım PC'den yada telegramdan görev verdiğim zaman o 5 codex hesaplarını kullanacağız ajanlar hepsi kanka aynanda çalışacak yani tek bir hesaptan değil 5 hesabı aynanda çalışacak ve konuşacaklar istediğim konu"

### Functional Requirements

1. **Voice Input → Parallel Execution**
   - [ ] Ses'ten görev al (Whisper STT)
   - [ ] "paralel", "aynı anda" keywordlerini detekt et
   - [ ] Görevi 5 sub-task'a böl (LLM decomposer)
   - [ ] 5 Codex slot'a dağıt (1 task per slot, concurrent)
   - [ ] Her slot'dan output aldıkça real-time TTS raporu ver

2. **Quota Tracking (5 Codex Account)**
   - [ ] Daily call tracking per slot
   - [ ] 429 Rate Limit → cooldown logic
   - [ ] Slot rotation (exhausted → next available)
   - [ ] `state/codex_quotas.json` persistence

3. **Telegram Integration**
   - [ ] `/swarm [görev]` command
   - [ ] Task progress report (emoji + %)
   - [ ] 5 concurrent result notifications

4. **Result Aggregation**
   - [ ] 5 output'ı combine et
   - [ ] Errors ve successes ayrı rapor et
   - [ ] TTS-friendly narrative oluştur

---

## 📐 Success Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Parallelization** | Tasks executed concurrently | 5 tasks simultaneously |
| **Response time** | Single vs. Parallel | <2s overhead |
| **Quota tracking** | Per-slot tracking accuracy | 100% |
| **Error recovery** | Rate limit recovery rate | 99% successful retry |
| **Voice integration** | Speech-to-task coverage | 90% intent detection |
| **Codex coordination** | Slot utilization | 5/5 slots active |

---

## 🏗️ Architecture

### Components

1. **QuotaTracker** — Redis/JSON state
2. **ParallelCodexDispatcher** — Async task runner
3. **VoiceTaskDispatcher** — Whisper → decompose → dispatch
4. **SwarmSkill** — `/swarm` command handler
5. **ResultAggregator** — Output synthesis + TTS

### Data Flow

```
Voice/Telegram Input
  ↓
IntentParser (paralel keyword detect)
  ↓
TaskDecomposer (LLM: split to 5 tasks)
  ↓
QuotaTracker (check availability)
  ↓
ParallelCodexDispatcher
  ├─ Task1 → Codex/forge
  ├─ Task2 → Codex/nexus
  ├─ Task3 → Codex/spark
  ├─ Task4 → Codex/atlas
  └─ Task5 → Codex/shield
  ↓ (async polling)
ResultAggregator
  ↓
TTS Narrative Output
```

---

## 🚀 Deliverables

| File | Purpose | Status |
|------|---------|--------|
| `server/multi_account_swarm.py` | Core orchestrator | ✅ Template ready |
| `server/skills/swarm_skill.py` | `/swarm` handler | ❌ TODO |
| `server/voice/voice_swarm_dispatcher.py` | Voice integration | ❌ TODO |
| `config/codex_slots.yaml` | Slot configuration | ❌ TODO |
| `state/codex_quotas.json` | Runtime quota state | ❌ TODO |
| `tests/test_swarm_orchestration.py` | Unit tests | ❌ TODO |

---

## ⚠️ Constraints & Risks

| Risk | Mitigation |
|------|-----------|
| Codex API rate limits | Exponential backoff + slot rotation |
| Task decomposition quality | LLM-based + user confirmation option |
| Concurrent execution overhead | Async/await patterns |
| Quota reset timing | UTC-based state with daily reset |

---

## 📅 Timeline

- **Phase 1** (4 hours): Base orchestrator + quota tracking
- **Phase 2** (3 hours): Telegram integration
- **Phase 3** (2 hours): Voice integration
- **Phase 4** (2 hours): Testing + hardening

**Total:** 11 hours (peut-être parallel Codex slots reduces to ~17 hours with prep)

---

## 📞 Approval

- [ ] Ekrem: Requirement confirm
- [ ] Team: Architecture review
- [ ] QA: Test plan

---

**Next:** `/speckit.plan` → technical design

