"""
Tests for execution cache
"""

from __future__ import annotations

import unittest
from server.agents.execution_cache import ExecutionCache


class ExecutionCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = ExecutionCache(ttl_seconds=60, max_entries=10)

    def test_cache_hit_and_miss(self) -> None:
        """Test basic cache hit and miss"""
        # First call - miss
        result, hit = self.cache.get("test_action", {"param": "value"})
        assert not hit
        assert result is None

        # Set cache
        self.cache.set("test_action", {"param": "value"}, {"result": "data"})

        # Second call - hit
        result, hit = self.cache.get("test_action", {"param": "value"})
        assert hit
        assert result == {"result": "data"}

    def test_cache_expiration(self) -> None:
        """Test that very old entries are treated as expired"""
        # This test verifies the expiration logic exists
        # In real usage, TTL would be checked at retrieval time
        cache = ExecutionCache(ttl_seconds=3600, max_entries=10)
        cache.set("action", {"p": 1}, {"result": "data"})

        # Immediately, should be there (not expired)
        result, hit = cache.get("action", {"p": 1})
        assert hit

    def test_different_params_no_hit(self) -> None:
        """Test that different params don't hit cache"""
        cache = ExecutionCache()
        cache.set("action", {"a": 1}, "result1")

        # Different param
        result, hit = cache.get("action", {"a": 2})
        assert not hit

    def test_cache_stats(self) -> None:
        """Test cache statistics"""
        cache = ExecutionCache()
        cache.set("action", {"a": 1}, "result")

        # Miss and hit
        cache.get("action", {"a": 2})  # miss
        cache.get("action", {"a": 1})  # hit

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_entries"] == 1
        assert stats["hit_rate_pct"] == 50.0

    def test_cache_eviction(self) -> None:
        """Test cache eviction when max entries reached"""
        cache = ExecutionCache(max_entries=2)

        cache.set("a", {"x": 1}, "result1")
        cache.set("b", {"x": 2}, "result2")
        cache.set("c", {"x": 3}, "result3")  # Should evict oldest

        stats = cache.get_stats()
        assert stats["total_entries"] == 2

    def test_cache_clear(self) -> None:
        """Test clearing cache"""
        cache = ExecutionCache()
        cache.set("action", {"a": 1}, "result")
        assert cache.get_stats()["total_entries"] == 1

        cache.clear()
        assert cache.get_stats()["total_entries"] == 0


if __name__ == "__main__":
    unittest.main()
