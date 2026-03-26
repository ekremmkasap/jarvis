from __future__ import annotations

from typing import Any


def render_report(data: dict[str, Any]) -> str:
    lines = [
        '## Incident Summary',
        '',
        f"- Workflow `{data.get('workflow_name', 'unknown')}` failed on branch `{data.get('branch', 'unknown')}`.",
        '',
        '## Likely Root Cause',
        '',
        f"- {data.get('heuristic', {}).get('root_cause', 'Unknown')}",
        '',
        '## Evidence',
        '',
    ]
    signal_lines = data.get('signal_lines', [])
    if signal_lines:
        for line in signal_lines[:10]:
            lines.append(f'- `{line}`')
    else:
        lines.append('- No error lines were extracted from the available logs.')

    lines.extend(['', '## Minimal Fix Plan', ''])
    lines.append(f"- {data.get('heuristic', {}).get('fix', 'Review the failing job and reproduce locally.')}")
    return '\n'.join(lines)
