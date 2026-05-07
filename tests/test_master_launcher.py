from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from master_launcher import MasterLauncher


class MasterLauncherTests(unittest.TestCase):
    def test_voice_process_defaults_to_mark_xxxv_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as mark_tmp:
            with patch.dict(os.environ, {"JARVIS_VOICE_RUNTIME": "mark_xxxv"}, clear=False):
                launcher = MasterLauncher()
                launcher.mark_xxxv_dir = Path(mark_tmp)

                label, command, env, cwd = launcher._voice_process_spec()

        self.assertEqual(label, "Mark-XXXV live runtime")
        self.assertEqual(command[-1], "main.py")
        self.assertEqual(env["JARVIS_RUNTIME_UI"], "bridge")
        self.assertEqual(cwd, Path(mark_tmp))

    def test_cleanup_at_exit_is_noop_when_no_processes_started(self) -> None:
        launcher = MasterLauncher()
        with patch.object(launcher, "shutdown", wraps=launcher.shutdown) as shutdown_spy:
            launcher._cleanup_at_exit()

        shutdown_spy.assert_not_called()
        self.assertFalse(launcher._shutdown_started)

    def test_cleanup_at_exit_stops_child_processes_without_system_exit(self) -> None:
        launcher = MasterLauncher()
        fake_proc = Mock()
        fake_proc.pid = 4242
        fake_proc.poll.return_value = None
        launcher.processes["VOICE"] = fake_proc

        with patch.object(launcher, "_terminate_process", return_value=True) as terminate_mock:
            launcher._cleanup_at_exit()

        terminate_mock.assert_called_once_with(fake_proc)
        self.assertTrue(launcher._shutdown_started)

    def test_launcher_sets_default_obsidian_vault_when_missing(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OBSIDIAN_VAULT_PATH": "",
                "JARVIS_OBSIDIAN_AUTO_OPEN": "0",
            },
            clear=False,
        ):
            launcher = MasterLauncher()

        self.assertEqual(launcher.obsidian_vault_dir, launcher.root / "wiki")
        self.assertEqual(os.environ.get("OBSIDIAN_VAULT_PATH"), str(launcher.root / "wiki"))


if __name__ == "__main__":
    unittest.main()
