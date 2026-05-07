from __future__ import annotations

import importlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

import skills.memory_skill as memory_skill


class MemorySkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "jarvis_memory.db"
        self.original_env = os.environ.get("JARVIS_MEMORY_DB")
        os.environ["JARVIS_MEMORY_DB"] = str(self.db_path)
        self.module = importlib.reload(memory_skill)

    def tearDown(self) -> None:
        if self.original_env is None:
            os.environ.pop("JARVIS_MEMORY_DB", None)
        else:
            os.environ["JARVIS_MEMORY_DB"] = self.original_env
        importlib.reload(memory_skill)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_env_override_controls_db_path(self) -> None:
        self.assertEqual(self.module.get_db_path(), self.db_path)
        self.module.init_db()
        self.assertTrue(self.db_path.exists())

    def test_messages_round_trip_in_sqlite(self) -> None:
        self.module.save_message("u-1", "user", "merhaba")
        self.module.save_message("u-1", "assistant", "selam")

        history = self.module.get_history("u-1", limit=2)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")


if __name__ == "__main__":
    unittest.main()
