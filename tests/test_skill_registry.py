from __future__ import annotations

from pathlib import Path
import sys


SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))


from skill_registry import SkillEntry, SkillRegistry


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
