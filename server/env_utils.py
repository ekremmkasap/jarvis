from __future__ import annotations

import os
from pathlib import Path


def get_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_env_files(*args: str | Path, paths: list[str | Path] | None = None) -> None:
    if args:
        paths = list(args)
    """Load .env files into os.environ (does not override existing values)."""
    if paths is None:
        root = Path(__file__).resolve().parents[1]
        paths = [root / ".env", root / ".env.local"]
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if k and k not in os.environ:
                os.environ[k] = v
