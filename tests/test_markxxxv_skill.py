from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

import skills.markxxxv_skill as markxxxv_skill


class _FakeHTTPResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class MarkxxxvSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_env = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.original_env)
        importlib.reload(markxxxv_skill)

    def test_usage_message(self) -> None:
        module = importlib.reload(markxxxv_skill)
        result = module.handle_markxxxv("")
        self.assertIn("Kullanim: /markxxxv [gorev]", result)

    def test_status_does_not_leak_api_key(self) -> None:
        os.environ["MARKXXXV_API_KEY"] = "secret-value"
        module = importlib.reload(markxxxv_skill)

        result = module.markxxxv_status()

        self.assertIn("API key: `var`", result)
        self.assertNotIn("secret-value", result)

    def test_http_mode_returns_reply(self) -> None:
        os.environ["MARKXXXV_MODE"] = "http"
        os.environ["MARKXXXV_BASE_URL"] = "http://127.0.0.1:9999"
        os.environ["MARKXXXV_API_KEY"] = "test-key"
        module = importlib.reload(markxxxv_skill)

        with patch.object(module, "urlopen", return_value=_FakeHTTPResponse('{"reply":"Tamam"}')) as mocked_urlopen:
            result = module.handle_markxxxv("test gorevi", "42")

        self.assertEqual(result, "Tamam")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:9999/command")
        self.assertEqual(json.loads(request.data.decode("utf-8"))["goal"], "test gorevi")
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertEqual(headers["authorization"], "Bearer test-key")

    def test_auto_mode_falls_back_to_module(self) -> None:
        os.environ["MARKXXXV_MODE"] = "auto"
        os.environ["MARKXXXV_BASE_URL"] = "http://127.0.0.1:9999"
        module = importlib.reload(markxxxv_skill)

        with patch.object(module, "_run_http_mode", side_effect=RuntimeError("offline")):
            with patch.object(module, "_run_module_mode", return_value="Yerel sonuc"):
                result = module.handle_markxxxv("bir gorev", "7")

        self.assertEqual(result, "Yerel sonuc")

    def test_module_mode_import_failure_falls_back_to_http(self) -> None:
        os.environ["MARKXXXV_MODE"] = "module"
        os.environ["MARKXXXV_BASE_URL"] = "http://127.0.0.1:9999"
        module = importlib.reload(markxxxv_skill)

        with patch.object(module, "_run_module_mode", side_effect=ImportError("missing dep")):
            with patch.object(module, "_run_http_mode", return_value="HTTP sonuc") as http_mode:
                result = module.handle_markxxxv("bir gorev", "8")

        self.assertEqual(result, "HTTP sonuc")
        http_mode.assert_called_once()

    def test_module_mode_reports_missing_repo(self) -> None:
        os.environ["MARKXXXV_MODE"] = "module"
        os.environ["MARKXXXV_REPO_PATH"] = "external-repos/missing-mark"
        module = importlib.reload(markxxxv_skill)

        result = module.handle_markxxxv("test")

        self.assertIn("Mark-XXXV kurulumu eksik", result)


if __name__ == "__main__":
    unittest.main()
