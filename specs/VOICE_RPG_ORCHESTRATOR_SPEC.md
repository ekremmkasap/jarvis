# Jarvis Voice RPG Orchestrator — Sesli Orkestrasyonun Görselleştirilmesi

**Tarih**: 2026-04-15  
**Durum**: SPECIFICATION  
**Inspirasyon**: @ohmo.ai "RPG agent world" post (1.6K engagement)  
**Hedef**: Jarvis'i sesli, görsel, interaktif orchestration platformuna dönüştür

---

## Vizyon

Kullanıcı (Ekrem) konuşuyor:
```
Ekrem: "Sabri, araştırma yap, rapor ver"
  │
  └─► Hologram ve web shows:
      • Sabri (CEO avatar) kırmızı, pulsing — stratejive düşünüyor
      • Mert (Researcher avatar) mavi, moving — web'de arama yapıyor  
      • Real-time narration: "Mert Türkçe startuplardan bilgi toplayıp Sabri'ye sunuyor..."
      • Bottom: Live transcript + sentiment gauge
  │
  └─► 30 saniye sonra:
      Mert (otonom voice): "📊 Buldum! 5 trend var..."
      [Hologram: Mert avatar, kırmızı → yeşil (tamamlandı)]
      Sabri sesli: "İyi, raporla"
      [Screen: Report görüntüleniyor, Sabri'nin yorumları]
```

**Farklı olan**: Not just text outputs — **live orchestration theater**

---

## Architecture: 4 Layer

```
Layer 1: Voice + NLP Processing
  ├─ STT (Logitech → RealtimeSTT)
  ├─ Intent parsing (Sabri vs Seda vs Mert)
  └─ Task delegation

Layer 2: RPG World State
  ├─ Persona avatars (pixel agents)
  ├─ World zones (strategy war room, dev workspace, research library)
  ├─ Agent states (idle, thinking, working, complete)
  └─ Particle effects (sparkles = learning, red cross = error, etc.)

Layer 3: Real-time Sync
  ├─ Hologram (Electron app) updates every 100ms
  ├─ Web dashboard shows same world
  ├─ Voice narration = state transitions
  └─ Transcript log (searchable)

Layer 4: Orchestration Engine
  ├─ Task spawning + delegation
  ├─ Inter-agent messaging
  ├─ Fallback + retry logic
  └─ Memory consolidation integration
```

---

## Layer 1: Voice Intent Routing

**File**: `server/services/voice_rpg_orchestrator.py`

```python
class VoiceRPGOrchestrator:
    """
    Sesli komut → RPG agent state transitions
    """
    
    async def process_voice_command(self, audio_text: str) -> dict:
        """
        "Sabri'ye araştırma yap, ondan sonra Seda'ya kod yaz" parse et.
        
        Returns:
          {
            "primary_agent": "sabri",
            "task": "research",
            "subtasks": [
              {"agent": "sabri", "action": "plan_research", "params": {...}},
              {"agent": "mert", "action": "execute_research", "params": {...}},
              {"agent": "sabri", "action": "review", "params": {...}},
              {"agent": "seda", "action": "implement_findings"}
            ],
            "narration": "Sabri and Mert starting research cycle...",
            "estimated_duration": 180  # seconds
          }
        """
        
        # Step 1: Parse intent
        intent = await parse_voice_intent(audio_text)
        
        # Step 2: Extract personas mentioned
        personas_mentioned = extract_personas(audio_text)  # ["sabri", "mert", "seda"]
        
        # Step 3: Build task chain
        subtasks = build_task_chain(
            intent=intent,
            personas=personas_mentioned,
            context=self.conversation_history
        )
        
        # Step 4: Generate narration
        narration = generate_narration(
            primary_agent=intent['primary_agent'],
            subtasks=subtasks,
            style='rpg'  # "Sabri boards the strategy airship..."
        )
        
        # Step 5: Update world state
        world_state = {
            'agents': {
                persona: {
                    'state': 'thinking',  # idle → thinking → working → done
                    'task': subtask['action'],
                    'progress': 0,
                    'avatar_color': get_persona_color(persona),
                    'animation': 'thinking_idle'
                }
                for persona, subtask in zip(personas_mentioned, subtasks)
            },
            'environment': 'strategy_chamber',  # zone changes based on task
            'narration': narration,
            'estimated_time': estimate_duration(subtasks)
        }
        
        return {
            'intent': intent,
            'subtasks': subtasks,
            'world_state': world_state,
            'narration': narration
        }
```

---

## Layer 2: RPG World State Management

**File**: `server/services/rpg_world_state.py`

