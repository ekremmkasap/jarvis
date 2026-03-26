from __future__ import annotations

from typing import Any

SIGNAL_TOKENS = ('error', 'failed', 'exception', 'traceback', 'panic', 'timeout', 'segmentation', 'assert')


def extract_signal_lines(log_text: str, max_lines: int = 80) -> list[str]:
    lines: list[str] = []
    for line in log_text.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in SIGNAL_TOKENS):
            lines.append(line.strip())
        if len(lines) >= max_lines:
            break
    return lines
