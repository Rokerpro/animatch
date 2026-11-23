"""Per-client request throttling for expensive endpoints.

Uses a fixed window counter. The in-memory store is per process; set REDIS_URL so
all workers and replicas share one counter.
"""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from fastapi import HTTPException, Request, status

from app.core.client_ip import resolve_client_ip
from app.core.config import settings

logger = logging.getLogger(__name__)


class ThrottleStore(Protocol):
    async def hit(self, key: str, window_seconds: int) -> tuple[int, int]:
        """Count a request; return (count in window, seconds until the window ends)."""
        ...


class MemoryThrottleStore:
    def __init__(self) -> None:
        self._windows: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, window_seconds: int) -> tuple[int, int]:
        now = time.monotonic()
        count, reset_at = self._windows.get(key, (0, now + window_seconds))
        if now >= reset_at:
            count, reset_at = 0, now + window_seconds
        count += 1
        self._windows[key] = (count, reset_at)
        if len(self._windows) > 50_000:
            self._windows = {k: v for k, v in self._windows.items() if v[1] > now}
        return count, max(1, int(reset_at - now))

    def reset(self) -> None:
        self._windows.clear()


class RedisThrottleStore:
    def __init__(self, client: Any) -> None:
        self._client = client

    async def hit(self, key: str, window_seconds: int) -> tuple[int, int]:
        redis_key = f"throttle:{key}"
        count = await self._client.incr(redis_key)
        if count == 1:
            await self._client.expire(redis_key, window_seconds)
        ttl = await self._client.ttl(redis_key)
        if ttl is None or ttl < 0:
            await self._client.expire(redis_key, window_seconds)
            ttl = window_seconds
        return int(count), int(ttl)


_store: ThrottleStore | None = None
_memory_store = MemoryThrottleStore()


def get_throttle_store() -> ThrottleStore:
    global _store
    if _store is None:
        if settings.REDIS_URL:
            import redis.asyncio as redis

            _store = RedisThrottleStore(redis.from_url(settings.REDIS_URL))
        else:
            _store = _memory_store
    return _store


def reset_throttle_state() -> None:
    """Clear counters and the cached store (tests)."""
    global _store
    _store = None
    _memory_store.reset()


def throttle(scope: str, limit_setting: str) -> Callable[[Request], Awaitable[None]]:
    """Dependency limiting each client IP to `limit_setting` requests per minute."""

    async def dependency(request: Request) -> None:
        limit = int(getattr(settings, limit_setting))
        if limit <= 0:
            return
        peer = request.client.host if request.client else None
        ip = resolve_client_ip(peer, request.headers.get("X-Forwarded-For"))
        try:
            count, retry_after = await get_throttle_store().hit(f"{scope}:{ip}", 60)
        except Exception:
            logger.warning(
                "Throttle store unavailable; allowing request", exc_info=True
            )
            return
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
