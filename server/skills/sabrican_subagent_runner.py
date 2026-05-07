"""
Sabrican alt ajan orkestrasyonu.
OpenClaw secondary layer dahil.
Sirali calisir, hata toleransli.
"""

from __future__ import annotations

from typing import Any, Callable

from server.openclaw_bridge import (
    AuthProfileSync,
    ChannelDeliveryOperator,
    GatewayHealthWatcher,
)
from server.skills.sabrican_ops_skill import (
    check_service_health,
    docker_status,
    get_system_status,
)

SubagentHandler = Callable[[dict[str, Any]], dict[str, Any]]


def run_deploy(payload: dict[str, Any]) -> dict[str, Any]:
    docker = docker_status()
    return {
        "ok": bool(docker.get("ok")),
        "status": "ready" if docker.get("ok") else "blocked",
        "docker": docker,
        "payload": dict(payload or {}),
    }


def check_ci(payload: dict[str, Any]) -> dict[str, Any]:
    requested_services = payload.get("services")
    services = requested_services if isinstance(requested_services, list) else [
        "bridge",
        "ollama",
    ]
    checks = [check_service_health(str(service)) for service in services]
    ok = all(bool(item.get("ok")) for item in checks)
    return {
        "ok": ok,
        "status": "ok" if ok else "degraded",
        "checks": checks,
    }


def check_services(payload: dict[str, Any]) -> dict[str, Any]:
    service_name = str(payload.get("service_name") or payload.get("service") or "").strip()
    if service_name and service_name.lower() != "system":
        return check_service_health(service_name, url=payload.get("url"))

    system_status = get_system_status()
    system_status["status"] = (
        "ok"
        if all(bool(item.get("ok")) for item in system_status.get("services", []))
        else "degraded"
    )
    return system_status


SUBAGENT_REGISTRY: dict[str, SubagentHandler] = {
    "deploy_runner": run_deploy,
    "ci_monitor": check_ci,
    "service_watcher": check_services,
    "gateway_health_watcher": lambda payload: GatewayHealthWatcher().check(),
    "channel_delivery_operator": lambda payload: ChannelDeliveryOperator().deliver(
        str(payload.get("channel") or ""),
        payload.get("payload", payload),
    ),
    "auth_profile_sync": lambda payload: AuthProfileSync().sync(
        str(payload.get("profile_id") or "")
    ),
}


def _coerce_task(task: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(task, str):
        return task.strip(), {}
    if isinstance(task, dict):
        task_type = str(task.get("type") or task.get("task") or task.get("name") or "").strip()
        payload = task.get("payload")
        return task_type, dict(payload) if isinstance(payload, dict) else {}
    raise TypeError("task_definition_must_be_string_or_mapping")


def run_subagent_chain(task_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sirali calistir, hata toleransli."""
    results: list[dict[str, Any]] = []
    for task in task_list or []:
        task_type = ""
        try:
            task_type, payload = _coerce_task(task)
            if not task_type:
                raise ValueError("missing_task_type")
            fn = SUBAGENT_REGISTRY.get(task_type)
            if fn is None:
                raise ValueError("unknown_agent")
            result = fn(payload)
            results.append({"task": task_type, "status": "done", "result": result})
        except Exception as exc:
            error = str(exc)
            results.append(
                {
                    "task": task_type or str(task),
                    "status": "failed",
                    "error": error,
                    "result": {"error": error},
                }
            )
    return results
