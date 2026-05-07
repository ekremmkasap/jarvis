# Next Fixes After Bring-Up V1

Priority order only. Do not widen scope.

## 1. Fix the preferred local STT path

Current blocker:

- `RealtimeSTT` initialization raises `PermissionError: [WinError 5] Access is denied`

Why this is next:

- It is the highest-ROI blocker between "booting" and "behaving like a real local assistant"
- The rest of the voice stack already reaches fallback listening mode

Expected investigation target:

- Windows permission and multiprocessing behavior around `RealtimeSTT.AudioToTextRecorder`
- device selection and microphone access mode

## 2. Decide whether wake-word mode is required immediately

Current blocker:

- `PICOVOICE_ACCESS_KEY` missing

Decision:

- if "say Jarvis" wake-word behavior is required now, configure Picovoice
- if not, continue with direct microphone listening while local STT is stabilized

## 3. Keep non-voice stacks off during stabilization

Do not boot together in the next pass:

- `services/orchestrator/main.py`
- `server/orchestrator/ui/app.py`
- `server/orchestrator/ui/agentic_app.py`
- frontend on `3000`
- OpenClaw paths

Reason:

- they do not fix the voice blocker
- they increase ownership confusion

## 4. Optional cleanup after voice is stable

- make `master_launcher.py` less misleading about gateway ownership
- document bridge vs orchestrator vs UI more sharply
- add a known-good launcher for persistent voice runtime if detached shells/tool harnesses kill child processes

## One-line next fix

Fix `RealtimeSTT` Windows `WinError 5` so `hey_jarvis.py` can stay on the preferred local speech path instead of falling through to the weaker fallback chain.
