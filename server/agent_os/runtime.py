import json
from pathlib import Path

from team_orchestrator import TeamOrchestrator


class AgentOSRuntime:
    def __init__(self, llm_call, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.manifest_path = self.base_dir / "config" / "department_manifest.json"
        self.workspace_dir = self.base_dir / "agent_workspace" / "departments"
        self.manifest = self._load_manifest()
        self.team = TeamOrchestrator(llm_call)

    def run(self, goal: str, chat_id: str = "0") -> dict:
        route = self._classify_goal(goal)
        departments = self._select_departments(goal, route)
        context_packet = self._build_context_packet(departments)
        result = self.team.run(
            goal,
            chat_id=chat_id,
            inputs={
                "route": route,
                "departments": departments,
                "context_packet": context_packet,
            },
        )
        result["route"] = route
        result["departments"] = departments
        result["context_packet"] = context_packet
        result["summary"] = self._build_summary(result)
        return result

    def _load_manifest(self) -> dict:
        with open(self.manifest_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _classify_goal(self, goal: str) -> str:
        lower = goal.lower()
        for route, keywords in self.manifest.get("route_keywords", {}).items():
            if any(keyword in lower for keyword in keywords):
                return route
        return self.manifest.get("default_route", "operations")

    def _select_departments(self, goal: str, route: str) -> list[dict]:
        lower = goal.lower()
        selected_ids = list(self.manifest.get("route_map", {}).get(route, []))
        for department in self.manifest.get("departments", []):
            if any(keyword in lower for keyword in department.get("keywords", [])) and department["id"] not in selected_ids:
                selected_ids.append(department["id"])
        if self.manifest.get("default_department") not in selected_ids:
            selected_ids.insert(0, self.manifest.get("default_department", "assistant"))

        selected = []
        for department_id in selected_ids:
            record = next((item for item in self.manifest.get("departments", []) if item["id"] == department_id), None)
            if record:
                selected.append(record)
        return selected[: self.manifest.get("max_departments", 4)]

    def _build_context_packet(self, departments: list[dict]) -> str:
        packets = []
        for department in departments:
            dept_dir = self.workspace_dir / department["id"]
            agent_path = dept_dir / "AGENT.md"
            memory_path = dept_dir / "MEMORY.md"
            skills_dir = dept_dir / "skills"
            skill_files = sorted(item.name for item in skills_dir.glob("*.md")) if skills_dir.exists() else []
            agent_text = agent_path.read_text(encoding="utf-8") if agent_path.exists() else ""
            memory_text = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
            packets.append(
                "\n".join(
                    [
                        f"[DEPARTMENT] {department['name']} ({department['id']})",
                        f"Mission: {department.get('mission', '')}",
                        f"Tools: {', '.join(department.get('tools', [])) or 'none'}",
                        f"Skills: {', '.join(skill_files) or 'none'}",
                        f"Agent Context: {agent_text[:700].strip()}",
                        f"Memory: {memory_text[:500].strip()}",
                    ]
                ).strip()
            )
        return "\n\n".join(packet for packet in packets if packet.strip())

    def _build_summary(self, result: dict) -> str:
        departments = ", ".join(item["id"] for item in result.get("departments", [])) or "assistant"
        synthesis = result.get("synthesis") or result.get("reason") or "No synthesis produced."
        return (
            f"Agent OS Route: {result.get('route', 'operations')}\n"
            f"Departments: {departments}\n"
            f"Task: {result.get('task_id', '-') }\n"
            f"Status: {result.get('status', 'unknown')}\n\n"
            f"{synthesis}"
        )
