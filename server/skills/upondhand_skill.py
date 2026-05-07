from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
OPENHANDS_REPO_DIR = ROOT_DIR / "external-repos" / "OpenHands"
OPENHANDS_RUNTIME_DIR = ROOT_DIR / "openhands"
OPENHANDS_WORKSPACE_DIR = OPENHANDS_RUNTIME_DIR / "workspace"
OPENHANDS_CONFIG_PATH = OPENHANDS_RUNTIME_DIR / "config.toml"


def _normalize_args(args: str = "") -> str:
    return str(args or "").strip().lower()


def _relative_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return str(path)


def run_upondhand(args: str = "") -> str:
    normalized = _normalize_args(args)
    lines = [
        "upondhand durum",
        "",
        f"Repo yolu: {'OK' if OPENHANDS_REPO_DIR.exists() else 'MISSING'} `{_relative_path(OPENHANDS_REPO_DIR)}`",
        f"Runtime yolu: {'OK' if OPENHANDS_RUNTIME_DIR.exists() else 'MISSING'} `{_relative_path(OPENHANDS_RUNTIME_DIR)}`",
        f"Workspace: {'OK' if OPENHANDS_WORKSPACE_DIR.exists() else 'MISSING'} `{_relative_path(OPENHANDS_WORKSPACE_DIR)}`",
        f"Config: {'OK' if OPENHANDS_CONFIG_PATH.exists() else 'MISSING'} `{_relative_path(OPENHANDS_CONFIG_PATH)}`",
        "",
        "Not: Gorev calistirmak icin `/openhands [gorev]` kullan.",
    ]

    if normalized not in {"", "durum", "status"}:
        lines.extend(
            [
                "",
                f"Istek: `{str(args).strip()}`",
                "Bu alias yalnizca durum ve yol dogrulamasi verir.",
            ]
        )

    return "\n".join(lines)
