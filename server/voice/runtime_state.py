from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "server" / "logs"
DESKTOP_ASSISTANT_PATH = LOG_DIR / "desktop_assistant.json"
VOICE_EVENTS_PATH = LOG_DIR / "voice_runtime_events.jsonl"

_LOCK = threading.Lock()

_DEFAULT_STATE: dict[str, Any] = {
    "phase": "idle",
    "text": "Jarvis hazir.",
    "agent": "voice",
    "latestPreview": "",
    "updated_at": 0.0,
    "runtime": {
        "status": "offline",
        "detail": "voice runtime inactive",
        "source": "unknown",
        "mode": "",
        "wake_mode": "",
        "stt_backend": "",
        "tts_backend": "",
    },
    "voice": {
        "last_heard": "",
        "last_response": "",
        "heard_at": 0.0,
        "response_at": 0.0,
        "turn_count": 0,
    },
}


def _clone_default_state() -> dict[str, Any]:
    return json.loads(json.dumps(_DEFAULT_STATE))


def load_runtime_state() -> dict[str, Any]:
    if DESKTOP_ASSISTANT_PATH.exists():
        try:
            payload = json.loads(DESKTOP_ASSISTANT_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                merged = _clone_default_state()
                merged.update(payload)
                if isinstance(payload.get("runtime"), dict):
                    merged["runtime"].update(payload["runtime"])
                if isinstance(payload.get("voice"), dict):
                    merged["voice"].update(payload["voice"])
                return merged
        except Exception:
            pass
    return _clone_default_state()


def _write_state(payload: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DESKTOP_ASSISTANT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _append_event(payload: dict[str, Any]) -> None:
    event = {
        "updated_at": payload.get("updated_at", time.time()),
        "phase": payload.get("phase", "idle"),
        "agent": str(payload.get("agent") or ""),
        "text": str(payload.get("text") or "")[:180],
        "latestPreview": str(payload.get("latestPreview") or "")[:180],
        "runtime": payload.get("runtime", {}),
        "voice": {
            "last_heard": str(payload.get("voice", {}).get("last_heard") or "")[:160],
            "last_response": str(payload.get("voice", {}).get("last_response") or "")[:160],
            "turn_count": int(payload.get("voice", {}).get("turn_count") or 0),
        },
    }
    try:
        with VOICE_EVENTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def publish_runtime_state(
    *,
    phase: str | None = None,
    text: str | None = None,
    latest_preview: str | None = None,
    agent: str | None = None,
    runtime_status: str | None = None,
    runtime_detail: str | None = None,
    source: str | None = None,
    mode: str | None = None,
    wake_mode: str | None = None,
    stt_backend: str | None = None,
    tts_backend: str | None = None,
    last_heard: str | None = None,
    last_response: str | None = None,
    increment_turn: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with _LOCK:
        payload = load_runtime_state()
        now = time.time()

        if phase is not None:
            payload["phase"] = str(phase or "idle").strip() or "idle"
        if text is not None:
            payload["text"] = str(text or "").strip() or _DEFAULT_STATE["text"]
        if latest_preview is not None:
            payload["latestPreview"] = str(latest_preview or "").strip()[:180]
        if agent is not None:
            payload["agent"] = str(agent or "").strip() or _DEFAULT_STATE["agent"]

        runtime = payload.setdefault("runtime", {})
        if runtime_status is not None:
            runtime["status"] = str(runtime_status or "").strip() or _DEFAULT_STATE["runtime"]["status"]
        if runtime_detail is not None:
            runtime["detail"] = str(runtime_detail or "").strip()
        if source is not None:
            runtime["source"] = str(source or "").strip()
        if mode is not None:
            runtime["mode"] = str(mode or "").strip()
        if wake_mode is not None:
            runtime["wake_mode"] = str(wake_mode or "").strip()
        if stt_backend is not None:
            runtime["stt_backend"] = str(stt_backend or "").strip()
        if tts_backend is not None:
            runtime["tts_backend"] = str(tts_backend or "").strip()

        voice = payload.setdefault("voice", {})
        if last_heard is not None:
            heard_text = str(last_heard or "").strip()
            voice["last_heard"] = heard_text[:180]
            voice["heard_at"] = now
            if latest_preview is None and heard_text:
                payload["latestPreview"] = heard_text[:180]
        if last_response is not None:
            response_text = str(last_response or "").strip()
            voice["last_response"] = response_text[:220]
            voice["response_at"] = now
            if increment_turn and response_text:
                voice["turn_count"] = int(voice.get("turn_count") or 0) + 1
            if text is None and response_text:
                payload["text"] = response_text[:220]

        payload["updated_at"] = now

        if extra:
            payload.update(extra)

        _write_state(payload)
        _append_event(payload)
        return payload


def set_runtime_online(
    *,
    source: str,
    detail: str = "",
    mode: str = "",
    wake_mode: str = "",
    stt_backend: str = "",
    tts_backend: str = "",
    agent: str = "voice",
    phase: str = "idle",
    text: str = "Jarvis hazir.",
) -> dict[str, Any]:
    return publish_runtime_state(
        phase=phase,
        text=text,
        agent=agent,
        runtime_status="online",
        runtime_detail=detail,
        source=source,
        mode=mode,
        wake_mode=wake_mode,
        stt_backend=stt_backend,
        tts_backend=tts_backend,
    )


def set_runtime_offline(
    *,
    source: str,
    detail: str = "voice runtime offline",
    agent: str = "voice",
    text: str = "Jarvis cevrimdisi.",
) -> dict[str, Any]:
    return publish_runtime_state(
        phase="offline",
        text=text,
        agent=agent,
        runtime_status="offline",
        runtime_detail=detail,
        source=source,
    )
