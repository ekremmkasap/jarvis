#!/usr/bin/env python3
"""Gemini chat session primitives for Jarvis voice integration."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from retry_strategy import RetryStrategy, RetryConfig

DEFAULT_MODEL = "models/gemini-2.5-flash"
DEFAULT_SESSION_SECONDS = 300


class GeminiVoiceError(RuntimeError):
    """Base error type for Gemini voice layer failures."""


class GeminiConfigError(GeminiVoiceError):
    """Raised when required configuration is missing."""


class GeminiSessionTimeout(GeminiVoiceError):
    """Raised when a session exceeded allowed duration."""


def load_env_file(env_path: Path | None = None) -> None:
    """Load .env keys if present without overriding existing environment."""
    target = env_path or Path(".env")
    if not target.exists():
        return
    for raw_line in target.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def resolve_api_key() -> str:
    api_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise GeminiConfigError("Missing Gemini API key. Set GEMINI_API_KEY or GOOGLE_API_KEY.")
    return api_key


def build_default_logger(log_path: Path | None = None) -> logging.Logger:
    logs_dir = Path("server") / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    final_path = log_path or (logs_dir / "gemini_voice.log")

    logger_name = f"jarvis.voice.gemini.{final_path.resolve()}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == final_path.resolve():
            return logger

    file_handler = logging.FileHandler(final_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)
    return logger


def build_gemini_client(api_key: Optional[str] = None):
    try:
        import google.genai as genai
    except Exception as exc:  # pragma: no cover - exercised in runtime environments without dependency
        raise GeminiVoiceError(f"google.genai import failed: {exc}") from exc

    key = api_key or resolve_api_key()
    return genai.Client(api_key=key)


@dataclass
class ConversationTurn:
    user_text: str
    assistant_text: str
    elapsed_seconds: float


class GeminiConversationSession:
    """Stateful Gemini conversation session with hard session timeout, circuit breaker, and retry logic."""

    def __init__(
        self,
        *,
        client=None,
        model: str = DEFAULT_MODEL,
        session_seconds: int = DEFAULT_SESSION_SECONDS,
        logger: Optional[logging.Logger] = None,
        time_fn: Optional[Callable[[], float]] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        if session_seconds <= 0:
            raise ValueError("session_seconds must be positive.")
        self.client = client or build_gemini_client()
        self.model = model
        self.session_seconds = int(session_seconds)
        self.logger = logger or build_default_logger()
        self._time_fn = time_fn or time.time
        self._started_at = self._time_fn()
        self.turns: list[ConversationTurn] = []

        # Initialize hardening components
        self.circuit_breaker = CircuitBreaker(
            circuit_breaker_config or CircuitBreakerConfig(failure_threshold=3, recovery_timeout=300),
            logger=self.logger,
        )
        self.retry_strategy = RetryStrategy(retry_config or RetryConfig(max_attempts=3), logger=self.logger)

        self.logger.info("Gemini voice session started model=%s duration_seconds=%s", self.model, self.session_seconds)

    def elapsed_seconds(self) -> float:
        return max(0.0, self._time_fn() - self._started_at)

    def is_active(self) -> bool:
        return self.elapsed_seconds() <= self.session_seconds

    def remaining_seconds(self) -> float:
        return max(0.0, self.session_seconds - self.elapsed_seconds())

    def send_user_message(self, user_text: str, use_fallback: bool = True) -> str:
        text = str(user_text or "").strip()
        if not text:
            raise GeminiVoiceError("user_text cannot be empty.")
        if not self.is_active():
            raise GeminiSessionTimeout("Conversation session expired.")

        self.logger.info("Gemini user_turn elapsed=%.2f text=%s", self.elapsed_seconds(), text[:200])

        try:
            # Attempt with circuit breaker and retry
            def _call_gemini():
                response = self.client.models.generate_content(model=self.model, contents=text)
                assistant_text = str(getattr(response, "text", "") or "").strip()
                if not assistant_text:
                    raise GeminiVoiceError("Gemini returned empty response text.")
                return assistant_text

            try:
                assistant_text = self.circuit_breaker.call(self.retry_strategy.execute, _call_gemini)
            except CircuitBreakerOpenError as exc:
                self.logger.error("Circuit breaker OPEN: %s", exc)
                if use_fallback:
                    return self._get_fallback_response(text)
                raise GeminiVoiceError(f"API service temporarily unavailable: {exc}") from exc

        except GeminiVoiceError:
            raise
        except Exception as exc:
            self.logger.exception("Gemini request failed: %s", exc)
            if use_fallback:
                return self._get_fallback_response(text)
            raise GeminiVoiceError(f"Gemini request failed: {exc}") from exc

        turn = ConversationTurn(user_text=text, assistant_text=assistant_text, elapsed_seconds=self.elapsed_seconds())
        self.turns.append(turn)
        self.logger.info("Gemini assistant_turn elapsed=%.2f chars=%d", turn.elapsed_seconds, len(assistant_text))
        return assistant_text

    def _get_fallback_response(self, user_text: str) -> str:
        """Generate helpful fallback response when API is unavailable."""
        self.logger.warning("Using fallback response for user input: %s", user_text[:100])

        fallback_responses = {
            "merhaba": "Merhaba! Şu anda Gemini API'ye erişilemiyor. Lütfen birkaç saniye sonra tekrar deneyin.",
            "selam": "Selam! API geçici olarak kullanılamıyor. Tekrar bağlantı sağlanacak.",
            "help": "Help is temporarily unavailable. The API service is experiencing issues. Please try again in a few moments.",
            "yardım": "Yardım şu anda sağlanemiyor. API servisi zorluk yaşıyor. Lütfen birkaç saniye sonra deneyin.",
        }

        text_lower = user_text.lower().strip()
        for key, response in fallback_responses.items():
            if key in text_lower:
                return response

        return "API servisi şu anda kullanılamıyor. Lütfen birkaç saniye sonra tekrar deneyin. / API service temporarily unavailable. Please try again shortly."


def run_cli_chat() -> int:
    load_env_file()
    logger = build_default_logger()

    try:
        session = GeminiConversationSession(logger=logger)
    except GeminiVoiceError as exc:
        print(f"Hata: {exc}")
        return 1

    print("Jarvis Gemini Chat (type 'quit' to exit)")
    print("-" * 40)
    while session.is_active():
        user_input = input("\nSiz: ").strip()
        if user_input.lower() in {"quit", "exit", "cikis"}:
            break
        if not user_input:
            continue
        try:
            reply = session.send_user_message(user_input)
            print(f"Jarvis: {reply}\n")
        except GeminiSessionTimeout:
            print("Oturum suresi doldu.")
            break
        except GeminiVoiceError as exc:
            print(f"Hata: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli_chat())
