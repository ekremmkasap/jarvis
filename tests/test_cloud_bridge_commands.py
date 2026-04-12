from __future__ import annotations

from pathlib import Path


BRIDGE_PATH = Path(__file__).parent.parent / "server" / "bridge.py"


def test_cloud_command_routes_exist_in_bridge() -> None:
    content = BRIDGE_PATH.read_text(encoding="utf-8", errors="replace")

    assert 'elif command == "/cloud-durum":' in content
    assert 'elif command == "/cloud-ec2-liste":' in content
    assert 'elif command == "/cloud-ec2-baslat":' in content
    assert 'elif command == "/cloud-ec2-durdur":' in content
    assert 'elif command == "/cloud-s3-liste":' in content
    assert 'elif command == "/cloud-maliyet":' in content


def test_cloud_command_helpers_are_present() -> None:
    content = BRIDGE_PATH.read_text(encoding="utf-8", errors="replace")

    assert "def _truncate_cloud_text" in content
    assert "def _cloud_status_summary" in content
    assert "def _cloud_list_ec2" in content
    assert "def _cloud_list_s3" in content
    assert "def _cloud_cost_summary" in content
