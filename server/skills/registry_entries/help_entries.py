from __future__ import annotations

from server.help_command_handlers import registry_help
from server.skill_registry import SkillEntry, SkillRegistry


def register_help_skill(registry: SkillRegistry):
    registry.register(
        SkillEntry(
            command="/yardim",
            handler=registry_help,
            description="Kategorilere gore komut listesini goster",
            category="system",
        )
    )
