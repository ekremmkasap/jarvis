from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.subagent_registry import (
    ALLOWED_MODES,
    ALLOWED_TOOLS,
    SubAgentRegistry,
    SubAgentRegistryError,
    SubAgentSpec,
    get_subagent,
    load_registry,
    reset_registry,
    subagents_for,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_SUBAGENTS_YAML = REPO_ROOT / "config" / "subagents.yaml"
REAL_AGENTS_YAML = REPO_ROOT / "config" / "agents.yaml"


@pytest.fixture(autouse=True)
def _reset_default_registry():
    reset_registry()
    yield
    reset_registry()


@pytest.fixture
def custom_yaml(tmp_path):
    """Build a minimal subagents.yaml + matching agents.yaml for isolated tests."""
    def _build(sub_entries: dict, personas: dict):
        sub_path = tmp_path / "subagents.yaml"
        sub_path.write_text(yaml.safe_dump({"subagents": sub_entries}), encoding="utf-8")
        agents_path = tmp_path / "agents.yaml"
        agents_path.write_text(yaml.safe_dump({"personas": personas}), encoding="utf-8")
        return sub_path, agents_path

    return _build


# ---------- real-file coverage ----------


def test_real_registry_loads_all_sub_agents() -> None:
    reg = SubAgentRegistry()
    names = set(reg.names())
    assert "obsidian_writer" in names
    assert "voc_researcher" in names
    assert "shadowbroker_operator" in names
    # agents.yaml defines 30 unique sub_agents total
    assert len(reg) == 30


def test_real_registry_has_no_validation_warnings() -> None:
    reg = SubAgentRegistry()
    warnings = reg.validate()
    assert warnings == [], f"unexpected warnings: {warnings}"


def test_real_for_persona_sabri_matches_agents_yaml() -> None:
    reg = SubAgentRegistry()
    sabri = [s.name for s in reg.for_persona("sabri")]
    assert sabri == ["voc_researcher", "brand_dna_writer", "ad_prompt_generator", "copywriter", "obsidian_writer"]


def test_real_for_persona_luna_contains_shadowbroker() -> None:
    reg = SubAgentRegistry()
    names = {s.name for s in reg.for_persona("luna")}
    assert "shadowbroker_operator" in names
    assert "vuln_scanner" in names


def test_real_for_persona_unknown_returns_empty() -> None:
    reg = SubAgentRegistry()
    assert reg.for_persona("ghost_persona_999") == []


def test_real_module_level_helpers_work() -> None:
    all_sabri = subagents_for("sabri")
    assert len(all_sabri) == 5
    assert get_subagent("obsidian_writer") is not None
    assert get_subagent("nonexistent_xyz") is None


# ---------- custom fixture coverage ----------


def test_get_raises_on_missing(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {"alpha": {"description": "a", "mode": "subagent", "tools": {"read": True}, "prompt": "go"}},
        {},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    with pytest.raises(KeyError):
        reg.get("beta")
    assert reg.try_get("beta") is None


def test_list_all_respects_hidden_flag(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {
            "visible_one": {
                "description": "v1",
                "mode": "subagent",
                "hidden": False,
                "tools": {"read": True},
                "prompt": "p",
            },
            "hidden_one": {
                "description": "h1",
                "mode": "subagent",
                "hidden": True,
                "tools": {"read": True},
                "prompt": "p",
            },
        },
        {},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    assert [s.name for s in reg.list_all()] == ["hidden_one", "visible_one"]
    assert [s.name for s in reg.list_all(include_hidden=False)] == ["visible_one"]


def test_unknown_tool_produces_warning(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {
            "bad_tools": {
                "description": "x",
                "mode": "subagent",
                "tools": {"read": True, "rootkit": True},
                "prompt": "p",
            }
        },
        {},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    warnings = reg.validate()
    assert any("unknown tool 'rootkit'" in w for w in warnings)
    # valid tool is kept, bad tool dropped
    spec = reg.get("bad_tools")
    assert spec.has_tool("read") is True
    assert "rootkit" not in spec.tools


def test_empty_description_warns(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {
            "silent": {
                "description": "",
                "mode": "subagent",
                "tools": {"read": True},
                "prompt": "p",
            }
        },
        {},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    warnings = reg.validate()
    assert any("description is empty" in w for w in warnings)


def test_empty_prompt_warns(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {
            "mute": {
                "description": "d",
                "mode": "subagent",
                "tools": {"read": True},
                "prompt": "",
            }
        },
        {},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    warnings = reg.validate()
    assert any("prompt is empty" in w for w in warnings)


def test_unknown_mode_warns_and_falls_back(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {
            "weird": {
                "description": "d",
                "mode": "primary",
                "tools": {"read": True},
                "prompt": "p",
            }
        },
        {},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    warnings = reg.validate()
    assert any("unknown mode 'primary'" in w for w in warnings)
    assert reg.get("weird").mode == "subagent"


def test_persona_references_unknown_subagent_warns(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {"alpha": {"description": "a", "mode": "subagent", "tools": {"read": True}, "prompt": "p"}},
        {"sabri": {"sub_agents": ["alpha", "ghost_helper"]}},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    warnings = reg.validate()
    assert any("unknown sub_agent 'ghost_helper'" in w for w in warnings)
    assert reg.missing_for_persona("sabri") == ["ghost_helper"]


def test_for_persona_returns_only_known_specs(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {"alpha": {"description": "a", "mode": "subagent", "tools": {"read": True}, "prompt": "p"}},
        {"sabri": {"sub_agents": ["alpha", "ghost_helper"]}},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    names = [s.name for s in reg.for_persona("sabri")]
    assert names == ["alpha"]  # ghost_helper dropped silently


def test_yaml_not_found_raises(tmp_path) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(SubAgentRegistryError):
        SubAgentRegistry(yaml_path=missing, agents_yaml=None)


def test_custom_yaml_override_via_env(monkeypatch, custom_yaml) -> None:
    sub, agents = custom_yaml(
        {"ovr": {"description": "d", "mode": "subagent", "tools": {"read": True}, "prompt": "p"}},
        {},
    )
    monkeypatch.setenv("JARVIS_SUBAGENTS_YAML", str(sub))
    monkeypatch.setenv("JARVIS_AGENTS_YAML", str(agents))
    reset_registry()
    reg = load_registry()
    assert reg.names() == ["ovr"]
    assert reg.yaml_path == sub


def test_load_registry_is_memoized(monkeypatch, custom_yaml) -> None:
    sub, agents = custom_yaml(
        {"m": {"description": "d", "mode": "subagent", "tools": {"read": True}, "prompt": "p"}},
        {},
    )
    monkeypatch.setenv("JARVIS_SUBAGENTS_YAML", str(sub))
    monkeypatch.setenv("JARVIS_AGENTS_YAML", str(agents))
    r1 = load_registry()
    r2 = load_registry()
    assert r1 is r2
    r3 = load_registry(refresh=True)
    assert r3 is not r1


def test_spec_has_tool_and_allowed_tools(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {
            "mixed": {
                "description": "d",
                "mode": "subagent",
                "tools": {"read": True, "write": False, "bash": True},
                "prompt": "p",
            }
        },
        {},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    spec = reg.get("mixed")
    assert spec.has_tool("read") is True
    assert spec.has_tool("write") is False
    assert spec.has_tool("bash") is True
    assert spec.allowed_tools() == ["bash", "read"]


def test_registry_iteration_and_contains(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {
            "a": {"description": "d", "mode": "subagent", "tools": {"read": True}, "prompt": "p"},
            "b": {"description": "d", "mode": "subagent", "tools": {"read": True}, "prompt": "p"},
        },
        {},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    assert "a" in reg
    assert "missing" not in reg
    assert {s.name for s in reg} == {"a", "b"}


def test_allowed_constants_are_stable() -> None:
    # Guard against accidental loosening of the whitelist.
    assert "bash" in ALLOWED_TOOLS
    assert "obsidian" in ALLOWED_TOOLS
    assert ALLOWED_MODES == frozenset({"subagent"})


def test_persona_id_sanitized_for_traversal(custom_yaml) -> None:
    sub, agents = custom_yaml(
        {"a": {"description": "d", "mode": "subagent", "tools": {"read": True}, "prompt": "p"}},
        {"sabri": {"sub_agents": ["a"]}},
    )
    reg = SubAgentRegistry(yaml_path=sub, agents_yaml=agents)
    # Traversal attempts resolve to empty rather than crash
    assert reg.for_persona("../../etc/passwd") == []
