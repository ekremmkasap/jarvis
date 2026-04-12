from __future__ import annotations

from pathlib import Path


BRIDGE_PATH = Path(__file__).parent.parent / "server" / "bridge.py"
CLOUD_PAGE_PATH = Path(__file__).parent.parent / "apps" / "web-ui" / "src" / "app" / "cloud" / "page.tsx"


def test_cloud_api_endpoints_exist_in_bridge() -> None:
    content = BRIDGE_PATH.read_text(encoding="utf-8", errors="replace")

    assert 'elif path == "/api/cloud/ec2":' in content
    assert 'elif path == "/api/cloud/s3":' in content
    assert 'elif path == "/api/cloud/cost":' in content
    assert 'elif path == "/api/cloud/alerts":' in content
    assert 'elif path == "/api/cloud/ec2/action":' in content
    assert "def _handle_cloud_ec2_action_endpoint" in content


def test_cloud_page_wires_bridge_routes() -> None:
    content = CLOUD_PAGE_PATH.read_text(encoding="utf-8", errors="replace")

    assert "NEXT_PUBLIC_BRIDGE_API" in content
    assert "/api/cloud/ec2" in content
    assert "/api/cloud/s3" in content
    assert "/api/cloud/cost" in content
    assert "/api/cloud/alerts" in content
    assert "/api/cloud/ec2/action" in content
    assert "BudgetAlert" in content
