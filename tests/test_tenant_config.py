from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path


class TenantConfigShapeTests(unittest.TestCase):
    def test_template_uses_env_fields(self) -> None:
        template_path = Path(__file__).resolve().parents[1] / "server" / "tenants" / "_template" / "config.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        self.assertIn("telegram_token_env", template)
        self.assertIn("authorized_chat_id_env", template)


if __name__ == "__main__":
    unittest.main()
