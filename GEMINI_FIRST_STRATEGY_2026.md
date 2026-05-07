# 🔮 JARVIS MODEL STRATEGY 2026 — GEMINI FIRST

**Status:** Active Implementation  
**Scope:** Immediate (Next 8 weeks)  
**Future Review:** Q3 2026 (AirLLM, Qwen 2.5 evaluate)  

---

## 📌 Karar: Gemini-Only Start

### Neden Gemini Seçildi?

| Seçim Kriterleri | Gemini 2.5 Flash | AirLLM | Qwen 2.5 | Karar |
|------------------|------------------|--------|----------|-------|
| **Voice Native** | ✅ Mükemmel | ❌ Yok | ❌ Yok | Gemini |
| **Free Tier** | ✅ 1500 req/day | N/A | N/A | Gemini |
| **Setup Hızı** | ✅ 5 min | ⏳ 30 min | ⏳ 30 min | Gemini |
| **Türkçe** | 🟡 İyi | ✅ Mükemmel | ✅ Mükemmel | İleri |
| **Offline** | ❌ Hayır | ✅ Evet | ✅ Evet | İleri |
| **Cost** | 💰 Düşük | 💰 $0 | 💰 $0 | İleri |
| **Production Ready** | ✅ Evet | ⏳ Yeni | ✅ Evet | Gemini |

