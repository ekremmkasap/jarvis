from __future__ import annotations

from pathlib import Path


class WorkspaceManager:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    BASE = ROOT_DIR / ".worktrees"
    SLOTS = ("atlas", "forge", "nexus", "shield", "spark")

    def _slot_name(self, slot: str) -> str:
        normalized = str(slot or "").strip().lower()
        return normalized or "unknown"

    def get_path(self, slot: str) -> Path:
        return self.BASE / self._slot_name(slot)

    def exists(self, slot: str) -> bool:
        return self.get_path(slot).exists()

    def init_command(self, slot: str) -> str:
        path = self.get_path(slot)
        return f'git worktree add "{path}" origin/main'

    def clean_command(self, slot: str) -> str:
        path = self.get_path(slot)
        return f'git -C "{path}" reset --hard HEAD; if ($?) {{ git -C "{path}" clean -fd }}'

    def status(self) -> dict[str, bool]:
        return {slot: self.exists(slot) for slot in self.SLOTS}
