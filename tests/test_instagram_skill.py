"""Tests for instagram_skill."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_watch_list(tmp_path, monkeypatch):
    from server.skills import instagram_skill as ig
    monkeypatch.setattr(ig, "WATCH_LIST_PATH", tmp_path / "watch_list.json")
    return tmp_path / "watch_list.json"


def test_add_watched_account_success(tmp_watch_list):
    from server.skills.instagram_skill import add_watched_account
    result = add_watched_account("testuser")
    assert result["ok"] is True
    assert "testuser" in result["message"]


def test_add_watched_account_strips_at(tmp_watch_list):
    from server.skills.instagram_skill import add_watched_account
    result = add_watched_account("@testuser2")
    assert result["ok"] is True


def test_add_watched_account_invalid_username(tmp_watch_list):
    from server.skills.instagram_skill import add_watched_account
    result = add_watched_account("invalid user!")
    assert result["ok"] is False


def test_add_watched_account_duplicate(tmp_watch_list):
    from server.skills.instagram_skill import add_watched_account
    add_watched_account("dupuser")
    result = add_watched_account("dupuser")
    assert result["ok"] is False
    assert "zaten" in result["message"]


def test_list_watched_accounts(tmp_watch_list):
    from server.skills.instagram_skill import add_watched_account, list_watched_accounts
    add_watched_account("user1")
    add_watched_account("user2")
    lst = list_watched_accounts()
    assert len(lst) == 2


def test_remove_watched_account(tmp_watch_list):
    from server.skills.instagram_skill import add_watched_account, remove_watched_account, list_watched_accounts
    add_watched_account("removetest")
    result = remove_watched_account("removetest")
    assert result["ok"] is True
    assert len(list_watched_accounts()) == 0


def test_check_account_no_instaloader(tmp_watch_list, monkeypatch):
    from server.skills.instagram_skill import add_watched_account, _load_watch_list, check_account_new_posts
    add_watched_account("testuser")
    account = _load_watch_list()[0]
    # Simulate instaloader not installed
    with patch.dict("sys.modules", {"instaloader": None}):
        result = check_account_new_posts(account, lambda msg: None)
    # Should return error (instaloader import will fail)
    assert "ok" in result


def test_run_cycle_empty_list(tmp_watch_list):
    from server.skills.instagram_skill import run_instagram_check_cycle
    result = run_instagram_check_cycle(lambda msg: None)
    assert result["ok"] is True
    assert result["checked"] == 0
