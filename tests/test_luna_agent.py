from __future__ import annotations

import importlib
import json
import os
import sys
import types
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).parent.parent
SERVER_PATH = ROOT / "server"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
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


from server.services import luna_agent
from server.skills import luna_scan_skill


@pytest.fixture()
def luna_paths(tmp_path, monkeypatch):
    targets_path = tmp_path / "luna_targets.yaml"
    audit_path = tmp_path / "luna_audit.jsonl"
    targets_path.write_text(
        yaml.safe_dump(
            {
                "targets": [
                    {
                        "id": "jarvis-bridge",
                        "url": "http://127.0.0.1:8081/health",
                        "scope": ["localhost:8081"],
                        "type": "own_system",
                        "program": None,
                        "added_at": "2026-04-13T00:00:00Z",
                        "scan_path": ".",
                    }
                ]
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(luna_agent, "LUNA_TARGETS_PATH", targets_path)
    monkeypatch.setattr(luna_agent, "LUNA_AUDIT_LOG_PATH", audit_path)
    return targets_path, audit_path


def test_is_authorized_returns_target_for_whitelisted_id(luna_paths):
    target = luna_agent.is_authorized("jarvis-bridge")

    assert target["id"] == "jarvis-bridge"
    assert target["type"] == "own_system"


def test_is_authorized_raises_for_unknown_target(luna_paths):
    with pytest.raises(luna_agent.TargetNotAuthorizedError):
        luna_agent.is_authorized("unknown-target")


def test_audit_log_appends_jsonl_record(luna_paths):
    _, audit_path = luna_paths

    luna_agent.audit_log(
        action="scan",
        target="jarvis-bridge",
        finding="FOX-1",
        severity="high",
        notes="test finding",
    )

    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["persona"] == "luna"
    assert payload["target"] == "jarvis-bridge"
    assert payload["finding_id"] == "FOX-1"
    assert payload["severity"] == "high"


def test_run_foxguard_scan_returns_graceful_error_when_binary_missing(monkeypatch):
    monkeypatch.setattr(luna_scan_skill.shutil, "which", lambda _: None)

    result = luna_scan_skill.run_foxguard_scan(ROOT)

    assert result["ok"] is False
    assert result["error"] == "foxguard_not_installed"


def test_parse_foxguard_output_maps_findings():
    raw = {
        "raw": json.dumps(
            {
                "findings": [
                    {
                        "id": "FG-001",
                        "severity": "HIGH",
                        "type": "hardcoded_secret",
                        "title": "Hardcoded secret",
                        "description": "Secret literal found",
                        "path": "server/bridge.py",
                    }
                ]
            }
        )
    }

    findings = luna_scan_skill.parse_foxguard_output(raw)

    assert len(findings) == 1
    assert findings[0]["id"] == "FG-001"
    assert findings[0]["severity"] == "high"
    assert findings[0]["type"] == "hardcoded_secret"


def test_scan_target_raises_for_unauthorized_target(luna_paths):
    with pytest.raises(luna_agent.TargetNotAuthorizedError):
        luna_agent.scan_target("unauthorized")


def test_scan_target_logs_graceful_failure_when_foxguard_missing(
    luna_paths, monkeypatch
):
    _, audit_path = luna_paths
    monkeypatch.setattr(luna_agent, "ROOT_DIR", ROOT)
    monkeypatch.setattr(
        luna_agent,
        "run_foxguard_scan",
        lambda path: {"ok": False, "error": "foxguard_not_installed", "path": str(path)},
    )

    result = luna_agent.scan_target("jarvis-bridge")

    assert result["ok"] is False
    assert result["error"] == "foxguard_not_installed"
    records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert any(record["action"] == "scan" for record in records)
    assert any("foxguard_not_installed" in (record["notes"] or "") for record in records)


def test_scan_target_writes_findings_to_audit_log(luna_paths, monkeypatch):
    _, audit_path = luna_paths
    monkeypatch.setattr(luna_agent, "ROOT_DIR", ROOT)
    monkeypatch.setattr(
        luna_agent,
        "run_foxguard_scan",
        lambda path: {
            "ok": True,
            "path": str(path),
            "raw": json.dumps(
                {
                    "findings": [
                        {
                            "id": "FG-002",
                            "severity": "medium",
                            "title": "Weak config",
                            "description": "Configuration issue",
                            "path": "server/config.py",
                        }
                    ]
                }
            ),
        },
    )

    result = luna_agent.scan_target("jarvis-bridge")

    assert result["ok"] is True
    assert len(result["findings"]) == 1
    records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert any(record["action"] == "scan_finding" for record in records)
    assert any(record["finding_id"] == "FG-002" for record in records)


def test_luna_tara_bridge_command_uses_scan_target(monkeypatch):
    import bridge as bridge_module

    bridge = importlib.reload(bridge_module)
    monkeypatch.setattr(
        bridge,
        "_get_active_persona_payload",
        lambda chat_id=None, lane=None: {"id": "luna"},
    )

    monkeypatch.setattr(
        "server.services.luna_agent.scan_target",
        lambda target_id: {
            "ok": True,
            "target_id": target_id,
            "findings": [
                {"severity": "high"},
                {"severity": "info"},
            ],
        },
    )

    result = bridge.handle_command(123, "/luna-tara jarvis-bridge")

    assert "Luna tarama tamamlandi" in result
    assert "Bulgu: 2" in result


def test_luna_commands_reject_when_luna_is_not_active(monkeypatch):
    import bridge as bridge_module

    bridge = importlib.reload(bridge_module)
    monkeypatch.setattr(
        bridge,
        "_get_active_persona_payload",
        lambda chat_id=None, lane=None: {"id": "seda"},
    )
    monkeypatch.setattr(
        "server.services.luna_agent.scan_target",
        lambda target_id: pytest.fail("scan_target should not run when Luna is inactive"),
    )

    result = bridge.handle_command(123, "/luna-tara jarvis-bridge")

    assert result == "Bu komut sadece Luna aktifken kullanılabilir"
