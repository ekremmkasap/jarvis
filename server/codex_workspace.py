from __future__ import annotations

import subprocess
from pathlib import Path


class WorkspaceManager:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    BASE = ROOT_DIR / "worktrees"
    SLOTS = ("atlas", "forge", "nexus", "shield", "spark")

    def _slot_name(self, slot: str) -> str:
        normalized = str(slot or "").strip().lower()
        return normalized or "unknown"

    def get_path(self, slot: str) -> Path:
        return self.BASE / self._slot_name(slot)

    def get_branch(self, slot: str) -> str:
        return f"codex/{self._slot_name(slot)}"

    def exists(self, slot: str) -> bool:
        return self.get_path(slot).exists()

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.ROOT_DIR,
            check=check,
            text=True,
            capture_output=True,
        )

    def _branch_exists(self, branch: str) -> bool:
        result = self._run_git("show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
        return result.returncode == 0

    def init_command(self, slot: str) -> str:
        path = self.get_path(slot)
        branch = self.get_branch(slot)
        return f'git worktree add "{path}" "{branch}"'

    def clean_command(self, slot: str) -> str:
        path = self.get_path(slot)
        return f'git -C "{path}" reset --hard HEAD; if ($?) {{ git -C "{path}" clean -fd }}'

    def ensure(self, slot: str) -> Path:
        slot_name = self._slot_name(slot)
        path = self.get_path(slot_name)
        branch = self.get_branch(slot_name)
        if path.exists():
            return path

        self.BASE.mkdir(parents=True, exist_ok=True)
        if self._branch_exists(branch):
            self._run_git("worktree", "add", str(path), branch)
        else:
            self._run_git("worktree", "add", "-b", branch, str(path), "HEAD")
        return path

    def cleanup(self, slot: str, job_id: str) -> bool:
        slot_name = self._slot_name(slot)
        branch = f"{self.get_branch(slot_name)}/job/{str(job_id or '').strip()}"
        if not str(job_id or "").strip():
            return False
        if not self._branch_exists(branch):
            return False
        result = self._run_git("branch", "-D", branch, check=False)
        return result.returncode == 0

    def list_paths(self) -> dict[str, str]:
        return {slot: str(self.get_path(slot)) for slot in self.SLOTS if self.get_path(slot).exists()}

    def status(self) -> dict[str, bool]:
        return {slot: self.exists(slot) for slot in self.SLOTS}


def ensure_worktree(slot_id: str) -> Path:
    return WorkspaceManager().ensure(slot_id)


def get_worktree_path(slot_id: str) -> str:
    return str(WorkspaceManager().get_path(slot_id))


def cleanup_worktree(slot_id: str, job_id: str) -> bool:
    return WorkspaceManager().cleanup(slot_id, job_id)


def list_worktrees() -> dict[str, str]:
    return WorkspaceManager().list_paths()
