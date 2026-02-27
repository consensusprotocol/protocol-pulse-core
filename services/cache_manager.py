from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Optional


class SignalTerminalCacheManager:
    """Flask-Caching helper focused on Signal Terminal payloads."""

    DEFAULT_FEED_TIMEOUT = 30
    DEFAULT_STATS_TIMEOUT = 20
    DEFAULT_RECENT_TIMEOUT = 45

    def __init__(self, cache_backend: Any):
        self.cache = cache_backend

    def _build_key(self, namespace: str, payload: Optional[Dict[str, Any]] = None) -> str:
        if not payload:
            return f"signal_terminal:{namespace}"
        encoded = json.dumps(payload, sort_keys=True, default=str)
        suffix = hashlib.sha1(encoded.encode("utf-8")).hexdigest()
        return f"signal_terminal:{namespace}:{suffix}"

    def get_or_set(
        self,
        namespace: str,
        producer,
        *,
        timeout: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        key = self._build_key(namespace, payload)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        value = producer()
        self.cache.set(key, value, timeout=timeout)
        return value

    def cached_feed(self, producer, *, platform: Optional[str] = None, limit: int = 50) -> Any:
        return self.get_or_set(
            "feed",
            producer,
            timeout=self.DEFAULT_FEED_TIMEOUT,
            payload={"platform": platform or "all", "limit": int(limit)},
        )

    def cached_stats(self, producer, *, window_minutes: int = 60) -> Any:
        now = datetime.utcnow()
        window_bucket = now.replace(second=0, microsecond=0)
        bucket_step = max(1, int(window_minutes // 5) or 1)
        window_bucket -= timedelta(minutes=window_bucket.minute % bucket_step)
        return self.get_or_set(
            "stats",
            producer,
            timeout=self.DEFAULT_STATS_TIMEOUT,
            payload={"window_minutes": int(window_minutes), "bucket": window_bucket.isoformat()},
        )

    def cached_recent_events(self, producer, *, hours: int = 12, cap: int = 100) -> Any:
        return self.get_or_set(
            "recent",
            producer,
            timeout=self.DEFAULT_RECENT_TIMEOUT,
            payload={"hours": int(hours), "cap": int(cap)},
        )

    def invalidate_signal_terminal(self) -> None:
        """Invalidate all Signal Terminal cache keys when backend supports wildcard delete."""
        delete_many = getattr(self.cache, "delete_many", None)
        if callable(delete_many):
            try:
                delete_many("signal_terminal:feed", "signal_terminal:stats", "signal_terminal:recent")
            except Exception:
                pass


def init_signal_terminal_cache(app, cache_backend) -> SignalTerminalCacheManager:
    manager = SignalTerminalCacheManager(cache_backend)
    app.extensions = getattr(app, "extensions", {})
    app.extensions["signal_terminal_cache"] = manager
    return manager
