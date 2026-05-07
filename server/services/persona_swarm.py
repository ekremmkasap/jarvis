from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable


ALLOWED_EXECUTOR_IDS = (
    "web_search",
    "file_reader",
    "code_analyzer",
    "obsidian_writer",
    "summarizer",
)
DEFAULT_MAX_WORKERS = 4

ExecutorFn = Callable[[dict[str, Any], dict[str, Any]], Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_persona_id(persona_id: str) -> str:
    value = str(persona_id or "").strip().lower()
    if not value:
        raise ValueError("persona_id is required")
    return value


def _build_task_id() -> str:
    return f"pt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"


def allowed_executors_for_persona(persona: dict[str, Any] | None) -> list[str]:
    raw = persona.get("sub_agents") if isinstance(persona, dict) else []
    if not isinstance(raw, list):
        return []

    allowed: list[str] = []
    for item in raw:
        executor_id = str(item or "").strip()
        if executor_id in ALLOWED_EXECUTOR_IDS and executor_id not in allowed:
            allowed.append(executor_id)
    return allowed


def _exec_web_search(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query") or payload.get("goal") or "").strip()
    if not query:
        return {"ok": False, "error": "query_required"}
    try:
        import requests as _req
        resp = _req.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "no_redirect": 1},
            timeout=10,
        )
        data = resp.json()
        answer = (
            data.get("AbstractText")
            or data.get("Answer")
            or "; ".join(r.get("Text", "") for r in data.get("RelatedTopics", [])[:3])
            or "Sonuç bulunamadı."
        )
        return {"ok": True, "result": answer[:2000], "query": query}
    except Exception as e:
        return {"ok": False, "error": str(e), "query": query}


