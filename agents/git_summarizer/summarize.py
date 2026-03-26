from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from scripts.utils import run_command

FIELD_SEPARATOR = '\x1f'


def collect_recent_commits(repo_path: Path, window: str, max_count: int = 30) -> list[dict[str, Any]]:
    output = run_command(
        [
            'git',
            'log',
            f'--since={window}',
            f'--max-count={max_count}',
            f'--pretty=format:%H{FIELD_SEPARATOR}%an{FIELD_SEPARATOR}%ad{FIELD_SEPARATOR}%s',
            '--date=short',
        ],
        cwd=repo_path,
    )
    if not output:
        return []

    commits: list[dict[str, Any]] = []
    for line in output.splitlines():
        parts = line.split(FIELD_SEPARATOR)
        if len(parts) != 4:
            continue
        commits.append(
            {
                'sha': parts[0],
                'author': parts[1],
                'date': parts[2],
                'subject': parts[3],
            }
        )
    return commits


def build_stats(commits: list[dict[str, Any]]) -> dict[str, Any]:
    author_counts = Counter(commit['author'] for commit in commits)
    return {
        'commit_count': len(commits),
        'author_count': len(author_counts),
        'top_authors': author_counts.most_common(5),
    }
