from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml


RETRYABLE_HTTP_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
RETRYABLE_ERROR_TOKENS = (
    "timeout",
    "timed out",
    "connection reset",
    "temporarily unavailable",
)
OPENAI_COMPATIBLE_PROVIDER_KINDS = {
    "openai",
    "openai-completions",
    "groq",
    "gemini",
    "glm",
    "cerebras",
}


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    kind: str
    base_url: str
    api_key: str
    timeout: int
    optional: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Candidate:
    provider: str
    model: str
    source: str
    warning: str = ""
    error: str = ""


@dataclass
class RouterSettings:
    enabled: bool
    default_provider: str
    retry_attempts: int
    backoff_seconds: float
    providers: dict[str, ProviderConfig]
    chains: dict[str, list[Candidate]]


def _parse_candidate(step: Any, source: str) -> Candidate | None:
    if isinstance(step, dict):
        provider = str(step.get("provider", "")).strip()
        model = str(step.get("model", "")).strip()
        if provider and model:
            return Candidate(provider=provider, model=model, source=source)
        return None
    if isinstance(step, str):
        raw = step.strip()
        if not raw:
            return None
        if "::" in raw:
            provider, model = raw.split("::", 1)
            provider = provider.strip()
            model = model.strip()
            if provider and model:
                return Candidate(provider=provider, model=model, source=source)
    return None


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}
    if isinstance(content, dict):
        return content
    return {}


def _build_provider(
    name: str,
    raw: dict[str, Any],
    default_ollama_url: str,
    request_timeout: int,
) -> ProviderConfig:
    kind = str(raw.get("kind", "ollama")).strip().lower() or "ollama"
    base_url = str(raw.get("base_url", "")).strip()
    base_url_env = str(raw.get("base_url_env", "")).strip()
    if base_url_env:
        base_url = os.environ.get(base_url_env, base_url).strip()
    if not base_url and kind == "ollama":
        base_url = default_ollama_url

    api_key_env = str(raw.get("api_key_env", "")).strip()
    api_key = str(raw.get("api_key", "")).strip()
    if api_key_env:
        api_key = os.environ.get(api_key_env, api_key).strip()

    timeout = int(raw.get("timeout", request_timeout))
    optional = bool(raw.get("optional", False))
    extra_headers = raw.get("extra_headers", {}) or {}
    normalized_headers = {
        str(key): str(value)
        for key, value in extra_headers.items()
        if str(key).strip() and str(value).strip()
    }
    return ProviderConfig(
        name=name,
        kind=kind,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        timeout=timeout,
        optional=optional,
        extra_headers=normalized_headers,
    )


def load_router_settings(
    root_dir: Path, default_ollama_url: str, request_timeout: int
) -> RouterSettings:
    config_path_raw = os.environ.get(
        "JARVIS_MODEL_ROUTER_CONFIG", "config/model_router.yml"
    ).strip()
    config_path = Path(config_path_raw)
    if not config_path.is_absolute():
        config_path = root_dir / config_path
    config_data = _read_yaml(config_path)

    enabled_default = bool(config_data.get("enabled", True))
    enabled = _as_bool(os.environ.get("JARVIS_MODEL_ROUTER_ENABLED"), enabled_default)
    default_provider = (
        str(config_data.get("default_provider", "ollama")).strip() or "ollama"
    )

    retry_cfg = config_data.get("retry", {}) or {}
    retry_attempts = int(retry_cfg.get("attempts", 2))
    backoff_seconds = float(retry_cfg.get("base_delay_seconds", 1.0))

    providers_raw = config_data.get("providers", {}) or {}
    providers: dict[str, ProviderConfig] = {}

    providers["ollama"] = _build_provider(
        "ollama",
        providers_raw.get("ollama", {}) or {},
        default_ollama_url=default_ollama_url,
        request_timeout=request_timeout,
    )

    for name, raw in providers_raw.items():
        name_str = str(name).strip()
        if not name_str or name_str == "ollama":
            continue
        if not isinstance(raw, dict):
            continue
        providers[name_str] = _build_provider(
            name_str,
            raw,
            default_ollama_url=default_ollama_url,
            request_timeout=request_timeout,
        )

    chains: dict[str, list[Candidate]] = {}
    chains_raw = config_data.get("chains", {}) or {}
    for route_name, steps in chains_raw.items():
        route_key = str(route_name).strip()
        if not route_key or not isinstance(steps, list):
            continue
        parsed_steps: list[Candidate] = []
        for step in steps:
            candidate = _parse_candidate(step, source=f"config:{route_key}")
            if candidate:
                parsed_steps.append(candidate)
        chains[route_key] = parsed_steps

    return RouterSettings(
        enabled=enabled,
        default_provider=default_provider,
        retry_attempts=max(1, retry_attempts),
        backoff_seconds=max(0.0, backoff_seconds),
        providers=providers,
        chains=chains,
    )


