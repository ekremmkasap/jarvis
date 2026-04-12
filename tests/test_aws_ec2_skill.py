from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys


SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))


import skills.aws_ec2_skill as aws_ec2_skill


def _fake_instance(
    instance_id: str = "i-1234567890",
    *,
    state: str = "running",
    name: str = "web-1",
    public_ip: str = "1.2.3.4",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=instance_id,
        tags=[{"Key": "Name", "Value": name}],
        state={"Name": state},
        instance_type="t3.micro",
        public_ip_address=public_ip,
        launch_time=datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc),
    )


def test_list_instances_returns_expected_shape() -> None:
    fake_instances = [_fake_instance()]
    fake_resource = Mock()
    fake_resource.instances.all.return_value = fake_instances

    with patch.object(aws_ec2_skill, "aws_resource", return_value=fake_resource):
        result = aws_ec2_skill.list_instances()

    assert isinstance(result, list)
    assert result == [
        {
            "id": "i-1234567890",
            "name": "web-1",
            "state": "running",
            "type": "t3.micro",
            "region": "us-east-1",
            "public_ip": "1.2.3.4",
            "launch_time": "2026-04-12T10:00:00+00:00",
        }
    ]


def test_start_and_stop_instance_return_ok_payloads() -> None:
    fake_client = Mock()

    with patch.object(aws_ec2_skill, "aws_client", return_value=fake_client):
        start_result = aws_ec2_skill.start_instance("i-start")
        stop_result = aws_ec2_skill.stop_instance("i-stop")

    fake_client.start_instances.assert_called_once_with(InstanceIds=["i-start"])
    fake_client.stop_instances.assert_called_once_with(InstanceIds=["i-stop"])
    assert start_result["ok"] is True
    assert "i-start" in start_result["message"]
    assert stop_result["ok"] is True
    assert "i-stop" in stop_result["message"]


def test_exception_returns_error_dict() -> None:
    with patch.object(aws_ec2_skill, "aws_resource", side_effect=RuntimeError("boom")):
        result = aws_ec2_skill.list_instances()

    assert result == {"ok": False, "error": "boom"}


def test_get_instance_status_includes_uptime() -> None:
    fake_resource = Mock()
    fake_resource.Instance.return_value = _fake_instance(instance_id="i-status")

    with patch.object(aws_ec2_skill, "aws_resource", return_value=fake_resource):
        with patch.object(
            aws_ec2_skill,
            "utcnow",
            return_value=datetime(2026, 4, 12, 13, 30, tzinfo=timezone.utc),
        ):
            result = aws_ec2_skill.get_instance_status("i-status")

    assert result == {
        "state": "running",
        "uptime_hours": 3.5,
        "type": "t3.micro",
        "region": "us-east-1",
    }
