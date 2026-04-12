from __future__ import annotations

import unittest
from unittest.mock import patch

from server.codex_task_router import CodexTaskRouter, SlotExhaustedError, get_fallback_chain, route_keywords, route_task


class _DummyAccountManager:
    def __init__(self, available: dict[str, bool]) -> None:
        self.available = available

    def is_slot_available(self, slot_id: str) -> bool:
        return bool(self.available.get(slot_id, False))


class CodexTaskRouterTests(unittest.TestCase):
    def test_get_fallback_chain_returns_role_affinity(self) -> None:
        self.assertEqual(get_fallback_chain("backend"), ["forge", "nexus"])
        self.assertEqual(get_fallback_chain("security"), ["shield", "nexus"])
        self.assertEqual(get_fallback_chain("voice"), ["spark", "nexus"])
        self.assertEqual(get_fallback_chain("video"), ["spark", "nexus"])

    def test_route_task_prefers_first_available_affinity_slot(self) -> None:
        with patch("server.codex_task_router.get_account_manager", return_value=_DummyAccountManager({"forge": True, "nexus": True})):
            router = CodexTaskRouter()

        self.assertEqual(router.route_task({"role": "backend", "description": "bridge endpoint"}), "forge")

    def test_route_task_falls_back_to_nexus(self) -> None:
        with patch("server.codex_task_router.get_account_manager", return_value=_DummyAccountManager({"forge": False, "nexus": True})):
            router = CodexTaskRouter()

        self.assertEqual(router.route_task({"role": "backend", "description": "bridge endpoint"}), "nexus")

    def test_route_task_uses_type_when_role_missing(self) -> None:
        with patch("server.codex_task_router.get_account_manager", return_value=_DummyAccountManager({"shield": True, "nexus": True})):
            router = CodexTaskRouter()

        self.assertEqual(router.route_task({"type": "security", "description": "audit"}), "shield")

    def test_route_task_infers_voice_keyword_to_spark(self) -> None:
        with patch("server.codex_task_router.get_account_manager", return_value=_DummyAccountManager({"spark": True, "nexus": True})):
            router = CodexTaskRouter()

        self.assertEqual(router.route_task({"description": "voice stack duzelt"}), "spark")

    def test_route_task_raises_when_nexus_unavailable(self) -> None:
        with patch("server.codex_task_router.get_account_manager", return_value=_DummyAccountManager({"atlas": False, "forge": False, "nexus": False})):
            router = CodexTaskRouter()

        with self.assertRaises(SlotExhaustedError):
            router.route_task({"role": "manager", "description": "plan"})

    def test_module_route_task_wrapper_works(self) -> None:
        with patch("server.codex_task_router.get_account_manager", return_value=_DummyAccountManager({"spark": True, "nexus": True})):
            self.assertEqual(route_task({"role": "video", "description": "render"}), "spark")

    def test_route_keywords_align_with_canonical_slots(self) -> None:
        self.assertEqual(route_keywords("voice stack duzelt"), ["spark"])
        self.assertEqual(route_keywords("guvenlik audit yap"), ["shield"])
        self.assertEqual(route_keywords("overflow kapasite kullan"), ["nexus"])


if __name__ == "__main__":
    unittest.main()
