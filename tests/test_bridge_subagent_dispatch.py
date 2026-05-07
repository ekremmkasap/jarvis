from __future__ import annotations

import importlib
import io
import json
import os
import sys
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

from subagent_dispatcher import (
    DispatchResult,
    PersonaNotFoundError,
    SubAgentNotAllowedError,
)


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


class SubAgentBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = importlib.reload(bridge_module)

    # ---------- GET /api/persona/<id>/subagents ----------

    def test_get_subagents_returns_persona_list(self) -> None:
        handler = _FakeGetHandler("/api/persona/sabri/subagents")
        self.bridge._webhandler_do_get_with_subagents(handler)

        self.assertEqual(handler.status_code, 200)
        self.assertEqual(handler.payload["ok"], True)
        self.assertEqual(handler.payload["persona_id"], "sabri")
        names = [entry["name"] for entry in handler.payload["subagents"]]
        self.assertIn("obsidian_writer", names)
        self.assertIn("copywriter", names)

    def test_get_subagents_unknown_persona_returns_empty_list(self) -> None:
        handler = _FakeGetHandler("/api/persona/ghost_persona_xyz/subagents")
        self.bridge._webhandler_do_get_with_subagents(handler)

        self.assertEqual(handler.status_code, 200)
        self.assertEqual(handler.payload["ok"], True)
        self.assertEqual(handler.payload["count"], 0)

    # ---------- POST /api/persona/<id>/subagent/<name> ----------

    def _stub_dispatcher_with(self, result: DispatchResult):
        dispatcher_mod = self.bridge._load_subagent_dispatcher_module()

        class _StubDispatcher:
            def dispatch(self_, persona_id, agent_name, task, **kwargs):
                return result

        return patch.object(dispatcher_mod, "get_dispatcher", return_value=_StubDispatcher())

    def test_post_dispatch_success_returns_result_dict(self) -> None:
        result = DispatchResult(
            persona_id="sabri",
            agent_name="copywriter",
            task="reklam metni yaz",
            ok=True,
            output="Başlık: Yeni kampanya",
            model="m1",
            provider="stub",
        )
        with self._stub_dispatcher_with(result):
            handler = _FakePostHandler(
                "/api/persona/sabri/subagent/copywriter",
                b'{"task":"reklam metni yaz"}',
            )
            self.bridge._webhandler_do_post_with_subagents(handler)

        self.assertEqual(handler.status_code, 200)
        self.assertEqual(handler.payload["ok"], True)
        self.assertEqual(handler.payload["agent_name"], "copywriter")
        self.assertEqual(handler.payload["output"], "Başlık: Yeni kampanya")

    def test_post_dispatch_missing_task_returns_400(self) -> None:
        handler = _FakePostHandler(
            "/api/persona/sabri/subagent/copywriter",
            b'{}',
        )
        self.bridge._webhandler_do_post_with_subagents(handler)

        self.assertEqual(handler.status_code, 400)
        self.assertEqual(handler.payload["ok"], False)
        self.assertIn("task", str(handler.payload.get("message", "")).lower())

    def test_post_dispatch_unknown_persona_returns_404(self) -> None:
        dispatcher_mod = self.bridge._load_subagent_dispatcher_module()

        class _BoomDispatcher:
            def dispatch(self_, persona_id, agent_name, task, **kwargs):
                raise PersonaNotFoundError(f"persona not defined: {persona_id}")

        with patch.object(dispatcher_mod, "get_dispatcher", return_value=_BoomDispatcher()):
            handler = _FakePostHandler(
                "/api/persona/unknown/subagent/copywriter",
                b'{"task":"hello"}',
            )
            self.bridge._webhandler_do_post_with_subagents(handler)

        self.assertEqual(handler.status_code, 404)
        self.assertEqual(handler.payload["error"], "persona_not_found")

    def test_post_dispatch_not_allowed_returns_403(self) -> None:
        dispatcher_mod = self.bridge._load_subagent_dispatcher_module()

        class _DenyDispatcher:
            def dispatch(self_, persona_id, agent_name, task, **kwargs):
                raise SubAgentNotAllowedError("not authorized")

        with patch.object(dispatcher_mod, "get_dispatcher", return_value=_DenyDispatcher()):
            handler = _FakePostHandler(
                "/api/persona/sabri/subagent/shadowbroker_operator",
                b'{"task":"scan"}',
            )
            self.bridge._webhandler_do_post_with_subagents(handler)

        self.assertEqual(handler.status_code, 403)
        self.assertEqual(handler.payload["error"], "subagent_not_allowed")

    def test_post_dispatch_invalid_json_returns_400(self) -> None:
        handler = _FakePostHandler(
            "/api/persona/sabri/subagent/copywriter",
            b'{not-json',
        )
        self.bridge._webhandler_do_post_with_subagents(handler)

        self.assertEqual(handler.status_code, 400)
        self.assertIn("invalid JSON", handler.payload["error"])

    def test_post_dispatch_non_object_body_returns_400(self) -> None:
        handler = _FakePostHandler(
            "/api/persona/sabri/subagent/copywriter",
            b'[1,2,3]',
        )
        self.bridge._webhandler_do_post_with_subagents(handler)

        self.assertEqual(handler.status_code, 400)
        self.assertIn("JSON object", handler.payload["error"])

    def test_post_dispatch_passes_persist_flag(self) -> None:
        captured = {}

        class _RecordingDispatcher:
            def dispatch(self_, persona_id, agent_name, task, **kwargs):
                captured.update(kwargs)
                captured["persona_id"] = persona_id
                captured["agent_name"] = agent_name
                captured["task"] = task
                return DispatchResult(
                    persona_id=persona_id,
                    agent_name=agent_name,
                    task=task,
                    ok=True,
                    output="ok",
                )

        dispatcher_mod = self.bridge._load_subagent_dispatcher_module()
        with patch.object(dispatcher_mod, "get_dispatcher", return_value=_RecordingDispatcher()):
            handler = _FakePostHandler(
                "/api/persona/sabri/subagent/obsidian_writer",
                json.dumps({
                    "task": "yaz",
                    "persist_to_brain": True,
                    "context": {"kanal": "telegram"},
                    "max_tokens": 512,
                }).encode("utf-8"),
            )
            self.bridge._webhandler_do_post_with_subagents(handler)

        self.assertEqual(handler.status_code, 200)
        self.assertEqual(captured["persona_id"], "sabri")
        self.assertEqual(captured["agent_name"], "obsidian_writer")
        self.assertEqual(captured["task"], "yaz")
        self.assertTrue(captured["persist_to_brain"])
        self.assertEqual(captured["context"], {"kanal": "telegram"})
        self.assertEqual(captured["max_tokens"], 512)


if __name__ == "__main__":
    unittest.main()
