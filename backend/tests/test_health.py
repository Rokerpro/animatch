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
