import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Verifies that the /api/health endpoint returns 200 OK
    with correct status and version.
    """
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == settings.APP_VERSION
    assert data["environment"] == settings.ENVIRONMENT
    assert data["database"] in ["connected", "disconnected"]


@pytest.mark.asyncio
async def test_liveness_is_always_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_requires_loaded_index(
    client: AsyncClient, seeded_catalog, db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.recs.engine import rebuild_index_from_db
    from app.recs.vectors import VectorIndex, get_index, set_index

    previous = get_index()
    try:
        set_index(VectorIndex())
        empty = await client.get("/api/health/ready")
        assert empty.status_code == 503
        assert empty.json()["index"] == "empty"

        await rebuild_index_from_db(db_session)
        ready = await client.get("/api/health/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"
    finally:
        set_index(previous)