```python
@dataclass
class PersonaAvatar:
    """RPG dünyasında persona'nın görünümü"""
    persona_id: str
    name: str
    color: str  # hex (#FF6B6B for red, #4ECDC4 for teal, etc.)
    position: tuple  # (x, y) in RPG world grid
    state: str  # 'idle', 'thinking', 'working', 'communicating', 'celebrating'
    current_task: Optional[str]
    progress: float  # 0.0 to 1.0
    animation: str  # 'thinking_idle', 'walking', 'typing', 'reading'
    particles: List[str]  # ['sparkle', 'error', 'success']
    

class RPGWorldState:
    """
    Live world state — hologram + web dashboard synchronized
    """
    
    def __init__(self):
        self.avatars: Dict[str, PersonaAvatar] = {}
        self.zones: Dict[str, 'Zone'] = {}
        self.events: List['Event'] = []
        self.narration_queue: List[str] = []
        self.broadcast_socket = None  # WebSocket to hologram + web
    
    async def update_agent_state(
        self,
        persona_id: str,
        state: str,
        task: str,
        progress: float = 0.0
    ):
        """
        Agent state'i update et ve broadcast et.
        
        State machine:
          idle → thinking → working → (processing) → done
                                    └─ error → idle
        """
        
        if persona_id not in self.avatars:
            return
        
        avatar = self.avatars[persona_id]
        old_state = avatar.state
        avatar.state = state
        avatar.current_task = task
        avatar.progress = progress
        
        # Animation update
        if state == 'thinking':
            avatar.animation = 'thinking_idle'
            avatar.particles = ['sparkle']
        elif state == 'working':
            avatar.animation = 'typing'
            avatar.particles = ['energy']
        elif state == 'done':
            avatar.animation = 'celebrating'
            avatar.particles = ['success', 'sparkle']
        
        # Generate voice narration
        narration = generate_state_narration(
            persona=persona_id,
            old_state=old_state,
            new_state=state,
            task=task
        )
        self.narration_queue.append(narration)
        
        # Broadcast update
        await self.broadcast_world_state()
    
    async def broadcast_world_state(self):
        """
        Live state'i hologram + web'e gönder
        """
        state_payload = {
            'timestamp': datetime.now().isoformat(),
            'avatars': {
                id: asdict(avatar)
                for id, avatar in self.avatars.items()
            },
            'narration_queue': self.narration_queue,
            'environment': self.get_current_environment()
        }
        
        # WebSocket broadcast
        if self.broadcast_socket:
            await self.broadcast_socket.broadcast(state_payload)
```

---

## Layer 3: Real-time Sync — Hologram Integration

**File**: `server/services/hologram_rpg_sync.py`

```python
class HologramRPGSync:
    """
    Hologram (Electron) ile real-time world state sync
    
    Update frequency: 100ms (10 FPS for smooth animations)
    Data: Avatar positions, animations, particles, narration
    """
    
    async def init_websocket_server(self, port: int = 8082):
        """
        WebSocket server başlat (hologram polling yerine push)
        """
        from fastapi import WebSocket
        
        @app.websocket("/ws/rpg-world")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            
            try:
                while True:
                    # Send world state every 100ms
                    state = await self.get_live_world_state()
                    await websocket.send_json(state)
                    await asyncio.sleep(0.1)  # 100ms
            
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                await websocket.close()


# Hologram React component style (pseudo-code):
"""
function RPGWorldRenderer({ worldState }) {
  return (
    <div className="rpg-world">
      {/* Background zone */}
      <ZoneBackground zone={worldState.environment} />
      
      {/* Pixel avatars */}
      {Object.entries(worldState.avatars).map(([id, avatar]) => (
        <PixelAvatar
          key={id}
          persona={avatar.name}
          x={avatar.position[0]}
          y={avatar.position[1]}
          color={avatar.color}
          animation={avatar.animation}
          particles={avatar.particles}
          progress={avatar.progress}
        />
      ))}
      
      {/* Real-time narration */}
      <NarrationBubble text={worldState.narration_queue[0]} />
      
      {/* Progress bar */}
      <ProgressBar value={calculateAverageProgress(worldState.avatars)} />
    </div>
  )
}
"""
```

---

## Layer 4: Orchestration + Voice Synthesis

**Integration with existing**:
- `hey_jarvis.py` — STT input + TTS output
- `master_launcher.py` — Process orchestration
- `memory_consolidation.py` — Learning feedback

