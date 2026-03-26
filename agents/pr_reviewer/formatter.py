from __future__ import annotations

from typing import Any


def render_review(data: dict[str, Any]) -> str:
    summary = data.get('file_summary', {})
    lines = [
        '## Summary',
        '',
        f"- {summary.get('total_files', 0)} files changed, +{summary.get('total_additions', 0)} / -{summary.get('total_deletions', 0)} lines.",
        '',
        '## Findings',
        '',
    ]
    high_risk = summary.get('high_risk', [])
    if high_risk:
        for item in high_risk[:8]:
            lines.append(f"- `{item['filename']}` has {item['changes']} line changes and should get a focused review.")
    else:
        lines.append('- No obvious high-risk files were detected from file stats alone.')

    lines.extend(['', '## Review Focus', ''])
    lines.append('- Confirm tests cover changed behavior in the highest-change files.')
    lines.append('- Verify migrations, auth, config, and deployment paths if touched.')

    lines.extend(['', '## Suggested Next Steps', ''])
    lines.append('- Request targeted review from the owner of the highest-risk files before merge.')
    return '\n'.join(lines)
