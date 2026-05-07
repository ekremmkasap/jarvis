from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Callable


ROOT_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT_DIR / "server" / "skills"
SERVICES_DIR = Path(__file__).resolve().parent

for path in (ROOT_DIR, SKILLS_DIR, SERVICES_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from tool_router import route_task
from tool_runtime import (
    format_openhands_status,
    format_opencode_status,
    get_openhands_runtime_status,
    get_opencode_status,
    probe_command,
    start_openhands_runtime,
    start_opencode_serve,
)


_FALLBACKS: dict[str, list[str]] = {
    "openhands": ["codex", "jarvis"],
    "aider": ["codex", "jarvis"],
    "cline": ["aider", "jarvis"],
    "codex": ["aider", "jarvis"],
    "claude": ["jarvis"],
    "mcp": ["jarvis"],
    "jarvis_simulation": ["jarvis"],
    "jarvis": [],
}

_ACCOUNT_BLOCK_STATUSES = {
    "disabled",
    "error",
    "inactive",
    "offline",
    "offline_pending",
    "quota_exceeded",
}

_ACCOUNT_WARN_STATUSES = {
    "limited",
    "pending_login",
    "rate_limited",
    "unknown",
}

_RUNTIME_LAUNCH_HINTS = (
    "baslat",
    "build",
    "calistir",
    "create",
    "duzelt",
    "fix",
    "generate",
    "kur",
    "launch",
    "olustur",
    "refactor",
    "run",
    "setup",
    "start",
    "uret",
    "yap",
)


def _build_result(
    *,
    tool: str,
    label: str,
    ok: bool,
    output: str = "",
    error: str | None = None,
    fallback_used: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "ok": bool(ok),
        "tool": tool,
        "output": str(output or ""),
        "error": str(error or "") or None,
        "fallback_used": bool(fallback_used),
        "details": dict(details or {}),
    }
    payload["details"].setdefault("label", label)
    payload["details"].setdefault("executed", False)
    payload["details"].setdefault("mode", "thin_wrapper")
    return payload


def _extract_first_url(text: str) -> str:
    match = re.search(r"https?://\S+", str(text or ""))
    return match.group(0).rstrip("),.]") if match else ""


def _should_launch_runtime(task: str, context: dict[str, Any]) -> bool:
    if not bool(context.get("allow_side_effects")):
        return False
    text = str(task or "").strip().lower()
    return any(token in text for token in _RUNTIME_LAUNCH_HINTS)


def _load_policy_snapshot(agent_id: str, task_type: str) -> dict[str, Any]:
    snapshot = {
        "available": False,
        "accepted": True,
        "approval_needed": False,
        "reason": "policy_not_checked",
    }
    if not agent_id:
        return snapshot
    try:
        from policy_engine import dispatch_policy_check

        policy = dispatch_policy_check("swarm", agent_id, task_type)
        snapshot.update(policy if isinstance(policy, dict) else {})
        snapshot["available"] = True
        reasons: list[str] = []
        if str(snapshot.get("blocking_reason") or "").strip():
            reasons.append(str(snapshot.get("blocking_reason")).strip())
        warning_reasons = snapshot.get("warning_reasons") or []
        if isinstance(warning_reasons, list):
            reasons.extend(str(item).strip() for item in warning_reasons if str(item).strip())
        if reasons:
            snapshot["reason"] = "; ".join(reasons)
        elif bool(snapshot.get("accepted", True)):
            snapshot["reason"] = "ok"
    except Exception as exc:
        snapshot["reason"] = f"policy_unavailable: {str(exc)[:120]}"
    return snapshot


def _load_account_snapshot(agent_id: str) -> dict[str, Any]:
    snapshot = {
        "available": False,
        "account_id": "",
        "status": "unknown",
        "provider": "-",
        "reason": "no_agent_binding",
    }
    if not agent_id:
        return snapshot
    try:
        from account_monitor import load_account_registry
        from policy_engine import get_agent_manifest

        manifest = get_agent_manifest(agent_id) or {}
        account_id = str(manifest.get("account") or "").strip()
        provider = str(manifest.get("provider") or "-").strip() or "-"
        snapshot["provider"] = provider
        snapshot["account_id"] = account_id
        if not account_id:
            snapshot["reason"] = "manifest_account_missing"
            return snapshot
        registry = load_account_registry()
        accounts = registry.get("accounts") if isinstance(registry, dict) else []
        for item in accounts or []:
            current_id = str((item or {}).get("id") or "").strip()
            if current_id != account_id:
                continue
            status = str((item or {}).get("status") or "unknown").strip().lower() or "unknown"
            snapshot.update(
                {
                    "available": True,
                    "status": status,
                    "provider": str((item or {}).get("provider") or provider or "-").strip() or "-",
                    "remaining_estimate": str((item or {}).get("remaining_estimate") or "-").strip() or "-",
                    "reason": "ok",
                }
            )
            return snapshot
        snapshot["reason"] = "account_not_found"
    except Exception as exc:
        snapshot["reason"] = f"account_unavailable: {str(exc)[:120]}"
    return snapshot


def _build_context(preferred_agent: str, task_type: str, allow_side_effects: bool = False) -> dict[str, Any]:
    return {
        "agent_id": str(preferred_agent or "").strip(),
        "task_type": str(task_type or "summary").strip() or "summary",
        "policy": _load_policy_snapshot(str(preferred_agent or "").strip(), str(task_type or "summary").strip() or "summary"),
        "account": _load_account_snapshot(str(preferred_agent or "").strip()),
        "allow_side_effects": bool(allow_side_effects),
    }


def _account_gate(tool: str, context: dict[str, Any]) -> tuple[bool, str]:
    account = context.get("account") if isinstance(context.get("account"), dict) else {}
    status = str(account.get("status") or "unknown").strip().lower()
    if not account.get("available"):
        return True, str(account.get("reason") or "account_not_bound")
    if status in _ACCOUNT_BLOCK_STATUSES:
        return False, f"account_blocked:{status}"
    if status in _ACCOUNT_WARN_STATUSES and tool in {"claude"}:
        return False, f"account_risky:{status}"
    return True, "ok"


def _run_skill(module_name: str, function_name: str, task_text: str) -> str:
    module = __import__(module_name, fromlist=[function_name])
    fn = getattr(module, function_name)
    return str(fn(task_text))


def _recommended_repos(task: str, primary_tool: str) -> list[dict[str, Any]]:
    try:
        from external_repo_registry import recommend_external_repos
    except Exception:
        try:
            from server.services.external_repo_registry import recommend_external_repos
        except Exception:
            return []
    try:
        return recommend_external_repos(task, primary_tool=primary_tool, limit=3)
    except Exception:
        return []


def call_openhands(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    gate_ok, gate_reason = _account_gate("openhands", context)
    if not gate_ok:
        return _build_result(
            tool="openhands",
            label="OpenHands",
            ok=False,
            error=f"OpenHands account gate blocked: {gate_reason}",
            details={"mode": "gated", "executed": False, "gate_reason": gate_reason},
        )

    status = get_openhands_runtime_status()
    repo_ok = (ROOT_DIR / "external-repos" / "OpenHands").exists()
    if status.get("running"):
        return _build_result(
            tool="openhands",
            label="OpenHands",
            ok=True,
            output=format_openhands_status(status),
            details={
                "mode": "runtime_active",
                "executed": False,
                "repo_ok": repo_ok,
                "docker_ok": bool(status.get("docker_ok")),
                "daemon_available": bool(status.get("daemon_available")),
                "ui_url": status.get("url"),
            },
        )

    if _should_launch_runtime(task, context):
        launched = start_openhands_runtime()
        if launched.get("running"):
            return _build_result(
                tool="openhands",
                label="OpenHands",
                ok=True,
                output=format_openhands_status(launched),
                details={
                    "mode": "runtime_launch",
                    "executed": True,
                    "repo_ok": repo_ok,
                    "docker_ok": bool(launched.get("docker_ok")),
                    "daemon_available": bool(launched.get("daemon_available")),
                    "ui_url": launched.get("url"),
                    "container_id": launched.get("container_id"),
                },
            )
        return _build_result(
            tool="openhands",
            label="OpenHands",
            ok=False,
            error=str(launched.get("reason") or "OpenHands runtime baslatilamadi."),
            details={
                "mode": "runtime_launch",
                "executed": True,
                "repo_ok": repo_ok,
                "docker_ok": bool(launched.get("docker_ok")),
                "daemon_available": bool(launched.get("daemon_available")),
            },
        )

    output = format_openhands_status(status)
    return _build_result(
        tool="openhands",
        label="OpenHands",
        ok=bool(repo_ok and status.get("docker_ok") and status.get("daemon_available")),
        output=output if status.get("docker_ok") else "",
        error=None if (repo_ok and status.get("docker_ok") and status.get("daemon_available")) else str(status.get("reason") or "OpenHands runtime hazir degil."),
        details={
            "mode": "runtime_ready",
            "executed": False,
            "repo_ok": repo_ok,
            "docker_ok": bool(status.get("docker_ok")),
            "daemon_available": bool(status.get("daemon_available")),
            "ui_url": status.get("url"),
        },
    )


def call_aider(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    gate_ok, gate_reason = _account_gate("aider", context)
    if not gate_ok:
        return _build_result(
            tool="aider",
            label="Aider",
            ok=False,
            error=f"Aider account gate blocked: {gate_reason}",
            details={"mode": "gated", "executed": False, "gate_reason": gate_reason},
        )

    repo_ok = (ROOT_DIR / "external-repos" / "aider").exists()
    probe = probe_command("aider", ["--version"])
    installed = bool(probe.get("ok"))
    version = str(probe.get("message") or "").strip()
    try:
        output = _run_skill("aider_skill", "run_aider", task)
    except Exception as exc:
        return _build_result(
            tool="aider",
            label="Aider",
            ok=False,
            error=f"Aider wrapper failed: {str(exc)[:160]}",
            details={"mode": "thin_wrapper", "executed": False, "repo_ok": repo_ok, "installed": installed},
        )

    return _build_result(
        tool="aider",
        label="Aider",
        ok=bool(installed),
        output=output if installed else "",
        error=None if installed else "Aider CLI bulunamadi.",
        details={
            "mode": "thin_wrapper",
            "executed": False,
            "repo_ok": repo_ok,
            "installed": installed,
            "version": version,
            "command": probe.get("command"),
        },
    )


def call_cline(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    gate_ok, gate_reason = _account_gate("cline", context)
    if not gate_ok:
        return _build_result(
            tool="cline",
            label="Cline",
            ok=False,
            error=f"Cline account gate blocked: {gate_reason}",
            details={"mode": "gated", "executed": False, "gate_reason": gate_reason},
        )

    repo_ok = (ROOT_DIR / "external-repos" / "cline").exists()
    has_pkg = (ROOT_DIR / "external-repos" / "cline" / "package.json").exists()
    try:
        output = _run_skill("cline_skill", "run_cline", task)
    except Exception as exc:
        return _build_result(
            tool="cline",
            label="Cline",
            ok=False,
            error=f"Cline wrapper failed: {str(exc)[:160]}",
            details={"mode": "thin_wrapper", "executed": False, "repo_ok": repo_ok, "has_pkg": has_pkg},
        )

    ok = bool(repo_ok and has_pkg)
    return _build_result(
        tool="cline",
        label="Cline",
        ok=ok,
        output=output if ok else "",
        error=None if ok else "Cline repo/package.json hazir degil.",
        details={
            "mode": "thin_wrapper",
            "executed": False,
            "repo_ok": repo_ok,
            "has_pkg": has_pkg,
        },
    )


def call_codex(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    gate_ok, gate_reason = _account_gate("codex", context)
    if not gate_ok:
        return _build_result(
            tool="codex",
            label="OpenCode / Codex",
            ok=False,
            error=f"Codex account gate blocked: {gate_reason}",
            details={"mode": "gated", "executed": False, "gate_reason": gate_reason},
        )

    status = get_opencode_status()
    if status.get("running"):
        return _build_result(
            tool="codex",
            label="OpenCode / Codex",
            ok=True,
            output=format_opencode_status(status),
            details={
                "mode": "runtime_active",
                "executed": False,
                "cli_ok": bool(status.get("cli_ok")),
                "command": status.get("command"),
                "server_ready": True,
                "port": status.get("port"),
                "url": status.get("url"),
            },
        )

    if _should_launch_runtime(task, context):
        launched = start_opencode_serve()
        if launched.get("running"):
            return _build_result(
                tool="codex",
                label="OpenCode / Codex",
                ok=True,
                output=format_opencode_status(launched),
                details={
                    "mode": "runtime_launch",
                    "executed": True,
                    "cli_ok": bool(launched.get("cli_ok")),
                    "command": launched.get("command"),
                    "server_ready": True,
                    "port": launched.get("port"),
                    "url": launched.get("url"),
                },
            )
        return _build_result(
            tool="codex",
            label="OpenCode / Codex",
            ok=False,
            error=str(launched.get("reason") or "OpenCode runtime baslatilamadi."),
            details={
                "mode": "runtime_launch",
                "executed": True,
                "cli_ok": bool(launched.get("cli_ok")),
                "command": launched.get("command"),
                "server_ready": False,
                "port": launched.get("port"),
            },
        )

    return _build_result(
        tool="codex",
        label="OpenCode / Codex",
        ok=bool(status.get("cli_ok")),
        output=format_opencode_status(status) if status.get("cli_ok") else "",
        error=None if status.get("cli_ok") else "OpenCode CLI ve local serve runtime bulunamadi.",
        details={
            "mode": "runtime_ready",
            "executed": False,
            "cli_ok": bool(status.get("cli_ok")),
            "cli_info": status.get("version"),
            "command": status.get("command"),
            "server_ready": bool(status.get("running")),
            "port": status.get("port"),
            "url": status.get("url"),
        },
    )


def call_claude(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    gate_ok, gate_reason = _account_gate("claude", context)
    if not gate_ok:
        return _build_result(
            tool="claude",
            label="Claude",
            ok=False,
            error=f"Claude account gate blocked: {gate_reason}",
            details={"mode": "gated", "executed": False, "gate_reason": gate_reason},
        )

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    provider = "anthropic" if anthropic_key else "openrouter" if openrouter_key else "none"
    ok = bool(anthropic_key or openrouter_key)
    output = ""
    if ok:
        output = (
            "Claude adapter hazir. Derin analiz/review gorevleri cloud route ile kosulabilir.\n"
            f"Provider: {provider}"
        )
    return _build_result(
        tool="claude",
        label="Claude",
        ok=ok,
        output=output,
        error=None if ok else "Claude icin ANTHROPIC_API_KEY veya OPENROUTER_API_KEY gerekli.",
        details={
            "mode": "thin_wrapper",
            "executed": False,
            "provider": provider,
        },
    )


def call_mcp(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    url = _extract_first_url(task)
    try:
        from youtube_unified_skill import get_transcript, list_backends

        backend_report = list_backends()
        if url and ("youtube.com" in url or "youtu.be" in url):
            transcript = get_transcript(url)
            ok = not transcript.startswith(("X", "x", "!", "❌"))
            return _build_result(
                tool="mcp",
                label="MCP / Ingestion",
                ok=ok,
                output=transcript if ok else "",
                error=None if ok else transcript,
                details={
                    "mode": "skill_exec",
                    "executed": True,
                    "source_url": url,
                    "backend_report": backend_report[:240],
                },
            )
        return _build_result(
            tool="mcp",
            label="MCP / Ingestion",
            ok=True,
            output=(
                "MCP / transcript backend hazir. Gorev dis veri toplama gerektiriyor; "
                "somut URL veya query ile ingestion katmani calistirilabilir.\n\n"
                + backend_report
            ),
            details={
                "mode": "thin_wrapper",
                "executed": False,
                "source_url": url,
            },
        )
    except Exception as exc:
        return _build_result(
            tool="mcp",
            label="MCP / Ingestion",
            ok=False,
            error=f"MCP ingestion hazir degil: {str(exc)[:160]}",
            details={"mode": "thin_wrapper", "executed": False, "source_url": url},
        )


def call_jarvis_simulation(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return _build_result(
        tool="jarvis_simulation",
        label="Jarvis Simulation",
        ok=False,
        error="Jarvis Simulation adapter henuz wire edilmedi.",
        details={"mode": "stub", "executed": False},
    )


def call_jarvis(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    return _build_result(
        tool="jarvis",
        label="Jarvis",
        ok=True,
        output="Jarvis native fallback hazir. Gorev task_bus uzerinden canonical agente aktarilacak.",
        details={
            "mode": "native",
            "executed": False,
            "agent_id": str(context.get("agent_id") or "").strip(),
            "task_type": str(context.get("task_type") or "").strip(),
        },
    )


_ADAPTERS: dict[str, Callable[[str, dict[str, Any] | None], dict[str, Any]]] = {
    "openhands": call_openhands,
    "aider": call_aider,
    "cline": call_cline,
    "codex": call_codex,
    "claude": call_claude,
    "mcp": call_mcp,
    "jarvis_simulation": call_jarvis_simulation,
    "jarvis": call_jarvis,
}


def execute_via_tool_router(
    task: str,
    preferred_agent: str = "",
    task_type: str = "summary",
    allow_side_effects: bool = False,
) -> dict[str, Any]:
    task_text = str(task or "").strip()
    decision = route_task(task_text)
    primary_tool = str(decision.get("tool") or "jarvis").strip() or "jarvis"
    context = _build_context(preferred_agent, task_type, allow_side_effects=allow_side_effects)
    attempts: list[dict[str, Any]] = []

    chain = [primary_tool]
    for fallback in _FALLBACKS.get(primary_tool, []):
        if fallback not in chain:
            chain.append(fallback)

    final_failure: dict[str, Any] | None = None
    for index, tool_name in enumerate(chain):
        adapter = _ADAPTERS.get(tool_name, call_jarvis)
        result = adapter(task_text, context=context)
        attempt = {
            "tool": tool_name,
            "ok": bool(result.get("ok")),
            "error": result.get("error"),
            "mode": (result.get("details") or {}).get("mode"),
            "executed": bool((result.get("details") or {}).get("executed")),
        }
        attempts.append(attempt)

        if result.get("ok"):
            result["fallback_used"] = index > 0
            details = result.get("details") if isinstance(result.get("details"), dict) else {}
            details["recommended_repos"] = _recommended_repos(task_text, primary_tool)
            details["primary_tool"] = primary_tool
            details["routing_reason"] = str(decision.get("reason") or "").strip()
            details["confidence"] = str(decision.get("confidence") or "").strip()
            details["attempts"] = attempts
            details["policy"] = context.get("policy")
            details["account"] = context.get("account")
            if index > 0:
                details["fallback_from"] = primary_tool
            result["details"] = details
            return result
        final_failure = result

    details = dict((final_failure or {}).get("details") or {})
    details["recommended_repos"] = _recommended_repos(task_text, primary_tool)
    details["primary_tool"] = primary_tool
    details["routing_reason"] = str(decision.get("reason") or "").strip()
    details["confidence"] = str(decision.get("confidence") or "").strip()
    details["attempts"] = attempts
    details["policy"] = context.get("policy")
    details["account"] = context.get("account")
    return _build_result(
        tool=primary_tool,
        label=str(decision.get("label") or "Jarvis").strip() or "Jarvis",
        ok=False,
        error=(final_failure or {}).get("error") or "Tool execution adapter bir sonuc uretemedi.",
        fallback_used=len(attempts) > 1,
        details=details,
    )


def build_tool_execution_report(
    task: str,
    preferred_agent: str = "",
    task_type: str = "summary",
) -> str:
    result = execute_via_tool_router(
        task,
        preferred_agent=preferred_agent,
        task_type=task_type,
        allow_side_effects=False,
    )
    details = result.get("details") if isinstance(result.get("details"), dict) else {}
    lines = [
        "TOOL EXECUTION",
        f"Hedef: {str(task or '')[:120]}",
        f"Secilen tool: {details.get('label', result.get('tool', '-'))} ({result.get('tool', '-')})",
        f"Durum: {'ok' if result.get('ok') else 'error'}",
        f"Fallback: {'yes' if result.get('fallback_used') else 'no'}",
        f"Mode: {details.get('mode', '-')}",
        f"Gerekce: {details.get('routing_reason', '-')}",
    ]
    if result.get("error"):
        lines.append(f"Hata: {result['error']}")
    if result.get("output"):
        lines.append("")
        lines.append(str(result["output"])[:600])
    recommended_repos = details.get("recommended_repos") if isinstance(details.get("recommended_repos"), list) else []
    if recommended_repos:
        lines.append("")
        lines.append("Repo onerileri:")
        for entry in recommended_repos[:3]:
            lines.append(
                f"- {entry.get('label', '-')} [{entry.get('status', '-')}] -> {entry.get('path', '-')}"
            )
    return "\n".join(lines)