class ModelRouter:
    def __init__(self, settings: RouterSettings):
        self.settings = settings

    def inspect_model_ref(self, model_ref: str | None) -> dict[str, Any]:
        raw_ref = str(model_ref or "").strip()
        info: dict[str, Any] = {
            "raw": raw_ref,
            "provider": "",
            "model": "",
            "explicit_provider": False,
            "valid": True,
            "warning": "",
            "error": "",
        }
        if not raw_ref:
            info["valid"] = False
            info["error"] = "Model referansi bos."
            return info

        if raw_ref.endswith(":cloud") or raw_ref.endswith("-cloud"):
            info["valid"] = False
            info["error"] = (
                "Eski ':cloud' model alias'i artik desteklenmiyor. "
                "provider/model formatini kullanin."
            )
            return info

        parsed = _parse_candidate(raw_ref, source="inspect:model_ref")
        if parsed:
            info["provider"] = parsed.provider
            info["model"] = parsed.model
            info["explicit_provider"] = True
            if parsed.provider not in self.settings.providers:
                info["valid"] = False
                info["error"] = f"Provider tanimli degil: {parsed.provider}"
            return info

        if "/" in raw_ref:
            provider_name, model_name = raw_ref.split("/", 1)
            provider_name = provider_name.strip().lower()
            model_name = model_name.strip()
            if provider_name in self.settings.providers and model_name:
                info["provider"] = provider_name
                info["model"] = model_name
                info["explicit_provider"] = True
                return info

            info["valid"] = False
            info["error"] = (
                f"Belirsiz model referansi: {raw_ref}. "
                "Multi-provider modda provider/model veya provider::model kullanin."
            )
            return info

        info["provider"] = self.settings.default_provider
        info["model"] = raw_ref
        return info

    def _candidate_from_model_ref(
        self,
        model_ref: str | None,
        *,
        source: str,
    ) -> Candidate | None:
        inspected = self.inspect_model_ref(model_ref)
        if not inspected["raw"]:
            return None

        return Candidate(
            provider=str(inspected.get("provider", "")),
            model=str(inspected.get("model", "")) or str(inspected["raw"]),
            source=source,
            warning=str(inspected.get("warning", "")),
            error=str(inspected.get("error", "")),
        )

    def _build_chain(
        self,
        primary_model: str,
        fallback_model: str | None,
        route_name: str | None,
        extra_fallback_models: list[str] | None = None,
    ) -> list[Candidate]:
        chain: list[Candidate] = []

        primary_candidate = self._candidate_from_model_ref(
            primary_model,
            source="route:primary",
        )
        if primary_candidate:
            chain.append(primary_candidate)

        fallback_candidate = self._candidate_from_model_ref(
            fallback_model,
            source="route:fallback",
        )
        if fallback_candidate:
            chain.append(fallback_candidate)

        for model_name in extra_fallback_models or []:
            extra_candidate = self._candidate_from_model_ref(
                model_name,
                source="route:extra_fallback",
            )
            if extra_candidate:
                chain.append(extra_candidate)

        for key in (route_name or "", "default"):
            if not key:
                continue
            chain.extend(self.settings.chains.get(key, []))

        dedup: list[Candidate] = []
        seen: set[tuple[str, str]] = set()
        for candidate in chain:
            marker = (candidate.provider, candidate.model)
            if marker in seen:
                continue
            seen.add(marker)
            dedup.append(candidate)
        return dedup

    def _is_retryable(self, status_code: int | None, error_text: str) -> bool:
        if status_code in RETRYABLE_HTTP_CODES:
            return True
        lower = error_text.lower()
        return any(token in lower for token in RETRYABLE_ERROR_TOKENS)

    def _open_json(
        self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers=headers, method="POST")
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read())

    def _call_ollama(
        self,
        provider: ProviderConfig,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None,
        max_tokens: int,
        num_ctx: int,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": max_tokens,
                "num_ctx": num_ctx,
            },
        }
        if system:
            payload["system"] = system

        headers = {"Content-Type": "application/json", **provider.extra_headers}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        result = self._open_json(
            f"{provider.base_url}/api/chat",
            payload,
            headers,
            timeout=provider.timeout,
        )
        content = result.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("Ollama bos yanit dondu.")
        return str(content)

    def _call_openai_compatible(
        self,
        provider: ProviderConfig,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None,
        max_tokens: int,
    ) -> str:
        wire_messages: list[dict[str, str]] = []
        if system:
            wire_messages.append({"role": "system", "content": system})
        for item in messages:
            role = str(item.get("role", "user")).strip().lower()
            if role not in {"system", "user", "assistant", "tool"}:
                role = "user"
            wire_messages.append(
                {"role": role, "content": str(item.get("content", ""))}
            )

        payload = {
            "model": model,
            "messages": wire_messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        headers = {"Content-Type": "application/json", **provider.extra_headers}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        result = self._open_json(
            f"{provider.base_url}/chat/completions",
            payload,
            headers,
            timeout=provider.timeout,
        )
        choices = result.get("choices", [])
        if not choices:
            raise RuntimeError("Provider choices donmedi.")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = [
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            ]
            content = "".join(text_parts)
        if not content:
            raise RuntimeError("Provider bos yanit dondu.")
        return str(content)

    def _call_provider(
        self,
        provider: ProviderConfig,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None,
        max_tokens: int,
        num_ctx: int,
    ) -> str:
        if provider.kind in OPENAI_COMPATIBLE_PROVIDER_KINDS:
            return self._call_openai_compatible(
                provider=provider,
                model=model,
                messages=messages,
                system=system,
                max_tokens=max_tokens,
            )
        if provider.kind == "ollama":
            return self._call_ollama(
                provider=provider,
                model=model,
                messages=messages,
                system=system,
                max_tokens=max_tokens,
                num_ctx=num_ctx,
            )
        raise RuntimeError(f"Unsupported provider kind: {provider.kind}")

    def chat(
        self,
        *,
        route_name: str | None,
        primary_model: str,
        fallback_model: str | None,
        extra_fallback_models: list[str] | None = None,
        messages: list[dict[str, Any]],
        system: str | None,
        max_tokens: int,
        num_ctx: int,
    ) -> tuple[str, dict[str, Any]]:
        if not self.settings.enabled:
            trace = {
                "ok": False,
                "error": "Model router disabled by config.",
                "route": route_name or "",
                "selected_provider": "",
                "selected_model": "",
                "selected_candidate": "",
                "fallback_used": False,
                "attempts": [],
            }
            return trace["error"], trace

        candidates = self._build_chain(
            primary_model,
            fallback_model,
            route_name,
            extra_fallback_models=extra_fallback_models,
        )
        attempts: list[dict[str, Any]] = []

        for index, candidate in enumerate(candidates):
            if candidate.error:
                attempts.append(
                    {
                        "provider": candidate.provider,
                        "model": candidate.model,
                        "ok": False,
                        "retryable": False,
                        "error": candidate.error,
                        "warning": candidate.warning,
                        "source": candidate.source,
                    }
                )
                continue

            provider = self.settings.providers.get(candidate.provider)
            if not provider:
                attempts.append(
                    {
                        "provider": candidate.provider,
                        "model": candidate.model,
                        "ok": False,
                        "retryable": False,
                        "error": "Provider config bulunamadi.",
                    }
                )
                continue
            if provider.kind in OPENAI_COMPATIBLE_PROVIDER_KINDS and not provider.api_key:
                attempts.append(
                    {
                        "provider": candidate.provider,
                        "model": candidate.model,
                        "ok": False,
                        "retryable": False,
                        "error": "API key eksik.",
                    }
                )
                continue
            if not provider.base_url:
                attempts.append(
                    {
                        "provider": candidate.provider,
                        "model": candidate.model,
                        "ok": False,
                        "retryable": False,
                        "error": "Base URL eksik.",
                    }
                )
                continue

            for attempt in range(1, self.settings.retry_attempts + 1):
                try:
                    response = self._call_provider(
                        provider=provider,
                        model=candidate.model,
                        messages=messages,
                        system=system,
                        max_tokens=max_tokens,
                        num_ctx=num_ctx,
                    )
                    attempts.append(
                        {
                            "provider": candidate.provider,
                            "model": candidate.model,
                            "ok": True,
                            "attempt": attempt,
                            "warning": candidate.warning,
                            "source": candidate.source,
                        }
                    )
                    trace = {
                        "ok": True,
                        "error": "",
                        "route": route_name or "",
                        "selected_provider": candidate.provider,
                        "selected_model": candidate.model,
                        "selected_candidate": f"{candidate.provider}/{candidate.model}",
                        "fallback_used": index > 0,
                        "attempts": attempts,
                    }
                    return response, trace
                except HTTPError as exc:
                    status_code = int(getattr(exc, "code", 0))
                    error_body = exc.read().decode("utf-8", errors="ignore")
                    message = f"HTTP {status_code}: {error_body[:300]}"
                    retryable = self._is_retryable(status_code, message)
                except URLError as exc:
                    status_code = None
                    message = f"URL error: {exc.reason}"
                    retryable = self._is_retryable(status_code, message)
                except Exception as exc:  # noqa: BLE001
                    status_code = None
                    message = str(exc)
                    retryable = self._is_retryable(status_code, message)

                attempts.append(
                    {
                        "provider": candidate.provider,
                        "model": candidate.model,
                        "ok": False,
                        "attempt": attempt,
                        "retryable": retryable,
                        "error": message[:300],
                        "warning": candidate.warning,
                        "source": candidate.source,
                    }
                )
                if retryable and attempt < self.settings.retry_attempts:
                    delay = self.settings.backoff_seconds * (2 ** (attempt - 1))
                    if delay > 0:
                        time.sleep(delay)
                    continue
                break

        final_error = "Tum provider/model denemeleri basarisiz."
        if attempts:
            final_error = attempts[-1].get("error", final_error)
        trace = {
            "ok": False,
            "error": final_error,
            "route": route_name or "",
            "selected_provider": "",
            "selected_model": "",
            "selected_candidate": "",
            "fallback_used": len(candidates) > 1,
            "attempts": attempts,
        }
        return final_error, trace

    def build_health_snapshot(
        self,
        *,
        route_map: dict[str, Any] | None = None,
        ollama_models: list[str] | None = None,
        last_trace: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ollama_model_list = [
            str(item).strip() for item in (ollama_models or []) if str(item).strip()
        ]
        providers: dict[str, dict[str, Any]] = {}
        overall_status = "healthy" if self.settings.enabled else "disabled"

        for name, provider in self.settings.providers.items():
            issues: list[str] = []
            status = "healthy"
            label = "configured"

            if not provider.base_url:
                issues.append("base-url-missing")
                status = "degraded"
                label = "base-url-missing"
            elif provider.kind == "ollama":
                if ollama_model_list:
                    label = f"ready ({len(ollama_model_list)} models)"
                else:
                    status = "degraded"
                    label = "no-models"
            elif provider.kind in OPENAI_COMPATIBLE_PROVIDER_KINDS and not provider.api_key:
                issues.append("api-key-missing")
                if provider.optional:
                    label = "optional-api-key-missing"
                else:
                    status = "degraded"
                    label = "api-key-missing"

            providers[name] = {
                "status": status,
                "label": label,
                "kind": provider.kind,
                "base_url": provider.base_url,
                "has_api_key": bool(provider.api_key),
                "optional": bool(provider.optional),
                "issues": issues,
            }
            if status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"

        routes: dict[str, dict[str, Any]] = {}
        for route_name, raw_route in (route_map or {}).items():
            route = raw_route if isinstance(raw_route, dict) else {}
            route_status = "healthy"
            refs: list[dict[str, Any]] = []
            issues: list[str] = []
            raw_refs: list[tuple[str, str]] = []

            primary_ref = str(route.get("model", "")).strip()
            if primary_ref:
                raw_refs.append(("primary", primary_ref))

            fallback_ref = str(route.get("fallback", "")).strip()
            if fallback_ref:
                raw_refs.append(("fallback", fallback_ref))

            second_fallback = route.get("second_fallback")
            if isinstance(second_fallback, str) and second_fallback.strip():
                raw_refs.append(("second_fallback", second_fallback.strip()))
            elif isinstance(second_fallback, list):
                for index, item in enumerate(second_fallback, start=1):
                    item_ref = str(item).strip()
                    if item_ref:
                        raw_refs.append((f"extra_fallback_{index}", item_ref))

            for slot, ref in raw_refs:
                inspected = self.inspect_model_ref(ref)
                provider_name = str(inspected.get("provider", "")).strip()
                provider_status = providers.get(provider_name, {}).get("status", "")
                entry = {
                    "slot": slot,
                    "raw": ref,
                    "provider": provider_name,
                    "model": str(inspected.get("model", "")).strip(),
                    "valid": bool(inspected.get("valid", False)),
                    "warning": str(inspected.get("warning", "")).strip(),
                    "error": str(inspected.get("error", "")).strip(),
                }
                refs.append(entry)

                if not entry["valid"]:
                    route_status = "degraded"
                    if entry["error"]:
                        issues.append(f"{slot}: {entry['error']}")
                    continue

                if provider_status == "degraded":
                    route_status = "degraded"
                    issues.append(f"{slot}: provider degraded ({provider_name})")

            routes[str(route_name)] = {
                "status": route_status,
                "refs": refs,
                "issues": issues,
            }
            if route_status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"

        active = last_trace if isinstance(last_trace, dict) else {}
        return {
            "enabled": self.settings.enabled,
            "status": overall_status,
            "default_provider": self.settings.default_provider,
            "providers": providers,
            "routes": routes,
            "active": active,
        }


def build_model_router(
    root_dir: Path, default_ollama_url: str, request_timeout: int
) -> ModelRouter:
    settings = load_router_settings(
        root_dir=root_dir,
        default_ollama_url=default_ollama_url,
        request_timeout=request_timeout,
    )
    return ModelRouter(settings=settings)
