from __future__ import annotations

from typing import Any


def render_summary(data: dict[str, Any]) -> str:
    commits = data.get('commits', [])
    stats = data.get('stats', {})
    lines = [
        '## Summary',
        '',
        f"- {stats.get('commit_count', 0)} commits across {stats.get('author_count', 0)} active authors.",
        '',
        '## Activity',
        '',
    ]

    for author, count in stats.get('top_authors', []):
        lines.append(f'- {author}: {count} commits')

    lines.extend(['', '## Risks', ''])
    risky_commits = [commit for commit in commits if any(token in commit['subject'].lower() for token in ('refactor', 'migrate', 'auth', 'deploy', 'config'))]
    if risky_commits:
        for commit in risky_commits[:5]:
            lines.append(f"- {commit['subject']} ({commit['author']})")
    else:
        lines.append('- No obvious high-risk commit subjects were detected in the recent window.')

    lines.extend(['', '## Follow-up', ''])
    if commits:
        lines.append('- Review the most recent infrastructure and auth-related commits before the next release cut.')
    else:
        lines.append('- No recent commits detected for the configured window.')
    return '\n'.join(lines)
