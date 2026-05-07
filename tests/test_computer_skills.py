from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from server.skills import computer_agent_skill, computer_control_skill


class _FakePyAutoGUI:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.FAILSAFE = False
        self.PAUSE = 0.0

    def moveTo(self, x: int, y: int, duration: float = 0.0) -> None:
        self.calls.append(("moveTo", x, y, duration))

    def click(
        self,
        x: int,
        y: int,
        *,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.15,
    ) -> None:
        self.calls.append(("click", x, y, button, clicks, interval))

    def write(self, text: str, interval: float = 0.05) -> None:
        self.calls.append(("write", text, interval))

    def press(self, key: str) -> None:
        self.calls.append(("press", key))

    def hotkey(self, *keys: str) -> None:
        self.calls.append(("hotkey",) + keys)

    def scroll(self, clicks: int) -> None:
        self.calls.append(("scroll", clicks))

    def size(self) -> tuple[int, int]:
        return (1920, 1080)

    def position(self) -> tuple[int, int]:
        return (100, 200)

    def screenshot(self, path: str | None = None):
        self.calls.append(("screenshot", path))
        if path:
            Path(path).write_bytes(b"fake-image")
        return None


class ComputerSkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.fake_pyautogui = _FakePyAutoGUI()

        self.patches = [
            patch.object(computer_control_skill, "LOG_DIR", self.temp_dir),
            patch.object(computer_control_skill, "STATUS_FILE", self.temp_dir / "desktop_control_status.json"),
            patch.object(computer_control_skill, "EVENTS_FILE", self.temp_dir / "desktop_control_events.jsonl"),
            patch.object(computer_control_skill, "SCREENSHOT_FILE", self.temp_dir / "desktop_control_last.png"),
            patch.object(computer_control_skill.importlib, "import_module", return_value=self.fake_pyautogui),
            patch.object(computer_agent_skill, "STATUS_FILE", self.temp_dir / "desktop_agent_status.json"),
            patch.object(computer_agent_skill, "EVENTS_FILE", self.temp_dir / "desktop_agent_events.jsonl"),
        ]

        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_action_plan_uses_explicit_primitives_and_logs_status(self) -> None:
        result = computer_control_skill.execute_action_plan(
            [
                {"type": "click", "x": 10, "y": 20},
                {"type": "type", "text": "secret value"},
            ],
            source="test_suite",
            goal="Fill the login form",
        )

        self.assertTrue(result["ok"])
        self.assertIn(("click", 10, 20, "left", 1, 0.15), self.fake_pyautogui.calls)
        self.assertIn(("write", "secret value", 0.05), self.fake_pyautogui.calls)

        status = json.loads((self.temp_dir / "desktop_control_status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["source"], "test_suite")
        self.assertEqual(status["last_action"]["type"], "type")
        self.assertEqual(status["last_action"]["text_length"], len("secret value"))
        self.assertNotIn("text", status["last_action"])

    def test_plan_action_blocks_unsupported_action_types(self) -> None:
        invalid_plan = json.dumps(
            {
                "goal_status": "ready_to_execute",
                "summary": "Run a shell command",
                "confidence": 0.9,
                "actions": [{"type": "shell", "command": "del C:\\"}],
            }
        )

        with patch.object(computer_agent_skill, "_call_ollama_generate", return_value=invalid_plan):
            plan = computer_agent_skill.plan_action(
                "Delete files",
                "Windows Explorer is open on the Desktop.",
            )

        self.assertEqual(plan["goal_status"], "blocked")
        self.assertEqual(plan["actions"], [])
        self.assertTrue(any("unsupported action type" in error for error in plan["validation_errors"]))

    def test_run_computer_agent_executes_validated_action_plan(self) -> None:
        safe_plan = {
            "goal_status": "ready_to_execute",
            "summary": "Click the login button that is already visible.",
            "confidence": 0.8,
            "actions": [{"type": "click", "x": 120, "y": 240, "reason": "Login button"}],
            "validation_errors": [],
        }

        with patch.object(
            computer_agent_skill,
            "analyze_screen",
            return_value="Browser acik, login butonu gorunuyor.",
        ), patch.object(computer_agent_skill, "plan_action", return_value=safe_plan):
            result = computer_agent_skill.run_computer_agent("/yap", "giris yap")

        self.assertIn("*Plan:*", result)
        self.assertIn(("click", 120, 240, "left", 1, 0.15), self.fake_pyautogui.calls)

        status = json.loads((self.temp_dir / "desktop_agent_status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["plan"]["action_count"], 1)

    def test_run_computer_agent_blocks_raw_code_path(self) -> None:
        result = computer_agent_skill.run_computer_agent("/kodcalistir", "print('hello')")

        self.assertIn("devre disi", result)
        status = json.loads((self.temp_dir / "desktop_agent_status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "blocked")
        self.assertEqual(status["command"], "kodcalistir")

    def test_browser_goal_uses_playwright_fallback(self) -> None:
        with patch.object(computer_agent_skill, "_run_browser_goal", return_value="*Tarayici:* Tarayici acildi.") as browser_goal:
            result = computer_agent_skill.run_computer_agent("/yap", "youtube ac")

        self.assertEqual(result, "*Tarayici:* Tarayici acildi.")
        browser_goal.assert_called_once_with("youtube ac", "yap")


if __name__ == "__main__":
    unittest.main()
