from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT_PATH = Path(__file__).resolve().parents[1]
MARKXXXV_PATH = ROOT_PATH / "external-repos" / "Mark-XXXV"

if str(MARKXXXV_PATH) not in sys.path:
    sys.path.insert(0, str(MARKXXXV_PATH))

import actions.computer_settings as computer_settings


class _FakePyAutoGUI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def press(self, key: str) -> None:
        self.calls.append(("press", key))


class MarkXXXVComputerSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_pyautogui = _FakePyAutoGUI()
        self.original_pyautogui = getattr(computer_settings, "pyautogui", None)
        self.original_flag = computer_settings._PYAUTOGUI
        computer_settings.pyautogui = self.fake_pyautogui
        computer_settings._PYAUTOGUI = True

    def tearDown(self) -> None:
        if self.original_pyautogui is not None:
            computer_settings.pyautogui = self.original_pyautogui
        computer_settings._PYAUTOGUI = self.original_flag

    def test_microphone_description_toggles_ui_mute_hotkey(self) -> None:
        result = computer_settings.computer_settings({"description": "mikrofonu kapat"})

        self.assertEqual(result, "Done: toggle_microphone.")
        self.assertEqual(self.fake_pyautogui.calls, [("press", "f4")])

    def test_computer_control_action_re_detects_from_description(self) -> None:
        result = computer_settings.computer_settings(
            {"action": "computer_control", "description": "mute the microphone"}
        )

        self.assertEqual(result, "Done: toggle_microphone.")
        self.assertEqual(self.fake_pyautogui.calls, [("press", "f4")])


if __name__ == "__main__":
    unittest.main()
