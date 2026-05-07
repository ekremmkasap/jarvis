# Voice Recovery Runlog V2

Validated on 2026-04-12.

## Live repo facts carried forward

- Worktree is dirty. Changes were kept surgical.
- `hey_jarvis.py` is the voice path under repair.
- `server/bridge.py` is the backend target.
- current `8081` ownership is not trustworthy.

## Pre-patch evidence

### Existing `8081` state was contradictory

- `server/data/bridge_heartbeat.json` contained:
  - `pid: 11940`
  - `web_port: 8081`
- `http://127.0.0.1:8081/health` -> `Uzak sunucuya bağlanılamıyor`
- `http://127.0.0.1:8081/api/status` -> `Uzak sunucuya bağlanılamıyor`

Conclusion:

- heartbeat/lock state could not be trusted as proof that HTTP was actually alive

## Patches applied

### Backend truthfulness

- `server/bridge.py`
  - moved HTTP bind into the main startup path with `build_web_server()`
  - no longer claims success before the HTTP server object is created
  - shuts the server down explicitly on exit

### Voice recovery behavior

- `hey_jarvis.py`
  - default chat priority changed to `backend`
  - provider order is now backend/local first, Gemini last
  - `JARVIS_ALLOW_MULTI_INSTANCE=1` bypasses the singleton for validation
  - safe-start now suppresses audio output
  - text mode now exits cleanly on `EOF`

### Launcher cleanup

- `master_launcher.py`
  - `JARVIS_ENABLE_HOLOGRAM` default -> `0`
  - `JARVIS_WAIT_FOR_GATEWAY` default -> `0`
- `JARVIS_BASLAT.bat`
  - now sets those recovery defaults if missing
- `SISTEM_J.bat`
  - no longer starts Mark-XXXV or a rival bridge path
  - now forwards to `JARVIS_BASLAT.bat`
- `server/start_jarvis.bat`
  - now runs backend-only as `bridge.py --web-only`
  - defaults `JARVIS_ENABLE_TELEGRAM=0`
- `server/start_voice.bat`
  - defaults `JARVIS_CHAT_PRIORITY=backend`

## Validation log

### Syntax

Ran:

- `python -m py_compile hey_jarvis.py`
- `python -m py_compile server/bridge.py`
- `python -m py_compile master_launcher.py`
- `python -m py_compile server/watchdog.py`

Result:

- all passed

### Existing tests

Ran:

- `python -m unittest tests.test_runtime_config`
- `python -m unittest tests.test_watchdog`

Result:

- both passed

### Clean side-port bridge boot

Foreground boot on `8094`:

- `JARVIS_WEB_PORT=8094`
- `JARVIS_ENABLE_TELEGRAM=0`
- `python server/bridge.py --web-only`

Observed output:

- `Web dashboard: http://127.0.0.1:8094`
- `Bridge runtime forced into --web-only mode; Telegram will stay disabled.`
- `Telegram adapter disabled. Running in dashboard/HTTP mode only.`

### HTTP proof from another clean boot

Controlled boot on `8097` followed by `curl`:

- `/health` returned JSON with `status: "degraded"` and `HTTP_STATUS:503`
- body included `runtime_label: "Standalone Service [web-only]"`
- body included `live.status: "degraded"`
- body included `voice.status: "offline"`

Controlled boot on `8096`:

- `/api/status` returned JSON successfully
- `/api/chat` timed out at 25 seconds

### Voice proof

Ran:

- `JARVIS_ALLOW_MULTI_INSTANCE=1`
- `JARVIS_SAFE_START=1`
- `JARVIS_DISABLE_AUDIO=1`
- `JARVIS_BACKEND_URL=http://127.0.0.1:65535`
- `GEMINI_API_KEY=''`
- `JARVIS_CHAT_MODEL=deepseek-coder:latest`
- piped one line into `python hey_jarvis.py`

Observed output:

- singleton bypass message printed
- safe-start banner printed
- text mode started
- backend-first failure printed:
  - `[BACKEND fallback] <urlopen error [WinError 10061] ...>`
- local fallback returned one reply

Runtime state after run:

- `server/logs/desktop_assistant.json`
  - `mode: "text"`
  - `stt_backend: "text_input"`
  - `turn_count: 1`
  - `last_heard: "Merhaba Jarvis, tek cumlede durumunu soyle."`
  - `last_response` populated
