# Specification: Agent Teams + Swarm Mode + Top 5 Skills Integration

**Feature ID**: 008-swarm-skills-integration  
**Created**: 2026-04-15  
**Status**: Specification Complete  
**Timeout Window**: 120 seconds (aggregate)

---

## Vision

Jarvis'i 7 persona swarm'a dönüştür. Şu an sequential tek agent çalışıyor; hedef paralel multi-persona dispatch. 5 yeni specialist skill entegre et, web UI SaaS metrikleri göster, TTS announce ekle.

### Success Criteria

1. Paralel agent dispatch: `swarm_run(goal, personas=["seda","mert"])` ile 2+ persona eş zamanlı çalışır
2. Aggregate timeout: 120s içinde kısmi sonuçlar döner
3. 5 skill hazır: Financial Analyst, Engineering Team, Marketing, C-Level, Autoresearch
4. Web UI: SaaS metrikleri (MRR, customer count) dashboard'da görünür
5. TTS announce: Swarm start/end seslendirilir
6. Luna guard: Hard-reject "canlı hedef", "saldır", "exploit" gibi kelimeleri
7. Zero regression: Bridge eski route'lar bozulmamış, Telegram komutları çalışıyor

---

## Functional Requirements

### FR-001: Paralel Persona Dispatch
- User: `/paralel-araştır "e-ticaret trendi" seda mert`
- System: Seda + Mert eş zamanlı başlatılır
- Result: Combined answer içinde her persona's contribute'u yazılı
- Timeout: 120s (kısmi ok)

### FR-002: 5 Specialist Skill
1. **Financial Analyst**: MRR trend, ratio, DCF valuation
2. **Engineering Team**: Backend + voice + video slot coordination
3. **Marketing Core**: Landing page, copy, CTA, lead magnet
4. **C-Level Advisor**: CEO strategy, vision, market positioning
5. **Autoresearch Loop**: Iterative research (max 3 iteration, timeout-aware)

### FR-003: SaaS Metrics Dashboard
- Display: MRR (TRY), customer count, 30d trend
- Data source: Encrypted SQLite (state/saas_metrics.db)
- Email: SHA256 hash (never plain)
- Refresh: 60s polling

### FR-004: TTS Announce
- Start: "Swarm başlıyor: [goal ilk 60 char]"
- Done: "Tamamlandı. [persona count] görev."
- Via: state/swarm_tts_queue.json → hey_jarvis polling

### FR-005: Luna Security Guard
- Hard-reject keywords: "exploit", "hack", "saldır", "canlı hedef", "DDoS"
- Response: "LUNA: Bu istek reddedildi. Yalnızca savunma amaçlı lab bağlamında çalışabilirim."
- Guard points: swarm_skill.py + bridge.py _handle_team_dispatch_endpoint()

### FR-006: Web UI SaaS + Swarm Panels
- SaasMetricsPanel: MRR sparkline, customer count
- SwarmTeamPanel: Persona checkbox, goal input, live status
- Location: apps/web-ui/src/app/ops/page.tsx

---

## Non-Functional Requirements

### NFR-001: Backward Compatibility
- Bridge: ZERO satır değişikliği, sadece additive
- Telegram: Tüm existing komutlar unchanged
- API: GET /api/swarm-status response format aynı

### NFR-002: Security & Privacy
- Credentials: Asla log/UI'a gitmez
- Email: SHA256 hash, plain metin yasak
- Luna: Defense-in-depth (2 guard point)

### NFR-003: Performance
- Aggregate timeout: 120s (hard deadline)
- Partial results: Accepted
- Web polling: 60s (metrics), 4s (swarm status)

### NFR-004: Quota & Rate Limiting
- Codex daily: 100 request limit (untouched)
- Per-slot timeout: 120s (Codex config zaten hazır)

---

## Architecture Sketch

```
User → Bridge (port 8081)
  ├─ POST /api/swarm/team-dispatch
  │   ├─ Luna guard check
  │   ├─ swarm_run(goal, personas)
  │   └─ TTS queue write
  │
  ├─ GET /api/saas-metrics
  │   └─ SaasDB (state/saas_metrics.db)
  │
  ├─ GET /api/swarm-status (existing)
  │
  └─ Telegram /paralel-araştır
      └─ intent router → swarm_skill.py

Parallel execution:
  swarm_run(goal, personas=["seda","mert"])
    ├─ dispatch_job(goal, slot=forge) → Seda's Codex slot
    ├─ dispatch_job(goal, slot=nexus) → Mert's Codex slot
    └─ wait(timeout=120s) → aggregate results

Web UI:
  ops/page.tsx
    ├─ SaasMetricsPanel (GET /api/saas-metrics every 60s)
    └─ SwarmTeamPanel (GET /api/swarm-status every 4s)

hey_jarvis.py:
  idle loop → check state/swarm_tts_queue.json every 10s → speak()
```

---

## Data Model

### state/saas_metrics.db (SQLite, not committed)
```
TABLE mrr_records:
  id INTEGER PK
  date TEXT (YYYY-MM-DD)
  mrr_usd REAL
  customer_count INTEGER
  churn_rate REAL (0-1)
  plan TEXT (starter|pro|agency)
  notes TEXT

TABLE customer_events:
  id INTEGER PK
  customer_email_hash TEXT (SHA256)
  event_type TEXT (signup|upgrade|churn|payment)
  amount REAL
  timestamp TEXT (ISO8601)
```

### state/swarm_tts_queue.json (not committed)
```json
{
  "queue": [
    {"event_id": "uuid", "text": "Swarm başlıyor...", "type": "start", "ts": 1713195000},
    {"event_id": "uuid", "text": "Tamamlandı. 2 görev.", "type": "done", "ts": 1713195120}
  ]
}
```

---

## Acceptance Criteria

- 5 skill Python modules created + imported cleanly
- swarm_skill.py personas param tested (mock dispatch_job)
- Bridge /api/saas-metrics, /api/swarm/team-dispatch endpoints live
- Web UI SaasMetricsPanel + SwarmTeamPanel rendered
- TTS queue polling in hey_jarvis.py working
- Luna guard blocks exploit keywords (unit test)
- 48+ unit tests pass (existing + new)
- Bridge regression: GET /api/swarm-status format unchanged
- Telegram /paralel-araştır commands unchanged

---

## Open Questions (Resolved)

**Q1: Swarm Result Aggregation Timeout**  
**A**: 120 seconds. Autoresearch 45s + Financial 30s parallel → 120s buffer dahil yeterli.

---

## References

- **Plan**: specs/008-swarm-skills-integration/plan.md
- **Tasks**: specs/008-swarm-skills-integration/tasks.md
- **Model Routing**: config/model_router.yml
- **Persona System**: config/agents.yaml, server/persona_manager.py:72-150
- **Codex Slots**: server/agents/codex_slot_agents.py:PERSONA_SLOT
- **Skill Registry**: server/skills/skill_registry.py
