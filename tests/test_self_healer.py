from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

from server.agents import self_healer


class SelfHealerTests(unittest.TestCase):
    @patch("server.agents.self_healer._is_windows", return_value=True)
    def test_windows_missing_binary_fix_uses_where_and_py(self, _mock_windows) -> None:
        fixes = self_healer.generate_fix("foo --version", "missing_binary")

        self.assertTrue(fixes[0].startswith("where foo"))
        self.assertIn("py -m pip install foo", fixes[1])

    @patch("server.agents.self_healer._is_windows", return_value=False)
    def test_posix_permission_fix_uses_chmod(self, _mock_windows) -> None:
        fixes = self_healer.generate_fix("./tool.sh", "permission")

        self.assertTrue(fixes[0].startswith("chmod +x"))
        self.assertIn("ls -la", fixes[1])

    @patch("server.agents.self_healer._is_windows", return_value=True)
    def test_windows_port_fix_does_not_use_head(self, _mock_windows) -> None:
        fix = self_healer._detect_port_fix("address already in use: :8091")

        self.assertIn("netstat -ano", fix)
        self.assertNotIn("head -5", fix)


if __name__ == "__main__":
    unittest.main()
