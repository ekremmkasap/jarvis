from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

import skills.playwright_browser_skill as browser_skill


class _FakeSession:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.calls: list[tuple[str, str]] = []

    def open_url(self, target: str) -> str:
        self.calls.append(("open", target))
        return f"OPEN {target}"

    def search(self, query: str) -> str:
        self.calls.append(("search", query))
        return f"SEARCH {query}"

    def click(self, target: str) -> str:
        self.calls.append(("click", target))
        return f"CLICK {target}"

    def type_text(self, text: str) -> str:
        self.calls.append(("type", text))
        return f"TYPE {text}"

    def screenshot(self) -> str:
        self.calls.append(("screenshot", ""))
        return "SHOT"

    def close(self) -> str:
        self.calls.append(("close", ""))
        return "CLOSE"


class PlaywrightBrowserSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = importlib.reload(browser_skill)
        self.module._BROWSER_SESSIONS.clear()

    def test_open_command_uses_same_session_per_user(self) -> None:
        fake_session = _FakeSession("42")
        with patch.object(self.module, "BrowserSession", return_value=fake_session) as browser_ctor:
            first = self.module.handle_browser("youtube.com ac", "42")
            second = self.module.handle_browser("ara: python tutorial", "42")

        self.assertEqual(first, "OPEN youtube.com")
        self.assertEqual(second, "SEARCH python tutorial")
        self.assertEqual(browser_ctor.call_count, 1)
        self.assertEqual(fake_session.calls, [("open", "youtube.com"), ("search", "python tutorial")])

    def test_click_and_type_commands(self) -> None:
        fake_session = _FakeSession("abc")
        with patch.object(self.module, "BrowserSession", return_value=fake_session):
            click_result = self.module.handle_browser("tikla: Giris Yap", "abc")
            type_result = self.module.handle_browser("yaz merhaba dunya", "abc")

        self.assertEqual(click_result, "CLICK Giris Yap")
        self.assertEqual(type_result, "TYPE merhaba dunya")

    def test_screenshot_and_close(self) -> None:
        fake_session = _FakeSession("u1")
        with patch.object(self.module, "BrowserSession", return_value=fake_session):
            shot_result = self.module.handle_browser("ekran goruntusu", "u1")
            close_result = self.module.handle_browser("kapat", "u1")

        self.assertEqual(shot_result, "SHOT")
        self.assertEqual(close_result, "CLOSE")
        self.assertNotIn("u1", self.module._BROWSER_SESSIONS)

    def test_empty_command_returns_usage(self) -> None:
        result = self.module.handle_browser("", "x")
        self.assertIn("Kullanim: /tarayici", result)


if __name__ == "__main__":
    unittest.main()
