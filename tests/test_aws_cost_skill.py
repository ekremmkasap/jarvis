from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import sys


SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))


import skills.aws_cost_skill as aws_cost_skill


def test_get_monthly_cost_parses_cost_explorer_response() -> None:
    fake_client = Mock()
    fake_client.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-04-01", "End": "2026-04-14"},
                "Total": {"UnblendedCost": {"Amount": "18.75"}},
                "Groups": [
                    {
                        "Keys": ["Amazon EC2"],
                        "Metrics": {"UnblendedCost": {"Amount": "12.5"}},
                    },
                    {
                        "Keys": ["Amazon S3"],
                        "Metrics": {"UnblendedCost": {"Amount": "6.25"}},
                    },
                ],
            }
        ]
    }

    with patch.object(aws_cost_skill, "aws_client", return_value=fake_client):
        result = aws_cost_skill.get_monthly_cost()

    assert result["total_usd"] == 18.75
    assert result["by_service"] == {"Amazon EC2": 12.5, "Amazon S3": 6.25}
    assert result["currency"] == "USD"
    assert "mock" not in result


def test_get_monthly_cost_returns_mock_data_when_cost_explorer_fails() -> None:
    with patch.object(aws_cost_skill, "aws_client", side_effect=RuntimeError("ce unavailable")):
        result = aws_cost_skill.get_monthly_cost()

    assert result["mock"] is True
    assert result["currency"] == "USD"
    assert result["by_service"]["Amazon EC2"] == 30.0


def test_get_cost_trend_returns_month_entries() -> None:
    fake_client = Mock()
    fake_client.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {"TimePeriod": {"Start": "2026-02-01"}, "Total": {"UnblendedCost": {"Amount": "10.0"}}},
            {"TimePeriod": {"Start": "2026-03-01"}, "Total": {"UnblendedCost": {"Amount": "15.0"}}},
            {"TimePeriod": {"Start": "2026-04-01"}, "Total": {"UnblendedCost": {"Amount": "17.5"}}},
        ]
    }

    with patch.object(aws_cost_skill, "aws_client", return_value=fake_client):
        result = aws_cost_skill.get_cost_trend(3)

    assert result == [
        {"month": "2026-02-01", "total_usd": 10.0},
        {"month": "2026-03-01", "total_usd": 15.0},
        {"month": "2026-04-01", "total_usd": 17.5},
    ]


def test_save_alert_threshold_writes_state_file() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        alerts_path = Path(tmp_dir) / "cost_alerts.json"

        with patch.object(aws_cost_skill, "COST_ALERTS_PATH", alerts_path):
            with patch.object(aws_cost_skill, "STATE_DIR", Path(tmp_dir)):
                result = aws_cost_skill.save_alert_threshold("Amazon EC2", 50.0)

        payload = json.loads(alerts_path.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert payload["thresholds"][0]["service"] == "Amazon EC2"
    assert payload["thresholds"][0]["usd_limit"] == 50.0


def test_get_budget_alerts_uses_saved_thresholds() -> None:
    thresholds = [{"service": "Amazon EC2", "usd_limit": 100.0, "updated_at": "2026-04-13T01:00:00+00:00"}]

    with patch.object(aws_cost_skill, "_load_saved_thresholds", return_value=thresholds):
        with patch.object(
            aws_cost_skill,
            "get_monthly_cost",
            return_value={"total_usd": 20.0, "by_service": {"Amazon EC2": 45.0}, "currency": "USD", "period": "x"},
        ):
            with patch.object(aws_cost_skill, "aws_client", side_effect=RuntimeError("no budgets")):
                result = aws_cost_skill.get_budget_alerts()

    assert result == [
        {
            "name": "Amazon EC2",
            "limit_usd": 100.0,
            "current_usd": 45.0,
            "pct_used": 45.0,
        }
    ]


def test_check_cost_alerts_returns_list() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        alerts_path = Path(tmp_dir) / "cost_alerts.json"
        alerts_path.write_text(
            json.dumps([{"service": "Amazon EC2", "usd_limit": 100.0}], ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(aws_cost_skill, "COST_ALERTS_PATH", alerts_path):
            with patch.object(
                aws_cost_skill,
                "get_monthly_cost",
                return_value={"total_usd": 20.0, "by_service": {"Amazon EC2": 45.0}, "currency": "USD", "period": "x"},
            ):
                result = aws_cost_skill.check_cost_alerts()

    assert result == [
        {
            "service": "Amazon EC2",
            "limit_usd": 100.0,
            "current_usd": 45.0,
            "pct_used": 45.0,
            "alert": False,
        }
    ]


def test_check_cost_alerts_alert_flag_set_when_above_80pct() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        alerts_path = Path(tmp_dir) / "cost_alerts.json"
        alerts_path.write_text(
            json.dumps({"thresholds": [{"service": "Amazon S3", "usd_limit": 50.0}]}, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(aws_cost_skill, "COST_ALERTS_PATH", alerts_path):
            with patch.object(
                aws_cost_skill,
                "get_monthly_cost",
                return_value={"total_usd": 44.0, "by_service": {"Amazon S3": 45.0}, "currency": "USD", "period": "x"},
            ):
                result = aws_cost_skill.check_cost_alerts()

    assert result[0]["alert"] is True
    assert result[0]["pct_used"] == 90.0


def test_get_cost_summary_text_under_300_chars() -> None:
    with patch.object(
        aws_cost_skill,
        "get_monthly_cost",
        return_value={
            "total_usd": 123.45,
            "by_service": {
                "Amazon Elastic Compute Cloud": 70.0,
                "Amazon Simple Storage Service": 30.0,
                "AWS Lambda": 12.5,
                "Amazon CloudFront": 10.95,
            },
            "currency": "USD",
            "period": "x",
        },
    ):
        with patch.object(
            aws_cost_skill,
            "check_cost_alerts",
            return_value=[{"service": "Amazon Elastic Compute Cloud", "alert": True}],
        ):
            summary = aws_cost_skill.get_cost_summary_text()

    assert len(summary) <= 300
    assert "Bu ay: $123.45" in summary
    assert "Amazon Elastic Compute Cloud" in summary
    assert "uyari esigi asildi" in summary
