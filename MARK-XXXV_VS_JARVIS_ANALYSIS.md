# Mark-XXXV vs Jarvis — Comprehensive Comparison & Integration Strategy

**Date:** 2026-04-04  
**Prepared by:** Claude Haiku 4.5  
**Status:** Final Analysis — Ready for Integration Planning

---

## Executive Summary

**Mark-XXXV** (by FatihMakes) and **Jarvis Mission Control** (by Ekrem) are complementary AI systems targeting different operating modes:

| Aspect | Mark-XXXV | Jarvis |
|--------|-----------|--------|
| **Primary Focus** | Real-time voice interaction + PC control | Autonomous 24-hour operation + multi-channel delivery |
| **Target Audience** | Single-user interactive assistant | Enterprise automation + team coordination |
| **Deployment Model** | Local-first, single machine | Swarm-capable, multi-agent, networked |
| **Architecture** | Action-centric (17 modules) | Orchestration-centric (29 agents + 74 skills) |
| **Voice Strategy** | Native audio in/out (Gemini 2.5 Flash) | TTS/STT middleware (Piper + RealtimeSTT) |
| **Output Channels** | UI + Voice | Telegram + Web Dashboard + Hologram |
| **Memory Model** | Conversational (identity/preferences/projects) | Hierarchical (L0/L1/L2) + SQLite |
| **Autonomy** | Task execution (on-demand) | Continuous loops (hourly reports) |

**Strategic Recommendation:** Adopt Mark-XXXV's **planner-executor-memory pattern** into Jarvis while preserving Jarvis's **orchestration and autonomous loop capabilities**.

---

## System Architecture Comparison

### Mark-XXXV Architecture

```
┌─────────────────────────────────────┐
│         UI (Electron/PyQt)          │ ← Status indicators, F4 mute, keyboard input
│    LISTENING / SPEAKING / THINKING  │
└──────────────┬──────────────────────┘
               │
        ┌──────▼──────┐
        │  main.py    │ ← Entry point: voice stream handler
        └──────┬──────┘
               │
       ┌───────┴──────────────────────────┐
       │                                  │
   ┌───▼───┐                      ┌──────▼──────┐
   │ AUDIO │ ◄──Gemini 2.5 Flash──┤  LLM LOOP   │
   │ (STT) │   (native-audio-     │  (async)    │
   └───┬───┘    preview)          └──────┬──────┘
       │                                  │
       └──────────────┬───────────────────┘
                      │
              ┌───────▼────────┐
              │  Agent Layer   │
              ├────────────────┤
              │ • Planner      │ ← Break task into steps
              │ • Executor     │ ← Run tools + handle errors
              │ • Error        │ ← Analyze failures, replan
              │   Handler      │
              └───────┬────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
  ┌───▼────┐  ┌──────▼──────┐ ┌─────▼────┐
  │ Actions│  │   Memory    │ │  Config  │
  │ (17x)  │  │   Manager   │ │  (API    │
  │        │  │             │ │   keys)  │
  │Apps    │  │ JSON storage│ │          │
  │Files   │  │ Thread lock │ │          │
  │Browser │  │ Extraction  │ │          │
  │Games   │  │ Prompt      │ │          │
  └────────┘  └─────────────┘ └──────────┘
```

