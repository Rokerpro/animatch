"""API integration tests for recommendation endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_quiz_endpoint(client: AsyncClient):
    """GET /api/quiz returns the 7 questions."""
    response = await client.get("/api/quiz")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 7
    q_ids = [q["id"] for q in data]
    assert "mood" in q_ids
    assert "length" in q_ids
    assert "era" in q_ids


@pytest.mark.asyncio
async def test_recs_similar_empty_or_404(client: AsyncClient):
    """GET /api/recs/similar/9999999 returns 404 for missing anime."""
    response = await client.get("/api/recs/similar/9999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_recs_me_unauthorized(client: AsyncClient):
    """GET /api/recs/me without auth returns 401."""
    response = await client.get("/api/recs/me")
    assert response.status_code == 401
