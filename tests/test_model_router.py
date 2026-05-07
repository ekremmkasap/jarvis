from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import os

from server.model_router import Candidate, ModelRouter, ProviderConfig, RouterSettings, load_router_settings


class FakeRouter(ModelRouter):
    def __init__(self, settings: RouterSettings, outcomes: dict[tuple[str, str], object]):
        super().__init__(settings=settings)
        self.outcomes = outcomes
        self.calls: list[tuple[str, str]] = []

    def _call_provider(self, provider, model, messages, system, max_tokens, num_ctx):  # type: ignore[override]
        self.calls.append((provider.name, model))
        outcome = self.outcomes.get((provider.name, model))
        if isinstance(outcome, Exception):
            raise outcome
        if outcome is None:
            raise RuntimeError("missing outcome")
        return str(outcome)


def _settings_for_test() -> RouterSettings:
    providers = {
        "ollama": ProviderConfig(
            name="ollama",
            kind="ollama",
            base_url="http://127.0.0.1:11434",
            api_key="",
            timeout=10,
        ),
        "openrouter": ProviderConfig(
            name="openrouter",
            kind="openai",
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            timeout=10,
        ),
        "groq": ProviderConfig(
            name="groq",
            kind="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key="test-key",
            timeout=10,
        ),
        "gemini": ProviderConfig(
            name="gemini",
            kind="gemini",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key="test-key",
            timeout=10,
        ),
    }
    chains = {
        "default": [Candidate(provider="openrouter", model="google/gemini-2.0-flash", source="config:default")]
    }
    return RouterSettings(
        enabled=True,
        default_provider="ollama",
        retry_attempts=1,
        backoff_seconds=0.0,
        providers=providers,
        chains=chains,
    )


