# Backend Voice Validation V2

Validated on 2026-04-12.

## Backend

### Broken live canonical port

Evidence:

- `server/data/bridge_heartbeat.json` reported `pid 11940` on `8081`
- `Invoke-WebRequest http://127.0.0.1:8081/health` failed with connection error
- `Invoke-WebRequest http://127.0.0.1:8081/api/status` failed with connection error

Meaning:

- current live `8081` owner remains untrusted

### Clean side-port backend

Evidence from controlled boot:

- `server/bridge.py --web-only` reached:
  - `Web dashboard: http://127.0.0.1:8094`
- `curl http://127.0.0.1:8097/health`
  - JSON body returned
  - HTTP code `503`
  - payload `status: "degraded"`
- `Invoke-WebRequest http://127.0.0.1:8096/api/status`
  - returned JSON successfully

Meaning:

- patched bridge can bind and serve HTTP
- `/health` is degraded, not dead
- the old false-positive "bridge is healthy because heartbeat exists" issue is reduced

### Remaining backend failure

Evidence:

- `POST http://127.0.0.1:8096/api/chat`
  - timed out after 25 seconds

Meaning:

- backend chat latency is still too slow for a good voice loop

## Voice

### Safe-start proof

Evidence:

- `hey_jarvis.py` started with:
  - `JARVIS_ALLOW_MULTI_INSTANCE=1`
  - `JARVIS_SAFE_START=1`
  - `JARVIS_DISABLE_AUDIO=1`
- printed:
  - multi-instance override
  - safe-start banner
  - text mode banner

### Backend-first fallback proof

Evidence:

- with `JARVIS_BACKEND_URL=http://127.0.0.1:65535`
- run output contained:
  - `[BACKEND fallback] <urlopen error [WinError 10061] ...>`
- same run still returned one assistant reply from local fallback

Meaning:

- `hey_jarvis.py` now behaves like a recovery-capable assistant path:
  - backend first
  - local fallback second

### Runtime-state proof

Evidence from `server/logs/desktop_assistant.json` and `server/logs/voice_runtime_events.jsonl`:

- `mode: "text"`
- `stt_backend: "text_input"`
- `turn_count: 1`
- `last_heard` populated
- `last_response` populated
- offline state written on exit

Meaning:

- one full safe-start turn completed and state was persisted

## Validation summary

- syntax: pass
- watchdog tests: pass
- runtime config tests: pass
- clean bridge HTTP bind: pass
- clean bridge `/api/status`: pass
- clean bridge `/health`: degraded but reachable
- clean bridge `/api/chat`: fail, timed out
- safe-start voice turn: pass
