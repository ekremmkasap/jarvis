from __future__ import annotations

from typing import Any


def infer_labels(title: str, body: str, config: dict[str, Any]) -> list[str]:
    text = f'{title}\n{body}'.lower()
    labels = list(config.get('default_labels', []))
    for keyword, mapped_labels in config.get('keyword_labels', {}).items():
        if keyword.lower() in text:
            for label in mapped_labels:
                if label not in labels:
                    labels.append(label)
    return labels


def infer_priority(title: str, body: str, config: dict[str, Any], default_priority: str = 'medium') -> str:
    text = f'{title}\n{body}'.lower()
    priority_keywords = config.get('priority_keywords', {})
    for priority in ('high', 'medium', 'low'):
        for keyword in priority_keywords.get(priority, []):
            if keyword.lower() in text:
                return priority
    return default_priority
