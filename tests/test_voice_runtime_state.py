from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.voice import runtime_state


class VoiceRuntimeStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.patches = [
            patch.object(runtime_state, "LOG_DIR", self.temp_dir),
            patch.object(runtime_state, "DESKTOP_ASSISTANT_PATH", self.temp_dir / "desktop_assistant.json"),
            patch.object(runtime_state, "VOICE_EVENTS_PATH", self.temp_dir / "voice_runtime_events.jsonl"),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_publish_runtime_state_writes_canonical_payload(self) -> None:
        runtime_state.set_runtime_online(
            source="hey_jarvis",
            detail="RealtimeSTT hazir",
            mode="realtime_stt",
            wake_mode="jarvis_keyword",
            stt_backend="realtime_stt",
            tts_backend="edge_tts",
            agent="jarvis",
            phase="idle",
            text="Jarvis hazir.",
        )
        runtime_state.publish_runtime_state(
            phase="thinking",
            latest_preview="chrome ac",
            last_heard="Jarvis chrome ac",
            runtime_status="online",
            runtime_detail="Komut isleniyor",
            source="hey_jarvis",
            tts_backend="edge_tts",
        )
        runtime_state.publish_runtime_state(
            phase="speaking",
            text="Chrome aciliyor",
            last_response="Chrome aciliyor",
            increment_turn=True,
            runtime_status="online",
            runtime_detail="Yanit veriliyor",
            source="hey_jarvis",
            tts_backend="edge_tts",
        )

        payload = runtime_state.load_runtime_state()
        self.assertEqual(payload["phase"], "speaking")
        self.assertEqual(payload["runtime"]["source"], "hey_jarvis")
        self.assertEqual(payload["runtime"]["status"], "online")
        self.assertEqual(payload["agent"], "jarvis")
        self.assertEqual(payload["voice"]["last_heard"], "Jarvis chrome ac")
        self.assertEqual(payload["voice"]["last_response"], "Chrome aciliyor")
        self.assertEqual(payload["voice"]["turn_count"], 1)
        self.assertEqual(payload["latestPreview"], "chrome ac")

        events = (self.temp_dir / "voice_runtime_events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(events), 3)
        last_event = json.loads(events[-1])
        self.assertEqual(last_event["phase"], "speaking")
        self.assertEqual(last_event["agent"], "jarvis")
        self.assertEqual(last_event["voice"]["turn_count"], 1)

    def test_publish_runtime_state_preserves_active_persona_agent(self) -> None:
        runtime_state.publish_runtime_state(
            phase="listening",
            text="Buse dinliyor.",
            agent="buse",
            runtime_status="online",
            runtime_detail="Hazir",
            source="hey_jarvis",
            tts_backend="edge_tts",
        )

        payload = runtime_state.load_runtime_state()
        self.assertEqual(payload["agent"], "buse")

        event = json.loads(
            (self.temp_dir / "voice_runtime_events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()[-1]
        )
        self.assertEqual(event["agent"], "buse")


if __name__ == "__main__":
    unittest.main()