```python
async def orchestrate_with_voice(
    voice_command: str,
    orchestrator: VoiceRPGOrchestrator,
    world_state: RPGWorldState
):
    """
    Full loop: Voice → World update → TTS response → Next action
    """
    
    # 1. Parse voice intent + build task chain
    response = await orchestrator.process_voice_command(voice_command)
    
    # 2. Update RPG world (visual feedback)
    await world_state.update_from_response(response)
    
    # 3. Execute subtasks (parallel where possible)
    results = await execute_subtasks(response['subtasks'])
    
    # 4. Update world with progress
    for i, result in enumerate(results):
        await world_state.update_agent_state(
            persona_id=response['subtasks'][i]['agent'],
            state='done' if result['success'] else 'error',
            task=response['subtasks'][i]['action'],
            progress=1.0 if result['success'] else 0.0
        )
    
    # 5. Generate voice response (persona speaks)
    primary_persona = response['intent']['primary_agent']
    voice_response = generate_persona_voice_response(
        persona=primary_persona,
        results=results,
        world_state=world_state
    )
    
    # 6. Speak (TTS)
    await speak_response(voice_response, persona=primary_persona)
    
    # 7. Save memory
    await memory_consolidation.record_orchestration(
        command=voice_command,
        result=results,
        world_state=world_state
    )
```

---

## UI: Web Dashboard (Real-time)

**File**: `apps/web-ui/pages/rpg-orchestrator.tsx`

```typescript
export default function RPGOrchestrator() {
  const [worldState, setWorldState] = useState(null)
  const [narration, setNarration] = useState('')
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8082/ws/rpg-world')
    
    ws.onmessage = (event) => {
      const state = JSON.parse(event.data)
      setWorldState(state)
      
      // TTS narration if available
      if (state.narration_queue[0]) {
        setNarration(state.narration_queue[0])
        // Could trigger text-to-speech here
      }
    }
    
    return () => ws.close()
  }, [])
  
  return (
    <div className="rpg-orchestrator">
      <h1>🎮 Jarvis Orchestrator World</h1>
      
      {worldState && (
        <>
          {/* RPG world visualization */}
          <RPGWorld state={worldState} />
          
          {/* Live transcript */}
          <NarrationLog narration={narration} />
          
          {/* Agent health/progress */}
          <AgentStatus avatars={worldState.avatars} />
          
          {/* Task queue */}
          <TaskQueue tasks={worldState.tasks} />
        </>
      )}
    </div>
  )
}
```

---

## Voice Narration Examples

| State | Example Narration |
|-------|-------------------|
| Task start | "Sabri boards the strategy chamber... Mert enters the research library..." |
| Working 25% | "Mert searches Turkish startup databases..." |
| Working 50% | "Mert synthesizes findings... Sabri reviews incoming data..." |
| Completion | "✨ Mert completes research! Sabri celebrates the insight!" |
| Error | "⚠️ Seda encounters a bug! Redeploying..." |

---

## Implementation Phases

### Phase 1 (1-2 weeks): Foundations
- [ ] `voice_rpg_orchestrator.py` — Intent parsing + task chaining
- [ ] `rpg_world_state.py` — Avatar state management
- [ ] WebSocket sync (hologram ↔ backend)
- [ ] Basic pixel avatars (no animations yet)

### Phase 2 (1 week): Voice + Narration
- [ ] Real-time narration generation
- [ ] TTS persona voices (Turkish + English)
- [ ] Voice feedback loop
- [ ] Particle effects

### Phase 3 (1 week): Polish + Performance
- [ ] Animations (walking, typing, celebrating)
- [ ] Zone transitions (war room → dev space → research library)
- [ ] Web dashboard
- [ ] Performance optimization (WebSocket batching)

### Phase 4 (2 weeks): Advanced Features
- [ ] Agent-to-agent visible messaging (chat bubbles)
- [ ] Memory consolidation integration (learning agents)
- [ ] Recording + replay
- [ ] Multiplayer (multiple users watching same world)

---

## Why This Works (Marketing)

Turkish market engagement research proved:
- **Educator credibility + autonomy narrative = 2.0-2.43x**
- **Philosophical positioning (whip vs wand) = 1.6K engagement**

Jarvis Voice RPG:
- ✅ **Visual storytelling** — not boring text or charts
- ✅ **Autonomy** — agents work independently, user just directs
- ✅ **Entertainment** — game mechanics, pixel art, narration
- ✅ **Accessibility** — voice-first (no keyboard needed!)
- ✅ **Community** — "Which persona is your favorite?"

---

## Files to Create

1. `server/services/voice_rpg_orchestrator.py`
2. `server/services/rpg_world_state.py`
3. `server/services/hologram_rpg_sync.py`
4. `apps/web-ui/components/RPGWorld.tsx`
5. `apps/web-ui/pages/rpg-orchestrator.tsx`
6. `config/rpg_world_config.json` — Avatar definitions, zones, narration templates

---

## Success Metrics

| Metric | Target |
|--------|--------|
| **Engagement** (Instagram) | 2.0-3.0x vs feature posts |
| **Watch time** (hologram) | 5+ minutes per session |
| **Voice commands** | 80% successful parsing |
| **Followers** | 100K in 6 months (vs 50K without) |

---

**Status**: ✅ READY TO START PHASE 1

Başlasak mı?
