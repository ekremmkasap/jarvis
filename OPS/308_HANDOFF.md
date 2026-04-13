# AGENTS.md 9-Agent Canonical — Handoff Notu

## Ozet
9 canonical agent implement edildi, bridge entegrasyonu harden edildi, Telegram keyword dispatch ve per-agent persistent memory eklendi.

## Agent Listesi

| Agent | Dosya | Gorev |
|-------|-------|-------|
| PlannerAgent | `server/agents/canonical/planner.py` | Goal -> structured plan |
| RepoAnalystAgent | `server/agents/canonical/repo_analyst.py` | git log + file scan -> health report |
| DeveloperAgent | `server/agents/canonical/developer.py` | Feature/bug -> bounded code change |
| ReviewerAgent | `server/agents/canonical/reviewer.py` | git diff -> review raporu |
| DebugAgent | `server/agents/canonical/debug_agent.py` | Hata -> root cause analysis |
| ReleaseAgent | `server/agents/canonical/release_agent.py` | git log -> changelog + semver |
| DocsAgent | `server/agents/canonical/docs_agent.py` | Kod -> dokumantasyon |
| VoiceNarratorAgent | `server/agents/canonical/voice_narrator.py` | Output -> kisa TTS metni |
| MissionControlAgent | `server/agents/canonical/mission_control.py` | Tum canonical agentleri izle |

## Bridge Endpoint

Primary endpoint:

`POST http://127.0.0.1:8081/agent`

Request body:

```json
{
  "agent": "planner",
  "task": "Jarvis durumunu raporla",
  "context": {}
}
```

Backward-compatible default:
- canonical agent raw payload doner

Optional wrapped response:

```json
{
  "agent": "planner",
  "task": "Jarvis durumunu raporla",
  "context": {},
  "wrapped_response": true
}
```

Wrapped response shape:

```json
{
  "ok": true,
  "agent": "planner",
  "result": "[CANONICAL/planner] ...",
  "raw": {
    "agent_id": "planner",
    "status": "ok"
  }
}
```

## Telegram Kullanimi

- `plan yap X` -> `PlannerAgent`
- `hata var X` -> `DebugAgent`
- `review et X` -> `ReviewerAgent`
- `kod yaz X` -> `DeveloperAgent`
- `release yap X` -> `ReleaseAgent`
- `dokumantasyon yaz X` -> `DocsAgent`
- `sistem durumu X` -> `MissionControlAgent`

Tam liste:
- `AGENT_KEYWORDS` in [server/bridge.py](C:\Users\sergen\Desktop\jarvis-mission-control\server\bridge.py)

## Health Check

`GET http://127.0.0.1:8081/api/agents/health`

Payload:
- `agents`: per-agent `ok/error`
- `total`: canonical agent count
- `healthy`: successful health checks

Health mode lightweight calisir; full agent task execution yapmaz.

## Persistent Memory

Konum:
- `state/agent_memory/<agent_id>.json`

API:
- `remember(key, value)`
- `recall(key, default=None)`
- `memory_summary()`

Automatic writes:
- `last_task`
- `last_run`

Base class:
- [base.py](C:\Users\sergen\Desktop\jarvis-mission-control\server\agents\canonical\base.py)

## Voice Hook

Dosya:
- [hey_jarvis.py](C:\Users\sergen\Desktop\jarvis-mission-control\hey_jarvis.py)

Akis:
- `handle(...)` -> `narrate_agent_result(...)`
- `VoiceNarratorAgent` sonucu kisaltir
- narrator fail ederse sanitized fallback TTS kullanilir

## Yeni Agent Ekleme

1. `server/agents/canonical/yeni_agent.py` olustur ve `CanonicalAgent` extend et
2. `server/agents/canonical/__init__.py` icine export ekle
3. `server/bridge.py` icindeki `_load_canonical_agent_classes()` ve `AGENT_KEYWORDS` map'ini guncelle

## Bridge Restart

- `python server/bridge.py`
- veya `SISTEM_J.bat webonly`

Canli process eskiyse yeni `/agent` ve `/api/agents/health` surface'leri gorunmez.

## Test Komutu

```powershell
python -m pytest `
  tests/test_canonical_batch1.py `
  tests/test_canonical_batch2.py `
  tests/test_canonical_batch3.py `
  tests/test_canonical_batch4.py `
  tests/test_hey_jarvis_live_mode.py `
  tests/test_canonical_telegram.py `
  tests/test_agent_memory.py -v --tb=short
```

## Bilinen Limitasyonlar

- Canli bridge process restart edilmeden yeni endpoint surface'leri gorunmeyebilir
- `DeveloperAgent` health check lightweight instantiate modunda dogrulanir; write task execution yapilmaz
- `VoiceNarratorAgent` varsayilan olarak deterministic compression kullanir
- LLM provider erisimi yoksa canonical agentler fallback payload uretebilir
