from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, call, patch
import sys


SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))


import skills.aws_s3_skill as aws_s3_skill


def test_list_buckets_returns_expected_shape() -> None:
    fake_client = Mock()
    fake_client.list_buckets.return_value = {
        "Buckets": [
            {
                "Name": "alpha-bucket",
                "CreationDate": datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
            }
        ]
    }

    with patch.object(aws_s3_skill, "aws_client", return_value=fake_client):
        with patch.object(aws_s3_skill, "_bucket_region", return_value="eu-central-1"):
            result = aws_s3_skill.list_buckets()

    assert result == [
        {
            "name": "alpha-bucket",
            "region": "eu-central-1",
            "creation_date": "2026-04-10T08:00:00+00:00",
        }
    ]


def test_list_objects_limits_to_expected_format() -> None:
    fake_client = Mock()
    fake_client.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "reports/daily.csv",
                "Size": 128,
                "LastModified": datetime(2026, 4, 11, 9, 30, tzinfo=timezone.utc),
            }
        ]
    }

    with patch.object(aws_s3_skill, "aws_client", return_value=fake_client):
        result = aws_s3_skill.list_objects("alpha-bucket", "reports/")

    fake_client.list_objects_v2.assert_called_once_with(Bucket="alpha-bucket", Prefix="reports/", MaxKeys=100)
    assert result == [
        {
            "key": "reports/daily.csv",
            "size_bytes": 128,
            "last_modified": "2026-04-11T09:30:00+00:00",
        }
    ]


def test_get_bucket_size_sums_multiple_pages() -> None:
    fake_client = Mock()
    fake_client.list_objects_v2.side_effect = [
        {
            "Contents": [{"Key": "a.txt", "Size": 5}, {"Key": "b.txt", "Size": 7}],
            "IsTruncated": True,
            "NextContinuationToken": "token-1",
        },
        {
            "Contents": [{"Key": "c.txt", "Size": 11}],
            "IsTruncated": False,
        },
    ]

    with patch.object(aws_s3_skill, "aws_client", return_value=fake_client):
        result = aws_s3_skill.get_bucket_size("alpha-bucket")

    assert result == {"total_size_bytes": 23, "object_count": 3}
    assert fake_client.list_objects_v2.mock_calls == [
        call(Bucket="alpha-bucket", MaxKeys=1000),
        call(Bucket="alpha-bucket", MaxKeys=1000, ContinuationToken="token-1"),
    ]


def test_upload_and_delete_return_ok_payloads() -> None:
    fake_client = Mock()

    with patch.object(aws_s3_skill, "aws_client", return_value=fake_client):
        with patch.object(aws_s3_skill, "_bucket_region", return_value="us-east-1"):
            upload_result = aws_s3_skill.upload_file("alpha-bucket", "reports/out.csv", "C:/tmp/out.csv")
        delete_result = aws_s3_skill.delete_object("alpha-bucket", "reports/out.csv")

    fake_client.upload_file.assert_called_once_with("C:/tmp/out.csv", "alpha-bucket", "reports/out.csv")
    fake_client.delete_object.assert_called_once_with(Bucket="alpha-bucket", Key="reports/out.csv")
    assert upload_result == {
        "ok": True,
        "url": "https://alpha-bucket.s3.amazonaws.com/reports/out.csv",
    }
    assert delete_result == {
        "ok": True,
        "message": "Object deleted: reports/out.csv",
    }


def test_exception_returns_error_dict() -> None:
    with patch.object(aws_s3_skill, "aws_client", side_effect=RuntimeError("bucket failure")):
        result = aws_s3_skill.list_buckets()

    assert result == {"ok": False, "error": "bucket failure"}
