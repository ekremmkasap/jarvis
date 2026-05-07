# 🚀 JARVIS 10-HOUR BUILDOUT ROADMAP (Ekrem Sleeping)

**Start Time:** 2026-04-04 07:30 UTC  
**End Time:** 2026-04-04 17:30 UTC  
**Mode:** UNATTENDED (no interruptions)  
**Parallel Codex Tabs:** 5 (Ahmet-1 through Ahmet-5)  
**Ram/Quota:** Conservative (avoid Codex overuse)  
**Status:** READY FOR EXECUTION  

---

## ⚡ EXECUTION PLAN

```
HOUR 1-2: Voice Layer Stabilization
├─ Gemini chat integration into bridge.py
├─ Test: 2-min voice loop
├─ Error handling + logging
└─ Branch: voice/gemini-integration

HOUR 3-4: Planner + Executor Foundation
├─ Create server/agents/task_planner_agent.py
├─ Create server/agents/executor_agent.py
├─ Define action_registry.json
└─ Branch: agents/planner-executor

HOUR 5-6: Task Bus Enhancement
├─ Integrate planner into task_bus.py
├─ Error handler (retry logic)
├─ Test: 3-step task execution
└─ Branch: tasks/error-recovery

HOUR 7-8: Memory System Upgrade
├─ Enhance memory extraction (every turn)
├─ Add aggressive memory logging
├─ Test: Learn preferences in 5 turns
└─ Branch: memory/aggressive-extraction

HOUR 9-10: Integration + Testing
├─ Merge all branches to main
├─ Full e2e test (voice → plan → execute → report)
├─ Telegram notification
└─ READY FOR PRODUCTION
```

---

## 📋 TASK BREAKDOWN (Codex Ahmet Distribution)

### **Ahmet-1 (Lead Architect)**
**Focus:** Voice → Bridge Integration  
**Hours:** 1-2  
**Tasks:**
- [ ] Integrate gemini_simple_chat.py into bridge.py
- [ ] Add `/voice-test` command (5-min loop)
- [ ] Implement fallback to Piper TTS
- [ ] Error handling for API failures
- [ ] Logging to server/logs/voice.jsonl
- [ ] Test: Respond to "Merhaba Jarvis"
- [ ] Commit: feat(voice): gemini-bridge-integration

**Codex Access:** Read bridge.py, write server/voice/

---

### **Ahmet-2 (Planner Specialist)**
**Focus:** Multi-step Task Planning  
**Hours:** 2-3  
**Tasks:**
- [ ] Design task_planner_agent.py (Mark-XXXV pattern)
- [ ] Implement plan() function → step list
- [ ] Max 7 steps per plan
- [ ] Validate each step against action_registry
- [ ] Return: {"steps": [...], "reasoning": "..."}
- [ ] Test: Plan a 3-step goal
- [ ] Commit: feat(agents): task-planner

**Codex Access:** Create server/agents/task_planner_agent.py

---

### **Ahmet-3 (Executor Engineer)**
**Focus:** Step Execution + Tools  
**Hours:** 3-4.5  
**Tasks:**
- [ ] Create executor_agent.py
- [ ] Implement execute_step(step) → result
- [ ] Tool invocation (bridge command calls)
- [ ] Error catching per step
- [ ] Result aggregation
- [ ] Test: Execute 3 Jarvis skills
- [ ] Commit: feat(agents): executor

**Codex Access:** Create server/agents/executor_agent.py, read server/skills/

---

### **Ahmet-4 (Error Recovery)**
**Focus:** Intelligent Replanning  
**Hours:** 4.5-6  
**Tasks:**
- [ ] Create error_handler_agent.py
- [ ] Analyze error → root cause
- [ ] Decision: RETRY | REPLAN | SKIP | ABORT
- [ ] If REPLAN: call planner with updated context
- [ ] Max 2 replan attempts
- [ ] Logging all errors + decisions
- [ ] Test: Fail task → auto-replan → success
- [ ] Commit: feat(agents): error-handler

**Codex Access:** Create server/agents/error_handler_agent.py, read planner/executor

---

### **Ahmet-5 (Integration Master)**
**Focus:** Full System Integration + Testing  
**Hours:** 6-10  
**Tasks:**
- [ ] Create action_registry.json (all 74 skills)
- [ ] Integrate planner → executor → error_handler into task_bus.py
- [ ] Full e2e test: voice input → parse goal → plan → execute → report
- [ ] Test Telegram notification with success metrics
- [ ] Merge all branches: voice/ agents/ tasks/ → main
- [ ] Final smoke test: 10-min autonomous loop
- [ ] Commit: chore(integration): week1-complete
- [ ] Document: WEEK1_COMPLETION.md

