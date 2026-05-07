from __future__ import annotations

import json
import os
import re
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SERVER_PATH = REPO_ROOT / "server"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

os.environ.setdefault("JARVIS_ENABLE_TELEGRAM", "0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")

if "telegram" not in sys.modules:
    telegram_package = types.ModuleType("telegram")
    telegram_intelligence_module = types.ModuleType("telegram.telegram_intelligence")

    class _DummyTelegramIntelligence:
        def __init__(self, *args, **kwargs) -> None:
            pass

    telegram_intelligence_module.TelegramIntelligence = _DummyTelegramIntelligence
    telegram_package.telegram_intelligence = telegram_intelligence_module
    sys.modules["telegram"] = telegram_package
    sys.modules["telegram.telegram_intelligence"] = telegram_intelligence_module

import bridge as bridge_module


def test_swarm_command_starts_coordinator_and_status_works() -> None:
    bridge_module._SWARM_COORDINATORS.clear()

    response = bridge_module.handle_command(
        301,
        "/swarm Build Jarvis Instagram account in 48 hours tmp/handles.sample.csv",
    )

    assert "Swarm baslatildi." in response
    assert "Durum: RUNNING" in response
    assert "Toplam gorev: 5" in response
    match = re.search(r"Goal ID: (swarm_[a-f0-9]+)", response)
    assert match is not None

    status = bridge_module.handle_command(301, f"/swarm-status {match.group(1)}")

    assert f"Swarm durumu: {match.group(1)}" in status
    assert "Durum: RUNNING" in status
    assert "Gorevler: 5" in status
    assert "task_001:" in status
    assert "task_005:" in status


def test_swarm_status_handles_unknown_goal() -> None:
    response = bridge_module.handle_command(302, "/swarm-status swarm_missing")

    assert response == "Swarm bulunamadi: swarm_missing"


def test_swarm_command_preserves_non_swarm_commands(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_SWARM_COORDINATOR_HANDLE_COMMAND",
        lambda chat_id, cmd: f"fallback:{chat_id}:{cmd}",
    )

    response = bridge_module.handle_command(303, "/not-a-swarm-command")

    assert response == "fallback:303:/not-a-swarm-command"


def test_swarm_result_and_finalize_write_report(monkeypatch, tmp_path: Path) -> None:
    bridge_module._SWARM_COORDINATORS.clear()
    monkeypatch.setattr(bridge_module, "_SWARM_REPORTS_DIR", tmp_path / "swarm_reports")

    start = bridge_module.handle_command(304, "/swarm Build Jarvis Instagram account")
    goal_id = re.search(r"Goal ID: (swarm_[a-f0-9]+)", start).group(1)

    ok_result = bridge_module.handle_command(
        304,
        f'/swarm-result {goal_id} task_001 ok | {{"output": {{"profiles": 5}}, "metrics": {{"profiles": 5}}}}',
    )
    failed_result = bridge_module.handle_command(
        304,
        f"/swarm-result {goal_id} task_002 fail | rate limited",
    )
    final = bridge_module.handle_command(304, f"/swarm-finalize {goal_id}")

    assert ok_result == f"Swarm sonucu kaydedildi: {goal_id} / task_001 (basarili)"
    assert failed_result == f"Swarm sonucu kaydedildi: {goal_id} / task_002 (hatali)"
    assert "Swarm final raporu hazir:" in final
    assert "Toplam: 5" in final
    assert "Basarili: 1" in final
    assert "Hatali: 1" in final
    assert "Bekleyen: 3" in final

    report_path = tmp_path / "swarm_reports" / f"{goal_id}.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["successful"] == 1
    assert report["summary"]["failed"] == 1
    assert report["summary"]["pending"] == 3
    assert report["outputs"]["task_001"] == {"profiles": 5}
    assert report["errors"]["task_002"] == "rate limited"


def test_swarm_result_handles_unknown_goal_and_task() -> None:
    bridge_module._SWARM_COORDINATORS.clear()

    unknown_goal = bridge_module.handle_command(
        305,
        "/swarm-result swarm_missing task_001 ok | done",
    )
    start = bridge_module.handle_command(305, "/swarm Test unknown task")
    goal_id = re.search(r"Goal ID: (swarm_[a-f0-9]+)", start).group(1)
    unknown_task = bridge_module.handle_command(
        305,
        f"/swarm-result {goal_id} task_999 ok | done",
    )

    assert unknown_goal == "Swarm bulunamadi: swarm_missing"
    assert "Swarm sonuc hatasi:" in unknown_task
    assert "Unknown swarm task: task_999" in unknown_task
