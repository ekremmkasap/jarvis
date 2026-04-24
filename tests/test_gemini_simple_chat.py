from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from server.voice.gemini_simple_chat import (
    GeminiConversationSession,
    GeminiSessionTimeout,
    GeminiVoiceError,
    build_default_logger,
)


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.current = float(start)

    def now(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += float(seconds)


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, fail_on: int | None = None, empty_on: int | None = None) -> None:
        self.calls = 0
        self.fail_on = fail_on
        self.empty_on = empty_on

    def generate_content(self, *, model: str, contents: str):
        self.calls += 1
        if self.fail_on is not None and self.calls == self.fail_on:
            raise RuntimeError("upstream_error")
        if self.empty_on is not None and self.calls == self.empty_on:
            return _FakeResponse("")
        return _FakeResponse(f"echo:{contents}")


class _FakeClient:
    def __init__(self, models: _FakeModels) -> None:
        self.models = models


class GeminiSimpleChatTests(unittest.TestCase):
    def test_two_minute_multi_turn_conversation_without_errors(self) -> None:
        clock = _FakeClock()
        models = _FakeModels()
        client = _FakeClient(models=models)

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "server" / "logs" / "gemini_voice.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            logger = build_default_logger(log_path=log_path)

            session = GeminiConversationSession(
                client=client,
                session_seconds=300,
                logger=logger,
                time_fn=clock.now,
            )

            prompts = [
                "Selam Jarvis",
                "Bugun yapilacaklari ozetle",
                "Oncelik sirasi ver",
                "Riskleri de ekle",
                "Bir de kısa check-list yaz",
                "Toparlayip tek cümleyle bitir",
            ]
            replies = []
            for prompt in prompts:
                replies.append(session.send_user_message(prompt))
                clock.advance(20)

            self.assertEqual(len(replies), 6)
            self.assertTrue(all(reply.startswith("echo:") for reply in replies))
            self.assertEqual(len(session.turns), 6)
            self.assertLessEqual(session.elapsed_seconds(), 120.0)
            self.assertTrue(log_path.exists())
            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn("Gemini voice session started", log_text)
            self.assertIn("Gemini assistant_turn", log_text)
            for handler in list(logger.handlers):
                handler.flush()
                handler.close()
                logger.removeHandler(handler)

    def test_session_timeout_is_enforced(self) -> None:
        clock = _FakeClock()
        client = _FakeClient(models=_FakeModels())
        session = GeminiConversationSession(client=client, session_seconds=5, time_fn=clock.now)
        session.send_user_message("ilk tur")
        clock.advance(6)
        with self.assertRaises(GeminiSessionTimeout):
            session.send_user_message("ikinci tur")

    def test_upstream_errors_are_retried(self) -> None:
        clock = _FakeClock()
        client = _FakeClient(models=_FakeModels(fail_on=1))
        session = GeminiConversationSession(client=client, session_seconds=120, time_fn=clock.now)
        reply = session.send_user_message("hata testi")
        self.assertEqual(reply, "echo:hata testi")
        self.assertEqual(client.models.calls, 2)

    def test_empty_response_is_retried(self) -> None:
        clock = _FakeClock()
        client = _FakeClient(models=_FakeModels(empty_on=1))
        session = GeminiConversationSession(client=client, session_seconds=120, time_fn=clock.now)
        reply = session.send_user_message("bos yanit testi")
        self.assertEqual(reply, "echo:bos yanit testi")
        self.assertEqual(client.models.calls, 2)


if __name__ == "__main__":
    unittest.main()
