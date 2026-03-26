from __future__ import annotations

import re
from typing import Any

HEURISTICS = [
    {
        'pattern': r'ModuleNotFoundError|No module named',
        'root_cause': 'Missing Python dependency or missing install step',
        'fix': 'Update requirements and ensure the dependency install step runs before tests.',
        'risk': 'medium',
    },
    {
        'pattern': r'npm ERR!|Cannot find module',
        'root_cause': 'Node dependency or build step drift',
        'fix': 'Refresh lockfile alignment and rerun the package install step in CI.',
        'risk': 'medium',
    },
    {
        'pattern': r'AssertionError|expected .* but got',
        'root_cause': 'Behavioral regression or stale test expectation',
        'fix': 'Inspect the failing test and the touched code path; update implementation or expectation deliberately.',
        'risk': 'high',
    },
    {
        'pattern': r'timed out|Timeout',
        'root_cause': 'Test timeout, flaky integration, or slow dependency startup',
        'fix': 'Check service startup timing and isolate flaky or long-running tests.',
        'risk': 'medium',
    },
]


def classify_failure(log_text: str) -> dict[str, Any]:
    for item in HEURISTICS:
        if re.search(item['pattern'], log_text, re.IGNORECASE):
            return item
    return {
        'root_cause': 'No strong heuristic match; manual log review is still needed.',
        'fix': 'Inspect the first failing job and reproduce the failure locally with the same command.',
        'risk': 'unknown',
        'pattern': 'none',
    }
