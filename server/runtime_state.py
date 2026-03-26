from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


class JsonMemoryStore:
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        try:
            with self.filepath.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {"sessions": {}, "history": [], "stats": {"total_queries": 0}}

    def _save(self) -> None:
        with self.filepath.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    def add_message(self, chat_id: int, role: str, content: str, model: str | None = None) -> None:
        key = str(chat_id)
        if key not in self.data["sessions"]:
            self.data["sessions"][key] = []
        self.data["sessions"][key].append(
            {
                "role": role,
                "content": content,
                "model": model,
                "time": datetime.now().isoformat(),
            }
        )
        self.data["sessions"][key] = self.data["sessions"][key][-20:]
        self.data["stats"]["total_queries"] += 1
        self._save()

    def get_history(self, chat_id: int, last_n: int = 10) -> list[dict[str, str]]:
        key = str(chat_id)
        msgs = self.data["sessions"].get(key, [])
        return [{"role": item["role"], "content": item["content"]} for item in msgs[-last_n:]]

    def clear(self, chat_id: int) -> None:
        self.data["sessions"][str(chat_id)] = []
        self._save()


@dataclass
class RuntimeState:
    memory_file: str | Path
    active_agents: dict[str, dict] = field(default_factory=dict)
    content_factory_sessions: dict[str, bool] = field(default_factory=dict)
    agent_os_runtime: object | None = None
    last_route_trace: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.memory = JsonMemoryStore(self.memory_file)
