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


if __name__ == "__main__":
    unittest.main()
