"""Skill-surface registry — metadata for every `skill_surfaces` entry in agents.yaml.

Surfaces are domain-level labels (e.g. `instagram`, `ebay_research`, `pentest`)
that a persona declares it covers. This registry normalises each label with a
description, category, optional module path, and optional slash-command trigger.

Read-only, no execution. Pairs with SubAgentRegistry (server/subagent_registry.py).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

try:  # pragma: no cover - import guard
    from server.skills.persona_obsidian_skill import _normalize_persona_id
except ImportError:  # pragma: no cover
    from skills.persona_obsidian_skill import _normalize_persona_id  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SURFACES_YAML = REPO_ROOT / "config" / "skill_surfaces.yaml"
DEFAULT_AGENTS_YAML = REPO_ROOT / "config" / "agents.yaml"

ALLOWED_CATEGORIES = frozenset({
    "content", "social", "video", "research",
    "ecommerce", "security", "compliance", "dev", "ops",
})


class SkillSurfaceRegistryError(RuntimeError):
    """Raised when the registry YAML is unreadable or malformed."""


@dataclass(frozen=True)
class SkillSurfaceSpec:
    name: str
    description: str
    category: str
    module: str | None = None
    command: str | None = None
    hidden: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "module": self.module,
            "command": self.command,
            "hidden": self.hidden,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SkillSurfaceRegistryError(f"yaml not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SkillSurfaceRegistryError(f"yaml parse error in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SkillSurfaceRegistryError(f"yaml root must be a mapping: {path}")
    return data


def _string_list(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, (list, tuple)):
        out: list[str] = []
        for item in raw:
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    return []


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_spec(name: str, raw: Any) -> tuple[SkillSurfaceSpec, list[str]]:
    warnings: list[str] = []
    if not isinstance(raw, dict):
        warnings.append(f"{name}: entry is not a mapping")
        raw = {}

    description = str(raw.get("description") or "").strip()
    if not description:
        warnings.append(f"{name}: description is empty")

    category = str(raw.get("category") or "").strip().lower()
    if not category:
        warnings.append(f"{name}: category is missing")
        category = "ops"
    elif category not in ALLOWED_CATEGORIES:
        warnings.append(
            f"{name}: unknown category '{category}' "
            f"(allowed: {sorted(ALLOWED_CATEGORIES)})"
        )

    hidden_raw = raw.get("hidden", False)
    hidden = bool(hidden_raw) if isinstance(hidden_raw, (bool, int)) else False

    spec = SkillSurfaceSpec(
        name=name,
        description=description,
        category=category,
        module=_opt_str(raw.get("module")),
        command=_opt_str(raw.get("command")),
        hidden=hidden,
    )
    return spec, warnings


class SkillSurfaceRegistry:
    """Read-only registry of skill-surface specs."""

    def __init__(
        self,
        *,
        yaml_path: str | Path | None = None,
        agents_yaml: str | Path | None = None,
    ) -> None:
        self._yaml_path = Path(yaml_path) if yaml_path else DEFAULT_SURFACES_YAML
        self._agents_yaml = Path(agents_yaml) if agents_yaml else DEFAULT_AGENTS_YAML
        self._specs: dict[str, SkillSurfaceSpec] = {}
        self._warnings: list[str] = []
        self._persona_refs: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        data = _load_yaml(self._yaml_path)
        raw_surfaces = data.get("skill_surfaces") or {}
        if not isinstance(raw_surfaces, dict):
            raise SkillSurfaceRegistryError(
                f"top-level 'skill_surfaces:' must be a mapping in {self._yaml_path}"
            )
        for name, entry in raw_surfaces.items():
            nname = str(name).strip()
            if not nname:
                self._warnings.append("encountered empty surface name — skipped")
                continue
            spec, warns = _parse_spec(nname, entry)
            self._specs[nname] = spec
            self._warnings.extend(warns)

        if self._agents_yaml.exists():
            try:
                agents_data = _load_yaml(self._agents_yaml)
            except SkillSurfaceRegistryError as exc:
                self._warnings.append(f"agents.yaml load failed: {exc}")
                return
            personas = agents_data.get("personas") or {}
            if isinstance(personas, dict):
                for pid, p in personas.items():
                    if not isinstance(p, dict):
                        continue
                    refs = _string_list(p.get("skill_surfaces"))
                    self._persona_refs[str(pid)] = refs
                    for ref in refs:
                        if ref not in self._specs:
                            self._warnings.append(
                                f"persona '{pid}' references unknown skill_surface '{ref}'"
                            )

    # ---------- query API ----------

    def get(self, name: str) -> SkillSurfaceSpec:
        spec = self._specs.get(name)
        if spec is None:
            raise KeyError(f"skill surface not registered: {name}")
        return spec

    def try_get(self, name: str) -> SkillSurfaceSpec | None:
        return self._specs.get(name)

    def list_all(self, *, include_hidden: bool = True) -> list[SkillSurfaceSpec]:
        specs = list(self._specs.values())
        if not include_hidden:
            specs = [s for s in specs if not s.hidden]
        return sorted(specs, key=lambda s: s.name)

    def names(self, *, include_hidden: bool = True) -> list[str]:
        return [s.name for s in self.list_all(include_hidden=include_hidden)]

    def by_category(self, category: str) -> list[SkillSurfaceSpec]:
        key = str(category or "").strip().lower()
        return sorted(
            (s for s in self._specs.values() if s.category == key),
            key=lambda s: s.name,
        )

    def for_persona(self, persona_id: str) -> list[SkillSurfaceSpec]:
        try:
            pid = _normalize_persona_id(persona_id)
        except Exception:
            return []
        refs = self._persona_refs.get(pid, [])
        out: list[SkillSurfaceSpec] = []
        for ref in refs:
            spec = self._specs.get(ref)
            if spec is not None:
                out.append(spec)
        return out

    def missing_for_persona(self, persona_id: str) -> list[str]:
        try:
            pid = _normalize_persona_id(persona_id)
        except Exception:
            return []
        refs = self._persona_refs.get(pid, [])
        return [r for r in refs if r not in self._specs]

    def validate(self) -> list[str]:
        return list(self._warnings)

    @property
    def yaml_path(self) -> Path:
        return self._yaml_path

    @property
    def agents_yaml_path(self) -> Path:
        return self._agents_yaml

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._specs

    def __iter__(self) -> Iterable[SkillSurfaceSpec]:
        return iter(self._specs.values())


# ---------- module-level helpers ----------

_DEFAULT_SURFACE_REGISTRY: SkillSurfaceRegistry | None = None


def load_surface_registry(*, refresh: bool = False) -> SkillSurfaceRegistry:
    global _DEFAULT_SURFACE_REGISTRY
    if _DEFAULT_SURFACE_REGISTRY is not None and not refresh:
        return _DEFAULT_SURFACE_REGISTRY
    yaml_override = os.environ.get("JARVIS_SURFACES_YAML")
    agents_override = os.environ.get("JARVIS_AGENTS_YAML")
    _DEFAULT_SURFACE_REGISTRY = SkillSurfaceRegistry(
        yaml_path=yaml_override,
        agents_yaml=agents_override,
    )
    return _DEFAULT_SURFACE_REGISTRY


def reset_surface_registry() -> None:
    global _DEFAULT_SURFACE_REGISTRY
    _DEFAULT_SURFACE_REGISTRY = None


def surfaces_for(persona_id: str) -> list[SkillSurfaceSpec]:
    return load_surface_registry().for_persona(persona_id)


def get_surface(name: str) -> SkillSurfaceSpec | None:
    return load_surface_registry().try_get(name)


__all__ = [
    "ALLOWED_CATEGORIES",
    "SkillSurfaceRegistry",
    "SkillSurfaceRegistryError",
    "SkillSurfaceSpec",
    "get_surface",
    "load_surface_registry",
    "reset_surface_registry",
    "surfaces_for",
]
