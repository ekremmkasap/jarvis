#!/usr/bin/env python3
"""
OpenClaw <-> Jarvis bridge helpers.

This module is not the canonical runtime. It provides optional helper calls for
Telegram delivery and agent dispatch when OpenClaw is available locally.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

from server.security.policy_gate import (
    evaluate_channel_delivery,
    evaluate_openclaw_task,
    format_policy_block_message,
)

JARVIS_CHAT_ID = os.environ.get("JARVIS_ALLOWED_CHAT_IDS", "").split(",")[0].strip()
OPENCLAW_PROFILE = os.environ.get("OPENCLAW_PROFILE", "").strip()
_WINDOWS_OPENCLAW_CLI = Path(os.environ.get("APPDATA", "")) / "npm" / "openclaw.cmd"
OPENCLAW_COMMAND = os.environ.get(
    "OPENCLAW_COMMAND",
    str(_WINDOWS_OPENCLAW_CLI) if os.name == "nt" and _WINDOWS_OPENCLAW_CLI.is_file() else "openclaw.cmd" if os.name == "nt" else "openclaw",
).strip()
OPENCLAW_OWNER_PERSONA = "sabrican"
OPENCLAW_SUB_AGENTS = (
    "openclaw_integrator",
    "gateway_health_watcher",
    "channel_delivery_operator",
    "auth_profile_sync",
)
OPENCLAW_SKILL_SURFACES = (
    "gateway_health",
    "channel_delivery",
    "auth_profile_sync",
    "wrapper_control",
)
OPENCLAW_CODEX_SUBAGENTS = (
    "devops-engineer",
    "deployment-engineer",
    "sre-engineer",
    "llm-architect",
)
OPENCLAW_DREAM_PHASES = ("light", "rem", "deep")


def _profile_name() -> str:
    return OPENCLAW_PROFILE or "main"


def _openclaw_home_path(*parts: str) -> Path:
    return Path.home() / ".openclaw" / Path(*parts)


def _profile_state_path(profile_name: str | None = None) -> Path:
    return _openclaw_home_path("agents", profile_name or _profile_name())


def normalize_dream_phase(phase: str | None = None) -> str:
    normalized = str(phase or "rem").strip().lower()
    if normalized in OPENCLAW_DREAM_PHASES:
        return normalized
    return "rem"


def get_dream_report_path(
    phase: str = "rem",
    date_key: str | None = None,
) -> Path:
    report_date = str(date_key or datetime.now().strftime("%Y-%m-%d")).strip()
    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%d")
    return _openclaw_home_path(
        "workspace",
        "memory",
        "dreaming",
        normalize_dream_phase(phase),
        f"{report_date}.md",
    )


def read_dream_report(
    phase: str = "rem",
    date_key: str | None = None,
) -> dict[str, Any]:
    normalized_phase = normalize_dream_phase(phase)
    report_path = get_dream_report_path(normalized_phase, date_key)
    content = ""
    if report_path.exists():
        content = report_path.read_text(encoding="utf-8")
    return {
        "phase": normalized_phase,
        "date": report_path.stem,
        "path": str(report_path),
        "exists": report_path.exists(),
        "content": content,
    }


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _load_openclaw_runtime_snapshot(profile_name: str) -> dict[str, Any]:
    config_path = _openclaw_home_path("openclaw.json")
    auth_path = _profile_state_path(profile_name) / "agent" / "auth-profiles.json"
    config = _read_json_file(config_path)
    auth_state = _read_json_file(auth_path)

    model_defaults = (
        config.get("agents", {})
        .get("defaults", {})
        .get("model", {})
    )
    primary_model = str(model_defaults.get("primary") or "").strip()
    fallback_models = [
        str(item).strip()
        for item in model_defaults.get("fallbacks", [])
        if str(item).strip()
    ]

    providers: list[dict[str, Any]] = []
    for profile_id, payload in (auth_state.get("profiles") or {}).items():
        if not isinstance(payload, dict):
            continue
        provider = str(payload.get("provider") or "").strip() or str(profile_id)
        mode = str(payload.get("mode") or payload.get("type") or "").strip() or "unknown"
        providers.append(
            {
                "id": str(profile_id),
                "provider": provider,
                "mode": mode,
                "has_api_key": bool(payload.get("api_key")),
                "has_access_token": bool(payload.get("access")),
            }
        )

    warnings: list[str] = []
    if not providers:
        warnings.append("auth-profiles-empty")
    if any(item["mode"] == "api_key" for item in providers):
        warnings.append("api-key-profile-present")
    if any(model.startswith("openai/") for model in [primary_model, *fallback_models] if model):
        warnings.append("openai-model-in-chain")

    return {
        "config_path": str(config_path),
        "auth_path": str(auth_path),
        "primary_model": primary_model or None,
        "fallback_models": fallback_models,
        "providers": providers,
        "warnings": warnings,
    }


def _resolve_openclaw_command() -> str:
    resolved = shutil.which(OPENCLAW_COMMAND)
    if resolved:
        return resolved
    raw_path = Path(OPENCLAW_COMMAND)
    if raw_path.is_file():
        return str(raw_path)
    return ""


def describe_openclaw_helper_runtime() -> dict[str, Any]:
    return {
        "id": "openclaw",
        "owner_persona": OPENCLAW_OWNER_PERSONA,
        "mode": "helper_only",
        "canonical_runtime": False,
        "bridge_module": "server.openclaw_bridge",
        "profile": _profile_name(),
        "sub_agents": list(OPENCLAW_SUB_AGENTS),
        "skill_surfaces": list(OPENCLAW_SKILL_SURFACES),
        "codex_subagents": list(OPENCLAW_CODEX_SUBAGENTS),
    }


def build_openclaw_health_snapshot() -> dict[str, Any]:
    descriptor = describe_openclaw_helper_runtime()
    resolved_command = _resolve_openclaw_command()
    profile_name = str(descriptor["profile"])
    profile_path = _profile_state_path(profile_name)
    auth_path = profile_path / "agent" / "auth-profiles.json"
    runtime_snapshot = _load_openclaw_runtime_snapshot(profile_name)
    wrapper_ok = (
        OPENCLAW_COMMAND.lower().endswith(".cmd") if os.name == "nt" else True
    )

    capabilities = {
        "gateway_health": {
            "ok": bool(resolved_command),
            "detail": "command-ready" if resolved_command else "command-missing",
        },
        "channel_delivery": {
            "ok": bool(resolved_command and JARVIS_CHAT_ID),
            "detail": (
                "telegram-ready"
                if resolved_command and JARVIS_CHAT_ID
                else "telegram-chat-id-missing"
                if resolved_command
                else "command-missing"
            ),
        },
        "auth_profile_sync": {
            "ok": profile_path.exists() and auth_path.exists(),
            "detail": (
                "auth-profiles-present"
                if auth_path.exists()
                else "profile-present"
                if profile_path.exists()
                else "profile-missing"
            ),
        },
        "wrapper_control": {
            "ok": bool(wrapper_ok and (resolved_command or OPENCLAW_COMMAND)),
            "detail": (
                "windows-cmd-wrapper"
                if os.name == "nt" and wrapper_ok
                else "unix-wrapper"
                if not os.name == "nt"
                else "wrapper-not-cmd"
            ),
        },
    }
    status = "healthy" if all(item["ok"] for item in capabilities.values()) else "degraded"
    return {
        **descriptor,
        "status": status,
        "command": OPENCLAW_COMMAND,
        "resolved_command": resolved_command,
        "chat_id_configured": bool(JARVIS_CHAT_ID),
        "profile_path": str(profile_path),
        "runtime_model": {
            "primary": runtime_snapshot.get("primary_model"),
            "fallbacks": runtime_snapshot.get("fallback_models", []),
        },
        "auth": {
            "path": runtime_snapshot.get("auth_path"),
            "providers": runtime_snapshot.get("providers", []),
            "warnings": runtime_snapshot.get("warnings", []),
        },
        "capabilities": capabilities,
    }


def _profile_args() -> list[str]:
    return [OPENCLAW_PROFILE] if OPENCLAW_PROFILE else []


def _base_command(*parts: str) -> list[str]:
    return [OPENCLAW_COMMAND, *_profile_args(), *parts]


def _run_async_helper(async_fn, *args: Any, **kwargs: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(async_fn(*args, **kwargs))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(async_fn(*args, **kwargs))).result()


async def send_telegram_update(
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> bool:
    """Send a formatted Telegram message via OpenClaw."""
    if not JARVIS_CHAT_ID:
        print("Telegram send skipped: JARVIS_ALLOWED_CHAT_IDS is empty")
        return False

    text = f"*{title}*\n{message}"
    if details:
        for key, value in details.items():
            text += f"\n- {key}: {value}"

    decision = evaluate_channel_delivery(
        "telegram",
        text,
        source="openclaw_bridge.telegram_update",
    )
    if not decision.allowed:
        print(format_policy_block_message(decision))
        return False

    cmd = _base_command(
        "message",
        "send",
        "--channel",
        "telegram",
        "--target",
        JARVIS_CHAT_ID,
        "--message",
        text,
        "--json",
    )

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = json.loads(result.stdout) if result.stdout else {}
        return bool(output.get("payload", {}).get("ok", False))
    except Exception as exc:
        print(f"Telegram send error: {exc}")
        return False


async def run_agent_task(
    task_desc: str,
    deliver: bool = True,
    persona_id: str = "sabrican",
) -> dict[str, Any]:
    """Run an OpenClaw agent task."""
    if not JARVIS_CHAT_ID:
        return {"status": "error", "error": "missing_chat_id"}

    runtime_snapshot = build_openclaw_health_snapshot()
    decision = evaluate_openclaw_task(
        task_desc,
        deliver=deliver,
        source="openclaw_bridge.agent_task",
        runtime_warnings=list(runtime_snapshot.get("auth", {}).get("warnings", [])),
        persona_id=persona_id,
    )
    if not decision.allowed:
        return {
            "status": "blocked",
            "error": "policy_gate",
            "message": format_policy_block_message(decision),
            "approval_id": decision.approval_id,
            "risk": decision.risk,
        }

    cmd = _base_command(
        "agent",
        "--channel",
        "telegram",
        "--to",
        JARVIS_CHAT_ID,
        "--message",
        task_desc,
        "--json",
    )

    if deliver:
        cmd.append("--deliver")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return json.loads(result.stdout) if result.stdout else {"status": "error"}
    except Exception as exc:
        print(f"Agent run error: {exc}")
        return {"status": "error", "error": str(exc)}


class GatewayHealthWatcher:
    """Read-only health probe for the helper-only OpenClaw gateway path."""

    helper_only = True

    def check(self) -> dict[str, Any]:
        started_at = time.perf_counter()
        snapshot = build_openclaw_health_snapshot()
        latency_ms = max(int((time.perf_counter() - started_at) * 1000), 0)
        capability = snapshot.get("capabilities", {}).get("gateway_health", {})
        if capability.get("ok"):
            status = "ok" if snapshot.get("status") == "healthy" else "degraded"
        else:
            status = "down"
        return {
            "status": status,
            "latency_ms": latency_ms,
            "detail": capability.get("detail"),
            "command": snapshot.get("resolved_command") or snapshot.get("command"),
        }


class ChannelDeliveryOperator:
    """Thin adapter for helper-only channel delivery via existing bridge calls."""

    helper_only = True

    def deliver(self, channel: str, payload: Any) -> dict[str, Any]:
        normalized_channel = str(channel or "").strip().lower()
        if normalized_channel != "telegram":
            return {
                "delivered": False,
                "channel": normalized_channel,
                "error": "unsupported_channel",
            }

        title = "Jarvis Update"
        details: dict[str, Any] | None = None
        message = ""
        if isinstance(payload, dict):
            title = str(payload.get("title") or title).strip() or title
            message = str(payload.get("message") or payload.get("text") or "").strip()
            raw_details = payload.get("details")
            if isinstance(raw_details, dict):
                details = raw_details
            if not message:
                extra_payload = {
                    key: value
                    for key, value in payload.items()
                    if key not in {"title", "message", "text", "details"}
                }
                if extra_payload:
                    message = json.dumps(extra_payload, ensure_ascii=False)
        else:
            message = str(payload or "").strip()

        if not message:
            return {
                "delivered": False,
                "channel": normalized_channel,
                "error": "empty_payload",
            }

        delivered = bool(
            _run_async_helper(send_telegram_update, title, message, details)
        )
        return {
            "delivered": delivered,
            "channel": normalized_channel,
            "title": title,
            "message": message,
            "details": details,
        }


class AuthProfileSync:
    """Helper-only profile visibility check for OpenClaw auth state."""

    helper_only = True

    def sync(self, profile_id: str) -> dict[str, Any]:
        requested_profile = str(profile_id or "").strip() or _profile_name()
        runtime = describe_openclaw_helper_runtime()
        profile_path = _profile_state_path(requested_profile)
        detail = "profile-present" if profile_path.exists() else "profile-missing"

        if requested_profile == runtime.get("profile"):
            capability = (
                build_openclaw_health_snapshot()
                .get("capabilities", {})
                .get("auth_profile_sync", {})
            )
            detail = str(capability.get("detail") or detail)

        return {
            "synced": profile_path.exists(),
            "profile_id": requested_profile,
            "active_profile": runtime.get("profile"),
            "profile_path": str(profile_path),
            "detail": detail,
        }


class OpenClawBridge:
    """Optional helper facade around OpenClaw commands."""

    def __init__(self) -> None:
        self.chat_id = JARVIS_CHAT_ID
        self.running = False

    def describe_runtime(self) -> dict[str, Any]:
        return describe_openclaw_helper_runtime()

    def health_snapshot(self) -> dict[str, Any]:
        return build_openclaw_health_snapshot()

    async def start_hourly_reporter(self, report_callback) -> None:
        """Send periodic reports while the helper is active."""
        self.running = True
        hour = 0

        while self.running and hour < 24:
            hour += 1
            report = await report_callback(hour)
            title = f"JARVIS AUTONOMOUS LOOP - Hour {hour}:00"
            details = {
                "Progress": f"{(hour / 24) * 100:.0f}%",
                "Tests": f"{report.get('tests_passed', 0)}/{report.get('tests_total', 0)}",
                "Improvement": f"{report.get('improvement_pct', 0):+.1f}%",
                "Commits": report.get("commits", 0),
                "Trend": report.get("trend", "analyzing"),
            }
            await send_telegram_update(title, "Periodic report", details)
            wait_time = 30 if os.environ.get("TEST_MODE") else 3600
            await asyncio.sleep(wait_time)

    async def dispatch_research(self, goal: str) -> str:
        """Dispatch a short research task."""
        task_desc = f"Do a short research pass: {goal}. Return concise bullet points."
        result = await run_agent_task(task_desc, deliver=False)
        return result.get("result", {}).get("payloads", [{}])[0].get("text", "")

    async def dispatch_code_task(self, design: str) -> str:
        """Dispatch a code-generation task."""
        task_desc = f"Write Python async code for this design. Return code only:\n{design}"
        result = await run_agent_task(task_desc, deliver=False)
        return result.get("result", {}).get("payloads", [{}])[0].get("text", "")

    async def alert(self, severity: str, message: str) -> None:
        """Send a severity-tagged alert."""
        await send_telegram_update(f"{severity.upper()} alert", message)


def run_gateway_health_watcher() -> dict[str, Any]:
    """Module-level wrapper: Sabrican gateway_health_watcher sub-agent."""
    return GatewayHealthWatcher().check()


def run_channel_delivery_operator(channel: str, payload: Any) -> dict[str, Any]:
    """Module-level wrapper: Sabrican channel_delivery_operator sub-agent."""
    return ChannelDeliveryOperator().deliver(channel, payload)


def run_auth_profile_sync(profile_id: str = "") -> dict[str, Any]:
    """Module-level wrapper: Sabrican auth_profile_sync sub-agent."""
    return AuthProfileSync().sync(profile_id)


def run_openclaw_integrator(task: str, deliver: bool = False) -> dict[str, Any]:
    """Module-level wrapper: Sabrican openclaw_integrator sub-agent.

    Dispatches a task to OpenClaw and optionally delivers result to Telegram.
    """
    result = _run_async_helper(run_agent_task, task, deliver)
    if not isinstance(result, dict):
        result = {"status": "error", "error": str(result)}
    return result


async def send_hour_report_to_telegram(hour: int, report_data: dict[str, Any]) -> bool:
    """Bridge helper for hourly report sends."""
    title = f"JARVIS AUTONOMOUS - Hour {hour}"
    details = {
        "Progress": f"{(hour / 24) * 100:.0f}%",
        "Improvement": f"{report_data.get('improvement_pct', 0):+.1f}%",
        "Tests": report_data.get("test_status", "pending"),
        "Commits": report_data.get("commits", 0),
    }
    return await send_telegram_update(title, "Automated report", details)


if __name__ == "__main__":
    bridge = OpenClawBridge()

    async def _test() -> None:
        await send_telegram_update("OpenClaw Bridge Test", "Jarvis + OpenClaw helper path is reachable.")
        print("Testing agent...")
        result = await bridge.dispatch_research("Telegram throughput optimization quick tips")
        print(f"Research result: {result[:100]}...")

    asyncio.run(_test())
