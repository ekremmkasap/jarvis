from __future__ import annotations

"""Generate a safe Jarvis repo file index for the wiki.

Only file metadata is written: path, name, extension, size and flags.
File contents are never copied into the index, so credentials/cookies stay out.
"""

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
WIKI_DIR = ROOT / "wiki"
DEFAULT_INDEX_PATH = WIKI_DIR / "repo-file-index.md"
DEFAULT_JSON_PATH = WIKI_DIR / "repo-file-index.json"

EXCLUDED_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "outputs",
    "logs",
    "tmp",
    "temp",
    "dist",
    "build",
}

SENSITIVE_NAME_MARKERS = (
    ".env",
    "secret",
    "token",
    "cookie",
    "credential",
    "key",
    "audit",
)


@dataclass(frozen=True)
class FileIndexEntry:
    path: str
    name: str
    extension: str
    top_level: str
    size_bytes: int
    sensitive_name: bool


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_rel(path: Path) -> str:
    return path.as_posix()


def _is_excluded(path: Path, root: Path, extra_excludes: Iterable[str] | None = None) -> bool:
    excluded = set(EXCLUDED_DIRS)
    excluded.update(str(item).strip() for item in (extra_excludes or []) if str(item).strip())
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    return any(part in excluded for part in rel_parts[:-1])


def _is_sensitive_name(name: str) -> bool:
    lowered = str(name or "").lower()
    return any(marker in lowered for marker in SENSITIVE_NAME_MARKERS)


def scan_repo_files(root: str | Path = ROOT, extra_excludes: Iterable[str] | None = None) -> list[FileIndexEntry]:
    root_path = Path(root).resolve()
    excluded = set(EXCLUDED_DIRS)
    excluded.update(str(item).strip() for item in (extra_excludes or []) if str(item).strip())
    entries: list[FileIndexEntry] = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in excluded
        ]
        current_dir = Path(dirpath)
        for filename in filenames:
            path = current_dir / filename
            if _is_excluded(path, root_path, extra_excludes):
                continue
            try:
                rel = path.relative_to(root_path)
                size = path.stat().st_size
            except OSError:
                continue
            top_level = rel.parts[0] if rel.parts else "."
            entries.append(
                FileIndexEntry(
                    path=_normalize_rel(rel),
                    name=path.name,
                    extension=path.suffix.lower(),
                    top_level=top_level,
                    size_bytes=size,
                    sensitive_name=_is_sensitive_name(path.name),
                )
            )
    return sorted(entries, key=lambda item: item.path.lower())


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _markdown_table(entries: list[FileIndexEntry]) -> list[str]:
    lines = ["| Path | Name | Ext | Size | Flags |", "|---|---|---:|---:|---|"]
    for entry in entries:
        flags = "sensitive-name" if entry.sensitive_name else ""
        lines.append(
            f"| `{entry.path}` | `{entry.name}` | `{entry.extension or '-'}` | "
            f"{_format_size(entry.size_bytes)} | {flags} |"
        )
    return lines


def build_markdown(entries: list[FileIndexEntry], *, root: str | Path = ROOT) -> str:
    generated_at = _now_iso()
    by_top_level: dict[str, list[FileIndexEntry]] = {}
    for entry in entries:
        by_top_level.setdefault(entry.top_level, []).append(entry)

    total_size = sum(entry.size_bytes for entry in entries)
    sensitive_count = sum(1 for entry in entries if entry.sensitive_name)

    lines = [
        "# Jarvis Repo File Index",
        "",
        f"Generated at: {generated_at}",
        f"Root: `{Path(root).resolve()}`",
        f"Indexed files: {len(entries)}",
        f"Indexed size: {_format_size(total_size)}",
        f"Sensitive-looking filenames: {sensitive_count}",
        "",
        "Note: Bu sayfa dosya icerigi tasimaz; sadece yol/ad/boyut metadatasi yazar.",
        "Excluded dirs: "
        + ", ".join(f"`{item}`" for item in sorted(EXCLUDED_DIRS)),
        "",
        "## Top Level Summary",
        "",
        "| Area | Files | Size |",
        "|---|---:|---:|",
    ]
    for area, area_entries in sorted(by_top_level.items(), key=lambda item: item[0].lower()):
        area_size = sum(entry.size_bytes for entry in area_entries)
        lines.append(f"| `{area}` | {len(area_entries)} | {_format_size(area_size)} |")

    for area, area_entries in sorted(by_top_level.items(), key=lambda item: item[0].lower()):
        lines.extend(["", f"## {area}", ""])
        lines.extend(_markdown_table(area_entries))

    lines.append("")
    return "\n".join(lines)


