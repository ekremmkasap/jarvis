from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from server.security import persona_capabilities


@pytest.fixture
def reset_cache():
    persona_capabilities._MATRIX_CACHE = None
    yield
    persona_capabilities._MATRIX_CACHE = None


def _write_custom_matrix(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "persona_capabilities": {
                    "default": {
                        "shell.safe": "allow",
                        "shell.full": "require_approval",
                        "pc.low_risk": "allow",
                        "pc.medium_risk": "require_approval",
                        "pc.high_risk": "require_approval",
                        "openclaw.helper": "require_approval",
                        "openclaw.deliver": "require_approval",
                        "operator.high_risk": "require_approval",
                    },
                    "sabri": {
                        "shell.safe": "deny",
                        "shell.full": "deny",
                        "pc.low_risk": "deny",
                        "pc.medium_risk": "deny",
                        "pc.high_risk": "deny",
                        "openclaw.helper": "deny",
                        "openclaw.deliver": "deny",
                        "operator.high_risk": "deny",
                    },
                    "sabrican": {
                        "shell.safe": "allow",
                        "shell.full": "require_approval",
                        "openclaw.helper": "allow",
                        "openclaw.deliver": "require_approval",
                    },
                    "bogus": {"fake.action": "allow", "shell.safe": "zoom"},
                }
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_default_persona_returns_baseline_decision(reset_cache, tmp_path, monkeypatch):
    config_path = tmp_path / "persona_capabilities.yaml"
    _write_custom_matrix(config_path)
    monkeypatch.setattr(persona_capabilities, "CONFIG_PATH", config_path)
    persona_capabilities.reload_matrix()

    assert persona_capabilities.resolve_capability("jarvis", "shell.safe") == "allow"
    assert persona_capabilities.resolve_capability("jarvis", "shell.full") == "require_approval"


def test_unknown_persona_falls_back_to_default(reset_cache, tmp_path, monkeypatch):
    config_path = tmp_path / "persona_capabilities.yaml"
    _write_custom_matrix(config_path)
    monkeypatch.setattr(persona_capabilities, "CONFIG_PATH", config_path)
    persona_capabilities.reload_matrix()

    assert persona_capabilities.resolve_capability("ghost_persona", "pc.low_risk") == "allow"
    assert (
        persona_capabilities.resolve_capability("ghost_persona", "operator.high_risk")
        == "require_approval"
    )


def test_customer_persona_denies_shell_and_pc(reset_cache, tmp_path, monkeypatch):
    config_path = tmp_path / "persona_capabilities.yaml"
    _write_custom_matrix(config_path)
    monkeypatch.setattr(persona_capabilities, "CONFIG_PATH", config_path)
    persona_capabilities.reload_matrix()

    assert persona_capabilities.resolve_capability("sabri", "shell.safe") == "deny"
    assert persona_capabilities.resolve_capability("sabri", "openclaw.deliver") == "deny"


def test_sabrican_inherits_default_for_missing_class(reset_cache, tmp_path, monkeypatch):
    config_path = tmp_path / "persona_capabilities.yaml"
    _write_custom_matrix(config_path)
    monkeypatch.setattr(persona_capabilities, "CONFIG_PATH", config_path)
    persona_capabilities.reload_matrix()

    assert persona_capabilities.resolve_capability("sabrican", "openclaw.helper") == "allow"
    # pc.low_risk missing for sabrican → falls back to default
    assert persona_capabilities.resolve_capability("sabrican", "pc.low_risk") == "allow"


def test_invalid_decision_and_unknown_action_ignored(reset_cache, tmp_path, monkeypatch):
    config_path = tmp_path / "persona_capabilities.yaml"
    _write_custom_matrix(config_path)
    monkeypatch.setattr(persona_capabilities, "CONFIG_PATH", config_path)
    persona_capabilities.reload_matrix()

    # Unknown action class always allowed (safe default, does not gate)
    assert persona_capabilities.resolve_capability("sabri", "imaginary.action") == "allow"
    # "bogus" persona had invalid decision values, falls back to default baseline
    assert persona_capabilities.resolve_capability("bogus", "shell.safe") == "allow"


def test_missing_yaml_returns_bundled_defaults(reset_cache, tmp_path, monkeypatch):
    missing_path = tmp_path / "does_not_exist.yaml"
    monkeypatch.setattr(persona_capabilities, "CONFIG_PATH", missing_path)
    persona_capabilities.reload_matrix()

    matrix = persona_capabilities.load_matrix()
    assert matrix["default"]["shell.safe"] == "allow"
    assert matrix["default"]["openclaw.deliver"] == "require_approval"
    assert matrix["default"]["dreams.snapshot"] == "require_approval"
    assert matrix["default"]["dreams.report"] == "require_approval"


def test_dreams_action_classes_known(reset_cache):
    persona_capabilities.reload_matrix()
    assert persona_capabilities.ACTION_DREAMS_SNAPSHOT in persona_capabilities.KNOWN_ACTION_CLASSES
    assert persona_capabilities.ACTION_DREAMS_REPORT in persona_capabilities.KNOWN_ACTION_CLASSES


def test_canonical_matrix_dreams_capabilities(reset_cache):
    """Canonical config/persona_capabilities.yaml gates dreams.* per persona."""
    persona_capabilities.reload_matrix()

    assert persona_capabilities.resolve_capability("sabrican", "dreams.snapshot") == "allow"
    assert persona_capabilities.resolve_capability("sabrican", "dreams.report") == "allow"

    assert persona_capabilities.resolve_capability("jarvis", "dreams.snapshot") == "allow"
    assert persona_capabilities.resolve_capability("jarvis", "dreams.report") == "allow"

    assert persona_capabilities.resolve_capability("sabri", "dreams.snapshot") == "deny"
    assert persona_capabilities.resolve_capability("buse", "dreams.report") == "deny"
    assert persona_capabilities.resolve_capability("luna", "dreams.snapshot") == "deny"
    assert persona_capabilities.resolve_capability("zeynep", "dreams.report") == "deny"

    assert persona_capabilities.resolve_capability("seda", "dreams.snapshot") == "deny"
    assert persona_capabilities.resolve_capability("seda", "dreams.report") == "require_approval"

    # Unknown persona → default require_approval
    assert (
        persona_capabilities.resolve_capability("ghost", "dreams.snapshot")
        == "require_approval"
    )
