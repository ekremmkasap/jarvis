from __future__ import annotations

from typing import Any


def _load_cloud_modules():
    from server.skills.aws_cost_skill import get_monthly_cost
    from server.skills.aws_ec2_skill import list_instances, start_instance, stop_instance
    from server.skills.aws_s3_skill import list_buckets

    return {
        "get_monthly_cost": get_monthly_cost,
        "list_buckets": list_buckets,
        "list_instances": list_instances,
        "start_instance": start_instance,
        "stop_instance": stop_instance,
    }


def truncate_cloud_text(text: str, limit: int = 400) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)].rstrip() + "..."


def cloud_state_label(state: str) -> str:
    mapping = {
        "running": "calisiyor",
        "pending": "basliyor",
        "stopped": "durdu",
        "stopping": "duruyor",
        "shutting-down": "kapaniyor",
        "terminated": "silindi",
    }
    return mapping.get(str(state or "").strip().lower(), str(state or "bilinmiyor"))


def cloud_status_summary(args: str = "", context: dict[str, Any] | None = None) -> str:
    del args, context
    modules = _load_cloud_modules()
    instances = modules["list_instances"]()
    buckets = modules["list_buckets"]()
    costs = modules["get_monthly_cost"]()

    instance_items = instances if isinstance(instances, list) else []
    bucket_items = buckets if isinstance(buckets, list) else []
    active_instances = sum(1 for item in instance_items if str(item.get("state")) == "running")
    total_usd = float(costs.get("total_usd") or 0.0) if isinstance(costs, dict) else 0.0
    return truncate_cloud_text(f"EC2: {active_instances} aktif / S3: {len(bucket_items)} bucket / Maliyet: ${total_usd:.2f}")


def cloud_list_ec2(args: str = "", context: dict[str, Any] | None = None) -> str:
    del args, context
    modules = _load_cloud_modules()
    instances = modules["list_instances"]()
    if isinstance(instances, dict) and instances.get("ok") is False:
        return truncate_cloud_text(f"EC2 hatasi: {instances.get('error', 'bilinmeyen hata')}")
    if not instances:
        return "EC2 Sunucular:\n- Kayit bulunamadi"

    lines = ["EC2 Sunucular:"]
    for item in instances[:10]:
        lines.append(
            f"- {item.get('id')} ({cloud_state_label(str(item.get('state') or ''))}) "
            f"{item.get('type')} {item.get('region')}"
        )
    return truncate_cloud_text("\n".join(lines))


def cloud_start_ec2(args: str = "", context: dict[str, Any] | None = None) -> str:
    del context
    instance_id = str(args or "").strip()
    if not instance_id:
        return "Kullanim: /cloud-ec2-baslat <instance_id>"

    modules = _load_cloud_modules()
    result = modules["start_instance"](instance_id)
    if result.get("ok"):
        return truncate_cloud_text(f"Sunucu baslatildi: {instance_id}")
    return truncate_cloud_text(f"EC2 hatasi: {result.get('error', 'bilinmeyen hata')}")


def cloud_stop_ec2(args: str = "", context: dict[str, Any] | None = None) -> str:
    del context
    instance_id = str(args or "").strip()
    if not instance_id:
        return "Kullanim: /cloud-ec2-durdur <instance_id>"

    modules = _load_cloud_modules()
    result = modules["stop_instance"](instance_id)
    if result.get("ok"):
        return truncate_cloud_text(f"Sunucu durduruldu: {instance_id}")
    return truncate_cloud_text(f"EC2 hatasi: {result.get('error', 'bilinmeyen hata')}")


def cloud_list_s3(args: str = "", context: dict[str, Any] | None = None) -> str:
    del args, context
    modules = _load_cloud_modules()
    buckets = modules["list_buckets"]()
    if isinstance(buckets, dict) and buckets.get("ok") is False:
        return truncate_cloud_text(f"S3 hatasi: {buckets.get('error', 'bilinmeyen hata')}")
    if not buckets:
        return "S3 Bucket'lar:\n- Kayit bulunamadi"

    lines = ["S3 Bucket'lar:"]
    for item in buckets[:10]:
        lines.append(f"- {item.get('name')} ({item.get('region')})")
    return truncate_cloud_text("\n".join(lines))


def cloud_cost_summary(args: str = "", context: dict[str, Any] | None = None) -> str:
    del args, context
    modules = _load_cloud_modules()
    payload = modules["get_monthly_cost"]()
    if not isinstance(payload, dict):
        return "Maliyet verisi alinamadi."

    total_usd = float(payload.get("total_usd") or 0.0)
    by_service = payload.get("by_service", {}) if isinstance(payload.get("by_service"), dict) else {}
    ec2_cost = float(by_service.get("Amazon EC2", 0.0))
    s3_cost = float(by_service.get("Amazon S3", 0.0))
    return truncate_cloud_text(f"Bu ay: ${total_usd:.2f}\nEC2: ${ec2_cost:.2f} / S3: ${s3_cost:.2f}")
