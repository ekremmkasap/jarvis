from __future__ import annotations

from pathlib import Path
from typing import Any

HIGH_RISK_SUFFIXES = {'.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.java', '.yml', '.yaml'}


def classify_file(file_data: dict[str, Any]) -> dict[str, Any]:
    filename = file_data.get('filename', '')
    suffix = Path(filename).suffix.lower()
    changes = int(file_data.get('changes', 0))
    risk = 'low'
    if suffix in HIGH_RISK_SUFFIXES or changes >= 250:
        risk = 'high'
    elif changes >= 80:
        risk = 'medium'
    return {
        'filename': filename,
        'status': file_data.get('status', 'modified'),
        'additions': int(file_data.get('additions', 0)),
        'deletions': int(file_data.get('deletions', 0)),
        'changes': changes,
        'risk': risk,
        'patch': '\n'.join((file_data.get('patch') or '').splitlines()[:20]),
    }


def summarize_files(files: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = [classify_file(file_data) for file_data in files]
    return {
        'files': parsed,
        'high_risk': [item for item in parsed if item['risk'] == 'high'],
        'total_files': len(parsed),
        'total_additions': sum(item['additions'] for item in parsed),
        'total_deletions': sum(item['deletions'] for item in parsed),
    }
