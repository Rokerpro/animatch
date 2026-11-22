import pytest
from httpx import AsyncClient

from app.core import ttl_cache
from app.core.ttl_cache import TTLCache


def test_ttl_cache_expires_and_evicts(monkeypatch: pytest.MonkeyPatch):
    now = [1000.0]
    monkeypatch.setattr(ttl_cache.time, "monotonic", lambda: now[0])
    cache: TTLCache[int] = TTLCache(max_entries=2, ttl_seconds=10)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)  # evicts least recently used ("b")
    assert cache.get("b") is None and cache.get("a") == 1
    now[0] += 11
    assert cache.get("a") is None


@pytest.mark.asyncio
async def test_similar_results_are_cached_per_parameters(
    client: AsyncClient,
    seeded_catalog,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.api import recs
    from app.recs.engine import rebuild_index_from_db

    await rebuild_index_from_db(db_session)

    calls: list[tuple] = []
    real = recs.recommend_similar

    def counting(**kwargs):
        calls.append((kwargs["anime_id"], kwargs["n"], kwargs["include_mature"]))
        return real(**kwargs)

    monkeypatch.setattr(recs, "recommend_similar", counting)

    first = await client.get("/api/recs/similar/154587?n=5")
    second = await client.get("/api/recs/similar/154587?n=5")
    assert first.status_code == 200 and first.json() == second.json()
    assert len(calls) == 1

    await client.get("/api/recs/similar/154587?n=6")
    await client.get("/api/recs/similar/16498?n=5")
    assert len(calls) == 3
