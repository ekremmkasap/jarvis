from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from server.runtime_config import load_runtime_config, validate_runtime_config


class RuntimeConfigTests(unittest.TestCase):
    def test_bridge_can_run_web_only_without_telegram(self) -> None:
        with tempfile.TemporaryDirectory() as root_tmp, tempfile.TemporaryDirectory() as base_tmp:
            root_dir = Path(root_tmp)
            base_dir = Path(base_tmp)
            env_path = root_dir / ".env"
            env_path.write_text("JARVIS_ENABLE_TELEGRAM=0\nJARVIS_WEB_PORT=8099\n", encoding="utf-8")

            original = os.environ.copy()
            try:
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
                os.environ.pop("TELEGRAM_CHAT_ID", None)
                config = load_runtime_config(root_dir, base_dir)
                validate_runtime_config(config)
                self.assertEqual(config.web_port, 8099)
                self.assertFalse(config.enable_telegram)
            finally:
                os.environ.clear()
                os.environ.update(original)

    def test_telegram_mode_requires_token_and_chat_id(self) -> None:
        with tempfile.TemporaryDirectory() as root_tmp, tempfile.TemporaryDirectory() as base_tmp:
            root_dir = Path(root_tmp)
            base_dir = Path(base_tmp)
            (root_dir / ".env").write_text("JARVIS_ENABLE_TELEGRAM=1\n", encoding="utf-8")

            original = os.environ.copy()
            try:
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
                os.environ.pop("TELEGRAM_CHAT_ID", None)
                config = load_runtime_config(root_dir, base_dir)
                with self.assertRaises(RuntimeError):
                    validate_runtime_config(config)
            finally:
                os.environ.clear()
                os.environ.update(original)


if __name__ == "__main__":
    unittest.main()
