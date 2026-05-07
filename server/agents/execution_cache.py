"""
Execution Cache
Caches execution results to avoid redundant operations
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable


@dataclass
class CacheEntry:
    """Cached execution result"""
    key: str
    result: Any
    timestamp: str
    ttl_seconds: int


class ExecutionCache:
    """Simple in-memory cache with optional persistence"""

    def __init__(
        self,
        ttl_seconds: int = 3600,  # 1 hour default
        max_entries: int = 1000,
        cache_dir: Path | str | None = None,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.cache: dict[str, CacheEntry] = {}
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.hits = 0
        self.misses = 0
        self.logger = self._build_logger()

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger("jarvis.agents.cache")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not any(
            isinstance(h, logging.FileHandler)
            and "execution_cache" in h.baseFilename
            for h in logger.handlers
        ):
            if self.cache_dir:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                handler = logging.FileHandler(
                    self.cache_dir / "execution_cache.log",
                    encoding="utf-8"
                )
                handler.setFormatter(
                    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
                )
                logger.addHandler(handler)
        return logger

    def _make_key(self, action: str, params: dict[str, Any]) -> str:
        """Create cache key from action and parameters"""
        # Only cache deterministic operations with stable params
        serialized = json.dumps(
            {"action": action, "params": params},
            sort_keys=True,
            ensure_ascii=False
        )
        return hashlib.md5(serialized.encode()).hexdigest()

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        created = datetime.fromisoformat(entry.timestamp)
        now = datetime.now(timezone.utc)
        return (now - created).total_seconds() > entry.ttl_seconds

    def get(
        self,
        action: str,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, bool]:
        """
        Get cached result if available and not expired.

        Returns:
            (result, was_hit)
        """
        params = params or {}
        key = self._make_key(action, params)

        if key in self.cache:
            entry = self.cache[key]
            if not self._is_expired(entry):
                self.hits += 1
                self.logger.info(f"cache_hit action={action} key={key[:8]}")
                return entry.result, True
            else:
                # Expired, remove it
                del self.cache[key]

        self.misses += 1
        return None, False

    def set(
        self,
        action: str,
        params: dict[str, Any] | None,
        result: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache an execution result"""
        params = params or {}
        key = self._make_key(action, params)
        ttl = ttl_seconds or self.ttl_seconds

        entry = CacheEntry(
            key=key,
            result=result,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ttl_seconds=ttl,
        )

        # Evict oldest if at capacity
        if len(self.cache) >= self.max_entries:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].timestamp
            )
            del self.cache[oldest_key]
            self.logger.debug(f"cache_evicted key={oldest_key[:8]}")

        self.cache[key] = entry
        self.logger.info(f"cache_set action={action} ttl={ttl}s key={key[:8]}")

    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.logger.info("cache_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "total_entries": len(self.cache),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate_pct": round(hit_rate, 1),
        }


def cached_execution(
    cache: ExecutionCache,
    ttl_seconds: int | None = None,
) -> Callable:
    """Decorator to cache execution results"""
    def decorator(func: Callable) -> Callable:
        def wrapper(action: str, params: dict[str, Any] | None = None) -> Any:
            params = params or {}

            # Try cache first
            result, hit = cache.get(action, params)
            if hit:
                return result

            # Execute
            result = func(action, params)

            # Cache result
            cache.set(action, params, result, ttl_seconds=ttl_seconds)

            return result

        return wrapper

    return decorator
