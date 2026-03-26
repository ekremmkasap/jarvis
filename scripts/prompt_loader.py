from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return '{' + key + '}'


def _stringify(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def load_prompt_template(path: str | Path) -> str:
    prompt_path = Path(path)
    return prompt_path.read_text(encoding='utf-8-sig')


def render_prompt(template: str, values: Mapping[str, Any]) -> str:
    payload = SafeDict({key: _stringify(value) for key, value in values.items()})
    return template.format_map(payload)

