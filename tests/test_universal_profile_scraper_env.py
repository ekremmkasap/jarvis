from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SERVER_PATH = REPO_ROOT / "server"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

from server.services.universal_profile_scraper import (  # noqa: E402
    InstagramProfileScraper,
    YouTubeChannelScraper,
)


def test_youtube_scraper_reads_api_key_from_env(monkeypatch) -> None:
    monkeypatch.setenv("YOUTUBE_API_KEY", "youtube-test-key")

    scraper = YouTubeChannelScraper()

    assert scraper.api_key == "youtube-test-key"


def test_youtube_scraper_explicit_api_key_wins(monkeypatch) -> None:
    monkeypatch.setenv("YOUTUBE_API_KEY", "env-key")

    scraper = YouTubeChannelScraper(api_key="explicit-key")

    assert scraper.api_key == "explicit-key"


def test_instagram_scraper_reads_optional_login_env(monkeypatch) -> None:
    monkeypatch.setenv("INSTAGRAM_USERNAME", "jarvis-user")
    monkeypatch.setenv("INSTAGRAM_PASSWORD", "jarvis-pass")

    scraper = InstagramProfileScraper()

    assert scraper.username == "jarvis-user"
    assert scraper.password == "jarvis-pass"
