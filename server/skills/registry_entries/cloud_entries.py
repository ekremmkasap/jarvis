from __future__ import annotations

from server.cloud_command_handlers import (
    cloud_cost_summary,
    cloud_list_ec2,
    cloud_list_s3,
    cloud_start_ec2,
    cloud_status_summary,
    cloud_stop_ec2,
)
from server.skill_registry import SkillEntry, SkillRegistry


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
