from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


def get_instance_metrics(instance_id: str, hours: int = 1) -> dict[str, Any]:
    try:
        period_hours = max(int(hours or 1), 1)
        client = aws_client("cloudwatch")
        end = utcnow()
        start = end - timedelta(hours=period_hours)

        def _metric_average(metric_name: str, unit: str) -> float:
            response = client.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start,
                EndTime=end,
                Period=3600,
                Statistics=["Average"],
                Unit=unit,
            )
            datapoints = response.get("Datapoints", [])
            if not datapoints:
                return 0.0
            return round(sum(float(point.get("Average") or 0.0) for point in datapoints) / len(datapoints), 2)

        cpu_avg = _metric_average("CPUUtilization", "Percent")
        network_in_mb = round(_metric_average("NetworkIn", "Bytes") / (1024 * 1024), 3)
        network_out_mb = round(_metric_average("NetworkOut", "Bytes") / (1024 * 1024), 3)
        payload = {
            "ok": True,
            "instance_id": instance_id,
            "cpu_avg": cpu_avg,
            "network_in_mb": network_in_mb,
            "network_out_mb": network_out_mb,
            "period_hours": period_hours,
        }
        log_cloud_operation("ec2", "get_instance_metrics", payload)
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("ec2", "get_instance_metrics_failed", {"instance_id": instance_id, "error": error})
        return {"ok": False, "error": error}


def reboot_instance(instance_id: str) -> dict[str, Any]:
    try:
        client = aws_client("ec2")
        client.reboot_instances(InstanceIds=[instance_id])
        payload = {"ok": True, "message": f"{instance_id} yeniden baslatildi."}
        log_cloud_operation("ec2", "reboot_instance", {"instance_id": instance_id, "ok": True})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("ec2", "reboot_instance_failed", {"instance_id": instance_id, "error": error})
        return {"ok": False, "error": error}


def _uptime_hours(launch_time: datetime) -> float:
    if launch_time.tzinfo is None:
        launch_time = launch_time.replace(tzinfo=timezone.utc)
    delta = utcnow() - launch_time.astimezone(timezone.utc)
    return round(max(delta.total_seconds(), 0) / 3600, 2)
