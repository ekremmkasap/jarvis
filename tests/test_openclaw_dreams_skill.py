from __future__ import annotations

import json

from server import persona_manager
from server import bridge
from server.security.policy_gate import PolicyDecision
from server.skills import openclaw_dreams_skill as skill


SAMPLE_REM_REPORT = """# REM Sleep

### Reflections
- Theme: `gateway` kept surfacing across 12 memories.
  - confidence: 1.00
  - evidence: memory/.dreams/session-corpus/2026-04-23.txt:1-3
  - note: reflection
- Theme: `heartbeat.md` kept surfacing across 8 memories.
  - confidence: 0.90
  - evidence: memory/.dreams/session-corpus/2026-04-23.txt:4-6
  - note: reflection

### Possible Lasting Truths
- Jarvis bridge health checks should stay visible to the operator.
"""


def _allowed_decision(action: str) -> PolicyDecision:
    return PolicyDecision(
        allowed=True,
        status="allowed",
        risk="low",
        reason="operator-action-allowed",
        action=action,
        audit_id="audit-1",
    )


def test_parse_dream_report_extracts_themes_and_truths() -> None:
    parsed = skill.parse_dream_report(SAMPLE_REM_REPORT)

    assert parsed["themes"] == [
        {"theme": "gateway", "count": 12},
        {"theme": "heartbeat.md", "count": 8},
    ]
    assert parsed["lasting_truths"] == [
        "Jarvis bridge health checks should stay visible to the operator."
    ]


def test_capture_dream_snapshot_writes_persona_memory(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(persona_manager, "AGENT_MEMORY_DIR", tmp_path / "agent_memory")
    monkeypatch.setattr(
        skill,
        "get_dream_report",
        lambda phase="rem": {
            "phase": phase,
            "path": "C:/Users/sergen/.openclaw/workspace/memory/dreaming/rem/2026-04-24.md",
            "exists": True,
            "content": SAMPLE_REM_REPORT,
        },
    )

    result = skill.capture_dream_snapshot("sabri")

    assert result["target_persona"] == "sabri"
    assert result["themes_captured"] == 2
    assert result["lasting_truths"] == 1
    assert result["memory_entries_written"] == 3

    memory_file = tmp_path / "agent_memory" / "sabri" / "memory.jsonl"
    lines = memory_file.read_text(encoding="utf-8").splitlines()
    texts = [json.loads(line)["text"] for line in lines]
    assert "[dream-theme] gateway: 12 kez" in texts
    assert "[dream-theme] heartbeat.md: 8 kez" in texts
    assert (
        "[dream-truth] Jarvis bridge health checks should stay visible to the operator."
        in texts
    )


def test_capture_dream_snapshot_handles_missing_report(monkeypatch) -> None:
    monkeypatch.setattr(
        skill,
        "get_dream_report",
        lambda phase="rem": {
            "phase": phase,
            "path": "C:/missing/rem.md",
            "exists": False,
            "content": "",
        },
    )

    result = skill.capture_dream_snapshot("sabrican")

    assert result["status"] == "missing_report"
    assert result["themes_captured"] == 0
    assert result["memory_entries_written"] == 0


def test_bridge_routes_dreams_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_current_persona_id", lambda chat_id=None: "sabrican")
    monkeypatch.setattr(
        bridge,
        "evaluate_operator_action",
        lambda *args, **kwargs: _allowed_decision("dreams_snapshot"),
    )
    monkeypatch.setattr(
        skill,
        "capture_dream_snapshot",
        lambda persona_id=None: {
            "status": "ok",
            "target_persona": persona_id or "sabrican",
            "themes_captured": 2,
            "lasting_truths": 1,
            "memory_entries_written": 3,
            "themes": ["gateway", "heartbeat.md"],
            "report_path": "C:/dreams/rem.md",
        },
    )

    result = bridge.handle_command(101, "/dusler-snapshot")

    assert "Dusler Snapshot" in result
    assert "Tema sayisi: 2" in result
    assert "Rapor: C:/dreams/rem.md" in result


def test_bridge_routes_dreams_report(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_current_persona_id", lambda chat_id=None: "sabrican")
    monkeypatch.setattr(
        bridge,
        "evaluate_operator_action",
        lambda *args, **kwargs: _allowed_decision("dreams_report"),
    )
    monkeypatch.setattr(
        skill,
        "get_dream_report",
        lambda phase="rem": {
            "phase": phase,
            "path": f"C:/dreams/{phase}.md",
            "exists": True,
            "content": "# Deep Sleep\n\n- Promoted 0 candidate(s) into MEMORY.md.",
        },
    )

    result = bridge.handle_command(102, "/dusler-rapor deep")

    assert "Dusler Raporu (deep)" in result
    assert "Promoted 0 candidate(s) into MEMORY.md." in result
