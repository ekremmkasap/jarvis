"""Sub-agent dispatcher — execution layer on top of SubAgentRegistry.

Given (persona_id, agent_name, task), this module:
  1. Resolves the persona's llm_profile from config/agents.yaml.
  2. Resolves the sub-agent's spec (description, prompt, tools) from subagents.yaml.
  3. Ensures the persona is actually allowed to call this sub-agent.
  4. Composes a system prompt and calls an injectable LLM callable.
  5. Optionally persists the result to the persona's JARVIS-Brain.

The LLM callable is dependency-injected so tests can stub it without touching
real providers. The default implementation lazily imports ModelRouter.

No bridge.py / master_launcher.py edits. Pure read + compute + optional write.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

try:  # pragma: no cover - import guard
    from server.subagent_registry import (
        SubAgentRegistry,
        SubAgentSpec,
        load_registry,
    )
except ImportError:  # pragma: no cover
    from subagent_registry import (  # type: ignore[no-redef]
        SubAgentRegistry,
        SubAgentSpec,
        load_registry,
    )

logger = logging.getLogger(__name__)

# Response shape: (output_text, trace_dict)
LLMCallable = Callable[[dict[str, Any]], tuple[str, dict[str, Any]]]

# Persona-loader signature
PersonaLoader = Callable[[], dict[str, dict[str, Any]]]


class DispatcherError(RuntimeError):
    """Base dispatcher error."""


class PersonaNotFoundError(DispatcherError):
    """Persona is not defined in agents.yaml."""


class SubAgentNotAllowedError(DispatcherError):
    """Sub-agent exists but is not listed under this persona's `sub_agents`."""


@dataclass(frozen=True)
class DispatchResult:
    persona_id: str
    agent_name: str
    task: str
    ok: bool
    output: str = ""
    error: str | None = None
    model: str = ""
    provider: str = ""
    duration_ms: int = 0
    memory_file: str | None = None
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "agent_name": self.agent_name,
            "task": self.task,
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
            "model": self.model,
            "provider": self.provider,
            "duration_ms": self.duration_ms,
            "memory_file": self.memory_file,
            "trace": dict(self.trace),
        }


def _compose_system_prompt(persona: dict[str, Any], spec: SubAgentSpec) -> str:
    """Glue persona identity + sub-agent role into a single system prompt."""
    parts: list[str] = []
    name = persona.get("name") or persona.get("persona_id", "").title()
    role = persona.get("role") or ""
    parts.append(f"Sen {name} personasının '{spec.name}' alt-ajanısın.")
    if role:
        parts.append(f"Parent persona rolü: {role}.")
    parts.append(f"Alt-ajan görevi: {spec.description}")
    allowed = spec.allowed_tools()
    if allowed:
        parts.append(f"Kullanabileceğin araçlar: {', '.join(allowed)}.")
    parts.append("Aşağıdaki talimatlara sadık kal:")
    parts.append(spec.prompt)
    return "\n\n".join(p for p in parts if p)


def _default_persona_loader() -> dict[str, dict[str, Any]]:
    from server.persona_manager import load_personas  # lazy import
    return load_personas()


