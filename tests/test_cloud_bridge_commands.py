from __future__ import annotations

from pathlib import Path
import sys


ROOT_PATH = Path(__file__).parent.parent
SERVER_PATH = ROOT_PATH / "server"
BRIDGE_PATH = SERVER_PATH / "bridge.py"

if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))


from skill_registry import SkillRegistry
from skills.registry_entries.cloud_entries import register_cloud_skills
from skills.registry_entries.help_entries import register_help_skill


def test_cloud_commands_dispatch_through_registry_in_bridge() -> None:
    content = BRIDGE_PATH.read_text(encoding="utf-8", errors="replace")

    assert 'elif command.startswith("/cloud-") or command in {' in content
    assert '"/yardim"' in content
    assert '"/ec2-izle"' in content
    assert '"/ec2-yeniden-baslat"' in content
    assert '"/s3-url"' in content
    assert '"/maliyet-uyari"' in content
    assert "COMMAND_REGISTRY.dispatch(command, args" in content


def test_cloud_registry_entries_register_expected_commands() -> None:
    registry = SkillRegistry()
    register_cloud_skills(registry)

    commands = [entry.command for entry in registry.list_commands(category="cloud")]

    assert commands == [
        "/cloud-durum",
        "/cloud-ec2-liste",
        "/cloud-ec2-baslat",
        "/cloud-ec2-durdur",
        "/cloud-s3-liste",
        "/cloud-maliyet",
        "/ec2-izle",
        "/ec2-yeniden-baslat",
        "/s3-url",
        "/maliyet-uyari",
        "/cloud-ozet",
    ]


def test_help_entry_returns_non_empty_turkish_list() -> None:
    registry = SkillRegistry()
    register_cloud_skills(registry)
    register_help_skill(registry)

    result = registry.dispatch("/yardim", context={"registry": registry})

    assert result.startswith("Komutlar:")
    assert "[cloud]" in result
