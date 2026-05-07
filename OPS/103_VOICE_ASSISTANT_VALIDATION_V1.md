# Voice Assistant Validation V1

Validated on 2026-04-10.

## Backend

Confirmed live:

- `GET http://127.0.0.1:8081/health`
- `GET http://127.0.0.1:8081/api/status`
- `POST http://127.0.0.1:8081/api/chat`

Confirmed absent:

- `GET http://127.0.0.1:8091/health`
- `GET http://127.0.0.1:3000`

## Bridge ownership

- `server/data/bridge_heartbeat.json` showed PID `3052`
- `netstat` showed `127.0.0.1:8081 LISTENING 3052`

## Voice script

Startup path proved from code:

- backend default -> `hey_jarvis.py:118`
- main speech-loop entry -> `hey_jarvis.py:737-742`
- fallback chain begins at `hey_jarvis.py:745-750`

## What worked

- startup banner printed successfully after the UTF-8 stream patch
- voice runtime reached the STT initialization path
- local TTS fallback loaded:
  - `"[TTS] Yukleniyor..."`
  - `"[TTS] Hazir."`
- final fallback entered microphone listening mode:
  - `"[MIK] Hazir - Konusmaya basla! (30 saniye konusma suresi)"`
  - `"[MIK] Dinliyorum..."`

## What failed

### Preferred online TTS path

- `edge_tts` failed because access to `speech.platform.bing.com:443` was blocked
- impact: no Microsoft TTS path
- observed fallback: Piper local TTS loaded successfully

### Preferred local STT path

- `RealtimeSTT` failed with `PermissionError: [WinError 5] Access is denied`
- failure site came from `AudioToTextRecorder` initialization
- impact: preferred local Whisper path is not currently usable in this environment

### Wake-word path

- Porcupine fallback requested `PICOVOICE_ACCESS_KEY`
- key not present
- impact: wake-word mode is not currently configured

## Bottom line

The assistant stack is not "fully clean", but it is now past startup failure and reaches a live speech-loop fallback state.

Current effective runtime picture:

- bridge backend: working
- voice launcher: working past startup
- local TTS fallback: working
- preferred local STT: blocked
- wake word: not configured
- continuous microphone fallback: reached

