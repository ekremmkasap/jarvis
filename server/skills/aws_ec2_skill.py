from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from .aws_common import (
        aws_client,
        aws_region,
        aws_resource,
        isoformat_or_none,
        log_cloud_operation,
        sanitize_text,
        utcnow,
    )
except ImportError:  # pragma: no cover - used by standalone smoke imports
    from aws_common import (  # type: ignore
        aws_client,
        aws_region,
        aws_resource,
        isoformat_or_none,
        log_cloud_operation,
        sanitize_text,
        utcnow,
    )


def list_instances() -> list[dict[str, Any]] | dict[str, Any]:
    try:
        ec2 = aws_resource("ec2")
        instances = []
        for instance in ec2.instances.all():
            name = ""
            for tag in getattr(instance, "tags", []) or []:
                if tag.get("Key") == "Name":
                    name = str(tag.get("Value") or "")
                    break
            instances.append(
                {
                    "id": str(getattr(instance, "id", "") or ""),
                    "name": name,
                    "state": str(((getattr(instance, "state", {}) or {}).get("Name")) or "unknown"),
                    "type": str(getattr(instance, "instance_type", "") or ""),
                    "region": aws_region(),
                    "public_ip": str(getattr(instance, "public_ip_address", "") or ""),
                    "launch_time": isoformat_or_none(getattr(instance, "launch_time", None)),
                }
            )
        log_cloud_operation("ec2", "list_instances", {"count": len(instances)})
        return instances
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("ec2", "list_instances_failed", {"error": error})
        return {"ok": False, "error": error}


def start_instance(instance_id: str) -> dict[str, Any]:
    try:
        client = aws_client("ec2")
        client.start_instances(InstanceIds=[instance_id])
        payload = {"ok": True, "message": f"Instance started: {instance_id}"}
        log_cloud_operation("ec2", "start_instance", {"instance_id": instance_id, "ok": True})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("ec2", "start_instance_failed", {"instance_id": instance_id, "error": error})
        return {"ok": False, "error": error}


def stop_instance(instance_id: str) -> dict[str, Any]:
    try:
        client = aws_client("ec2")
        client.stop_instances(InstanceIds=[instance_id])
        payload = {"ok": True, "message": f"Instance stopped: {instance_id}"}
        log_cloud_operation("ec2", "stop_instance", {"instance_id": instance_id, "ok": True})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("ec2", "stop_instance_failed", {"instance_id": instance_id, "error": error})
        return {"ok": False, "error": error}


def get_instance_status(instance_id: str) -> dict[str, Any]:
    try:
        instance = aws_resource("ec2").Instance(instance_id)
        state = str(((getattr(instance, "state", {}) or {}).get("Name")) or "unknown")
        launch_time = getattr(instance, "launch_time", None)
        uptime_hours = _uptime_hours(launch_time) if launch_time else 0.0
        payload = {
            "state": state,
            "uptime_hours": uptime_hours,
            "type": str(getattr(instance, "instance_type", "") or ""),
            "region": aws_region(),
        }
        log_cloud_operation("ec2", "get_instance_status", {"instance_id": instance_id, "state": state})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("ec2", "get_instance_status_failed", {"instance_id": instance_id, "error": error})
        return {"ok": False, "error": error}


def _uptime_hours(launch_time: datetime) -> float:
    if launch_time.tzinfo is None:
        launch_time = launch_time.replace(tzinfo=timezone.utc)
    delta = utcnow() - launch_time.astimezone(timezone.utc)
    return round(max(delta.total_seconds(), 0) / 3600, 2)
