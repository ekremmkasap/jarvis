from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server.codex_workspace as codex_workspace


class CodexWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init"], cwd=self.temp_root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "codex@example.com"], cwd=self.temp_root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Codex"], cwd=self.temp_root, check=True, capture_output=True, text=True)
        (self.temp_root / "README.md").write_text("workspace test\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.temp_root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.temp_root, check=True, capture_output=True, text=True)

        self.patches = [
            patch.object(codex_workspace.WorkspaceManager, "ROOT_DIR", self.temp_root),
            patch.object(codex_workspace.WorkspaceManager, "BASE", self.temp_root / "worktrees"),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_ensure_worktree_creates_slot_path(self) -> None:
        path = codex_workspace.ensure_worktree("forge")

        self.assertTrue(path.exists())
        self.assertTrue((self.temp_root / "worktrees" / "forge").exists())

    def test_get_worktree_path_uses_canonical_directory(self) -> None:
        path = codex_workspace.get_worktree_path("spark")

        self.assertTrue(path.endswith("worktrees\\spark") or path.endswith("worktrees/spark"))

    def test_list_worktrees_returns_existing_slot_paths(self) -> None:
        codex_workspace.ensure_worktree("atlas")
        codex_workspace.ensure_worktree("shield")

        worktrees = codex_workspace.list_worktrees()

        self.assertIn("atlas", worktrees)
        self.assertIn("shield", worktrees)

    def test_cleanup_worktree_returns_false_for_missing_job_branch(self) -> None:
        codex_workspace.ensure_worktree("nexus")

        self.assertFalse(codex_workspace.cleanup_worktree("nexus", "job-123"))


if __name__ == "__main__":
    unittest.main()
