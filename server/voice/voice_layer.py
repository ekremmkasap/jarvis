from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from server.voice.gemini_simple_chat import GeminiConversationSession, GeminiVoiceError


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "voice_layer.log"
TASK_PREFIXES = ("task:", "gorev:", "run task:")


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("jarvis.voice.layer")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == LOG_FILE for handler in logger.handlers):
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
    return logger


class _FallbackResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FallbackModels:
    def generate_content(self, *, model: str, contents: str) -> _FallbackResponse:
        prompt = str(contents or "").strip()
        reply = f"Fallback voice mode active. Processed with {model}: {prompt[:180]}"
        return _FallbackResponse(reply)


class _FallbackGeminiClient:
    def __init__(self) -> None:
        self.models = _FallbackModels()


@dataclass(frozen=True)
class VoiceSessionStatus:
    active: bool
    remaining_seconds: float
    turns: int
    mode: str


class VoiceConversationManager:
    def __init__(
        self,
        *,
        default_duration_seconds: int = 300,
        logger: logging.Logger | None = None,
    ) -> None:
        self.default_duration_seconds = max(1, int(default_duration_seconds))
        self.logger = logger or _build_logger()
        self._sessions: dict[str, GeminiConversationSession] = {}
        self._session_modes: dict[str, str] = {}

    @staticmethod
    def is_task_request(text: str) -> bool:
        normalized = str(text or "").strip().lower()
        return any(normalized.startswith(prefix) for prefix in TASK_PREFIXES)

    @staticmethod
    def extract_task_goal(text: str) -> str:
        normalized = str(text or "").strip()
        lowered = normalized.lower()
        for prefix in TASK_PREFIXES:
            if lowered.startswith(prefix):
                return normalized[len(prefix):].strip()
        return normalized

    def start_session(
        self,
        chat_id: int | str,
        *,
        duration_seconds: int | None = None,
        client: Any | None = None,
    ) -> VoiceSessionStatus:
        session_key = str(chat_id)
        session_length = max(1, int(duration_seconds or self.default_duration_seconds))
        mode = "gemini"
        try:
            session = GeminiConversationSession(client=client, session_seconds=session_length)
        except GeminiVoiceError as exc:
            mode = "fallback"
            self.logger.warning("voice_session_fallback chat_id=%s reason=%s", session_key, exc)
            session = GeminiConversationSession(
                client=_FallbackGeminiClient(),
                session_seconds=session_length,
            )
        self._sessions[session_key] = session
        self._session_modes[session_key] = mode
        self.logger.info("voice_session_started chat_id=%s duration_seconds=%s mode=%s", session_key, session_length, mode)
        return self.get_status(session_key)

    def stop_session(self, chat_id: int | str) -> VoiceSessionStatus:
        session_key = str(chat_id)
        session = self._sessions.pop(session_key, None)
        mode = self._session_modes.pop(session_key, "inactive")
        turns = len(session.turns) if session else 0
        self.logger.info("voice_session_stopped chat_id=%s turns=%s mode=%s", session_key, turns, mode)
        return VoiceSessionStatus(active=False, remaining_seconds=0.0, turns=turns, mode=mode)

    def get_status(self, chat_id: int | str) -> VoiceSessionStatus:
        session_key = str(chat_id)
        session = self._sessions.get(session_key)
        if session is None:
            return VoiceSessionStatus(active=False, remaining_seconds=0.0, turns=0, mode="inactive")
        active = session.is_active()
        mode = self._session_modes.get(session_key, "gemini")
        if not active:
            self.stop_session(session_key)
            return VoiceSessionStatus(active=False, remaining_seconds=0.0, turns=len(session.turns), mode=mode)
        return VoiceSessionStatus(
            active=True,
            remaining_seconds=session.remaining_seconds(),
            turns=len(session.turns),
            mode=mode,
        )

    def handle_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        task_runner: Callable[[str], Any] | None = None,
    ) -> dict[str, Any]:
        session_key = str(chat_id)
        session = self._sessions.get(session_key)
        if session is None:
            raise GeminiVoiceError("Voice session is not active.")

        if not session.is_active():
            self.stop_session(session_key)
            raise GeminiVoiceError("Voice session expired.")

        reply = session.send_user_message(text)
        payload: dict[str, Any] = {
            "reply": reply,
            "task_result": None,
            "turns": len(session.turns),
            "remaining_seconds": session.remaining_seconds(),
            "mode": self._session_modes.get(session_key, "gemini"),
        }
        self.logger.info("voice_session_turn chat_id=%s turns=%s", session_key, len(session.turns))

        if task_runner and self.is_task_request(text):
            goal = self.extract_task_goal(text)
            task_result = task_runner(goal)
            payload["task_result"] = task_result
            if isinstance(task_result, dict):
                task_summary = str(task_result.get("summary") or task_result.get("status") or "Task completed.")
            else:
                task_summary = str(task_result)
            payload["reply"] = f"{reply}\n\nTask flow:\n{task_summary}"
            self.logger.info("voice_session_task chat_id=%s goal=%s", session_key, goal[:160])

        return payload
