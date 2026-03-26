from __future__ import annotations

import os
from pathlib import Path

from scripts.utils import ensure_directory


def persist_output(output_root: Path, group: str, slug: str, body: str) -> Path:
    directory = ensure_directory(output_root / group)
    path = directory / f'{slug}.md'
    path.write_text(body.strip() + '\n', encoding='utf-8')
    return path


def append_job_summary(markdown: str) -> None:
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY', '').strip()
    if not summary_path:
        return
    with open(summary_path, 'a', encoding='utf-8') as handle:
        handle.write(markdown.strip() + '\n\n')
