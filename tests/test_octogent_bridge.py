from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server import octogent_bridge


class OctogentBridgeTests(unittest.TestCase):
    def test_descriptor_is_owned_by_sabrican(self) -> None:
        descriptor = octogent_bridge.describe_octogent_helper_runtime()

        self.assertEqual(descriptor["owner_persona"], "sabrican")
        self.assertEqual(descriptor["mode"], "helper_only")
        self.assertFalse(descriptor["canonical_runtime"])
        self.assertIn("tentacle_orchestrator", descriptor["sub_agents"])
        self.assertIn("tentacle_control", descriptor["skill_surfaces"])

    def test_health_snapshot_reports_optional_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "octogent"
            repo_dir.mkdir(parents=True, exist_ok=True)
            scaffold_dir = Path(tmp) / ".octogent"
            scaffold_dir.mkdir(parents=True, exist_ok=True)

            with patch.object(octogent_bridge, "OCTOGENT_REPO_DIR", repo_dir):
                with patch.object(octogent_bridge, "ROOT_DIR", Path(tmp)):
                    with patch.object(
                        octogent_bridge,
                        "_resolve_octogent_command",
                        return_value="C:\\tools\\octogent.cmd",
                    ):
                        with patch.object(
                            octogent_bridge,
                            "_resolve_pnpm_command",
                            return_value="C:\\tools\\pnpm.cmd",
                        ):
                            with patch.object(
                                octogent_bridge,
                                "_node_snapshot",
                                return_value={
                                    "ok": True,
                                    "detail": "node-supported",
                                    "version": "v24.13.0",
                                    "path": "C:\\Program Files\\nodejs\\node.exe",
                                },
                            ):
                                with patch.object(
                                    octogent_bridge,
                                    "_probe_octogent_api",
                                    return_value={
                                        "ok": True,
                                        "detail": "http-200",
                                        "status_code": 200,
                                        "url": "http://127.0.0.1:8787/api/setup",
                                    },
                                ):
                                    snapshot = (
                                        octogent_bridge.build_octogent_health_snapshot()
                                    )

        self.assertEqual(snapshot["status"], "healthy")
        self.assertEqual(snapshot["command_source"], "global")
        self.assertTrue(snapshot["capabilities"]["repo_clone"]["ok"])
        self.assertTrue(snapshot["capabilities"]["cli_ready"]["ok"])
        self.assertTrue(snapshot["capabilities"]["api_ready"]["ok"])
        self.assertEqual(snapshot["node"]["version"], "v24.13.0")

    def test_repo_wrapper_is_not_treated_as_healthy_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root_dir = Path(tmp)
            (root_dir / "octogent.cmd").write_text(
                "@echo off\r\necho wrapper\r\n",
                encoding="utf-8",
            )
            repo_dir = root_dir / "external-repos" / "octogent"
            repo_dir.mkdir(parents=True, exist_ok=True)

            with patch.object(octogent_bridge, "ROOT_DIR", root_dir):
                with patch.object(octogent_bridge, "OCTOGENT_REPO_DIR", repo_dir):
                    with patch.object(
                        octogent_bridge,
                        "_resolve_global_octogent_command",
                        return_value="",
                    ):
                        with patch.object(
                            octogent_bridge,
                            "_resolve_pnpm_command",
                            return_value="",
                        ):
                            with patch.object(
                                octogent_bridge,
                                "_node_snapshot",
                                return_value={
                                    "ok": False,
                                    "detail": "node-missing",
                                    "version": "",
                                },
                            ):
                                with patch.object(
                                    octogent_bridge,
                                    "_probe_octogent_api",
                                    return_value={
                                        "ok": False,
                                        "detail": "api-unreachable",
                                        "status_code": None,
                                        "url": "",
                                    },
                                ):
                                    snapshot = (
                                        octogent_bridge.build_octogent_health_snapshot()
                                    )

        self.assertEqual(snapshot["command_source"], "repo-wrapper")
        self.assertFalse(snapshot["capabilities"]["cli_ready"]["ok"])
        self.assertEqual(
            snapshot["capabilities"]["cli_ready"]["detail"],
            "command-missing",
        )
