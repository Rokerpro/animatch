import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.throttle import MemoryThrottleStore, RedisThrottleStore


@pytest.mark.asyncio
async def test_recs_endpoint_is_throttled_per_ip(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_RECS_PER_MINUTE", 3)
    codes = [(await client.get("/api/quiz")).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]
    blocked = await client.get("/api/quiz")
    assert int(blocked.headers["retry-after"]) >= 1


@pytest.mark.asyncio
async def test_limit_zero_disables_throttling(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_CATALOG_PER_MINUTE", 0)
    codes = {(await client.get("/api/genres")).status_code for _ in range(10)}
    assert codes == {200}


@pytest.mark.asyncio
async def test_catalog_and_recs_limits_are_independent(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_RECS_PER_MINUTE", 1)
    await client.get("/api/quiz")
    assert (await client.get("/api/quiz")).status_code == 429
    assert (await client.get("/api/genres")).status_code == 200


@pytest.mark.asyncio
async def test_memory_store_counts_within_window():
    store = MemoryThrottleStore()
    assert (await store.hit("k", 60))[0] == 1
    count, retry = await store.hit("k", 60)
    assert count == 2 and 1 <= retry <= 60
    assert (await store.hit("other", 60))[0] == 1


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expiry: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expiry[key] = seconds

    async def ttl(self, key: str) -> int:
        return self.expiry.get(key, -1)


@pytest.mark.asyncio
async def test_redis_store_sets_expiry_on_first_hit():
    fake = FakeRedis()
    store = RedisThrottleStore(fake)
    assert await store.hit("k", 60) == (1, 60)
    assert (await store.hit("k", 60))[0] == 2
    assert fake.expiry["throttle:k"] == 60


@pytest.mark.asyncio
async def test_store_failure_fails_open(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    class Broken:
        async def hit(self, key: str, window_seconds: int):
            raise ConnectionError("redis down")

    monkeypatch.setattr(settings, "RATE_LIMIT_RECS_PER_MINUTE", 1)
    monkeypatch.setattr("app.core.throttle._store", Broken())
    assert (await client.get("/api/quiz")).status_code == 200
    assert (await client.get("/api/quiz")).status_code == 200
