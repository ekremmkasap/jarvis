from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from server.agents.canonical import CANONICAL_AGENTS
from server.agents.canonical.mission_control import MissionControlAgent
from server.agents.canonical.runtime import format_canonical_result, handle_agent_request, match_canonical_agent


class CanonicalBatch4Tests(unittest.TestCase):
    def test_registry_contains_all_canonical_agents(self) -> None:
        self.assertEqual(
            set(CANONICAL_AGENTS.keys()),
            {
                "planner",
                "repo_analyst",
                "developer",
                "reviewer",
                "debug",
                "release",
                "docs",
                "voice_narrator",
                "mission_control",
            },
        )

    def test_mission_control_detects_stuck_and_critical_agents(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root_dir = Path(temp_dir)
            log_path = root_dir / "server" / "logs" / "canonical_agents.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now(UTC)
            entries = [
                {
                    "timestamp": (now - timedelta(minutes=15)).isoformat(),
                    "agent_id": "planner",
                    "status": "ok",
                },
                {
                    "timestamp": (now - timedelta(minutes=1)).isoformat(),
                    "agent_id": "debug",
                    "status": "error",
                },
                {
                    "timestamp": (now - timedelta(minutes=2)).isoformat(),
                    "agent_id": "debug",
                    "status": "error",
                },
                {
                    "timestamp": (now - timedelta(minutes=3)).isoformat(),
                    "agent_id": "debug",
                    "status": "error",
                },
                {
                    "timestamp": now.isoformat(),
                    "agent_id": "release",
                    "status": "ok",
                },
            ]
            log_path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")
            agent = MissionControlAgent(root_dir=root_dir, log_path=log_path)
            result = asyncio.run(agent.run("system health check", {}))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["overall_health"], "critical")
        self.assertEqual(result["agents"]["planner"], "stuck")
        self.assertEqual(result["agents"]["debug"], "critical")
        self.assertTrue(result["stuck_tasks"])

    def test_runtime_keyword_match_and_request_handler(self) -> None:
        self.assertEqual(match_canonical_agent("repo analiz yap"), "repo_analyst")
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            target = Path(temp_dir) / "generated.txt"
            relative = target.relative_to(Path.cwd())
            payload, status_code = handle_agent_request(
                {
                    "agent": "developer",
                    "task": "write generated text",
                    "context": {
                        "target_file": str(relative).replace("\\", "/"),
                        "change_description": "Create generated text",
                        "proposed_content": "ok\n",
                    },
                }
            )
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("files_changed", payload)

    def test_runtime_formats_mission_control_summary(self) -> None:
        formatted = format_canonical_result(
            "mission_control",
            {"status": "ok", "overall_health": "degraded", "stuck_tasks": [{"agent_id": "planner"}]},
        )
        self.assertIn("mission_control", formatted)
        self.assertIn("stuck=1", formatted)


if __name__ == "__main__":
    unittest.main()
