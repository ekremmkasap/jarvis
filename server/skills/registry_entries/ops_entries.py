from __future__ import annotations

from typing import Callable

from server.skill_registry import SkillEntry, SkillRegistry


def register_ops_skills(
    registry: SkillRegistry,
    *,
    codex_handler: Callable,
    codex_swarm_handler: Callable,
    codex_status_handler: Callable,
    codex_result_handler: Callable,
    wiki_handler: Callable,
):
    registry.register(
        SkillEntry(
            command="/codex",
            handler=codex_handler,
            description="Codex job baslat",
            category="codex",
            requires_args=True,
            min_args=1,
        )
    )
    registry.register(
        SkillEntry(
            command="/codex-swarm",
            handler=codex_swarm_handler,
            description="Coklu Codex slot gorevi baslat",
            category="codex",
            requires_args=True,
            min_args=1,
        )
    )
    registry.register(
        SkillEntry(
            command="/codex-durum",
            handler=codex_status_handler,
            description="Codex kuyruk ve quota ozetini goster",
            category="codex",
            aliases=["/codex-status"],
        )
    )
    registry.register(
        SkillEntry(
            command="/codex-sonuc",
            handler=codex_result_handler,
            description="Tek bir Codex job sonucunu getir",
            category="codex",
            requires_args=True,
            min_args=1,
        )
    )
    registry.register(
        SkillEntry(
            command="/wiki",
            handler=wiki_handler,
            description="Wiki sorgusu veya sayfa olusturma islemi",
            category="knowledge",
        )
    )
