# Launcher Conflicts V2

Validated on 2026-04-12.

## Canonical

### `JARVIS_BASLAT.bat`

Status: canonical Windows entrypoint

Why:

- points to `master_launcher.py`
- now defaults to:
  - `JARVIS_ENABLE_HOLOGRAM=0`
  - `JARVIS_WAIT_FOR_GATEWAY=0`

### `master_launcher.py`

Status: canonical Python entrypoint

Why:

- launches the selected recovery stack
- now skips gateway wait unless explicitly re-enabled
- now keeps hologram out of the first clean recovery boot by default

## Component launchers

### `server/start_jarvis.bat`

Status: backend-only component launcher

Current behavior:

- forces `--web-only`
- defaults `JARVIS_ENABLE_TELEGRAM=0`

### `server/start_voice.bat`

Status: voice-only component launcher

Current behavior:

- launches `..\hey_jarvis.py`
- defaults `JARVIS_CHAT_PRIORITY=backend`

## Neutralized conflict

### `SISTEM_J.bat`

Old problem:

- launched `server/bridge.py` directly
- then launched donor `external-repos/Mark-XXXV\main.py`
- created a second ownership story for "start Jarvis"

New state:

- legacy wrapper only
- forwards to `JARVIS_BASLAT.bat`

## Ruled out from first recovery boot

### `server/openclaw_bridge.py`

- helper-only
- not canonical runtime

### `server/watchdog.py`

- useful for restart control
- not part of the first clean recovery boot

### Gateway on `8082`

- not needed to get one coherent voice assistant path alive
- now excluded from the default recovery boot
