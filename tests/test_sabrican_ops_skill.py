from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.skills import sabrican_ops_skill


class SabricanOpsSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_path = self.temp_dir / "sabrican_ops.jsonl"
        self.log_patch = patch.object(sabrican_ops_skill, "OPS_LOG_PATH", self.log_path)
        self.log_patch.start()

    def tearDown(self) -> None:
        self.log_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_service_health_unknown_service(self) -> None:
        result = sabrican_ops_skill.check_service_health("bilinmeyen")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["error"], "unknown_service")
        self.assertTrue(self.log_path.exists())

    def test_get_system_status_returns_expected_shape(self) -> None:
        fake_services = [
            {"ok": True, "service": "bridge", "status": "up", "latency_ms": 10},
            {"ok": True, "service": "ollama", "status": "up", "latency_ms": 20},
            {"ok": False, "service": "hologram", "status": "down", "latency_ms": None},
        ]
        with (
            patch.object(sabrican_ops_skill, "check_service_health", side_effect=fake_services),
            patch.object(sabrican_ops_skill, "_read_system_metrics", return_value=(12.5, 48.0, 73.5)),
        ):
            result = sabrican_ops_skill.get_system_status()

        self.assertEqual(len(result["services"]), 3)
        self.assertEqual(result["cpu_pct"], 12.5)
        self.assertEqual(result["ram_pct"], 48.0)
        self.assertEqual(result["disk_pct"], 73.5)

    def test_restart_service_rejects_non_whitelisted_target(self) -> None:
        result = sabrican_ops_skill.restart_service("hologram")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "not_allowed")
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any("restart_service" in line for line in lines))

    def test_docker_status_gracefully_handles_missing_docker(self) -> None:
        with patch.object(
            sabrican_ops_skill.subprocess,
            "run",
            side_effect=FileNotFoundError("docker not found"),
        ):
            result = sabrican_ops_skill.docker_status()

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "docker_not_installed")
        self.assertEqual(result["containers"], [])


if __name__ == "__main__":
    unittest.main()