**Key Components:**
1. **main.py** — Audio stream handler, Gemini native audio loop
2. **agent/planner.py** — Multi-step task planning (max 5 steps)
3. **agent/executor.py** — Tool invocation, code generation, error handling
4. **agent/error_handler.py** — Failure analysis, replanning decision
5. **memory/memory_manager.py** — JSON-based hierarchical memory (identity/preferences/projects/relationships)
6. **actions/** — 17 domain-specific modules (flight_finder, browser_control, game_updater, etc.)

**Strengths:**
✅ **Native real-time voice** via Gemini 2.5 Flash (native audio preview)  
✅ **Planner-executor pattern** — clean separation of concerns  
✅ **Rich action library** — 17 pre-built modules covering common tasks  
✅ **Persistent conversational memory** — learns user preferences, projects, relationships  
✅ **Error introspection** — analyze failures and replan intelligently  
✅ **Game/Steam integration** — native support for game updates, auto-shutdown  
✅ **Mute button + UI feedback** — user control (F4 toggle, status indicators)  

---

### Jarvis Architecture

```
┌─────────────────────────────────────────────────────┐
│    Telegram + Web Dashboard + Desktop Hologram      │
│         (Multi-channel output layer)                │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────▼──────────────────┐
        │   bridge.py (Orchestrator)      │
        │  ──────────────────────────     │
        │  • Command router                │
        │  • Model selection (local/cloud) │
        │  • Permission layer (Task Bus)   │
        │  • Corporate hierarchy           │
        │  • Gateway management (8082)     │
        └────────────────┬─────────────────┘
                         │
      ┌──────────────────┼──────────────────────┐
      │                  │                      │
  ┌───▼────┐  ┌────────▼──────┐  ┌─────────▼──┐
  │ Agents │  │    Skills     │  │  Model     │
  │ (29x)  │  │    (74x)      │  │  Router    │
  │        │  │               │  │            │
  │Analysis│  │Domain-specific│  │  Local:    │
  │Agents  │  │ utilities     │  │  Ollama    │
  │        │  │               │  │            │
  │Video   │  │ Marketing,    │  │  Cloud:    │
  │Link    │  │ Engineering,  │  │  Google    │
  │        │  │ Finance,      │  │  OpenAI    │
  │Swarm   │  │ etc.          │  │  OpenRouter│
  │        │  │               │  │            │
  │Corp    │  │ Workflow      │  │            │
  │Coord   │  │ templates     │  │            │
  └────────┘  └───────────────┘  └────────────┘
                      │
      ┌───────────────┼─────────────────┐
      │               │                 │
 ┌────▼────┐  ┌──────▼──────┐  ┌──────▼─────┐
 │ Task Bus │  │  Permission │  │  Gateway   │
 │ & Queue  │  │  Layer      │  │  (multi-   │
 │          │  │             │  │   provider)│
 │Dispatcher│  │Policy eval  │  │            │
 │Priority  │  │Audit log    │  │ Port 8082  │
 │Track     │  │Redaction    │  │            │
 └──────────┘  └─────────────┘  └────────────┘
```

**Key Components:**
1. **bridge.py** — Central orchestrator (3500+ lines), router, permissions
2. **agents/** — 29 analysis agents (video, instagram, video_link, etc.)
3. **skills/** — 74 reusable skills (marketing, engineering, finance, etc.)
4. **gateway/server.py** — Multi-provider proxy (Ollama, OpenAI, Codex, Gemini)
5. **task_bus.py** — Queue dispatcher with permissions, priorities, audit
6. **runtime_state.py** — Heartbeat, lock management, state persistence
7. **server/logs/** — JSON memory storage (hierarchical L0/L1/L2)

**Strengths:**
✅ **Multi-channel orchestration** — Telegram, Web, Hologram unified  
✅ **Swarm-ready architecture** — Corporate hierarchy, multi-agent dispatch  
✅ **Autonomous loops** — 24-hour continuous operation with hourly reports  
✅ **Rich model ecosystem** — Local-first fallback chain (Ollama → Google → OpenRouter)  
✅ **Enterprise features** — Task Bus, permissions, audit logging, role-based control  
✅ **Skill composition** — 74 reusable skills across 21 domains  
✅ **Persistent state** — Hierarchical memory with SQLite backend  

---

## Detailed Feature Comparison

### 1. Voice & Audio

| Feature | Mark-XXXV | Jarvis | Winner |
|---------|-----------|--------|--------|
| **Audio Input** | PyAudio (native, real-time) | RealtimeSTT (cloud-ready) | Mark-XXXV (lower latency) |
| **Audio Output** | Gemini native (native-audio-preview) | Piper TTS (local) | Mark-XXXV (natural voice) |
| **Streaming** | Full duplex (native) | STT → Bridge → TTS | Mark-XXXV |
| **Language Support** | Any (Gemini support) | Multi-language | Tie |
| **Mute Control** | F4 hotkey + UI click | Manual telegram command | Mark-XXXV |
| **Voice Quality** | Excellent (Gemini trained) | Good (Piper) | Mark-XXXV |

**Recommendation:** Adopt Mark-XXXV's native audio stream + Gemini 2.5 Flash into Jarvis voice layer.

---

### 2. Task Planning & Execution

| Feature | Mark-XXXV | Jarvis | Winner |
|---------|-----------|--------|--------|
| **Planning** | Planner (5 step max) | No planner (direct dispatch) | Mark-XXXV |
| **Execution** | Executor (runs tools) | Agents (analyze) + Skills | Tie |
| **Error Handling** | Error Handler (replan) | Basic try/catch | Mark-XXXV |
| **Replanning** | Yes (smart replan) | No (fixed routes) | Mark-XXXV |
| **Tool Invocation** | Direct (17 actions) | Via Task Bus | Tie (different models) |
| **Code Generation** | Supported (Python) | Supported (OpenCode/Codex) | Jarvis (more sophisticated) |

**Recommendation:** Adopt Mark-XXXV's planner-executor-error-handler into Jarvis task dispatch layer.

---

### 3. Memory & Learning

| Feature | Mark-XXXV | Jarvis | Winner |
|---------|-----------|--------|--------|
| **Memory Format** | JSON (identity/prefs/projects) | SQLite + JSON (hierarchical) | Jarvis |
| **Persistence** | File-based | DB + file-based | Jarvis |
| **Hierarchy** | 6 categories (flat) | 3 levels (L0/L1/L2) | Jarvis |
| **Extraction** | LLM-driven (aggressive) | Manual (agent-driven) | Mark-XXXV (auto) |
| **Thread Safety** | Lock-based | Lock-based | Tie |
| **Truncation** | Yes (400 char max) | Unlimited | Tie |
| **Recall Speed** | Instant (file) | Query-based | Mark-XXXV |

**Recommendation:** Enhance Jarvis's memory with Mark-XXXV's aggressive extraction + category-based organization.

---

### 4. Actions & Skills

| Feature | Mark-XXXV | Jarvis | Winner |
|---------|-----------|--------|--------|
| **Action Count** | 17 modules | 74 skills | Jarvis |
| **Categories** | App/File/Browser/Game/System | 21 domains | Jarvis |
| **Browser Control** | Playwright native | yt-dlp + manual | Mark-XXXV |
| **Game Management** | Steam/Epic native | None | Mark-XXXV |
| **Code Execution** | Python generation | OpenCode/Codex | Jarvis |
| **File System** | Direct access | Direct access | Tie |
| **Web Search** | Native (web_search) | Serper API | Tie |

**Recommendation:** Add Mark-XXXV's game_updater + browser_control to Jarvis's skill library.

---

### 5. Output Channels

| Feature | Mark-XXXV | Jarvis | Winner |
|--------|-----------|--------|--------|
| **Voice Output** | Native audio | Piper TTS | Mark-XXXV |
| **UI/Visual** | Electron app (status) | Web + Hologram | Jarvis |
| **Messaging** | Console | Telegram | Jarvis |
| **Logging** | Console + traceback | JSON logs | Jarvis |
| **Multi-channel** | No | Yes | Jarvis |

**Recommendation:** Integrate Mark-XXXV's native audio into Jarvis's existing multi-channel system.

---

### 6. Autonomy & Reliability

| Feature | Mark-XXXV | Jarvis | Winner |
|---------|-----------|--------|--------|
| **Continuous Operation** | Interactive (on-demand) | 24-hour loops | Jarvis |
| **Heartbeat** | None | Yes (5s intervals) | Jarvis |
| **Process Lock** | None | Yes (single instance) | Jarvis |
| **State Persistence** | Memory file | Heartbeat + JSON | Jarvis |
| **Restart Handling** | None | Yes (watchdog) | Jarvis |
| **Error Recovery** | Replan | Task retry | Tie |

**Recommendation:** Keep Jarvis's autonomy system; add Mark-XXXV's error recovery.

---

## Integration Strategy

### Phase 1: Adopt Mark-XXXV's Core Patterns (Week 1)

**Goal:** Integrate planner-executor-error-handler into Jarvis's task dispatch.

#### 1.1 Planner Module
```python
# server/agents/task_planner_agent.py (NEW)
# Similar to Mark-XXXV's agent/planner.py
# But outputs to Jarvis's Task Bus format

def plan_task(user_goal: str, available_tools: list) -> list[dict]:
    """
    Break goal into max 7 steps (vs Mark's 5).
    Each step: {"action": tool_name, "params": {...}, "description": str}
    """
    pass

# Integrated into bridge.py:
# IF user_message contains multi-step intent:
#   steps = plan_task(message, get_available_tools())
#   FOR each step:
#     result = execute_step(step)
#     IF error: attempt replan()
```

**Integration Point:** `server/bridge.py` → `elif command == "/takim-planla"`

#### 1.2 Error Handler Module
```python
# server/agents/error_handler_agent.py (NEW)
# Similar to Mark-XXXV's agent/error_handler.py

def analyze_error(error_str: str, last_step: dict) -> ErrorDecision:
    """
    Analyze error using LLM.
    Decide: RETRY | REPLAN | ABORT | SKIP
    """
    pass

# Integrated into bridge.py Task Bus:
# IF task_result.error:
#   decision = analyze_error(error_text, task_definition)
#   EXECUTE decision (replan, retry, abort)
```

**Integration Point:** `server/skills/task_bus.py` → error handling path

#### 1.3 Memory Extraction
```python
# server/logs/memory_extraction.py (ENHANCED)
# Adopt Mark-XXXV's aggressive extraction

def should_extract_memory(user_text: str, jarvis_text: str) -> bool:
    """Every turn check (not every 3 turns)."""
    criteria = [
        len(user_text) > 5,
        not is_greeting(user_text),
        has_personal_info(user_text),  # Mark-XXXV pattern
    ]
    return any(criteria)  # Mark: more aggressive

def extract_memory(text: str, memory_context: dict) -> dict:
    """
    Extract with 6-category prompt (identity, preferences, projects, 
    relationships, wishes, notes) — Mark-XXXV style.
    """
    pass
```

**Integration Point:** `server/logs/memory.jsonl` → enhance extraction

---

### Phase 2: Integrate Voice Layer (Week 2)

**Goal:** Add Mark-XXXV's native audio stream + Gemini 2.5 Flash.

#### 2.1 Audio Stream Handler
```python
# server/voice/native_audio_stream.py (NEW)
# Adapt from Mark-XXXV's main.py audio loop

import pyaudio
from google import genai

def native_audio_loop(api_key: str):
    """
    Real-time audio stream to Gemini 2.5 Flash (native-audio-preview).
    Output: voice response (no TTS needed).
    """
    pass

# Alternative: Fallback to existing RealtimeSTT if Gemini unavailable
```

**Integration Point:** `server/voice/hey_jarvis.py` → new audio thread

#### 2.2 Voice Priority in Bridge
```python
# server/bridge.py → _handle_voice_message()
# IF native_audio_available:
#   response = native_audio_loop()  # Mark-XXXV style
# ELSE:
#   response = existing_flow()  # Fallback
```

**Integration Point:** `server/bridge.py` → voice dispatch

---

### Phase 3: Enhance Skills & Actions (Week 3)

**Goal:** Add Mark-XXXV's 17 actions to Jarvis's 74 skills.

#### 3.1 Port Mark-XXXV Actions
```
NEW skills:
  server/skills/game_updater_skill.py      (Mark: game_updater.py)
  server/skills/advanced_browser_skill.py  (Mark: browser_control.py)
  server/skills/code_generation_skill.py   (Mark: code_helper.py + executor.py)
  server/skills/flight_finder_skill.py     (Mark: flight_finder.py)
  server/skills/screen_intelligence_skill.py (Mark: screen_processor.py)

Bridge commands:
  /oyun-guncelle [game-name]     → game_updater_skill
  /browser [action]              → advanced_browser_skill
  /uçak-bul [route]              → flight_finder_skill
  /ekran-analiz                  → screen_intelligence_skill
```

**Integration Point:** `server/bridge.py` → new command handlers

#### 3.2 Unified Action Registry
```python
# server/config/action_registry.json (NEW)
{
  "actions": {
    "game_updater": {
      "params": ["action", "platform", "game_name"],
      "category": "system",
      "mark_origin": true
    },
    "browser_control": {
      "params": ["action", "url", "query"],
      "category": "web",
      "mark_origin": true
    },
    // ... existing Jarvis skills
  }
}

# Planner can reference this to validate step parameters
```

---

### Phase 4: UI Integration (Week 4)

**Goal:** Add Mark-XXXV's status indicators to Jarvis Hologram.

#### 4.1 Status Indicator UI
```javascript
// apps/desktop-hologram/src/components/VoiceStatus.tsx (ENHANCE)
// Add Mark-XXXV style indicators:
// LISTENING (green pulse)
// THINKING (blue spin)
// SPEAKING (orange wave)
// MUTED (red X)

export function VoiceStatusIndicator() {
  const [status, setStatus] = useState<'listening' | 'thinking' | 'speaking' | 'muted'>('listening');
  // Connect to server/voice/voice_status.json
}
```

#### 4.2 Mute Toggle
```javascript
// apps/desktop-hologram/src/hooks/useVoiceMute.ts (NEW)
// Global hotkey: F4 (Mark-XXXV style)
// Telegram: /sesini-kapat

window.addEventListener('keydown', (e) => {
  if (e.code === 'F4') {
    toggleVoiceMute();
  }
});
```

**Integration Point:** `apps/desktop-hologram/` → voice status layer

---

### Phase 5: Autonomous Loop Enhancement (Week 5)

**Goal:** Add error recovery + replanning to 24-hour loop.

#### 5.1 Loop with Planner
```python
# scripts/start_24h_autonomous_loop.py (ENHANCE)

async def hour_cycle(self, hour: int):
    # Current implementation
    report = { "phases": {} }
    
    # NEW: Add planner-executor pattern
    goal = f"Improve Jarvis throughput metric by 5% in hour {hour}"
    plan = await self.planner.plan_task(goal)  # NEW
    
    for step in plan:
        try:
            result = await self.executor.run_step(step)  # NEW
            report["phases"][step["action"]] = result
        except Exception as e:
            decision = await self.error_handler.analyze(e, step)  # NEW
            if decision == "REPLAN":
                plan = await self.planner.replan(goal, e)
            elif decision == "SKIP":
                continue
            # ... etc
    
    return report
```

**Integration Point:** `scripts/start_24h_autonomous_loop.py` → planner integration

---

## Risk Assessment & Mitigation

### Risk 1: Native Audio Stream Conflicts

**Risk:** Gemini 2.5 Flash native audio may conflict with existing Piper TTS + RealtimeSTT.

**Mitigation:**
- Run native audio in separate thread
- Implement toggle: `ENABLE_NATIVE_AUDIO=1` env var
- Fallback to existing stack if Gemini API fails
- Queue audio requests if both active

**Owner:** Voice team (Week 2)

---

### Risk 2: Planner Step Validation

**Risk:** Planner may generate invalid tool names or parameters.

**Mitigation:**
- Validate each step against `action_registry.json` before execution
- Error handler catches invalid steps + rereplans
- Logging all plan rejections to `server/logs/invalid_plans.jsonl`
- Rate-limit replanning (max 3 attempts per goal)

**Owner:** Task Bus team (Week 1)

---

### Risk 3: Memory Extraction Rate

**Risk:** Mark-XXXV's aggressive (every-turn) extraction may increase LLM costs.

**Mitigation:**
- Batch extractions (every 5 turns) by default
- Use local Ollama for extraction (cheaper than cloud)
- Fallback: extract only on high-confidence signals
- Monitor cost in `server/logs/memory_extraction_cost.jsonl`

**Owner:** Memory team (Week 1)

---

### Risk 4: Game Updater Permissions

**Risk:** Auto-shutdown / game installation may trigger security policies.

**Mitigation:**
- Require explicit Telegram confirmation before install/update
- Only allow for whitelisted games in config
- Log all game operations to audit log
- Disable by default (`ENABLE_GAME_MANAGEMENT=0`)

**Owner:** Security team (Week 3)

---

## Implementation Roadmap

### Week 1: Foundation (Planner + Error Handler)
- [ ] Create `server/agents/task_planner_agent.py`
- [ ] Create `server/agents/error_handler_agent.py`
- [ ] Enhance `server/skills/task_bus.py` with error path
- [ ] Create `server/config/action_registry.json`
- [ ] Test: `/takim-planla` command with 3-step task
- [ ] Test: Error recovery with replan

**Deliverable:** Planner working in Task Bus, 1-2 test tasks

---

### Week 2: Voice Layer (Native Audio)
- [ ] Create `server/voice/native_audio_stream.py`
- [ ] Add Gemini 2.5 Flash integration
- [ ] Implement fallback to RealtimeSTT
- [ ] Add env toggle `ENABLE_NATIVE_AUDIO`
- [ ] Update hologram to show audio thread status
- [ ] Test: Native audio loop (10 min)

**Deliverable:** Voice working via native audio OR RealtimeSTT fallback

---

### Week 3: Skills & Actions (Port Mark-XXXV)
- [ ] Port 5 priority actions (game, browser, flight, code, screen)
- [ ] Create bridge commands for each
- [ ] Update `server/config/action_registry.json`
- [ ] Write smoke tests for each new skill
- [ ] Documentation: `/oyun-guncelle` usage

**Deliverable:** 5 new Mark-XXXV skills working in bridge

---

### Week 4: UI (Status Indicators)
- [ ] Create `VoiceStatusIndicator` React component
- [ ] Add F4 hotkey handler
- [ ] Add `/sesini-kapat` telegram command
- [ ] Update hologram with status widget
- [ ] Test: Toggle mute 5 times, verify UI

**Deliverable:** Voice status visible on hologram + F4 working

---

### Week 5: Autonomous Loop (Planner Integration)
- [ ] Integrate planner into `start_24h_autonomous_loop.py`
- [ ] Add error handler to hourly cycle
- [ ] Update metrics to track plan success rate
- [ ] Test: 1-hour loop with planned improvements
- [ ] Measure: throughput improvement with planner vs without

**Deliverable:** 24-hour loop running with smart replanning

---

## What to Preserve in Jarvis

✅ **Keep these Jarvis strengths:**
1. **Multi-channel orchestration** (Telegram + Web + Hologram)
2. **Autonomous 24-hour loops** with hourly reporting
3. **Enterprise features** (Task Bus, permissions, audit logs)
4. **Skill library** (74 skills across 21 domains)
5. **Multi-provider model router** (local-first fallback)
6. **Corporate hierarchy** and swarm architecture
7. **State persistence** (heartbeat, lock, watchdog)

---

## What to Adopt from Mark-XXXV

✅ **Adopt these Mark-XXXV strengths:**
1. **Planner-executor pattern** for multi-step task planning
2. **Intelligent error handler** with replanning
3. **Aggressive memory extraction** (every turn, 6 categories)
4. **Native audio stream** (Gemini 2.5 Flash)
5. **Rich action library** (game_updater, browser_control, etc.)
6. **UI status indicators** (LISTENING/SPEAKING/THINKING/MUTED)
7. **F4 mute hotkey** for user control

---

## Success Criteria

By end of Week 5, Jarvis should:

- [ ] **Planner working:** Multi-step task planning → Task Bus dispatch
- [ ] **Error recovery working:** Failed tasks → replan → retry
- [ ] **Voice improved:** Native audio (if available) OR RealtimeSTT fallback
- [ ] **5 new actions:** game, browser, flight, code, screen
- [ ] **UI enhanced:** Status indicators + F4 mute
- [ ] **Loop improved:** 24-hour autonomous with planner integration
- [ ] **Backwards compatible:** Existing Jarvis commands still work
- [ ] **Zero regressions:** All 29 agents + 74 skills still functional

**Metric:** Successful execution of 3-step task + 1-hour autonomous loop = Integration complete.

---

## 🤖 Model Resources & Recommendations

### Local Models for Jarvis (No Cloud Dependency)

#### **AirLLM** — Run 70B Models on 4GB GPU
```
Technology: Layer-wise inference (loads one layer at a time)
├─ 70B model: 4GB GPU + 8GB VRAM
├─ 405B model: Passable with optimization
├─ Supports: Llama, Qwen, Mistral
├─ Platforms: Linux, Windows, macOS
└─ License: 100% Open Source

Jarvis Use: Fallback for large models
├─ Current: Ollama + Llama 3.2
├─ New: Ollama OR AirLLM (automatic selection)
├─ Benefit: Bigger models, same hardware
└─ GitHub: https://github.com/samadhaan/airllm
```

#### **Qwen 2.5 Series** — Best Turkish Support
```
Variants:
├─ Qwen 2.5 7B (lightweight, 2GB VRAM)
├─ Qwen 2.5 14B (balanced, 8GB VRAM) ← Recommended
├─ Qwen 2.5 72B (powerful, 8GB with AirLLM)
├─ Qwen QwQ-32B (specialized reasoning)
└─ Qwen Coder (code generation)

Turkish Language:
├─ Native Turkish support (trained on Turkish data)
├─ Better than Llama for Turkish tasks
├─ Instruction-following in Turkish

Jarvis Integration:
├─ Primary local model (replace Llama 3.2)
├─ Voice reasoning (Turkish understanding)
└─ Kaynak: https://github.com/QwenLM/Qwen2.5
```

#### **Gemma 4 & Gemini Nano 4** — Google's Lightweight
```
Gemma 4:
├─ 9B parameters
├─ 4GB VRAM
├─ On-device inference
├─ Free Hugging Face: google/gemma-2-9b

Gemini Nano 4:
├─ Mobile/embedded optimized
├─ Offline capable (TensorFlow Lite)
├─ 2x faster than Gemma 2
├─ Android/iOS native

Jarvis Voice Layer:
├─ Replace Piper TTS with Gemini Nano 4
├─ On-device voice reasoning
└─ No cloud dependency for voice
```

#### **Mistral Models** — Lightweight & Fast
```
Mistral 7B:
├─ 7B parameters
├─ 2GB VRAM only
├─ 50+ tokens/sec
├─ Apache 2.0 (commercial OK)
└─ Hugging Face: mistralai/Mistral-7B-Instruct-v0.2

Codestral:
├─ Code-specialized
├─ Function calling optimized
├─ Better than generic models for tools
└─ Kaynak: https://mistral.ai

Jarvis Use: Code generation + tool calling
```

### Cloud Models (Fallback & Specialized)

#### **Gemini API** — Current Recommended (Primary)
```
Tiers:
├─ Gemini 2.5 Flash (fast, recommended)
├─ Gemini 2.5 Pro (complex tasks)
├─ Gemini 1.5 Flash (cost optimized)
└─ Gemini 1.5 Pro (quality)

Features:
├─ Native audio (voice in/out)
├─ Vision (image analysis)
├─ Function calling
├─ 1500 free queries/day

Kaynak: https://aistudio.google.com/apikey
Cost: Free tier generous, paid: $0.075/1M tokens
```

#### **OpenAI GPT-4 Series**
```
Models:
├─ GPT-4o (multimodal, best value)
├─ GPT-4 Turbo (complex reasoning)
└─ GPT-3.5 Turbo (cost optimized, fallback)

Cost:
├─ GPT-4o: $2.50/1M input tokens
├─ GPT-3.5 Turbo: $0.50/1M input tokens

Jarvis Role: Secondary fallback, code analysis
```

#### **Claude API** — Quality Focus
```
Latest: Claude 4.6 (recommended)
├─ Extended thinking (adaptive)
├─ 200K context window
├─ 10M tokens/month free trial
└─ Best code analysis

Kaynak: https://claude.ai/claude-code
```

#### **Mistral API** — Budget-Friendly
```
Models:
├─ Mistral Large (powerful)
├─ Mistral Small (fast, cheap)
└─ Codestral (code specialized)

Pricing: $0.0015 per 1K input tokens (cheapest)
```

### Jarvis Recommended Model Stack (2026)

```
Layer 1 (Primary — Always Try):
├─ API: Gemini 2.5 Flash
├─ Latency: ~500ms
├─ Cost: Free tier (1500 req/day)
└─ Features: Voice, Vision, Functions

Layer 2 (Local Fallback):
├─ Ollama + Qwen 2.5 14B
├─ Latency: ~500ms-2s
├─ Cost: $0
└─ Features: Offline, Türkçe, Reliable

Layer 3 (Large Model Fallback):
├─ AirLLM + Qwen 2.5 72B
├─ Latency: 2-5s (layer-wise)
├─ Cost: $0
├─ VRAM: 8GB (optimized)
└─ When: Complex reasoning needed

Layer 4 (Cloud Backup):
├─ OpenAI GPT-3.5 Turbo
├─ Latency: ~2s
├─ Cost: $0.50/1M tokens
└─ When: Local unavailable, budget OK

Specialized:
├─ Code: Codestral (API) or Qwen Coder (local)
├─ Vision: Gemini 2.5 Flash (native)
├─ Voice: Gemini Nano 4 (on-device)
└─ Turkish: Qwen 2.5 (all variants)
```

### .env Configuration

```bash
# Primary LLM
PRIMARY_LLM=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=models/gemini-2.5-flash

# Local Fallback
OLLAMA_ENABLED=1
OLLAMA_MODEL=qwen2.5:14b
OLLAMA_URL=http://localhost:11434

# Large Model Fallback (Optional)
AIRLLM_ENABLED=1
AIRLLM_MODEL=qwen2.5:72b

# Secondary Cloud (Optional)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# Code Specialization
CODE_MODEL=codestral
VISION_MODEL=gemini-2.5-flash
VOICE_MODEL=gemini-nano-4

# Performance
MODEL_TIMEOUT_SECONDS=30
FALLBACK_ON_TIMEOUT=1
```

### Model Selection Algorithm

```python
def select_model(task_type, user_preference="fast"):
    """
    Auto-select best model for task
    """
    if task_type == "voice":
        return "gemini-2.5-flash"  # Native audio
    elif task_type == "code":
        return "codestral" if api_available else "qwen-coder"
    elif task_type == "vision":
        return "gemini-2.5-flash"  # Native vision
    elif task_type == "turkish_reasoning":
        return "qwen2.5:14b"  # Best Turkish
    elif task_type == "complex_reasoning":
        if offline_only:
            return "qwen2.5:72b" (AirLLM)
        else:
            return "gemini-2.5-pro"
    
    # Default
    if user_preference == "fast":
        return "gemini-2.5-flash"
    elif user_preference == "cheap":
        return "ollama:qwen2.5:7b"
    elif user_preference == "offline":
        return "ollama:qwen2.5:14b"
    else:
        return "gemini-2.5-flash"  # balanced default
```

---

## Code Locations Summary

### Mark-XXXV Reference Files (external-repos/Mark-XXXV/)
- `main.py` — Audio stream handler, Gemini loop
- `agent/planner.py` — Task planning logic
- `agent/executor.py` — Tool execution + code generation
- `agent/error_handler.py` — Error analysis + replanning
- `memory/memory_manager.py` — Aggressive memory extraction
- `actions/` — 17 domain modules (game_updater, browser_control, etc.)
- `ui.py` — Status indicators + mute button

### Jarvis Files to Modify/Create

#### Week 1
- ✨ `server/agents/task_planner_agent.py` (NEW)
- ✨ `server/agents/error_handler_agent.py` (NEW)
- 📝 `server/config/action_registry.json` (NEW)
- 📝 `server/skills/task_bus.py` (ENHANCE — error path)

#### Week 2
- ✨ `server/voice/native_audio_stream.py` (NEW)
- 📝 `server/bridge.py` (ENHANCE — voice dispatch)
- 📝 `.env` (ADD: ENABLE_NATIVE_AUDIO, GEMINI_API_KEY)

#### Week 3
- ✨ `server/skills/game_updater_skill.py` (NEW)
- ✨ `server/skills/advanced_browser_skill.py` (NEW)
- ✨ `server/skills/flight_finder_skill.py` (NEW)
- ✨ `server/skills/code_generation_skill.py` (NEW)
- ✨ `server/skills/screen_intelligence_skill.py` (NEW)
- 📝 `server/bridge.py` (ENHANCE — 5 new commands)

#### Week 4
- ✨ `apps/desktop-hologram/src/components/VoiceStatus.tsx` (NEW)
- ✨ `apps/desktop-hologram/src/hooks/useVoiceMute.ts` (NEW)
- 📝 `apps/desktop-hologram/` (ENHANCE — hotkey handler)

#### Week 5
- 📝 `scripts/start_24h_autonomous_loop.py` (ENHANCE — planner integration)
- 📝 `server/logs/memory_extraction.py` (ENHANCE — aggressive extraction)

---

## Conclusion

**Mark-XXXV** and **Jarvis** should **merge operationally** while maintaining **architectural separation**:

1. **Adopt Mark's patterns** (planner/executor/error-handler/memory)
2. **Enhance Jarvis's capabilities** (voice, error recovery, action library)
3. **Preserve Jarvis's strengths** (autonomy, orchestration, enterprise features)
4. **Create unified product** that is both interactive (Mark-style) AND autonomous (Jarvis-style)

**Final Vision:** A single AI assistant that can:
- 🎙️ Have real-time voice conversations (Mark-XXXV)
- 🔄 Autonomously improve itself 24 hours (Jarvis)
- 📱 Reach users on Telegram/Web/Desktop (Jarvis)
- 🧠 Remember everything (both)
- 🛠️ Fix its own errors (Mark-XXXV)
- 👥 Work as a team (Jarvis)

**Next Step:** User approval → Begin Week 1 implementation (Planner + Error Handler)

---

*End of Report*
