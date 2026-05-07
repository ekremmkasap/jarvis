from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.skill_surface_registry import (
    ALLOWED_CATEGORIES,
    SkillSurfaceRegistry,
    SkillSurfaceRegistryError,
    SkillSurfaceSpec,
    get_surface,
    load_surface_registry,
    reset_surface_registry,
    surfaces_for,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_SURFACES_YAML = REPO_ROOT / "config" / "skill_surfaces.yaml"
REAL_AGENTS_YAML = REPO_ROOT / "config" / "agents.yaml"


@pytest.fixture(autouse=True)
def _reset_default_registry():
    reset_surface_registry()
    yield
    reset_surface_registry()


@pytest.fixture
def custom_yaml(tmp_path):
    """Build a minimal skill_surfaces.yaml + matching agents.yaml for isolated tests."""
    def _build(surface_entries: dict, personas: dict):
        surf_path = tmp_path / "skill_surfaces.yaml"
        surf_path.write_text(
            yaml.safe_dump({"skill_surfaces": surface_entries}),
            encoding="utf-8",
        )
        agents_path = tmp_path / "agents.yaml"
        agents_path.write_text(yaml.safe_dump({"personas": personas}), encoding="utf-8")
        return surf_path, agents_path

    return _build


# ---------- real-file coverage ----------


def test_real_registry_loads_all_surfaces() -> None:
    reg = SkillSurfaceRegistry()
    names = set(reg.names())
    assert "instagram" in names
    assert "ebay_research" in names
    assert "pentest" in names
    assert "autoresearch" in names
    # snapshot count — config/skill_surfaces.yaml defines ~57 entries
    assert len(reg) >= 50


def test_real_registry_has_no_validation_warnings() -> None:
    reg = SkillSurfaceRegistry()
    warnings = reg.validate()
    assert warnings == [], f"unexpected warnings: {warnings}"


def test_real_by_category_returns_expected_groups() -> None:
    reg = SkillSurfaceRegistry()
    social_names = [s.name for s in reg.by_category("social")]
    assert "instagram" in social_names
    sec_names = [s.name for s in reg.by_category("security")]
    assert "pentest" in sec_names
    assert "shadowbroker" in sec_names


def test_real_for_persona_buse_has_social_surfaces() -> None:
    reg = SkillSurfaceRegistry()
    names = {s.name for s in reg.for_persona("buse")}
    # Buse is the social/content persona — should reference at least instagram or sosyal_medya
    assert names  # non-empty
    assert names & {"instagram", "sosyal_medya", "content_factory", "buse_content"}


def test_real_for_persona_unknown_returns_empty() -> None:
    reg = SkillSurfaceRegistry()
    assert reg.for_persona("ghost_persona_999") == []


def test_real_module_level_helpers_work() -> None:
    assert get_surface("instagram") is not None
    assert get_surface("nonexistent_xyz") is None
    # surfaces_for should return a list (possibly empty) for any persona id
    result = surfaces_for("buse")
    assert isinstance(result, list)


# ---------- custom fixture coverage ----------


def test_get_raises_on_missing(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {"alpha": {"description": "a", "category": "ops"}},
        {},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    with pytest.raises(KeyError):
        reg.get("beta")
    assert reg.try_get("beta") is None


def test_list_all_respects_hidden_flag(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {
            "visible_one": {
                "description": "v1",
                "category": "content",
                "hidden": False,
            },
            "hidden_one": {
                "description": "h1",
                "category": "dev",
                "hidden": True,
            },
        },
        {},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    assert [s.name for s in reg.list_all()] == ["hidden_one", "visible_one"]
    assert [s.name for s in reg.list_all(include_hidden=False)] == ["visible_one"]


def test_unknown_category_produces_warning(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {
            "bad_cat": {
                "description": "x",
                "category": "spacecraft",
            }
        },
        {},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    warnings = reg.validate()
    assert any("unknown category 'spacecraft'" in w for w in warnings)
    # spec is still retained with the declared (out-of-whitelist) category
    assert reg.get("bad_cat").category == "spacecraft"


def test_missing_category_falls_back_to_ops(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {
            "no_cat": {
                "description": "x",
            }
        },
        {},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    warnings = reg.validate()
    assert any("category is missing" in w for w in warnings)
    assert reg.get("no_cat").category == "ops"


def test_empty_description_warns(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {
            "silent": {
                "description": "",
                "category": "ops",
            }
        },
        {},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    warnings = reg.validate()
    assert any("description is empty" in w for w in warnings)


def test_persona_references_unknown_surface_warns(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {"alpha": {"description": "a", "category": "research"}},
        {"mert": {"skill_surfaces": ["alpha", "ghost_surface"]}},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    warnings = reg.validate()
    assert any("unknown skill_surface 'ghost_surface'" in w for w in warnings)


def test_for_persona_returns_only_known_specs(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {"alpha": {"description": "a", "category": "research"}},
        {"mert": {"skill_surfaces": ["alpha", "ghost_surface"]}},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    names = [s.name for s in reg.for_persona("mert")]
    assert names == ["alpha"]


def test_yaml_not_found_raises(tmp_path) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(SkillSurfaceRegistryError):
        SkillSurfaceRegistry(yaml_path=missing, agents_yaml=None)


def test_custom_yaml_override_via_env(monkeypatch, custom_yaml) -> None:
    surf, agents = custom_yaml(
        {"ovr": {"description": "d", "category": "ops"}},
        {},
    )
    monkeypatch.setenv("JARVIS_SURFACES_YAML", str(surf))
    monkeypatch.setenv("JARVIS_AGENTS_YAML", str(agents))
    reset_surface_registry()
    reg = load_surface_registry()
    assert reg.names() == ["ovr"]
    assert reg.yaml_path == surf


def test_load_registry_is_memoized(monkeypatch, custom_yaml) -> None:
    surf, agents = custom_yaml(
        {"m": {"description": "d", "category": "ops"}},
        {},
    )
    monkeypatch.setenv("JARVIS_SURFACES_YAML", str(surf))
    monkeypatch.setenv("JARVIS_AGENTS_YAML", str(agents))
    r1 = load_surface_registry()
    r2 = load_surface_registry()
    assert r1 is r2
    r3 = load_surface_registry(refresh=True)
    assert r3 is not r1


def test_spec_exposes_module_and_command(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {
            "insta": {
                "description": "ig",
                "category": "social",
                "module": "server.skills.instagram_skill",
                "command": "/instagram",
            },
            "bare": {
                "description": "bare",
                "category": "ops",
            },
        },
        {},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    insta = reg.get("insta")
    assert insta.module == "server.skills.instagram_skill"
    assert insta.command == "/instagram"
    bare = reg.get("bare")
    assert bare.module is None
    assert bare.command is None


def test_registry_iteration_and_contains(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {
            "a": {"description": "d", "category": "content"},
            "b": {"description": "d", "category": "ops"},
        },
        {},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    assert "a" in reg
    assert "missing" not in reg
    assert {s.name for s in reg} == {"a", "b"}


def test_allowed_categories_are_stable() -> None:
    # Guard against accidental loosening of the category whitelist.
    assert "social" in ALLOWED_CATEGORIES
    assert "security" in ALLOWED_CATEGORIES
    assert "content" in ALLOWED_CATEGORIES
    assert len(ALLOWED_CATEGORIES) == 9


def test_persona_id_sanitized_for_traversal(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {"a": {"description": "d", "category": "ops"}},
        {"sabri": {"skill_surfaces": ["a"]}},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    assert reg.for_persona("../../etc/passwd") == []


def test_by_category_is_sorted_and_filtered(custom_yaml) -> None:
    surf, agents = custom_yaml(
        {
            "zeta": {"description": "z", "category": "research"},
            "alpha": {"description": "a", "category": "research"},
            "mike": {"description": "m", "category": "ops"},
        },
        {},
    )
    reg = SkillSurfaceRegistry(yaml_path=surf, agents_yaml=agents)
    research_names = [s.name for s in reg.by_category("research")]
    assert research_names == ["alpha", "zeta"]
    ops_names = [s.name for s in reg.by_category("ops")]
    assert ops_names == ["mike"]
    assert reg.by_category("no_such_cat") == []
