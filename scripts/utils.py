from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: str | Path) -> dict[str, Any]:
    payload_path = Path(path)
    if not payload_path.exists():
        return {}
    return json.loads(payload_path.read_text(encoding='utf-8-sig'))


def load_yaml(path: str | Path) -> dict[str, Any]:
    payload_path = Path(path)
    if not payload_path.exists():
        return {}
    data = yaml.safe_load(payload_path.read_text(encoding='utf-8-sig'))
    return data or {}


def run_command(args: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def slugify(value: str) -> str:
    safe = ''.join(ch.lower() if ch.isalnum() else '-' for ch in value)
    while '--' in safe:
        safe = safe.replace('--', '-')
    return safe.strip('-') or 'artifact'


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f'automation.{name}')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.propagate = False
    return logger

