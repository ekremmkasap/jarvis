# OPS/65_CLAIMS_VS_REALITY_V5

Tarih: 2026-04-04

| Claim | Status | Confidence | Strongest Support | Strongest Contradiction | Next Step |
| --- | --- | --- | --- | --- | --- |
| V5 prompt dosyasi 30000 satir | VERIFIED | yuksek | exact count command | none | carry forward |
| tests.test_dashboard meaningfully passes | MOSTLY VERIFIED | yuksek | included in 25-test rerun | narrow proof only | keep narrow |
| 117/117 tests passing | CONTRADICTED | yuksek | historical report language only | current aggregate truth is now `python -m unittest discover -s tests -p "test_*.py"` => `200 tests OK`, so the old exact count is obsolete and should not be reused | replace legacy claim with exact current aggregate result |
| Current full unittest discovery passes | VERIFIED | yuksek | `python -m unittest discover -s tests -p "test_*.py"` => `Ran 200 tests ... OK` | warnings/noisy logs remain | keep exact command and current count attached |
| Bridge heartbeat and lock producer are working | VERIFIED | yuksek | producer files exist, heartbeat file updates, watchdog log shows producer/consumer interaction across two smoke runs | no long-duration stale-age proof yet | keep claim narrow to producer contract |
| Watchdog restart semantics are correct | MOSTLY VERIFIED | yuksek | forced-restart smoke now shows child death, new PID, and cleanup of old heartbeat/lock state in watchdog log | stale-age branch and full supervisor-shutdown cleanup are still narrower than broad production proof | keep live proof narrow and avoid overclaim |
| openclaw_web_only really means web-only | VERIFIED | yuksek | CLI override + wrapper + test | no live operator smoke | small process smoke later |
| Queue health metrics are semantically correct | MOSTLY VERIFIED | orta | snapshot + health endpoint + tests | persistence still partial | keep watch |
| Queue persistence is real | MOSTLY VERIFIED | yuksek | unittest recovery path + inline restart smoke both show state file reload and running-task recovery | no long-duration multi-process soak proof | keep claim narrow to restart persistence |
| Voice interruption behavior is acceptable | CONTRADICTED | orta | user target says it still cuts off early | no fix proof | treat as open defect |
| Source repos materially improve Jarvis | PARTIAL | orta | donor value identified | no integrated runtime proof | use as donor inventory |

## Carry-Forward Classification
### Reliable
- server/skills/memory_skill.py
- server/agents/self_healer.py
- services/voice/voice_service.py
- tests/test_task_queue.py
- tests/test_memory_skill.py
- tests/test_self_healer.py
- tests/test_dashboard.py
- server/runtime_config.py
- server/bridge.py heartbeat/lock producer path

### Partially correct
- services/orchestrator/task_queue.py
- services/orchestrator/agent_runner.py
- services/orchestrator/main.py
- openclaw.cmd migration path
- server/watchdog.py restart semantics

### Risky / needs repair
- openclaw_web_only.cmd operator meaning before this sprint
- install_openclaw_startup.cmd autostart blast radius
- legacy exact-count test claims without fresh rerun
- production-ready language without live Telegram/OpenClaw proof
- watchdog full shutdown cleanup under external supervisor exit remains unverified

## Current Aggregate Truth
- Full discovery currently passes with `200` tests.
- The prior aggregate breakage was traced to test-time `sys.path` shadowing of the root `agents` package plus package-relative drift in `server.voice.gemini_simple_chat`.
- Warnings still exist during the run:
  - `google.generativeai` deprecation warning in `server/agents/vision_analyzer.py`
  - FastAPI `on_event` deprecation warnings in `services/orchestrator/main.py`
  - noisy `Pattern analysis error: unsupported operand type(s) for +: 'int' and 'NoneType'` logs
  - `ResourceWarning` noise in `server/telegram/telegram_intelligence.py`

## Discipline Notes
- `py_compile` runtime proof degildir.
- Tek unittest broad production claim tasimaz.
- Wrapper name runtime behavior ile test edilmeden kabul edilmez.
- Docs code ile catisirsa docs stale sayilir.
- Aggregate test claim current tree ile tekrar gecmediyse tasinmaz.
