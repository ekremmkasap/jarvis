from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from .base import CanonicalAgent
from .constants import CANONICAL_AGENT_IDS


class MissionControlAgent(CanonicalAgent):
    agent_id = "mission_control"
    name = "MissionControlAgent"
    role = "Canonical agent health monitor"
    model_chain = "reasoning"
    model_preference = "groq/llama-3.3-70b-versatile"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC)
        entries = self._load_entries()
        last_activity = self._last_activity(entries)
        consecutive_errors = self._consecutive_errors(entries)

        agents: dict[str, str] = {}
        stuck_tasks: list[dict[str, str]] = []
        recommendations: list[str] = []

        stale_threshold = now - timedelta(minutes=10)
        for agent_id in CANONICAL_AGENT_IDS:
            timestamp = last_activity.get(agent_id)
            if consecutive_errors.get(agent_id, 0) >= 3:
                agents[agent_id] = "critical"
                recommendations.append(f"{agent_id}: inspect repeated failures and recent payloads.")
                continue
            if not timestamp:
                agents[agent_id] = "missing"
                recommendations.append(f"{agent_id}: no activity recorded yet.")
                continue

            parsed = self._parse_timestamp(timestamp)
            if parsed and parsed < stale_threshold:
                agents[agent_id] = "stuck"
                stuck_tasks.append({"agent_id": agent_id, "last_activity": timestamp})
                recommendations.append(f"{agent_id}: no activity for more than 10 minutes.")
            else:
                latest_status = self._latest_status(entries, agent_id)
                agents[agent_id] = "ok" if latest_status == "ok" else "degraded"

        overall_health = self._overall_health(agents)
        if not recommendations:
            recommendations.append("Canonical agents look healthy based on the latest activity log.")

        return {
            "agents": agents,
            "stuck_tasks": stuck_tasks,
            "last_activity_per_agent": last_activity,
            "overall_health": overall_health,
            "recommendations": recommendations[:8],
        }

    def _load_entries(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for line in self.log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                entries.append(item)
        return entries

    def _last_activity(self, entries: list[dict[str, Any]]) -> dict[str, str]:
        last_seen: dict[str, str] = {}
        for entry in entries:
            agent_id = str(entry.get("agent_id") or "").strip()
            timestamp = str(entry.get("timestamp") or "").strip()
            if agent_id and timestamp:
                last_seen[agent_id] = timestamp
        return last_seen

    def _latest_status(self, entries: list[dict[str, Any]], agent_id: str) -> str:
        for entry in reversed(entries):
            if str(entry.get("agent_id") or "").strip() == agent_id:
                return str(entry.get("status") or "error").strip().lower() or "error"
        return "error"

    def _consecutive_errors(self, entries: list[dict[str, Any]]) -> dict[str, int]:
        counts = {agent_id: 0 for agent_id in CANONICAL_AGENT_IDS}
        for agent_id in CANONICAL_AGENT_IDS:
            for entry in reversed(entries):
                if str(entry.get("agent_id") or "").strip() != agent_id:
                    continue
                status = str(entry.get("status") or "").strip().lower()
                if status == "error":
                    counts[agent_id] += 1
                elif status == "ok":
                    break
        return counts

    def _parse_timestamp(self, value: str) -> datetime | None:
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _overall_health(self, agents: dict[str, str]) -> str:
        states = set(agents.values())
        if "critical" in states:
            return "critical"
        if "stuck" in states or "degraded" in states or "missing" in states:
            return "degraded"
        return "ok"
