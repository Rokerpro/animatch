import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_v1_prefix_serves_the_same_routes(client: AsyncClient):
    legacy = await client.get("/api/health")
    versioned = await client.get("/api/v1/health")
    assert versioned.status_code == 200
    assert versioned.json() == legacy.json()


@pytest.mark.asyncio
async def test_v1_keeps_auth_and_csrf_behaviour(client: AsyncClient):
    csrf = await client.get("/api/v1/auth/csrf")
    assert csrf.status_code == 200 and csrf.json()["csrf_token"]
    assert (await client.post("/api/v1/auth/logout")).status_code == 403


@pytest.mark.asyncio
async def test_unknown_v1_path_is_404(client: AsyncClient):
    assert (await client.get("/api/v1/nope")).status_code == 404
    assert (await client.get("/api/v2/health")).status_code == 404