class ModelRouterTests(unittest.TestCase):
    def test_inspect_model_ref_rejects_deprecated_cloud_alias(self) -> None:
        router = ModelRouter(settings=_settings_for_test())

        inspected = router.inspect_model_ref("minimax-m2.7:cloud")

        self.assertFalse(inspected["valid"])
        self.assertIn(":cloud", inspected["error"])

    def test_inspect_model_ref_requires_explicit_provider_for_namespaced_models(self) -> None:
        router = ModelRouter(settings=_settings_for_test())

        inspected = router.inspect_model_ref("anthropic/claude-sonnet-4.6")

        self.assertFalse(inspected["valid"])
        self.assertIn("provider/model", inspected["error"])

    def test_inspect_model_ref_accepts_provider_separator_syntax(self) -> None:
        router = ModelRouter(settings=_settings_for_test())

        inspected = router.inspect_model_ref("groq::llama-3.3-70b-versatile")

        self.assertTrue(inspected["valid"])
        self.assertTrue(inspected["explicit_provider"])
        self.assertEqual(inspected["provider"], "groq")
        self.assertEqual(inspected["model"], "llama-3.3-70b-versatile")

    def test_build_chain_honors_provider_prefixed_route_models(self) -> None:
        settings = _settings_for_test()
        router = ModelRouter(settings=settings)

        chain = router._build_chain(
            primary_model="groq/llama-3.3-70b-versatile",
            fallback_model="gemini/gemini-2.5-flash",
            route_name=None,
            extra_fallback_models=["ollama/gemma4:e2b"],
        )

        self.assertEqual(chain[0].provider, "groq")
        self.assertEqual(chain[0].model, "llama-3.3-70b-versatile")
        self.assertEqual(chain[1].provider, "gemini")
        self.assertEqual(chain[1].model, "gemini-2.5-flash")
        self.assertEqual(chain[2].provider, "ollama")
        self.assertEqual(chain[2].model, "gemma4:e2b")

    def test_openai_compatible_provider_kinds_use_openai_call_path(self) -> None:
        settings = _settings_for_test()

        class DispatchRouter(ModelRouter):
            def __init__(self, settings: RouterSettings):
                super().__init__(settings=settings)
                self.dispatches: list[tuple[str, str]] = []

            def _call_openai_compatible(self, provider, model, messages, system, max_tokens):  # type: ignore[override]
                self.dispatches.append((provider.kind, model))
                return "openai-compatible"

            def _call_ollama(self, provider, model, messages, system, max_tokens, num_ctx):  # type: ignore[override]
                self.dispatches.append((provider.kind, model))
                return "ollama"

        router = DispatchRouter(settings=settings)

        result = router._call_provider(
            provider=settings.providers["groq"],
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "test"}],
            system=None,
            max_tokens=32,
            num_ctx=1024,
        )
        self.assertEqual(result, "openai-compatible")
        self.assertEqual(router.dispatches[-1], ("groq", "llama-3.3-70b-versatile"))

        result = router._call_provider(
            provider=settings.providers["gemini"],
            model="gemini-2.5-flash",
            messages=[{"role": "user", "content": "test"}],
            system=None,
            max_tokens=32,
            num_ctx=1024,
        )
        self.assertEqual(result, "openai-compatible")
        self.assertEqual(router.dispatches[-1], ("gemini", "gemini-2.5-flash"))

    def test_chat_reports_invalid_model_refs_without_provider_call(self) -> None:
        settings = _settings_for_test()
        settings.chains = {}
        router = FakeRouter(settings=settings, outcomes={})

        response, trace = router.chat(
            route_name=None,
            primary_model="minimax-m2.7:cloud",
            fallback_model=None,
            messages=[{"role": "user", "content": "test"}],
            system=None,
            max_tokens=32,
            num_ctx=1024,
        )

        self.assertIn(":cloud", response)
        self.assertFalse(trace["ok"])
        self.assertEqual(router.calls, [])

    def test_build_health_snapshot_marks_invalid_route_refs_degraded(self) -> None:
        router = ModelRouter(settings=_settings_for_test())

        snapshot = router.build_health_snapshot(
            route_map={
                "chat": {
                    "model": "groq/llama-3.3-70b-versatile",
                    "fallback": "minimax-m2.7:cloud",
                }
            },
            ollama_models=["gemma4:e2b"],
            last_trace={"selected_candidate": "groq/llama-3.3-70b-versatile"},
        )

        self.assertEqual(snapshot["status"], "degraded")
        self.assertEqual(snapshot["providers"]["groq"]["status"], "healthy")
        self.assertEqual(snapshot["routes"]["chat"]["status"], "degraded")
        self.assertTrue(snapshot["routes"]["chat"]["issues"])

    def test_fallback_moves_to_second_provider(self) -> None:
        settings = _settings_for_test()
        router = FakeRouter(
            settings=settings,
            outcomes={
                ("ollama", "primary-model"): RuntimeError("429 rate limit"),
                ("openrouter", "google/gemini-2.0-flash"): "fallback-ok",
            },
        )

        response, trace = router.chat(
            route_name=None,
            primary_model="primary-model",
            fallback_model=None,
            messages=[{"role": "user", "content": "test"}],
            system="system",
            max_tokens=100,
            num_ctx=1024,
        )

        self.assertEqual(response, "fallback-ok")
        self.assertTrue(trace["ok"])
        self.assertTrue(trace["fallback_used"])
        self.assertEqual(trace["selected_provider"], "openrouter")
        self.assertEqual(trace["selected_model"], "google/gemini-2.0-flash")

    def test_missing_api_key_skips_openai_provider(self) -> None:
        settings = _settings_for_test()
        settings.providers["openrouter"] = ProviderConfig(
            name="openrouter",
            kind="openai",
            base_url="https://openrouter.ai/api/v1",
            api_key="",
            timeout=10,
        )
        router = FakeRouter(
            settings=settings,
            outcomes={("ollama", "primary-model"): RuntimeError("offline")},
        )

        response, trace = router.chat(
            route_name="default",
            primary_model="primary-model",
            fallback_model=None,
            messages=[{"role": "user", "content": "test"}],
            system=None,
            max_tokens=50,
            num_ctx=256,
        )

        self.assertTrue(("offline" in response) or ("API key eksik" in response))
        self.assertFalse(trace["ok"])
        self.assertTrue(any("API key eksik" in item.get("error", "") for item in trace["attempts"]))

    def test_load_router_settings_reads_default_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_dir = root / "config"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "model_router.yml").write_text(
                "enabled: true\n"
                "default_provider: ollama\n"
                "chains:\n"
                "  default:\n"
                "    - provider: openrouter\n"
                "      model: google/gemini-2.0-flash\n",
                encoding="utf-8",
            )

            old_cfg = os.environ.get("JARVIS_MODEL_ROUTER_CONFIG")
            old_enabled = os.environ.get("JARVIS_MODEL_ROUTER_ENABLED")
            try:
                os.environ.pop("JARVIS_MODEL_ROUTER_CONFIG", None)
                os.environ.pop("JARVIS_MODEL_ROUTER_ENABLED", None)
                settings = load_router_settings(
                    root_dir=root,
                    default_ollama_url="http://127.0.0.1:11434",
                    request_timeout=120,
                )
            finally:
                if old_cfg is None:
                    os.environ.pop("JARVIS_MODEL_ROUTER_CONFIG", None)
                else:
                    os.environ["JARVIS_MODEL_ROUTER_CONFIG"] = old_cfg
                if old_enabled is None:
                    os.environ.pop("JARVIS_MODEL_ROUTER_ENABLED", None)
                else:
                    os.environ["JARVIS_MODEL_ROUTER_ENABLED"] = old_enabled

            self.assertTrue(settings.enabled)
            self.assertEqual(settings.default_provider, "ollama")
            self.assertIn("default", settings.chains)

    def test_repo_router_config_includes_persona_specific_providers_and_chains(self) -> None:
        root = Path(__file__).resolve().parent.parent
        settings = load_router_settings(
            root_dir=root,
            default_ollama_url="http://127.0.0.1:11434",
            request_timeout=120,
        )

        self.assertIn("gemini_deniz", settings.providers)
        self.assertIn("gemini_zeynep", settings.providers)
        self.assertTrue(settings.providers["gemini_deniz"].optional)
        self.assertTrue(settings.providers["gemini_zeynep"].optional)
        self.assertIn("marketing", settings.chains)
        self.assertIn("data", settings.chains)
        self.assertIn("system", settings.chains)
        self.assertEqual(settings.chains["marketing"][0].provider, "gemini")
        self.assertEqual(settings.chains["data"][0].provider, "gemini")
        self.assertEqual(settings.chains["system"][0].provider, "groq")


if __name__ == "__main__":
    unittest.main()
