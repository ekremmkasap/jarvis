import json
from pathlib import Path

import yaml

from server.skills import pc_control_gateway


def _write_test_whitelist(path: Path, allowed_dir: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "commands": {
                    "pc-durum": {"action": "system_status", "args_required": False},
                    "ekran-goruntusu": {"action": "screenshot", "args_required": False},
                    "ac": {
                        "action": "open_app",
                        "args_required": True,
                        "apps": {
                            "chrome": {"command": ["cmd", "/c", "start", "", "chrome"]},
                            "powershell": {"command": ["cmd", "/c", "start", "", "powershell"]},
                        },
                    },
                    "uyku": {
                        "action": "sleep_pc",
                        "args_required": False,
                        "requires_confirmation": True,
                    },
                    "dosya-gonder": {
                        "action": "send_file",
                        "args_required": True,
                        "allowed_dirs": [str(allowed_dir)],
                    },
                }
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_whitelist_allows_known_app(tmp_path, monkeypatch):
    config_path = tmp_path / "pc_control_whitelist.yaml"
    _write_test_whitelist(config_path, tmp_path)
    monkeypatch.setattr(pc_control_gateway, "CONFIG_PATH", config_path)

    approved, reason, _rule = pc_control_gateway.check_whitelist("ac", "chrome")

    assert approved is True
    assert reason == "approved"


def test_whitelist_blocks_unknown_app(tmp_path, monkeypatch):
    config_path = tmp_path / "pc_control_whitelist.yaml"
    _write_test_whitelist(config_path, tmp_path)
    monkeypatch.setattr(pc_control_gateway, "CONFIG_PATH", config_path)

    approved, reason, _rule = pc_control_gateway.check_whitelist("ac", "opera")

    assert approved is False
    assert reason == "app_not_whitelisted"


def test_whitelist_allows_file_from_allowed_directory(tmp_path, monkeypatch):
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    allowed_file = allowed_dir / "report.txt"
    allowed_file.write_text("ok", encoding="utf-8")

    config_path = tmp_path / "pc_control_whitelist.yaml"
    _write_test_whitelist(config_path, allowed_dir)
    monkeypatch.setattr(pc_control_gateway, "CONFIG_PATH", config_path)

    approved, reason, _rule = pc_control_gateway.check_whitelist("dosya-gonder", str(allowed_file))

    assert approved is True
    assert reason == "approved"


def test_execute_pc_status_command_writes_audit_log(tmp_path, monkeypatch):
    config_path = tmp_path / "pc_control_whitelist.yaml"
    _write_test_whitelist(config_path, tmp_path)
    audit_path = tmp_path / "pc_control_audit.jsonl"

    monkeypatch.setattr(pc_control_gateway, "CONFIG_PATH", config_path)
    monkeypatch.setattr(pc_control_gateway, "LOG_PATH", audit_path)
    monkeypatch.setattr(
        pc_control_gateway,
        "get_system_status",
        lambda: {
            "cpu_percent": 12.5,
            "ram_used_mb": 2048,
            "ram_total_mb": 8192,
            "disk_used_gb": 128.0,
            "disk_total_gb": 512.0,
            "jarvis_processes": ["bridge.py"],
            "ts": "2026-04-14T12:00:00+00:00",
        },
    )

    result = pc_control_gateway.execute_pc_command(
        "pc-durum",
        "",
        persona_id="sabrican",
        chat_id=42,
    )

    assert result["ok"] is True
    assert result["action"] == "system_status"
    assert "CPU: 12.5%" in result["message"]

    audit_lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 1
    audit_entry = json.loads(audit_lines[0])
    assert audit_entry["ok"] is True
    assert audit_entry["command_key"] == "pc-durum"
    assert audit_entry["chat_id"] == 42
    assert audit_entry["persona_id"] == "sabrican"


def test_execute_screenshot_command_returns_path_and_logs_obsidian(tmp_path, monkeypatch):
    config_path = tmp_path / "pc_control_whitelist.yaml"
    _write_test_whitelist(config_path, tmp_path)
    audit_path = tmp_path / "pc_control_audit.jsonl"
    screenshot_path = tmp_path / "shot.png"
    screenshot_path.write_bytes(b"png")
    obsidian_calls: list[tuple[str, str, str]] = []

    monkeypatch.setattr(pc_control_gateway, "CONFIG_PATH", config_path)
    monkeypatch.setattr(pc_control_gateway, "LOG_PATH", audit_path)
    monkeypatch.setattr(pc_control_gateway, "take_screenshot", lambda: str(screenshot_path))
    monkeypatch.setattr(
        pc_control_gateway,
        "_safe_obsidian_log",
        lambda command_key, args, result: obsidian_calls.append((command_key, args, result)),
    )

    result = pc_control_gateway.execute_pc_command(
        "ekran-goruntusu",
        "",
        persona_id="sabrican",
        chat_id=7,
    )

    assert result["ok"] is True
    assert result["action"] == "screenshot"
    assert result["path"] == str(screenshot_path)
    assert obsidian_calls == [("ekran-goruntusu", "", "Ekran goruntusu hazir.")]

    audit_lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 1
    audit_entry = json.loads(audit_lines[0])
    assert audit_entry["result"] == "Ekran goruntusu hazir."


def test_infer_pc_status_command():
    payload = pc_control_gateway.infer_pc_command("pc durum nedir")

    assert payload == {"command_key": "pc-durum", "args": ""}


def test_execute_pc_command_requires_policy_approval_for_sensitive_app(tmp_path, monkeypatch):
    config_path = tmp_path / "pc_control_whitelist.yaml"
    _write_test_whitelist(config_path, tmp_path)
    audit_path = tmp_path / "pc_control_audit.jsonl"

    monkeypatch.setattr(pc_control_gateway, "CONFIG_PATH", config_path)
    monkeypatch.setattr(pc_control_gateway, "LOG_PATH", audit_path)

    result = pc_control_gateway.execute_pc_command(
        "ac",
        "powershell",
        persona_id="sabrican",
        chat_id=7,
    )

    assert result["ok"] is False
    assert result["approval_id"]
    assert result["risk"] == "high"
    assert "policy gate" in result["message"].lower()


def test_execute_pc_sleep_command_requires_approval(tmp_path, monkeypatch):
    config_path = tmp_path / "pc_control_whitelist.yaml"
    _write_test_whitelist(config_path, tmp_path)
    audit_path = tmp_path / "pc_control_audit.jsonl"

    monkeypatch.setattr(pc_control_gateway, "CONFIG_PATH", config_path)
    monkeypatch.setattr(pc_control_gateway, "LOG_PATH", audit_path)

    result = pc_control_gateway.execute_pc_command(
        "uyku",
        "",
        persona_id="sabrican",
        chat_id=7,
    )

    assert result["ok"] is False
    assert result["approval_id"]
    assert result["risk"] in {"medium", "high"}
    assert "policy gate" in result["message"].lower()