def _default_llm_callable(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Real implementation — calls the project's ModelRouter."""
    from server.model_router import build_model_router  # lazy
    router = build_model_router()
    llm_profile = payload.get("llm_profile") or {}
    messages = payload["messages"]
    system = payload["system"]
    primary = llm_profile.get("model") or "gpt-4o-mini"
    fallback = llm_profile.get("fallback_model")
    route = llm_profile.get("model_chain")
    text, trace = router.chat(
        route_name=route,
        primary_model=primary,
        fallback_model=fallback,
        extra_fallback_models=None,
        messages=messages,
        system=system,
        max_tokens=payload.get("max_tokens", 1024),
        num_ctx=payload.get("num_ctx", 4096),
    )
    return text, trace


class SubAgentDispatcher:
    """Dispatch a task to a named sub-agent bound to a persona."""

    def __init__(
        self,
        *,
        registry: SubAgentRegistry | None = None,
        llm: LLMCallable | None = None,
        persona_loader: PersonaLoader | None = None,
    ) -> None:
        self._registry = registry or load_registry()
        self._llm = llm or _default_llm_callable
        self._persona_loader = persona_loader or _default_persona_loader

    # ---------- introspection ----------

    def available(self, persona_id: str) -> list[str]:
        return [s.name for s in self._registry.for_persona(persona_id)]

    def _resolve_persona(self, persona_id: str) -> dict[str, Any]:
        personas = self._persona_loader()
        if persona_id not in personas:
            raise PersonaNotFoundError(f"persona not defined: {persona_id}")
        return personas[persona_id]

    def _ensure_allowed(self, persona_id: str, agent_name: str) -> SubAgentSpec:
        allowed = {s.name for s in self._registry.for_persona(persona_id)}
        if agent_name not in allowed:
            raise SubAgentNotAllowedError(
                f"persona '{persona_id}' is not authorized to call sub-agent "
                f"'{agent_name}'. Allowed: {sorted(allowed) or '(none)'}"
            )
        spec = self._registry.try_get(agent_name)
        if spec is None:  # shouldn't happen — for_persona filters — defensive
            raise DispatcherError(f"sub-agent spec missing: {agent_name}")
        return spec

    # ---------- dispatch ----------

    def dispatch(
        self,
        persona_id: str,
        agent_name: str,
        task: str,
        *,
        context: dict[str, Any] | None = None,
        persist_to_brain: bool = False,
        max_tokens: int = 1024,
    ) -> DispatchResult:
        task_text = (task or "").strip()
        if not task_text:
            return DispatchResult(
                persona_id=persona_id,
                agent_name=agent_name,
                task=task or "",
                ok=False,
                error="task is empty",
            )

        try:
            persona = self._resolve_persona(persona_id)
            spec = self._ensure_allowed(persona_id, agent_name)
        except DispatcherError as exc:
            return DispatchResult(
                persona_id=persona_id,
                agent_name=agent_name,
                task=task_text,
                ok=False,
                error=str(exc),
            )

        system = _compose_system_prompt(persona, spec)
        user_content = task_text
        if context:
            bullets = "\n".join(f"- {k}: {v}" for k, v in context.items())
            user_content = f"{task_text}\n\nEk bağlam:\n{bullets}"

        payload = {
            "persona": persona,
            "spec": spec,
            "llm_profile": persona.get("llm_profile") or {},
            "system": system,
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": max_tokens,
        }

        started = time.monotonic()
        try:
            output, trace = self._llm(payload)
        except Exception as exc:  # LLM failure surfaces as a result, not a throw
            logger.exception("sub-agent dispatch failed: %s/%s", persona_id, agent_name)
            return DispatchResult(
                persona_id=persona_id,
                agent_name=agent_name,
                task=task_text,
                ok=False,
                error=f"llm_error: {exc}",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        duration_ms = int((time.monotonic() - started) * 1000)

        trace = dict(trace or {})
        ok = bool(trace.get("ok", bool(output)))
        model = str(trace.get("selected_model") or "")
        provider = str(trace.get("selected_provider") or "")

        memory_file: str | None = None
        if ok and persist_to_brain:
            memory_file = self._persist_to_brain(persona_id, spec, task_text, output)

        return DispatchResult(
            persona_id=persona_id,
            agent_name=agent_name,
            task=task_text,
            ok=ok,
            output=output,
            error=None if ok else str(trace.get("error") or "unknown_error"),
            model=model,
            provider=provider,
            duration_ms=duration_ms,
            memory_file=memory_file,
            trace=trace,
        )

    # ---------- brain persistence ----------

    def _persist_to_brain(
        self,
        persona_id: str,
        spec: SubAgentSpec,
        task: str,
        output: str,
    ) -> str | None:
        try:
            from server.persona_brain import PersonaBrain  # lazy
            brain = PersonaBrain(persona_id)
            body = f"**Task**: {task}\n\n{output}"
            path = brain.write_memory(
                topic=f"[{spec.name}] {task[:80]}",
                content=body,
                channel=f"subagent:{spec.name}",
            )
            return str(path)
        except Exception as exc:
            logger.warning("persist_to_brain failed for %s/%s: %s", persona_id, spec.name, exc)
            return None


# ---------- module-level convenience ----------


_DEFAULT_DISPATCHER: SubAgentDispatcher | None = None


def get_dispatcher() -> SubAgentDispatcher:
    global _DEFAULT_DISPATCHER
    if _DEFAULT_DISPATCHER is None:
        _DEFAULT_DISPATCHER = SubAgentDispatcher()
    return _DEFAULT_DISPATCHER


def reset_dispatcher() -> None:
    global _DEFAULT_DISPATCHER
    _DEFAULT_DISPATCHER = None


def dispatch(
    persona_id: str,
    agent_name: str,
    task: str,
    **kwargs: Any,
) -> DispatchResult:
    return get_dispatcher().dispatch(persona_id, agent_name, task, **kwargs)


__all__ = [
    "DispatcherError",
    "DispatchResult",
    "LLMCallable",
    "PersonaLoader",
    "PersonaNotFoundError",
    "SubAgentDispatcher",
    "SubAgentNotAllowedError",
    "dispatch",
    "get_dispatcher",
    "reset_dispatcher",
]
