from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.agents.canonical import CANONICAL_AGENTS
from server.agents.canonical.developer import DeveloperAgent
from server.agents.canonical.planner import PlannerAgent
from server.agents.canonical.repo_analyst import RepoAnalystAgent


class FakeRouter:
    def __init__(self, response: str = "", ok: bool = False) -> None:
        self.response = response
        self.ok = ok

    def chat(self, **_: object) -> tuple[str, dict[str, object]]:
        return self.response, {
            "ok": self.ok,
            "selected_candidate": "fake/model",
            "fallback_used": False,
            "attempts": [],
        }


class CanonicalBatch1Tests(unittest.TestCase):
    def test_registry_contains_batch1_agents(self) -> None:
        self.assertTrue({"planner", "repo_analyst", "developer"}.issubset(set(CANONICAL_AGENTS.keys())))

    def test_planner_falls_back_when_router_has_no_response(self) -> None:
        agent = PlannerAgent(router=FakeRouter())
        result = asyncio.run(agent.run("Jarvis icin yeni entegrasyon planla", {}))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["agent_id"], "planner")
        self.assertGreaterEqual(len(result["steps"]), 3)
        self.assertIn("developer", result["agents_needed"])

    def test_planner_parses_json_response(self) -> None:
        router = FakeRouter(
            response=json.dumps(
                {
                    "goals": ["Goal A"],
                    "agents_needed": ["planner", "developer"],
                    "steps": [{"title": "T1", "owner": "planner", "description": "D1"}],
                    "estimated_complexity": "medium",
                    "priority": "high",
                    "risk_score": 7,
                }
            ),
            ok=True,
        )
        agent = PlannerAgent(router=router)
        result = asyncio.run(agent.run("Plan", {}))

        self.assertEqual(result["goals"], ["Goal A"])
        self.assertEqual(result["priority"], "high")
        self.assertEqual(result["risk_score"], 7)

    def test_repo_analyst_builds_report_and_summary(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root_dir = Path(temp_dir)
            agent = RepoAnalystAgent(router=FakeRouter(), root_dir=root_dir)
            repo_path = root_dir

            with patch.object(
                RepoAnalystAgent,
                "_run_command",
                side_effect=[
                    "abc123 feat: add canonical agents\nfff999 fix: bridge health",
                    "server/bridge.py | 12 +++++++---\nserver/model_router.py | 4 ++--",
                    "tests/test_model_router.py | 8 +++++---",
                ],
            ):
                result = asyncio.run(agent.run("analyze repo", {"repo_path": str(repo_path)}))

            self.assertEqual(result["status"], "ok")
            self.assertIn("server/bridge.py", result["changed_files"])
            self.assertTrue(Path(result["report_path"]).exists())
            self.assertGreaterEqual(result["health_score"], 40)

    def test_developer_writes_only_explicit_repo_target(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root_dir = Path(temp_dir)
            target = root_dir / "tmp" / "generated.py"
            agent = DeveloperAgent(router=FakeRouter(), root_dir=root_dir)

            result = asyncio.run(
                agent.run(
                    "write file",
                    {
                        "target_file": "tmp/generated.py",
                        "change_description": "Create a generated module",
                        "proposed_content": "print('ok')\n",
                    },
                )
            )

            self.assertEqual(result["status"], "ok")
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "print('ok')\n")

    def test_developer_rejects_target_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root_dir = Path(temp_dir)
            outside_target = Path(tempfile.gettempdir()) / "developer_outside.txt"
            agent = DeveloperAgent(router=FakeRouter(), root_dir=root_dir)

            result = asyncio.run(
                agent.run(
                    "write file",
                    {
                        "target_file": str(outside_target),
                        "change_description": "Should fail",
                        "proposed_content": "denied\n",
                    },
                )
            )

            self.assertEqual(result["status"], "error")
            self.assertIn("outside repo root", result["error"])

    def test_base_log_redacts_sensitive_context_fields(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root_dir = Path(temp_dir)
            log_path = root_dir / "server" / "logs" / "canonical_agents.jsonl"
            agent = PlannerAgent(router=FakeRouter(), root_dir=root_dir, log_path=log_path)

            asyncio.run(agent.run("planla", {"api_key": "secret-value", "safe": "yes"}))

            payload = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[0])
            self.assertEqual(payload["context"]["api_key"], "[REDACTED]")
            self.assertEqual(payload["context"]["safe"], "yes")


if __name__ == "__main__":
    unittest.main()
