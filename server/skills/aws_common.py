from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import boto3  # type: ignore
except ImportError:  # pragma: no cover - exercised via patched attributes in tests
    class _Boto3Missing:
        def client(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("boto3 not installed")

        def resource(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("boto3 not installed")

    boto3 = _Boto3Missing()  # type: ignore


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CLOUD_LOG_PATH = DATA_DIR / "cloud_operations.jsonl"
SENSITIVE_ENV_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
)


def aws_region() -> str:
    return os.getenv("AWS_DEFAULT_REGION", "us-east-1").strip() or "us-east-1"


def aws_client(service_name: str, region_name: str | None = None) -> Any:
    return boto3.client(
        service_name,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=region_name or aws_region(),
    )


def aws_resource(service_name: str, region_name: str | None = None) -> Any:
    return boto3.resource(
        service_name,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=region_name or aws_region(),
    )


def sanitize_text(value: Any) -> str:
    text = str(value or "")
    for env_key in SENSITIVE_ENV_KEYS:
        env_value = os.getenv(env_key, "")
        if env_value:
            text = text.replace(env_value, "***REDACTED***")
    return text


def isoformat_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return sanitize_text(value)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def log_cloud_operation(service: str, action: str, payload: dict[str, Any]) -> None:
    # Keep tests isolated from local runtime log churn.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": utcnow().isoformat(),
        "service": sanitize_text(service),
        "action": sanitize_text(action),
        "payload": _sanitize_payload(payload),
    }
    with CLOUD_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {sanitize_text(key): _sanitize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, datetime):
        return isoformat_or_none(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return sanitize_text(value)
