from __future__ import annotations

import asyncio
import unittest

from server.agents.canonical import CANONICAL_AGENTS
from server.agents.canonical.docs_agent import DocsAgent
from server.agents.canonical.release_agent import ReleaseAgent
from server.agents.canonical.voice_narrator import VoiceNarratorAgent


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


class CanonicalBatch3Tests(unittest.TestCase):
    def test_registry_contains_batch3_agents(self) -> None:
        required = {"planner", "repo_analyst", "developer", "reviewer", "debug", "release", "docs", "voice_narrator"}
        self.assertTrue(required.issubset(set(CANONICAL_AGENTS.keys())))

    def test_release_agent_semver_fallback(self) -> None:
        agent = ReleaseAgent(router=FakeRouter())
        git_log = "\n".join(
            [
                "abc123 feat: add bridge routing",
                "def456 fix: tighten error handling",
                "999999 chore: refresh docs",
            ]
        )
        result = asyncio.run(
            agent.run(
                "prepare release",
                {"git_log": git_log, "current_version": "1.2.3"},
            )
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["suggested_version"], "1.3.0")
        self.assertTrue(result["changelog_entries"])
        self.assertEqual(result["breaking_changes"], [])

    def test_docs_agent_fallback_generates_markdown(self) -> None:
        agent = DocsAgent(router=FakeRouter())
        result = asyncio.run(
            agent.run(
                "update README with bridge command",
                {
                    "doc_type": "readme",
                    "description": "Document the bridge command usage for operators.",
                    "command": "python server/bridge.py --web-only",
                },
            )
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["doc_type"], "readme")
        self.assertIn("## Overview", result["content"])
        self.assertIn("python server/bridge.py --web-only", result["content"])
        self.assertEqual(result["target_file_suggestion"], "README.md")

    def test_voice_narrator_fallback_is_short_and_clean(self) -> None:
        agent = VoiceNarratorAgent(router=FakeRouter())
        raw = "```json {\"status\":\"ok\"} ``` Build bitti, http://example.com/log detaylari var, reviewer 2 issue buldu, debug sonucu hazir."
        result = asyncio.run(agent.run(raw, {}))

        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(result["compressed_length"], 200)
        self.assertNotIn("http", result["tts_text"].lower())
        self.assertNotIn("```", result["tts_text"])
        self.assertNotIn("`", result["tts_text"])


if __name__ == "__main__":
    unittest.main()