def _update_wiki_index() -> None:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    index_path = WIKI_DIR / "index.md"
    default = "# Jarvis Wiki - Ana Navigasyon\n\n## Auto Pages\n"
    existing = index_path.read_text(encoding="utf-8") if index_path.exists() else default
    entry = "- [[repo-file-index]] - Jarvis repo dosya manifesti"
    if entry not in existing:
        if "## Auto Pages" not in existing:
            existing = existing.rstrip() + "\n\n## Auto Pages\n"
        existing = existing.rstrip() + "\n" + entry + "\n"
        index_path.write_text(existing, encoding="utf-8")


def _append_wiki_log(count: int) -> None:
    log_path = WIKI_DIR / "log.md"
    default = "# Jarvis Wiki - Islem Gecmisi\n\n| Tarih | Kaynak | Olusturulan Sayfalar | Not |\n|-------|--------|----------------------|-----|\n"
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else default
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = f"| {today} | repo_file_index | repo-file-index | {count} dosya metadatasi indekslendi |"
    if row not in existing:
        log_path.write_text(existing.rstrip() + "\n" + row + "\n", encoding="utf-8")


def generate_repo_file_index(
    *,
    root: str | Path = ROOT,
    markdown_path: str | Path = DEFAULT_INDEX_PATH,
    json_path: str | Path = DEFAULT_JSON_PATH,
    extra_excludes: Iterable[str] | None = None,
    update_wiki_nav: bool = True,
) -> dict[str, object]:
    entries = scan_repo_files(root, extra_excludes=extra_excludes)
    markdown = build_markdown(entries, root=root)

    md_path = Path(markdown_path)
    js_path = Path(json_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")
    js_path.write_text(
        json.dumps([asdict(entry) for entry in entries], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if update_wiki_nav:
        _update_wiki_index()
        _append_wiki_log(len(entries))
    return {
        "ok": True,
        "count": len(entries),
        "markdown_path": str(md_path),
        "json_path": str(js_path),
    }


def find_repo_files(
    query: str,
    *,
    json_path: str | Path = DEFAULT_JSON_PATH,
    root: str | Path = ROOT,
    limit: int = 20,
) -> dict[str, object]:
    clean_query = str(query or "").strip().lower()
    if not clean_query:
        return {"ok": False, "error": "query required", "matches": []}

    index_path = Path(json_path)
    if index_path.exists():
        try:
            raw_entries = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            raw_entries = []
    else:
        raw_entries = [asdict(entry) for entry in scan_repo_files(root)]

    matches = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "")
        name = str(entry.get("name") or "")
        haystack = f"{path}\n{name}".lower()
        if clean_query in haystack:
            matches.append(entry)
        if len(matches) >= max(1, int(limit or 20)):
            break

    return {
        "ok": True,
        "query": query,
        "count": len(matches),
        "matches": matches,
        "json_path": str(index_path),
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jarvis repo file index generator")
    parser.add_argument("--check", action="store_true", help="Sadece dosya sayisini hesapla")
    parser.add_argument("--write", action="store_true", help="Wiki manifestini yaz")
    parser.add_argument("--find", help="Manifest icinde dosya ara")
    args = parser.parse_args(argv)

    if args.check:
        entries = scan_repo_files()
        print(json.dumps({"ok": True, "count": len(entries)}, ensure_ascii=False, indent=2))
        return 0

    if args.write:
        print(json.dumps(generate_repo_file_index(), ensure_ascii=False, indent=2))
        return 0

    if args.find:
        print(json.dumps(find_repo_files(args.find), ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
