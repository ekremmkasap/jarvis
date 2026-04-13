from __future__ import annotations

from pathlib import Path
import sys


ROOT_PATH = Path(__file__).parent.parent
SERVER_PATH = ROOT_PATH / "server"
BRIDGE_PATH = SERVER_PATH / "bridge.py"

if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))


from skill_registry import SkillRegistry
from skills.registry_entries.ops_entries import register_ops_skills


def _build_registry() -> SkillRegistry:
    registry = SkillRegistry()
    register_ops_skills(
        registry,
        codex_handler=lambda args, ctx: f"codex:{args}:{ctx.get('chat_id')}",
        codex_swarm_handler=lambda args, ctx: f"codex-swarm:{args}:{ctx.get('chat_id')}",
        codex_status_handler=lambda args, ctx: f"codex-durum:{ctx.get('chat_id')}",
        codex_result_handler=lambda args, ctx: f"codex-sonuc:{args}:{ctx.get('chat_id')}",
        wiki_handler=lambda args, ctx: f"wiki:{args}:{ctx.get('chat_id')}",
    )
    return registry


def test_bridge_routes_registry_managed_ops_commands() -> None:
    content = BRIDGE_PATH.read_text(encoding="utf-8", errors="replace")

    assert '"/codex"' in content
    assert '"/codex-swarm"' in content
    assert '"/codex-durum"' in content
    assert '"/codex-sonuc"' in content
    assert '"/wiki"' in content
    assert "COMMAND_REGISTRY.dispatch(command, args" in content


def test_codex_command_dispatch_regression() -> None:
    registry = _build_registry()

    assert registry.dispatch("/codex", "gorev", {"chat_id": 42}) == "codex:gorev:42"


def test_codex_swarm_command_dispatch_regression() -> None:
    registry = _build_registry()

    assert registry.dispatch("/codex-swarm", "dagit", {"chat_id": 42}) == "codex-swarm:dagit:42"


def test_codex_status_command_dispatch_regression() -> None:
    registry = _build_registry()

    assert registry.dispatch("/codex-durum", context={"chat_id": 42}) == "codex-durum:42"
    assert registry.dispatch("/codex-status", context={"chat_id": 42}) == "codex-durum:42"


def test_codex_result_command_dispatch_regression() -> None:
    registry = _build_registry()

    assert registry.dispatch("/codex-sonuc", "job-7", {"chat_id": 42}) == "codex-sonuc:job-7:42"


def test_wiki_command_dispatch_regression() -> None:
    registry = _build_registry()

    assert registry.dispatch("/wiki", "jarvis", {"chat_id": 42}) == "wiki:jarvis:42"
