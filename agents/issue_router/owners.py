from __future__ import annotations

from typing import Any


def resolve_owner(labels: list[str], config: dict[str, Any]) -> str:
    owner_map = config.get('label_owners', {})
    for label in labels:
        owner = owner_map.get(label)
        if owner:
            return owner
    return config.get('fallback_owner', 'manual review needed')


def resolve_mention(owner: str, config: dict[str, Any]) -> str:
    mention_map = config.get('mention_map', {})
    return mention_map.get(owner, owner)
