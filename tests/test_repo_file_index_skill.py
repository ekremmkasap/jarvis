from __future__ import annotations

import json
from pathlib import Path

from server.skills.repo_file_index_skill import (
    build_markdown,
    find_repo_files,
    generate_repo_file_index,
    scan_repo_files,
)


def test_scan_repo_files_excludes_node_modules(tmp_path: Path) -> None:
    (tmp_path / "server").mkdir()
    (tmp_path / "server" / "bridge.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("x", encoding="utf-8")

    entries = scan_repo_files(tmp_path)

    assert [entry.path for entry in entries] == ["server/bridge.py"]


def test_build_markdown_contains_paths_and_summary(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    entries = scan_repo_files(tmp_path)

    markdown = build_markdown(entries, root=tmp_path)

    assert "# Jarvis Repo File Index" in markdown
    assert "`a.txt`" in markdown
    assert "Top Level Summary" in markdown


def test_generate_repo_file_index_writes_markdown_and_json(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    wiki = tmp_path / "wiki"
    root.mkdir()
    (root / "server").mkdir()
    (root / "server" / "bridge.py").write_text("print('ok')", encoding="utf-8")

    result = generate_repo_file_index(
        root=root,
        markdown_path=wiki / "repo-file-index.md",
        json_path=wiki / "repo-file-index.json",
        update_wiki_nav=False,
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert (wiki / "repo-file-index.md").exists()
    payload = json.loads((wiki / "repo-file-index.json").read_text(encoding="utf-8"))
    assert payload[0]["path"] == "server/bridge.py"


def test_find_repo_files_reads_json_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "repo-file-index.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "path": "server/bridge.py",
                    "name": "bridge.py",
                    "extension": ".py",
                    "top_level": "server",
                    "size_bytes": 10,
                    "sensitive_name": False,
                }
            ]
        ),
        encoding="utf-8",
    )

    result = find_repo_files("bridge.py", json_path=manifest)

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["matches"][0]["path"] == "server/bridge.py"
