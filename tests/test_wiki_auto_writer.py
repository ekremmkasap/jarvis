from pathlib import Path

from server.skills import wiki_auto_writer


def test_write_wiki_page_updates_page_index_log_and_hot(tmp_path, monkeypatch):
    wiki_dir = tmp_path / "wiki"
    monkeypatch.setattr(wiki_auto_writer, "WIKI_DIR", wiki_dir)
    monkeypatch.setattr(wiki_auto_writer, "INDEX_PATH", wiki_dir / "index.md")
    monkeypatch.setattr(wiki_auto_writer, "LOG_PATH", wiki_dir / "log.md")
    monkeypatch.setattr(wiki_auto_writer, "HOT_PATH", wiki_dir / "hot.md")

    result = wiki_auto_writer.write_wiki_page(
        "Yeni Sayfa",
        "Bu bir wiki ozetidir.",
        ["mert", "seda"],
    )

    assert result["ok"] is True
    assert result["slug"] == "yeni-sayfa"
    assert result["path"] == "wiki/yeni-sayfa.md"
    assert result["linked_personas"] == ["mert", "seda"]

    page_path = wiki_dir / "yeni-sayfa.md"
    assert page_path.exists()
    content = page_path.read_text(encoding="utf-8")
    assert "# Yeni Sayfa" in content
    assert "Bu bir wiki ozetidir." in content
    assert "Linked personas: mert, seda" in content

    index_text = (wiki_dir / "index.md").read_text(encoding="utf-8")
    assert "[[yeni-sayfa]] - Yeni Sayfa" in index_text

    log_text = (wiki_dir / "log.md").read_text(encoding="utf-8")
    assert "| intent | yeni-sayfa | Yeni Sayfa |" in log_text

    hot_text = (wiki_dir / "hot.md").read_text(encoding="utf-8")
    assert "## Son Otomatik Guncelleme -" in hot_text
    assert "Bu bir wiki ozetidir." in hot_text


def test_update_hot_md_limits_summary_to_500_words(tmp_path, monkeypatch):
    hot_path = tmp_path / "wiki" / "hot.md"
    monkeypatch.setattr(wiki_auto_writer, "HOT_PATH", hot_path)

    summary = " ".join(f"kelime{i}" for i in range(600))
    wiki_auto_writer.update_hot_md(summary)

    hot_text = hot_path.read_text(encoding="utf-8")
    assert "kelime0" in hot_text
    assert "kelime499" in hot_text
    assert "kelime500" not in hot_text
