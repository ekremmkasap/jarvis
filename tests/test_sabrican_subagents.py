"""Sabrican subagent ve OpenClaw layer testleri."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from server.openclaw_bridge import (
    AuthProfileSync,
    ChannelDeliveryOperator,
    GatewayHealthWatcher,
)
from server.skills.sabrican_subagent_runner import (
    SUBAGENT_REGISTRY,
    run_subagent_chain,
)


def test_gateway_health_watcher_returns_status() -> None:
    watcher = GatewayHealthWatcher()
    snapshot = {
        "status": "healthy",
        "command": "openclaw.cmd",
        "resolved_command": "C:\\tools\\openclaw.cmd",
        "capabilities": {
            "gateway_health": {
                "ok": True,
                "detail": "command-ready",
            }
        },
    }

    with patch(
        "server.openclaw_bridge.build_openclaw_health_snapshot",
        return_value=snapshot,
    ):
        with patch(
            "server.openclaw_bridge.time.perf_counter",
            side_effect=[10.0, 10.012],
        ):
            result = watcher.check()

    assert watcher.helper_only is True
    assert result["status"] in ("ok", "degraded", "down")
    assert result["latency_ms"] == 12


def test_sabrican_subagent_chain_tolerates_failure() -> None:
    with patch.dict(
        SUBAGENT_REGISTRY,
        {
            "service_watcher": lambda payload: {
                "ok": True,
                "service": "bridge",
                "payload": payload,
            }
        },
        clear=False,
    ):
        results = run_subagent_chain(
            [
                {"type": "service_watcher", "payload": {}},
                {"type": "unknown_agent", "payload": {}},
            ]
        )

    assert any(item["status"] == "done" for item in results)
    assert any(item["status"] == "failed" for item in results)
    assert results[1]["task"] == "unknown_agent"
    assert "unknown_agent" in results[1]["error"]


def test_openclaw_is_helper_only() -> None:
    config = yaml.safe_load(Path("config/agents.yaml").read_text(encoding="utf-8"))
    sabrican = config["personas"]["sabrican"]
    openclaw = next(
        runtime
        for runtime in sabrican.get("secondary_runtimes", [])
        if runtime.get("id") == "openclaw"
    )
    octogent = next(
        runtime
        for runtime in sabrican.get("secondary_runtimes", [])
        if runtime.get("id") == "octogent"
    )

    assert openclaw["canonical_runtime"] is False
    assert openclaw["mode"] == "helper_only"
    assert set(openclaw.get("sub_agents", [])) >= {
        "gateway_health_watcher",
        "channel_delivery_operator",
        "auth_profile_sync",
    }
    assert octogent["canonical_runtime"] is False
    assert octogent["mode"] == "helper_only"
    assert set(octogent.get("sub_agents", [])) >= {
        "tentacle_orchestrator",
        "terminal_supervisor",
        "todo_swarm_manager",
    }
    assert GatewayHealthWatcher.helper_only is True
    assert ChannelDeliveryOperator.helper_only is True
    assert AuthProfileSync.helper_only is True