**Seçim Mantığı:**
- ✅ Hemen başlamak için en hızlı
- ✅ Voice + Vision native (Mark-XXXV pattern)
- ✅ Free tier generous (business doesn't need budget yet)
- ⏳ Qwen + AirLLM: Q3 2026 evaluate (not urgent)

---

## 🎯 GEMINI ARCHITECTURE (Immediate)

```
┌──────────────────────────────────────┐
│    USER INTERFACE                    │
│  ├─ Telegram (text + voice commands) │
│  ├─ Web Dashboard (control center)   │
│  ├─ Desktop Hologram (visual)        │
│  └─ Voice (Gemini 2.5 Flash native)  │
└────────────────┬─────────────────────┘
                 │
        ┌────────▼────────┐
        │  GEMINI API     │
        │  (Google AI)    │
        │  models/        │
        │  gemini-2.5-    │
        │  flash          │
        └────────┬────────┘
                 │
    ┌────────────┼──────────────┐
    │            │              │
┌───▼──┐  ┌─────▼────┐  ┌──────▼──┐
│Voice │  │Vision &  │  │Function │
│Input │  │Image     │  │Calling  │
│Output│  │Analysis  │  │(Tools)  │
└──────┘  └──────────┘  └─────────┘
```

---

## ⚙️ GEMINI IMPLEMENTATION ROADMAP

### Week 1-2: Voice Integration

```python
# server/voice/gemini_native_audio.py (NEW)

import asyncio
from google import genai

async def gemini_voice_loop():
    """Native audio streaming with Gemini 2.5 Flash"""
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    while True:
        # Real-time audio stream
        audio_stream = await capture_microphone()
        
        # Send to Gemini native audio
        response = await client.aio.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_audio(
                            data=audio_stream,
                            mime_type="audio/pcm"
                        )
                    ]
                )
            ]
        )
        
        # Play audio response
        await play_audio(response.audio)
```

**Integration Point:** `server/bridge.py` → Replace Piper TTS + RealtimeSTT

---

### Week 3-4: Vision & Analysis

```python
# server/agents/vision_analyzer.py (ENHANCE)

async def analyze_screen_with_gemini(screenshot_path):
    """Vision analysis using Gemini 2.5 Flash"""
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    with open(screenshot_path, "rb") as f:
        image_data = f.read()
    
    response = await client.aio.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_data(
                        data=image_data,
                        mime_type="image/png"
                    ),
                    types.Part.from_text("Analiz et ve ne gördüğünü söyle")
                ]
            )
        ]
    )
    
    return response.text
```

**Integration Point:** `server/agents/screen_processor.py` → Replace Ollama vision

---

### Week 5-6: Function Calling (Tools)

```python
# server/skills/gemini_tools.py (NEW)

async def execute_with_gemini_functions(user_request):
    """Tool execution with function calling"""
    
    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="open_app",
                    description="Open Windows application",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "app_name": types.Schema(type="STRING")
                        }
                    )
                ),
                types.FunctionDeclaration(
                    name="file_write",
                    description="Write content to file",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "file_path": types.Schema(type="STRING"),
                            "content": types.Schema(type="STRING")
                        }
                    )
                ),
                # ... more tools from Jarvis skill library
            ]
        )
    ]
    
    response = await client.aio.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=user_request,
        tools=tools
    )
    
    # Handle function calls
    for part in response.parts:
        if part.function_call:
            tool_name = part.function_call.name
            tool_args = part.function_call.args
            
            result = await execute_tool(tool_name, tool_args)
            # Send result back to Gemini
```

**Integration Point:** `server/skills/task_bus.py` → Replace direct tool dispatch

---

### Week 7-8: Autonomous Loop with Gemini

```python
# scripts/start_24h_autonomous_loop.py (ENHANCE)

async def hour_cycle_with_gemini(hour: int):
    """Hourly autonomous cycle with Gemini planning"""
    
    # Phase 1: Planning (Gemini thinks about improvement)
    plan_prompt = f"""
    Hour {hour} of 24-hour autonomous loop.
    Jarvis needs to improve throughput by 5%.
    
    Available tools: {list_available_tools()}
    
    What 3-step plan would you execute to improve?
    Format: 
    Step 1: [action]
    Step 2: [action]
    Step 3: [action]
    """
    
    plan_response = await gemini_request(plan_prompt)
    steps = parse_plan(plan_response.text)
    
    # Phase 2: Execution (Gemini executes with tools)
    results = []
    for step in steps:
        tool_result = await gemini_function_call(step)
        results.append(tool_result)
    
    # Phase 3: Metrics (Gemini evaluates improvement)
    metrics = measure_throughput()
    improvement_pct = ((metrics['new'] - metrics['old']) / metrics['old']) * 100
    
    report = {
        "hour": hour,
        "plan": steps,
        "results": results,
        "improvement": improvement_pct,
        "timestamp": datetime.now().isoformat()
    }
    
    # Send Telegram report
    await send_telegram_report(report)
    
    return report
```

---

## 💰 COST ANALYSIS (Gemini-Only)

### Free Tier Usage (1500 req/day)

```
Daily Usage Estimate:
├─ Voice interactions: 50 req/day (5 min each) = ~4 min/day
├─ Vision analysis: 10 req/day = 2 min/day
├─ Autonomous loop: 24 req/day (hourly) = 2 min/day
└─ Tool calls: 100 req/day = ~15 min/day

Total: ~23 min/day of voice
Free tier: 1500 req/day = PLENTY

Status: ✅ All within free tier
Cost: $0 per month
```

### Paid Tier (If Scaling)

```
Gemini 2.5 Flash Pricing:
├─ Input: $0.075 per 1M tokens
├─ Output: $0.30 per 1M tokens
└─ Estimate per month (at scale):
    - 1M tokens input = $0.075
    - 500K tokens output = $0.15
    - Monthly: ~$5-10 (very cheap)
```

---

## 🚀 DEPLOYMENT CHECKLIST (Gemini-Only)

### Week 1 (Voice)
- [ ] Get Gemini API key from https://aistudio.google.com/apikey
- [ ] Create `server/voice/gemini_native_audio.py`
- [ ] Test: 5-min voice conversation
- [ ] Integration: Hook into `server/bridge.py` voice handler
- [ ] Fallback: Keep Piper TTS as backup (if Gemini fails)

### Week 2 (Stabilization)
- [ ] Error handling (API timeouts, rate limits)
- [ ] Logging (all Gemini API calls)
- [ ] Metrics (latency, success rate)
- [ ] Test: 1-hour continuous voice interaction

### Week 3-4 (Vision)
- [ ] Create `server/agents/vision_analyzer.py`
- [ ] Integration: Screen analysis → Gemini vision
- [ ] Test: Analyze 10 different screenshots
- [ ] Bridge command: `/ekran-analiz`

### Week 5-6 (Tools)
- [ ] Create `server/skills/gemini_tools.py`
- [ ] Function declarations (all 74 Jarvis skills)
- [ ] Tool registry validation
- [ ] Test: Execute 5 multi-step tasks

### Week 7-8 (Autonomous)
- [ ] Integrate Gemini into `start_24h_autonomous_loop.py`
- [ ] Test: Run 1-hour loop with Gemini planning
- [ ] Metrics tracking (improvement %)
- [ ] Production readiness check

---

## .env Configuration (Gemini)

```bash
# Gemini API
GEMINI_API_KEY=your_key_from_aistudio
GEMINI_MODEL=models/gemini-2.5-flash
GEMINI_TIMEOUT=30

# Voice
ENABLE_GEMINI_VOICE=1
GEMINI_VOICE_LANGUAGE=tr-TR

# Vision
ENABLE_GEMINI_VISION=1

# Tools/Functions
ENABLE_GEMINI_FUNCTIONS=1
GEMINI_FUNCTION_TIMEOUT=60

# Fallback (keep for safety)
FALLBACK_VOICE_ENGINE=piper
OLLAMA_ENABLED=0  # Not using for now
```

---

## 🔄 FUTURE EXPANSION (Post Q3 2026)

When to evaluate alternatives:

### ⏰ Gemini Cost Becomes Issue
```
If: Monthly bill > $50
Then: Evaluate OpenAI GPT-3.5 Turbo (cheaper) or Mistral
When: Q3 2026 monthly review
```

### ⏰ Offline Requirement Emerges
```
If: Customer asks for "no internet needed"
Then: Deploy Ollama + Qwen 2.5 14B (local fallback)
When: Q3 2026 (if customer demand)
```

### ⏰ Turkish Reasoning Improves
```
If: Qwen 2.5 new version (2.5.1+) launches
Then: Benchmark vs Gemini 2.5 Flash
When: Q3-Q4 2026 (after field testing)
```

### ⏰ Performance Ceiling Hit
```
If: Gemini latency > 2 seconds consistently
Then: Evaluate Gemini Pro (larger) or add Ollama fallback
When: Q4 2026 (scale testing)
```

---

## 📊 SUCCESS METRICS (Gemini)

```
Baseline (Current):
├─ Voice latency: 500-800ms
├─ Vision success: 85%
├─ Tool success: 90%
└─ Autonomous loop: 24-hour runs

Target (8 weeks with Gemini):
├─ Voice latency: <500ms (native audio)
├─ Vision success: 95%+ (Gemini 2.5)
├─ Tool success: 95%+ (function calling)
└─ Autonomous loop: Smart planning + error recovery

Measurement:
├─ Daily logs: server/logs/gemini_metrics.jsonl
├─ Weekly report: server/logs/weekly_report.json
├─ Monthly dashboard: apps/web-ui/metrics
└─ Alerting: Telegram notification on failures
```

---

## 🛑 KNOWN LIMITATIONS (Gemini)

```
Offline-Only Scenarios:
❌ No internet = No Gemini
⚠️ Mitigation: Fallback to Ollama (if added later)

Rate Limits:
⚠️ Free tier: 1500 req/day max
⚠️ If exceeded: 429 error
✅ Solution: Switch to paid tier ($0.075/1M tokens)

Latency:
⚠️ Voice: ~500ms network latency
✅ Good enough for interactive agent

Privacy:
⚠️ Audio sent to Google servers
❌ Not suitable for HIPAA/sensitive data
⚠️ Mitigation: Offline option (Q3 2026)
```

---

## 📝 DECISION LOG

**2026-04-04 — Gemini-Only Decision**
- ✅ Approved: Start with Gemini 2.5 Flash
- ✅ Deferred: AirLLM (evaluate Q3 2026)
- ✅ Deferred: Qwen 2.5 (evaluate Q3 2026)
- ✅ Reason: Fastest path to production, native voice, free tier sufficient
- ✅ Timeline: 8 weeks (end of May 2026)
- ✅ Owner: Ekrem (Jarvis Mission Control)

---

## 🎯 NEXT STEP

**Week 1 Action Items:**
1. Get Gemini API key
2. Create `server/voice/gemini_native_audio.py`
3. Test voice loop (5 minutes)
4. Commit to GitHub
5. Deploy to test environment

Ready? 🚀

