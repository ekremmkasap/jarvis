from __future__ import annotations

import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from server.services import persona_swarm


def test_allowed_executors_for_persona_filters_invalid_ids():
    allowed = persona_swarm.allowed_executors_for_persona(
        {"sub_agents": ["file_reader", "invalid", "summarizer", "file_reader"]}
    )

    assert allowed == ["file_reader", "summarizer"]


def test_run_plan_executes_parallel_group_and_marks_done():
    seen = []

    def executor(payload, context):
        time.sleep(0.01)
        seen.append(context["step_id"])
        return {"ok": True, "output": payload.get("label")}

    plan = persona_swarm.build_plan(
        "seda",
        "repoyu analiz et",
        [
            {
                "id": "step_a",
                "type": "file_reader",
                "title": "Bridge oku",
                "payload": {"label": "bridge"},
                "parallel_group": "analysis",
            },
            {
                "id": "step_b",
                "type": "code_analyzer",
                "title": "Persona manager tara",
                "payload": {"label": "persona"},
                "parallel_group": "analysis",
            },
            {
                "id": "step_c",
                "type": "summarizer",
                "title": "Ozetle",
                "payload": {"label": "summary"},
            },
        ],
    )

    result = persona_swarm.run_plan(
        plan,
        executors={
            "file_reader": executor,
            "code_analyzer": executor,
            "summarizer": executor,
        },
    )

    assert result["status"] == "done"
    assert result["summary"] == {"completed": 3, "failed": 0, "total": 3}
    assert set(seen) == {"step_a", "step_b", "step_c"}


def test_run_plan_is_fail_soft_when_executor_is_missing():
    plan = persona_swarm.build_plan(
        "mert",
        "kaynaklari tara",
        [
            {"id": "step_1", "type": "web_search", "title": "Web ara", "payload": {}},
            {
                "id": "step_2",
                "type": "summarizer",
                "title": "Ozetle",
                "payload": {"label": "ok"},
            },
        ],
    )

    result = persona_swarm.run_plan(
        plan,
        executors={"summarizer": lambda payload, context: {"ok": True, "output": "ok"}},
    )

    assert result["status"] == "failed"
    assert result["steps"][0]["status"] == "failed"
    assert result["steps"][1]["status"] == "done"