def _exec_file_reader(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    filepath = str(payload.get("path") or "").strip()
    if not filepath:
        return {"ok": False, "error": "path_required"}
    try:
        from pathlib import Path as _Path
        content = _Path(filepath).read_text(encoding="utf-8", errors="ignore")
        return {"ok": True, "result": content[:3000], "path": filepath}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": filepath}


def _exec_code_analyzer(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    code = str(payload.get("code") or payload.get("content") or "").strip()
    filepath = str(payload.get("path") or "").strip()
    if filepath and not code:
        try:
            from pathlib import Path as _Path
            code = _Path(filepath).read_text(encoding="utf-8", errors="ignore")[:5000]
        except Exception:
            pass
    if not code:
        return {"ok": False, "error": "code_or_path_required"}
    lines = code.splitlines()
    result = {
        "line_count": len(lines),
        "function_count": sum(1 for l in lines if l.strip().startswith("def ")),
        "class_count": sum(1 for l in lines if l.strip().startswith("class ")),
        "todo_count": sum(1 for l in lines if "TODO" in l or "FIXME" in l),
        "preview": "\n".join(lines[:20]),
    }
    return {"ok": True, "result": result}


def _exec_obsidian_writer(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    try:
        from server.skills.persona_obsidian_skill import write_persona_note as _write_note
        persona_id = str(context.get("persona_id") or "jarvis")
        title = str(payload.get("title") or "Swarm Notu")
        content = str(payload.get("content") or payload.get("text") or "")
        note = _write_note(persona_id=persona_id, title=title, content=content)
        return {"ok": True, "result": f"Kaydedildi: {note.get('path', '?')}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_summarizer(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text") or payload.get("content") or payload.get("result") or "").strip()
    if not text:
        return {"ok": False, "error": "text_required"}
    max_len = int(payload.get("max_length") or 300)
    summary = text[:max_len]
    last_period = summary.rfind(".")
    if last_period > 50:
        summary = summary[: last_period + 1]
    return {"ok": True, "result": summary}


def default_executor_registry() -> dict[str, ExecutorFn]:
    return {
        "web_search": _exec_web_search,
        "file_reader": _exec_file_reader,
        "code_analyzer": _exec_code_analyzer,
        "obsidian_writer": _exec_obsidian_writer,
        "summarizer": _exec_summarizer,
    }


def build_plan(
    persona_id: str,
    goal: str,
    steps: list[dict[str, Any]],
    *,
    task_id: str | None = None,
    allowed_executors: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    normalized_persona_id = _normalize_persona_id(persona_id)
    clean_goal = str(goal or "").strip()
    if not clean_goal:
        raise ValueError("goal is required")

    allowed = list(allowed_executors or ALLOWED_EXECUTOR_IDS)
    if not allowed:
        allowed = list(ALLOWED_EXECUTOR_IDS)

    plan = {
        "task_id": str(task_id or _build_task_id()),
        "persona_id": normalized_persona_id,
        "goal": clean_goal,
        "created_at": _now_iso(),
        "steps": [],
        "status": "planned",
    }

    for index, raw_step in enumerate(steps or [], start=1):
        step_type = str((raw_step or {}).get("type") or "").strip()
        if step_type not in ALLOWED_EXECUTOR_IDS:
            raise ValueError(f"unsupported executor type: {step_type}")
        if step_type not in allowed:
            raise ValueError(f"executor not allowed for persona: {step_type}")

        payload = (
            raw_step.get("payload") if isinstance(raw_step.get("payload"), dict) else {}
        )
        plan["steps"].append(
            {
                "id": str((raw_step or {}).get("id") or f"step_{index}"),
                "task_id": plan["task_id"],
                "type": step_type,
                "title": str((raw_step or {}).get("title") or f"Step {index}").strip()
                or f"Step {index}",
                "payload": dict(payload),
                "parallel_group": str(
                    (raw_step or {}).get("parallel_group") or ""
                ).strip(),
                "status": "pending",
                "result": None,
                "error": None,
            }
        )
    return plan


def _step_context(plan: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(plan.get("task_id") or ""),
        "persona_id": str(plan.get("persona_id") or ""),
        "goal": str(plan.get("goal") or ""),
        "step_id": str(step.get("id") or ""),
        "step_type": str(step.get("type") or ""),
        "step_title": str(step.get("title") or ""),
    }


def _run_single_step(
    plan: dict[str, Any],
    step: dict[str, Any],
    executor_registry: dict[str, ExecutorFn],
) -> None:
    step["status"] = "running"
    executor = executor_registry.get(str(step.get("type") or ""))
    if not callable(executor):
        step["status"] = "failed"
        step["error"] = f"executor_not_configured:{step.get('type') or 'unknown'}"
        return

    try:
        result = executor(dict(step.get("payload") or {}), _step_context(plan, step))
    except Exception as exc:
        step["status"] = "failed"
        step["error"] = str(exc)[:300]
        return

    if isinstance(result, dict) and result.get("ok") is False:
        step["status"] = "failed"
        step["error"] = str(result.get("error") or "executor_failed")
        step["result"] = result.get("output")
        return

    if isinstance(result, dict) and "output" in result:
        step["result"] = result.get("output")
    else:
        step["result"] = result
    step["status"] = "done"
    step["error"] = None


def _run_parallel_group(
    plan: dict[str, Any],
    steps: list[dict[str, Any]],
    executor_registry: dict[str, ExecutorFn],
    *,
    max_workers: int,
) -> None:
    with ThreadPoolExecutor(
        max_workers=max(1, min(max_workers, len(steps)))
    ) as executor:
        future_map = {
            executor.submit(_run_single_step, plan, step, executor_registry): step
            for step in steps
        }
        for future in as_completed(future_map):
            future.result()


def run_plan(
    plan: dict[str, Any],
    *,
    executors: dict[str, ExecutorFn] | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> dict[str, Any]:
    runtime_plan = deepcopy(plan)
    runtime_plan["status"] = "running"
    executor_registry = default_executor_registry()
    if isinstance(executors, dict):
        executor_registry.update(executors)

    steps = (
        runtime_plan.get("steps") if isinstance(runtime_plan.get("steps"), list) else []
    )
    index = 0
    while index < len(steps):
        current_step = steps[index]
        parallel_group = str(current_step.get("parallel_group") or "").strip()
        if parallel_group:
            grouped_steps = [current_step]
            next_index = index + 1
            while next_index < len(steps):
                candidate = steps[next_index]
                if str(candidate.get("parallel_group") or "").strip() != parallel_group:
                    break
                grouped_steps.append(candidate)
                next_index += 1

            if len(grouped_steps) > 1:
                _run_parallel_group(
                    runtime_plan,
                    grouped_steps,
                    executor_registry,
                    max_workers=max_workers,
                )
                index = next_index
                continue

        _run_single_step(runtime_plan, current_step, executor_registry)
        index += 1

    completed = sum(1 for step in steps if step.get("status") == "done")
    failed = sum(1 for step in steps if step.get("status") == "failed")
    runtime_plan["status"] = "failed" if failed else "done"
    runtime_plan["summary"] = {
        "completed": completed,
        "failed": failed,
        "total": len(steps),
    }
    return runtime_plan


__all__ = [
    "ALLOWED_EXECUTOR_IDS",
    "DEFAULT_MAX_WORKERS",
    "allowed_executors_for_persona",
    "build_plan",
    "default_executor_registry",
    "run_plan",
]
