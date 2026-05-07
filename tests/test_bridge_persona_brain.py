from __future__ import annotations

import importlib
import io
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

os.environ.setdefault("JARVIS_ENABLE_TELEGRAM", "0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")

if "telegram" not in sys.modules:
    telegram_package = types.ModuleType("telegram")
    telegram_intelligence_module = types.ModuleType("telegram.telegram_intelligence")

    class _DummyTelegramIntelligence:
        def __init__(self, *args, **kwargs) -> None:
            pass

    telegram_intelligence_module.TelegramIntelligence = _DummyTelegramIntelligence
    telegram_package.telegram_intelligence = telegram_intelligence_module
    sys.modules["telegram"] = telegram_package
    sys.modules["telegram.telegram_intelligence"] = telegram_intelligence_module

import bridge as bridge_module


def _seed_brain_vault(root: Path, persona_id: str = "sabri") -> Path:
    base = root / "personas" / persona_id
    (base / "02-Knowledge").mkdir(parents=True, exist_ok=True)
    (base / "03-Projects").mkdir(exist_ok=True)
    (base / "04-Memory").mkdir(exist_ok=True)
    (base / "05-Skills-Refs").mkdir(exist_ok=True)
    (base / "00-Identity.md").write_text(
        (
            f"---\npersona_id: {persona_id}\nname: Sabri\nrole: test\n---\n\n"
            "# Sabri - Dijital Kimlik\n\nTest identity body.\n"
        ),
        encoding="utf-8",
    )
    (base / "01-Daily-Log.md").write_text(
        "# Sabri - Gunluk Log\n\n### 2026-04-18 10:00 UTC\n- seed entry\n",
        encoding="utf-8",
    )
    return base


class _FakeGetHandler:
    def __init__(self, path: str) -> None:
        self.path = path
        self.payload = None
        self.status_code = None

    def _json(self, data, code=200):
        self.payload = data
        self.status_code = code


class _FakePostHandler(_FakeGetHandler):
    def __init__(self, path: str, body: bytes) -> None:
        super().__init__(path)
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)


class PersonaBrainBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = importlib.reload(bridge_module)

    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        _seed_brain_vault(self.temp_root, "sabri")
        self.env_patch = patch.dict(
            os.environ,
            {"JARVIS_BRAIN_VAULT": str(self.temp_root)},
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_get_persona_brain_endpoint_returns_snapshot(self) -> None:
        handler = _FakeGetHandler("/api/persona/sabri/brain?daily_tail=6")

        self.bridge._webhandler_do_get_with_persona_brain(handler)

        self.assertEqual(handler.status_code, 200)
        self.assertEqual(handler.payload["persona_id"], "sabri")
        self.assertEqual(handler.payload["available"], True)
        self.assertIn("identity", handler.payload)
        self.assertIn("daily_log_tail", handler.payload)

    def test_post_persona_brain_memory_writes_dated_file(self) -> None:
        handler = _FakePostHandler(
            "/api/persona/sabri/brain",
            b'{"action":"memory","topic":"landing page brief","content":"hero alanini guncelle","channel":"telegram"}',
        )

        self.bridge._webhandler_do_post_with_persona_brain(handler)

        self.assertEqual(handler.status_code, 200)
        self.assertEqual(handler.payload["ok"], True)
        self.assertEqual(handler.payload["action"], "memory")
        self.assertTrue(str(handler.payload["path"]).startswith("04-Memory/"))
        memory_files = list((self.temp_root / "personas" / "sabri" / "04-Memory").glob("*.md"))
        self.assertEqual(len(memory_files), 1)
        blob = memory_files[0].read_text(encoding="utf-8")
        self.assertIn("landing page brief", blob)
        self.assertIn("hero alanini guncelle", blob)

    def test_post_persona_brain_daily_log_appends_entry(self) -> None:
        handler = _FakePostHandler(
            "/api/persona/sabri/brain",
            b'{"action":"daily_log","entry":"- kampanya sonrasi karar notu"}',
        )

        self.bridge._webhandler_do_post_with_persona_brain(handler)

        self.assertEqual(handler.status_code, 200)
        self.assertEqual(handler.payload["path"], "01-Daily-Log.md")
        daily_log = (
            self.temp_root / "personas" / "sabri" / "01-Daily-Log.md"
        ).read_text(encoding="utf-8")
        self.assertIn("kampanya sonrasi karar notu", daily_log)

    def test_autonomous_record_persona_turns_writes_persona_brain_memory(self) -> None:
        with patch.object(
            self.bridge,
            "_get_active_persona_payload",
            return_value={"id": "sabri", "name": "Sabri"},
        ):
            self.bridge._autonomous_record_persona_turns(
                101,
                "landing page icin yeni hero metni yaz",
                "tamam, hero metni taslagini cikardim",
                source="bridge",
            )

        memory_files = list((self.temp_root / "personas" / "sabri" / "04-Memory").glob("*.md"))
        self.assertEqual(len(memory_files), 1)
        blob = memory_files[0].read_text(encoding="utf-8")
        self.assertIn("landing page icin yeni hero metni yaz", blob)
        self.assertIn("tamam, hero metni taslagini cikardim", blob)
        self.assertIn("_channel: bridge_", blob)

    def test_autonomous_record_persona_turns_skips_slash_commands_for_brain(self) -> None:
        with patch.object(
            self.bridge,
            "_get_active_persona_payload",
            return_value={"id": "sabri", "name": "Sabri"},
        ):
            self.bridge._autonomous_record_persona_turns(
                101,
                "/codex-durum",
                "slotlar hazir",
                source="bridge",
            )

        memory_files = list((self.temp_root / "personas" / "sabri" / "04-Memory").glob("*.md"))
        self.assertEqual(memory_files, [])


if __name__ == "__main__":
    unittest.main()
