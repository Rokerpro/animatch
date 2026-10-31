"""API integration tests for recommendation endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.recs.vectors import VectorIndex


@pytest.fixture
def start_index(monkeypatch):
    from app.api import recs

    items = []
    for anime_id, franchise, title in [
        (1, 10, "Seed One"),
        (2, 10, "Seed One sequel"),
        (3, 30, "Seed Two"),
        (4, 40, "Seed Three"),
        (5, 50, "Candidate Five"),
        (6, 60, "Candidate Six"),
        (7, 70, "Mature Seed"),
        (8, 80, "Candidate Eight"),
        (9, 90, "Candidate Nine"),
        (11, 110, "Candidate Eleven"),
    ]:
        items.append(
            {
                "id": anime_id,
                "title_english": title,
                "franchise_id": franchise,
                "average_score": 80,
                "popularity": 1000,
                "episodes": 12,
                "duration": 24,
                "season_year": 2020,
                "status": "FINISHED",
                "is_adult": anime_id == 7,
                "format": "TV",
                "genres": ["Drama", "Mystery"],
                "tags": [{"name": "Psychological", "rank": 90}],
            }
        )
    index = VectorIndex.build(items)
    monkeypatch.setattr(recs, "get_index", lambda: index)
    return index


@pytest.mark.asyncio
async def test_recs_start_validates_input_and_seed_constraints(
    client: AsyncClient, start_index
):
    cases = [
        ({}, 422, "Provide"),
        ({"liked_ids": [1, 3, 4, 5, 6, 7]}, 422, "at most 5"),
        ({"liked_ids": [1, 3]}, 422, "At least 3"),
        ({"liked_ids": [1, 2, 3]}, 422, "share a franchise"),
        ({"liked_ids": [1, 1, 3]}, 422, "duplicates"),
        ({"liked_ids": [1, 3, 999]}, 404, "not found"),
        ({"liked_ids": [1, 3, 7]}, 404, "restricted"),
    ]
    for payload, status_code, message in cases:
        response = await client.post("/api/recs/start", json=payload)
        assert response.status_code == status_code
        assert message.lower() in response.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_excluded_ids"),
    [
        pytest.param(
            {"quiz_answers": {"mood": "tense", "themes": "mystery"}, "limit": 1},
            None,
            id="quiz-only",
        ),
        # Liked IDs 1, 3, 4 belong to franchises 10, 30, 40. The fixture's
        # titles in those franchises are IDs 1, 2, 3, 4.
        pytest.param(
            {"liked_ids": [1, 3, 4], "limit": 10},
            {1, 2, 3, 4},
            id="liked-titles-only",
        ),
        pytest.param(
            {
                "quiz_answers": {"mood": "tense", "themes": "mystery"},
                "liked_ids": [1, 3, 4],
                "limit": 10,
            },
            {1, 2, 3, 4},
            id="quiz-and-liked-titles",
        ),
    ],
)
async def test_recs_start_accepts_quiz_titles_and_both_and_excludes_franchises(
    client: AsyncClient,
    start_index,
    payload: dict,
    expected_excluded_ids: set[int] | None,
):
    response = await client.post("/api/recs/start", json=payload)
    assert response.status_code == 200, f"payload={payload!r}"
    rows = response.json()
    assert len(rows) <= payload["limit"], f"payload={payload!r}"
    if expected_excluded_ids is not None:
        result_ids = {row["id"] for row in rows}
        assert result_ids.isdisjoint(
            expected_excluded_ids
        ), f"payload={payload!r}; expected exclusions={expected_excluded_ids}"
    assert all(
        "coverImage" in row and "reason" in row for row in rows
    ), f"payload={payload!r}"
    if "quiz_answers" in payload and "liked_ids" not in payload:
        assert rows, f"payload={payload!r}"
        assert all(
            "Matches your preference" in row["reason"] for row in rows
        ), f"payload={payload!r}"


@pytest.mark.asyncio
async def test_recs_start_returns_requested_limit_when_enough_candidates(
    client: AsyncClient, start_index
):
    payload = {"liked_ids": [1, 3, 4], "limit": 4}
    response = await client.post("/api/recs/start", json=payload)
    assert response.status_code == 200, f"payload={payload!r}"
    assert len(response.json()) == 4, f"payload={payload!r}"


@pytest.mark.asyncio
async def test_recs_start_returns_fewer_than_limit_and_is_deterministic(
    client: AsyncClient, start_index
):
    payload = {"liked_ids": [1, 3, 4], "limit": 10}
    first = await client.post("/api/recs/start", json=payload)
    second = await client.post("/api/recs/start", json=payload)
    assert first.status_code == 200, f"payload={payload!r}"
    assert len(first.json()) < payload["limit"], f"payload={payload!r}"
    assert first.json() == second.json(), f"payload={payload!r}"


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
