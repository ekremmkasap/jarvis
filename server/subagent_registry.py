"""Sub-agent registry — metadata for every `sub_agent` referenced in agents.yaml.

Read-only registry. Loads `config/subagents.yaml` and cross-checks persona
references from `config/agents.yaml`. Future dispatcher code (Paket D) will
call into this registry to resolve a persona's available helpers.

Schema per entry (config/subagents.yaml):
    subagents:
      <name>:
        description: one-line purpose
        mode: subagent             # enum reserved for future modes
        hidden: true|false
        tools: {read: true, ...}   # whitelisted tool names
        prompt: |
          Multi-line system prompt.

Only read + query + validate. No execution.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

try:  # pragma: no cover - import guard for packaged vs. flat layout
    from server.skills.persona_obsidian_skill import _normalize_persona_id
except ImportError:  # pragma: no cover
    from skills.persona_obsidian_skill import _normalize_persona_id  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBAGENTS_YAML = REPO_ROOT / "config" / "subagents.yaml"
DEFAULT_AGENTS_YAML = REPO_ROOT / "config" / "agents.yaml"

ALLOWED_TOOLS = frozenset({
    "read", "write", "edit", "bash", "skill",
    "web_search", "obsidian", "browser", "llm",
})
ALLOWED_MODES = frozenset({"subagent"})


class SubAgentRegistryError(RuntimeError):
    """Raised when the registry YAML is unreadable or malformed beyond recovery."""


@dataclass(frozen=True)
class SubAgentSpec:
    name: str
    description: str
    mode: str
    hidden: bool
    tools: dict[str, bool] = field(default_factory=dict)
    prompt: str = ""

    def has_tool(self, tool: str) -> bool:
        return bool(self.tools.get(tool, False))

    def allowed_tools(self) -> list[str]:
        return sorted(name for name, allowed in self.tools.items() if allowed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "mode": self.mode,
            "hidden": self.hidden,
            "tools": dict(self.tools),
            "allowed_tools": self.allowed_tools(),
            "prompt": self.prompt,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SubAgentRegistryError(f"yaml not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SubAgentRegistryError(f"yaml parse error in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SubAgentRegistryError(f"yaml root must be a mapping: {path}")
    return data


def _string_list(raw: Any) -> list[str]:
    """Mirrors persona_manager._string_list — cleans yaml string-list values."""
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


def _parse_spec(name: str, raw: Any) -> tuple[SubAgentSpec, list[str]]:
    warnings: list[str] = []
    if not isinstance(raw, dict):
        warnings.append(f"{name}: entry is not a mapping")
        raw = {}

    description = str(raw.get("description") or "").strip()
    if not description:
        warnings.append(f"{name}: description is empty")

    mode = str(raw.get("mode") or "subagent").strip()
    if mode not in ALLOWED_MODES:
        warnings.append(f"{name}: unknown mode '{mode}' (allowed: {sorted(ALLOWED_MODES)})")
        mode = "subagent"

    hidden_raw = raw.get("hidden", False)
    hidden = bool(hidden_raw) if isinstance(hidden_raw, (bool, int)) else False

    tools_raw = raw.get("tools") or {}
    tools: dict[str, bool] = {}
    if isinstance(tools_raw, dict):
        for tool_name, allowed in tools_raw.items():
            tname = str(tool_name).strip()
            if tname not in ALLOWED_TOOLS:
                warnings.append(f"{name}: unknown tool '{tname}' (allowed: {sorted(ALLOWED_TOOLS)})")
                continue
            tools[tname] = bool(allowed)
    else:
        warnings.append(f"{name}: tools must be a mapping, got {type(tools_raw).__name__}")

    prompt = str(raw.get("prompt") or "").strip()
    if not prompt:
        warnings.append(f"{name}: prompt is empty")

    spec = SubAgentSpec(
        name=name,
        description=description,
        mode=mode,
        hidden=hidden,
        tools=tools,
        prompt=prompt,
    )
    return spec, warnings


class SubAgentRegistry:
    """Read-only registry of sub-agent specs."""

    def __init__(
        self,
        *,
        yaml_path: str | Path | None = None,
        agents_yaml: str | Path | None = None,
    ) -> None:
        self._yaml_path = Path(yaml_path) if yaml_path else DEFAULT_SUBAGENTS_YAML
        self._agents_yaml = Path(agents_yaml) if agents_yaml else DEFAULT_AGENTS_YAML
        self._specs: dict[str, SubAgentSpec] = {}
        self._warnings: list[str] = []
        self._persona_refs: dict[str, list[str]] = {}
        self._load()

    # ---------- loading ----------

    def _load(self) -> None:
        data = _load_yaml(self._yaml_path)
        raw_agents = data.get("subagents") or {}
        if not isinstance(raw_agents, dict):
            raise SubAgentRegistryError(
                f"top-level 'subagents:' must be a mapping in {self._yaml_path}"
            )
        for name, entry in raw_agents.items():
            nname = str(name).strip()
            if not nname:
                self._warnings.append("encountered empty sub-agent name — skipped")
                continue
            spec, warns = _parse_spec(nname, entry)
            self._specs[nname] = spec
            self._warnings.extend(warns)

        # Persona cross-reference (best-effort — missing agents.yaml is fine for tests)
        if self._agents_yaml.exists():
            try:
                agents_data = _load_yaml(self._agents_yaml)
            except SubAgentRegistryError as exc:
                self._warnings.append(f"agents.yaml load failed: {exc}")
                return
            personas = agents_data.get("personas") or {}
            if isinstance(personas, dict):
                for pid, p in personas.items():
                    if not isinstance(p, dict):
                        continue
                    refs = _string_list(p.get("sub_agents"))
                    self._persona_refs[str(pid)] = refs
                    for ref in refs:
                        if ref not in self._specs:
                            self._warnings.append(
                                f"persona '{pid}' references unknown sub_agent '{ref}'"
                            )

    # ---------- query API ----------

    def get(self, name: str) -> SubAgentSpec:
        spec = self._specs.get(name)
        if spec is None:
            raise KeyError(f"sub-agent not registered: {name}")
        return spec

    def try_get(self, name: str) -> SubAgentSpec | None:
        return self._specs.get(name)

    def list_all(self, *, include_hidden: bool = True) -> list[SubAgentSpec]:
        specs = list(self._specs.values())
        if not include_hidden:
            specs = [s for s in specs if not s.hidden]
        return sorted(specs, key=lambda s: s.name)

    def names(self, *, include_hidden: bool = True) -> list[str]:
        return [s.name for s in self.list_all(include_hidden=include_hidden)]

    def for_persona(self, persona_id: str) -> list[SubAgentSpec]:
        try:
            pid = _normalize_persona_id(persona_id)
        except Exception:
            return []
        refs = self._persona_refs.get(pid, [])
        out: list[SubAgentSpec] = []
        for ref in refs:
            spec = self._specs.get(ref)
            if spec is not None:
                out.append(spec)
        return out

    def missing_for_persona(self, persona_id: str) -> list[str]:
        """Refs in agents.yaml that have no subagents.yaml entry."""
        try:
            pid = _normalize_persona_id(persona_id)
        except Exception:
            return []
        refs = self._persona_refs.get(pid, [])
        return [r for r in refs if r not in self._specs]

    def validate(self) -> list[str]:
        """Return accumulated warnings (does not raise)."""
        return list(self._warnings)

    # ---------- introspection ----------

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

    def __iter__(self) -> Iterable[SubAgentSpec]:
        return iter(self._specs.values())


# ---------- module-level helpers ----------

_DEFAULT_REGISTRY: SubAgentRegistry | None = None


def load_registry(*, refresh: bool = False) -> SubAgentRegistry:
    """Memoized default registry. Honors JARVIS_SUBAGENTS_YAML override."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is not None and not refresh:
        return _DEFAULT_REGISTRY
    yaml_override = os.environ.get("JARVIS_SUBAGENTS_YAML")
    agents_override = os.environ.get("JARVIS_AGENTS_YAML")
    _DEFAULT_REGISTRY = SubAgentRegistry(
        yaml_path=yaml_override,
        agents_yaml=agents_override,
    )
    return _DEFAULT_REGISTRY


def reset_registry() -> None:
    """Testing helper — drop the memoized registry."""
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = None


def subagents_for(persona_id: str) -> list[SubAgentSpec]:
    return load_registry().for_persona(persona_id)


def get_subagent(name: str) -> SubAgentSpec | None:
    return load_registry().try_get(name)


__all__ = [
    "ALLOWED_TOOLS",
    "ALLOWED_MODES",
    "SubAgentRegistry",
    "SubAgentRegistryError",
    "SubAgentSpec",
    "get_subagent",
    "load_registry",
    "reset_registry",
    "subagents_for",
]