**Codex Access:** Full write access (orchestrator role)

---

## 🔄 PARALLEL WORKFLOW

```
TIME  │ AHMET-1      │ AHMET-2      │ AHMET-3      │ AHMET-4      │ AHMET-5
──────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────
1h    │ Bridge int.  │ Plan design  │ (waiting)    │ (waiting)    │ (waiting)
2h    │ Voice test   │ Plan code    │ Executor des │ (waiting)    │ (waiting)
3h    │ Error handle │ Plan test    │ Executor cod │ Error design │ Registry
4h    │ Commit       │ Commit       │ Executor tes │ Error code   │ Task Bus
5h    │ (review)     │ (review)     │ (review)     │ Error test   │ Task Bus II
6h    │ (ready)      │ (ready)      │ (ready)      │ (commit)     │ Integration
7h    │ ─────────────────────────────────────────────────────────┼─ E2E TEST
8h    │ ─────────────────────────────────────────────────────────┼─ Loop test
9h    │ ─────────────────────────────────────────────────────────┼─ Merge all
10h   │ ─────────────────────────────────────────────────────────┼─ Smoke test
```

---

## 📊 SUCCESS CRITERIA

### Hour 2 Checkpoint
- [ ] `/voice-test` command returns Gemini response
- [ ] Logging shows 5-min conversation
- [ ] No Gemini API errors

### Hour 4 Checkpoint
- [ ] Planner.plan() outputs valid step list
- [ ] Executor.execute_step() runs Jarvis command
- [ ] Error handler catches failures

### Hour 6 Checkpoint
- [ ] Task Bus accepts planned steps
- [ ] Auto-replan on error
- [ ] All 74 skills in action_registry

### Hour 10 Checkpoint (GO/NO-GO)
- [ ] Full e2e: voice → plan → execute → report
- [ ] Telegram notification sent
- [ ] 10-min autonomous loop = SUCCESS
- [ ] Zero API quota issues
- [ ] Ready for production Week 2

---

## 🛑 GUARDRAILS

**DO NOT:**
- ❌ Break existing bridge.py (test before committing)
- ❌ Use >50% Codex quota (conservative approach)
- ❌ Commit to main without testing
- ❌ Skip error handling "for speed"
- ❌ Wake Ekrem (only commit + notify when DONE)

**DO:**
- ✅ Test each component in isolation first
- ✅ Commit working code (even if partial)
- ✅ Log all decisions + errors
- ✅ Merge to main only if ALL tests pass
- ✅ Document what you built

---

## 📝 OUTPUT ARTIFACTS

**Code:**
- server/voice/gemini_bridge_integration.py
- server/agents/task_planner_agent.py
- server/agents/executor_agent.py
- server/agents/error_handler_agent.py
- server/config/action_registry.json
- (Updated) server/skills/task_bus.py

**Branches:**
- voice/gemini-integration
- agents/planner-executor
- tasks/error-recovery
- memory/aggressive-extraction
- integration/week1-complete (main)

**Logs:**
- server/logs/voice.jsonl
- server/logs/planner.jsonl
- server/logs/executor.jsonl
- server/logs/errors.jsonl

**Documentation:**
- WEEK1_COMPLETION.md (what was built)
- NEXT_WEEK_PLAN.md (Week 2 roadmap)

---

## 🎯 FINAL DELIVERABLE

When all 10 hours complete:

1. **Branch:** main
2. **Commit:** "chore(week1): Gemini voice + planner-executor complete"
3. **Status:** ✅ READY FOR PRODUCTION
4. **Telegram Alert:** "Jarvis Week 1 complete. Voice + AI planning ready. Test autonomous loop?"
5. **Files Ready:**
   - Voice: `python server/voice/gemini_simple_chat.py` (test)
   - Planning: `python -c "from agents.task_planner_agent import plan; plan(...)"`
   - E2E: Run 10-min autonomous loop (no errors)

---

## 🚀 LAUNCH COMMAND

```bash
# Run all 5 Ahmet's in parallel (Codex background)
/codex-background --team jarvis-week1 --agents 5 --mode aggressive --quota conservative --watch-mode off

# Output: WEEK1_COMPLETION.md + ready for next phase
```

**Status: READY FOR EXECUTION**

Time to build. Let's go. 🔨

