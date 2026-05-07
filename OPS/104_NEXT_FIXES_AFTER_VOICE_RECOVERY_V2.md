# Next Fixes After Voice Recovery V2

Validated on 2026-04-12.

## Exact next fix

1. Reclaim canonical port `8081` from the current untrusted owner, then boot `JARVIS_BASLAT.bat` cleanly on `8081`.

Why this is next:

- the repo now has one clearer recovery path
- but the default canonical port is still occupied by something that keeps heartbeat/state confusing
- I did not kill that owner because it was not started by this pass

## Immediately after that

2. Fix `server/bridge.py` voice chat latency so `/api/chat` returns fast enough for `hey_jarvis.py`.

Current evidence:

- clean side-port `/api/chat` timed out after 25 seconds
- safe-start voice only felt responsive after local fallback was forced

Likely scope:

- route selection for voice/chat
- local fast-model preference for the voice lane
- timeout/fallback behavior inside backend chat

## Still not part of the first recovery boot

3. Keep these out until backend `8081` and voice turn latency are clean:

- hologram
- gateway on `8082`
- OpenClaw helper path
- watchdog restarts

## Success condition for the next pass

The next pass should only claim "working canonical stack" if all are true:

1. `JARVIS_BASLAT.bat` boots without port ambiguity
2. `http://127.0.0.1:8081/health` is reachable
3. `http://127.0.0.1:8081/api/status` is reachable
4. `POST http://127.0.0.1:8081/api/chat` returns in voice-usable time
5. `hey_jarvis.py` completes one turn without needing a validation-only override
