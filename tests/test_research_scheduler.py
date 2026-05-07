"""Tests for research_scheduler_skill."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "server" / "skills"))


@patch("server.skills.research_scheduler_skill.requests.get")
def test_fetch_github_trending_returns_list(mock_get):
    from server.skills.research_scheduler_skill import fetch_github_trending
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html><body>
    <article class="Box-row">
      <h2><a href="/owner/repo">Owner / Repo</a></h2>
      <p>A test description</p>
    </article>
    </body></html>
    """
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    items = fetch_github_trending(max_items=3)
    assert isinstance(items, list)
    for item in items:
        assert "source" in item and item["source"] == "github"
        assert "url" in item
        assert "title" in item


@patch("server.skills.research_scheduler_skill.requests.get")
def test_fetch_github_trending_on_error_returns_empty(mock_get):
    from server.skills.research_scheduler_skill import fetch_github_trending
    mock_get.side_effect = Exception("network error")
    items = fetch_github_trending()
    assert items == []


@patch("server.skills.research_scheduler_skill.requests.get")
def test_fetch_reddit_top_returns_list(mock_get):
    from server.skills.research_scheduler_skill import fetch_reddit_top
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "children": [
                {"data": {"title": "Test Post", "url": "https://example.com", "selftext": ""}}
            ]
        }
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    items = fetch_reddit_top(subreddits=["programming"], max_items=3)
    assert isinstance(items, list)
    if items:
        assert items[0]["source"] == "reddit"


@patch("server.skills.research_scheduler_skill.feedparser.parse")
def test_fetch_twitter_nitter_on_failure_returns_empty(mock_parse):
    from server.skills.research_scheduler_skill import fetch_twitter_nitter
    mock_parse.side_effect = Exception("nitter down")
    items = fetch_twitter_nitter()
    assert items == []


def test_build_brief_message_empty_items():
    from server.skills.research_scheduler_skill import build_brief_message
    msg = build_brief_message([])
    assert "Brief" in msg or "icerik" in msg
    assert len(msg) <= 3000


def test_build_brief_message_with_items():
    from server.skills.research_scheduler_skill import build_brief_message
    items = [
        {"source": "github", "title": "cool/repo", "url": "https://github.com/cool/repo",
         "summary": "desc", "fetched_at": "2026-04-13T08:00:00", "included_in_brief": None}
    ]
    msg = build_brief_message(items, soul_prefix="Gunaydın kanka!")
    assert "Gunaydın" in msg
    assert "GitHub" in msg or "github" in msg.lower()


def test_save_and_load_today_brief(tmp_path, monkeypatch):
    from server.skills import research_scheduler_skill as rss
    monkeypatch.setattr(rss, "BRIEF_HISTORY_PATH", tmp_path / "daily_brief_history.json")
    today = date.today().isoformat()
    brief = {
        "date": today, "items": [], "items_count": 0,
        "message_text": "test", "sent_at": None, "send_status": "sent"
    }
    rss.save_daily_brief(brief)
    loaded = rss.load_today_brief()
    assert loaded is not None
    assert loaded["date"] == today
    assert loaded["send_status"] == "sent"


def test_run_morning_brief_calls_send_fn(tmp_path, monkeypatch):
    from server.skills import research_scheduler_skill as rss
    monkeypatch.setattr(rss, "BRIEF_HISTORY_PATH", tmp_path / "daily_brief_history.json")
    sent_messages = []
    with patch.object(rss, "fetch_github_trending", return_value=[]):
        with patch.object(rss, "fetch_reddit_top", return_value=[]):
            with patch.object(rss, "fetch_twitter_nitter", return_value=[]):
                with patch.object(rss, "load_soul_context", return_value={"prefix": ""}):
                    result = rss.run_morning_brief(lambda msg: sent_messages.append(msg))
    assert "ok" in result
    assert len(sent_messages) == 1
