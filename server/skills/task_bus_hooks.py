from __future__ import annotations

from typing import Any


def emit_task_bus_event(
    event_name: str,
    payload: dict[str, Any],
    *,
    to_agent: str = "mission_control",
    from_agent: str = "video_workspace",
    task_type: str = "intelligence_event",
    policy_check: bool = False,
) -> dict[str, Any]:
    """
    Best-effort task_bus event hook.
    Never raises; caller flow must remain unaffected.
    """
    try:
        import task_bus
    except Exception as exc:
        return {"ok": False, "reason": f"task_bus_import_failed: {str(exc)[:120]}"}

    post_task = getattr(task_bus, "post_task", None)
    if not callable(post_task):
        return {"ok": False, "reason": "task_bus_post_task_missing"}

    event_payload = dict(payload or {})
    event_payload.setdefault("event_name", str(event_name or "event"))
    event_payload.setdefault("source", "video_workspace")
    event_payload.setdefault("task", str(event_payload.get("task") or event_payload.get("summary") or event_name or "event"))

    try:
        ok, result = post_task(
            str(from_agent or "video_workspace"),
            str(to_agent or "mission_control"),
            str(task_type or "intelligence_event"),
            event_payload,
            bool(policy_check),
        )
        return {"ok": bool(ok), "task_id": str(result) if ok else "", "reason": "" if ok else str(result)}
    except Exception as exc:
        return {"ok": False, "reason": f"task_bus_post_failed: {str(exc)[:120]}"}
