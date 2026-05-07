from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_PATH = Path(__file__).resolve().parents[1]
MARKXXXV_PATH = ROOT_PATH / "external-repos" / "Mark-XXXV"

if str(MARKXXXV_PATH) not in sys.path:
    sys.path.insert(0, str(MARKXXXV_PATH))

from memory import memory_manager


class _QuotaModel:
    def __init__(self) -> None:
        self.calls = 0

    def generate_content(self, _prompt: str):
        self.calls += 1
        raise RuntimeError("429 quota exceeded. Please retry in 12.5s.")


class MarkXXXVMemoryManagerTests(unittest.TestCase):
    def test_stage1_quota_error_enters_cooldown_and_skips_next_call(self) -> None:
        model = _QuotaModel()
        fake_genai = types.ModuleType("google.generativeai")
        fake_genai.configure = lambda api_key: None
        fake_genai.GenerativeModel = lambda _name: model
        fake_google = types.ModuleType("google")
        fake_google.generativeai = fake_genai

        memory_manager._STAGE1_BACKOFF_UNTIL = 0.0

        with (
            patch.dict(sys.modules, {"google": fake_google, "google.generativeai": fake_genai}),
            patch.object(memory_manager.time, "monotonic", side_effect=[0.0, 0.0, 1.0]),
        ):
            first = memory_manager.should_extract_memory("test", "reply", "key")
            second = memory_manager.should_extract_memory("test", "reply", "key")

        self.assertFalse(first)
        self.assertFalse(second)
        self.assertEqual(model.calls, 1)
        self.assertGreater(memory_manager._STAGE1_BACKOFF_UNTIL, 10.0)


if __name__ == "__main__":
    unittest.main()
