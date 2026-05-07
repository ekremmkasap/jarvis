# Canonical Voice Stack V2

Validated on 2026-04-12.

## Selected stack

For the first clean Jarvis voice recovery boot, the canonical stack is:

1. `JARVIS_BASLAT.bat`
2. `master_launcher.py`
3. `server/bridge.py --web-only`
4. `hey_jarvis.py`

Optional:

- `apps/desktop-hologram/` only when `JARVIS_ENABLE_HOLOGRAM=1`

## Why this stack

- `master_launcher.py` already owns the local voice stack and now defaults to:
  - hologram off
  - gateway wait off
- `hey_jarvis.py` is still the real speech loop and now defaults to backend-first chat with local fallback.
- `server/bridge.py` is still the backend HTTP surface on `8081`.
- `server/SOURCE_OF_TRUTH.md` now names `JARVIS_BASLAT.bat` and `master_launcher.py` as the voice recovery boot path.

## Explicit decisions

### Canonical backend startup path

- Full recovery boot: `JARVIS_BASLAT.bat`
- Backend-only component boot: `server/start_jarvis.bat`
- Runtime target: `server/bridge.py --web-only`

### Canonical voice startup path

- Full recovery boot: `JARVIS_BASLAT.bat`
- Voice-only component boot: `server/start_voice.bat`
- Runtime target: `hey_jarvis.py`

### Hologram in first recovery boot

- Excluded by default
- Re-enable only with `JARVIS_ENABLE_HOLOGRAM=1`

### OpenClaw in first recovery boot

- Excluded
- `server/openclaw_bridge.py` remains helper-only, not primary runtime

### Voice backend dependency choice

- `hey_jarvis.py` now uses backend-first by default
- Local Ollama remains the recovery fallback
- Gemini is no longer allowed to jump ahead of the canonical backend/local path

### Minimum "working voice assistant" definition for this pass

- `hey_jarvis.py` starts in safe-start text mode without fighting the singleton
- one user turn is accepted
- backend-first path is attempted
- local fallback returns a reply
- runtime state is written to `server/logs/desktop_assistant.json`

## Ruled out for first recovery boot

- `SISTEM_J.bat`
- donor `external-repos/Mark-XXXV`
- gateway wait on `8082`
- watchdog-managed restart path
- OpenClaw as primary runtime
