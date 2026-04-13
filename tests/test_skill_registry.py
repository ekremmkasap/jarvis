from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import sys


SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))


from skill_registry import SkillEntry, SkillRegistry
from skills.registry_entries.cloud_entries import register_cloud_skills


def test_register_and_dispatch_work() -> None:
    registry = SkillRegistry()
    registry.register(
        SkillEntry(
            command="/test",
            handler=lambda args, ctx: f"ok:{args}:{ctx.get('source')}",
            description="test komutu",
            category="test",
        )
    )

    result = registry.dispatch("/test", "merhaba", {"source": "unit"})

    assert result == "ok:merhaba:unit"


def test_unknown_command_returns_turkish_error() -> None:
    registry = SkillRegistry()

    result = registry.dispatch("/missing")

    assert result == "Bilinmeyen komut: /missing"


def test_alias_routing_works() -> None:
    registry = SkillRegistry()
    registry.register(
        SkillEntry(
            command="/yardim",
            handler=lambda args, ctx: "yardim",
            description="yardim",
            aliases=["/help"],
            category="system",
        )
    )

    assert registry.dispatch("/help") == "yardim"


def test_exception_returns_turkish_error_string() -> None:
    registry = SkillRegistry()
    registry.register(
        SkillEntry(
            command="/boom",
            handler=lambda args, ctx: (_ for _ in ()).throw(RuntimeError("patladi")),
            description="boom",
        )
    )

    result = registry.dispatch("/boom")

    assert result == "Hata (/boom): patladi"


def test_list_commands_filters_by_category() -> None:
    registry = SkillRegistry()
    registry.register(SkillEntry(command="/cloud", handler=lambda args, ctx: "cloud", description="cloud", category="cloud"))
    registry.register(
        SkillEntry(
            command="/yardim",
            handler=lambda args, ctx: "yardim",
            description="yardim",
            aliases=["/help"],
            category="system",
        )
    )

    commands = registry.list_commands(category="system")

    assert [entry.command for entry in commands] == ["/yardim"]


def test_ec2_izle_registered() -> None:
    registry = SkillRegistry()
    register_cloud_skills(registry)

    commands = [entry.command for entry in registry.list_commands(category="cloud")]

    assert "/ec2-izle" in commands


def test_s3_url_handler_missing_args_returns_error() -> None:
    registry = SkillRegistry()
    register_cloud_skills(registry)

    result = registry.dispatch("/s3-url", "alpha-bucket")

    assert "Kullanim: /s3-url <bucket> <key>" in result


def test_cloud_ozet_returns_string() -> None:
    registry = SkillRegistry()

    with patch("skills.registry_entries.cloud_entries.get_cost_summary_text", return_value="Bu ay: $12.50"):
        register_cloud_skills(registry)
        result = registry.dispatch("/cloud-ozet")

    assert result == "Bu ay: $12.50"
