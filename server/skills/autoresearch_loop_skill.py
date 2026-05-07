"""Autoresearch loop — iteratif research, max 3 iterasyon, timeout-aware."""
from __future__ import annotations

import time
from typing import Any


def _try_fetch(topic: str, iteration: int) -> str:
    try:
        from skills.mert_research_skill import run_mert_research  # type: ignore
    except Exception:
        try:
            from server.skills.mert_research_skill import run_mert_research  # type: ignore
        except Exception:
            run_mert_research = None  # type: ignore

    if callable(run_mert_research):
        try:
            query = f"{topic} (iter {iteration})"
            out = run_mert_research(query)  # type: ignore[misc]
            if out:
                return str(out)
        except Exception as e:
            return f"(iter {iteration} fetch error: {e})"
    return f"(iter {iteration}) research backend unavailable — topic={topic}"


def run_autoresearch_loop(
    topic: str,
    max_iterations: int = 3,
    timeout: float = 120.0,
    context: dict[str, Any] | None = None,
) -> str:
    context = context or {}
    started = time.time()
    results: list[str] = []
    for i in range(1, max_iterations + 1):
        elapsed = time.time() - started
        if elapsed >= timeout:
            results.append(f"[timeout {elapsed:.1f}s — iter {i} atlandı]")
            break
        remaining = timeout - elapsed
        if remaining < 1.0:
            break
        chunk = _try_fetch(topic, i)
        results.append(f"--- iter {i} ({elapsed:.1f}s) ---\n{chunk}")
    header = f"AUTORESEARCH LOOP — topic={topic!r} iters={len(results)} elapsed={time.time()-started:.1f}s"
    return header + "\n" + "\n\n".join(results)
