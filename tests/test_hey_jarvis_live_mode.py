from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch


class HeyJarvisLiveModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_env = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_main_prefers_gemini_live_when_enabled(self) -> None:
        os.environ["JARVIS_GEMINI_LIVE"] = "1"
        os.environ["JARVIS_ALLOW_MULTI_INSTANCE"] = "1"
        import hey_jarvis

        module = importlib.reload(hey_jarvis)
        module.JARVIS_GEMINI_LIVE = True
        module.ARGS.text_mode = False
        module.ARGS.no_greeting = True

        with patch.object(module, "_run_gemini_live_mode") as live_mode:
            with patch.object(module, "run_realtime_stt_mode") as realtime_mode:
                module.main()

        live_mode.assert_called_once()
        realtime_mode.assert_not_called()

    def test_narrate_agent_result_uses_voice_narrator(self) -> None:
        os.environ["JARVIS_ALLOW_MULTI_INSTANCE"] = "1"
        import hey_jarvis

        module = importlib.reload(hey_jarvis)

        class FakeNarrator:
            async def run(self, task: str, context: dict) -> dict:
                return {"tts_text": "Kisa ses ozeti."}

        module._voice_narrator = FakeNarrator()

        with patch.object(module, "speak") as speak_mock:
            spoken = module.narrate_agent_result("Raw technical output", track_response=True)

        self.assertEqual(spoken, "Kisa ses ozeti.")
        speak_mock.assert_called_once_with("Kisa ses ozeti.", track_response=True)


if __name__ == "__main__":
    unittest.main()
