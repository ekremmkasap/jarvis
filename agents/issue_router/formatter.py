from __future__ import annotations

from typing import Any


def render_triage(data: dict[str, Any]) -> str:
    labels = ', '.join(data.get('proposed_labels', [])) or 'none'
    lines = [
        '## Triage Summary',
        '',
        f"- Issue looks most aligned with `{data.get('priority', 'medium')}` priority work.",
        '',
        '## Recommended Labels',
        '',
        f'- {labels}',
        '',
        '## Priority',
        '',
        f"- {data.get('priority', 'medium')}",
        '',
        '## Owner Recommendation',
        '',
        f"- {data.get('owner_mention', 'manual review needed')}",
        '',
        '## Next Action',
        '',
        '- Confirm labels, then route to the recommended owner or queue for manual review.',
    ]
    return '\n'.join(lines)
