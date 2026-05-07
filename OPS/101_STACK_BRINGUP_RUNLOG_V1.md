# Stack Bring-Up Runlog V1

Validated on 2026-04-10.

## Pre-flight live state

- `8081` was already live.
- `8091` was down.
- `3000` was down.
- `11434` was live.

Observed responses:

- `GET http://127.0.0.1:8081/health` -> healthy
- `GET http://127.0.0.1:8081/api/status` -> online
- `GET http://127.0.0.1:8091/health` -> no response
- `GET http://127.0.0.1:3000` -> no response
- `GET http://127.0.0.1:11434/api/tags` -> `200`

Observed local ownership:

- `server/data/bridge_heartbeat.json` -> PID `3052`, port `8081`
- `netstat` -> `127.0.0.1:8081 LISTENING 3052`
- `netstat` -> `0.0.0.0:11434 LISTENING 18008`

## Backend validation

- `POST http://127.0.0.1:8081/api/chat` with a greeting returned a short chat response.
- One natural-language prompt still misrouted to a code/screen response. That is a bridge routing quality issue, not a bring-up blocker.

## Voice bring-up attempt 1

Command intent:

- Start `hey_jarvis.py --no-greeting` with redirected stdout/stderr for detached validation.

Result:

- Process exited immediately.
- Root cause was a Windows stdout encoding crash:
  - `UnicodeEncodeError: 'charmap' codec can't encode characters...`
  - failure site was the startup banner in `hey_jarvis.py`

## Fix applied

Minimal patch:

- Reconfigured `sys.stdout` and `sys.stderr` to `utf-8` with `errors="replace"` at startup in `hey_jarvis.py:25-30`.

Why this fix:

- It is narrow.
- It addresses the actual runtime failure.
- It protects all startup prints, not just one banner line.

## Voice bring-up attempt 2

Detached validation after patch:

- startup no longer crashed on banner encoding
- short detached process was not stable enough to trust as final evidence under this tool harness

## Voice bring-up attempt 3

Foreground validation command:

- `python -u hey_jarvis.py --no-greeting`

Observed output:

- startup banner printed successfully after the patch
- `RealtimeSTT` attempted first
- `edge_tts` failed because remote Bing speech endpoint access was blocked
- local Piper fallback loaded successfully
- `RealtimeSTT` failed with `PermissionError: [WinError 5] Access is denied`
- wake-word fallback required `PICOVOICE_ACCESS_KEY`, which was absent
- final fallback entered continuous microphone mode and printed:
  - `"[MIK] Hazir - Konusmaya basla! (30 saniye konusma suresi)"`
  - `"[MIK] Dinliyorum..."`

This is enough evidence that the voice stack boots, enters its speech-loop fallback chain, and reaches a live listening state.

## Final live state after execution

- Bridge remained live on `8081`
- Ollama remained live on `11434`
- Voice boot path was validated in foreground
- No attempt was made to boot `8091` or the UI stacks in the same pass

