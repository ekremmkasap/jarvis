from __future__ import annotations

import json
from pathlib import Path

from server.skills.media_intake_skill import (
    MediaIntakeSkill,
    detect_source_type,
    extract_first_url,
    find_cookie_file,
    format_media_intake_response,
)


def test_detect_source_type_instagram_reel() -> None:
    assert (
        detect_source_type("https://www.instagram.com/reel/DXJ5FqwkiVg/")
        == "instagram_reel"
    )


def test_extract_first_url_strips_trailing_punctuation() -> None:
    text = "kanka sunu izle: https://youtu.be/abcdefghijk)."
    assert extract_first_url(text) == "https://youtu.be/abcdefghijk"


def test_find_cookie_file_uses_explicit_path(tmp_path: Path) -> None:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape cookies", encoding="utf-8")

    assert find_cookie_file("https://www.instagram.com/reel/test/", str(cookie_file)) == cookie_file


def test_analyze_url_with_fake_extractor_writes_report(tmp_path: Path) -> None:
    def fake_extractor(url: str, download: bool, options: dict) -> dict:
        assert download is False
        assert options["skip_download"] is True
        return {
            "id": "DXJ5FqwkiVg",
            "title": "AI agent reel",
            "uploader": "creator.ai",
            "description": "Comment PROMPT for the free AI automation workflow.",
            "view_count": 1200,
            "like_count": 80,
            "comment_count": 32,
            "webpage_url": url,
            "extractor_key": "Instagram",
        }

    skill = MediaIntakeSkill(output_root=tmp_path, extractor=fake_extractor)
    result = skill.analyze_url(
        "https://www.instagram.com/reel/DXJ5FqwkiVg/",
        write_wiki=False,
    )

    assert result["ok"] is True
    assert result["metadata"]["title"] == "AI agent reel"
    assert "CTA/lead magnet" in result["analysis_notes"][0]
    assert Path(result["files"]["metadata_path"]).exists()
    assert Path(result["files"]["report_path"]).exists()

    metadata = json.loads(Path(result["files"]["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["metadata"]["id"] == "DXJ5FqwkiVg"


def test_analyze_url_supports_cookies_from_browser(tmp_path: Path) -> None:
    def fake_extractor(url: str, download: bool, options: dict) -> dict:
        assert options["cookiesfrombrowser"][0] == "chrome"
        assert "cookiefile" not in options
        return {
            "id": "abc",
            "title": "Browser cookie test",
            "webpage_url": url,
            "extractor_key": "Instagram",
        }

    skill = MediaIntakeSkill(
        output_root=tmp_path,
        extractor=fake_extractor,
        cookies_from_browser="chrome",
    )

    result = skill.analyze_url("https://www.instagram.com/reel/abc/", write_wiki=False)

    assert result["ok"] is True
    assert result["metadata"]["title"] == "Browser cookie test"


def test_format_response_contains_paths(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    report_path.write_text("# report", encoding="utf-8")
    response = format_media_intake_response(
        {
            "ok": True,
            "metadata": {
                "source_type": "instagram_reel",
                "title": "Hook testi",
                "uploader": "creator",
                "view_count": 10,
            },
            "analysis_notes": ["Metadata alindi."],
            "files": {"report_path": str(report_path)},
        }
    )

    assert "Video/kaynak Jarvis'e alindi." in response
    assert str(report_path) in response
