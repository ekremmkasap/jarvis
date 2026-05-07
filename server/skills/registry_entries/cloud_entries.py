from __future__ import annotations

from typing import Any

from server.cloud_command_handlers import (
    cloud_cost_summary,
    cloud_list_ec2,
    cloud_list_s3,
    cloud_start_ec2,
    cloud_status_summary,
    cloud_stop_ec2,
)
from server.skill_registry import SkillEntry, SkillRegistry
from server.skills.aws_cost_skill import check_cost_alerts, get_cost_summary_text
from server.skills.aws_ec2_skill import get_instance_metrics, reboot_instance
from server.skills.aws_s3_skill import generate_presigned_url


def register_cloud_skills(registry: SkillRegistry):
    registry.register(
        SkillEntry(
            command="/cloud-durum",
            handler=cloud_status_summary,
            description="Tum cloud servislerinin ozet durumu",
            category="cloud",
        )
    )
    registry.register(
        SkillEntry(
            command="/cloud-ec2-liste",
            handler=cloud_list_ec2,
            description="AWS EC2 sunucularini listele",
            category="cloud",
        )
    )
    registry.register(
        SkillEntry(
            command="/cloud-ec2-baslat",
            handler=cloud_start_ec2,
            description="AWS EC2 sunucusunu baslat",
            category="cloud",
            requires_args=True,
            min_args=1,
        )
    )
    registry.register(
        SkillEntry(
            command="/cloud-ec2-durdur",
            handler=cloud_stop_ec2,
            description="AWS EC2 sunucusunu durdur",
            category="cloud",
            requires_args=True,
            min_args=1,
        )
    )
    registry.register(
        SkillEntry(
            command="/cloud-s3-liste",
            handler=cloud_list_s3,
            description="AWS S3 bucket listesini getir",
            category="cloud",
        )
    )
    registry.register(
        SkillEntry(
            command="/cloud-maliyet",
            handler=cloud_cost_summary,
            description="Aylik cloud maliyetini ozetle",
            category="cloud",
        )
    )
    registry.register(
        SkillEntry(
            command="/ec2-izle",
            handler=lambda args, ctx: get_instance_metrics(args.strip()),
            description="EC2 instance CPU ve network metrikleri",
            category="cloud",
            requires_args=True,
            min_args=1,
        )
    )
    registry.register(
        SkillEntry(
            command="/ec2-yeniden-baslat",
            handler=lambda args, ctx: reboot_instance(args.strip()),
            description="EC2 instance yeniden baslat",
            category="cloud",
            requires_args=True,
            min_args=1,
        )
    )
    registry.register(
        SkillEntry(
            command="/s3-url",
            handler=lambda args, ctx: _s3_url_handler(args),
            description="S3 objesi icin gecici URL uret",
            category="cloud",
            requires_args=True,
            min_args=2,
        )
    )
    registry.register(
        SkillEntry(
            command="/maliyet-uyari",
            handler=lambda args, ctx: check_cost_alerts(),
            description="Maliyet esik uyarilari",
            category="cloud",
        )
    )
    registry.register(
        SkillEntry(
            command="/cloud-ozet",
            handler=lambda args, ctx: get_cost_summary_text(),
            description="Kisa cloud maliyet ozeti",
            category="cloud",
        )
    )


def _s3_url_handler(args: str) -> dict[str, Any]:
    parts = str(args or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        return {"ok": False, "error": "Kullanim: /s3-url <bucket> <key>"}
    return generate_presigned_url(parts[0], parts[1])
