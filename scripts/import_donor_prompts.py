from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_manifest() -> dict:
    manifest_path = ROOT / "config" / "donor_prompts.yml"
    with manifest_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def resolve_source_root(manifest: dict) -> Path:
    default_root = manifest.get("source_root", "")
    env_root = None
    try:
        import os

        env_raw = os.environ.get("JARVIS_DONOR_ROOT")
        if env_raw:
            env_root = Path(env_raw)
    except Exception:
        env_root = None
    if env_root:
        return env_root
    if default_root:
        return Path(default_root)
    return ROOT


def import_prompts() -> list[Path]:
    manifest = load_manifest()
    source_root = resolve_source_root(manifest)
    imported: list[Path] = []

    for item in manifest.get("imports", []):
        relative_source = item["source"]
        relative_target = item["target"]
        purpose = item.get("purpose", "").strip()

        source_path = source_root / relative_source
        target_path = ROOT / "prompts" / relative_target

        if not source_path.exists():
            raise FileNotFoundError(f"Missing donor prompt: {source_path}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        header = [
            "<!-- Imported donor prompt -->",
            f"<!-- Source: {source_path.as_posix()} -->",
        ]
        if purpose:
            header.append(f"<!-- Purpose: {purpose} -->")
        header.append("")

        content = source_path.read_text(encoding="utf-8", errors="replace")
        target_path.write_text("\n".join(header) + content, encoding="utf-8")
        imported.append(target_path)

    return imported


def main() -> int:
    imported = import_prompts()
    for path in imported:
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
