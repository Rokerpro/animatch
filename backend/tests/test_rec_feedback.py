"""Tests for "not interested" recommendation feedback."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.recs.engine import rebuild_index_from_db

SEEDS = {154587: 10, 16498: 9, 5114: 8}


@pytest.fixture
async def indexed(seeded_catalog, db_session: AsyncSession) -> None:
    await rebuild_index_from_db(db_session)


@pytest.mark.asyncio
async def test_feedback_requires_auth_and_csrf(client, indexed, register_user):
    assert (await client.get("/api/recs/feedback")).status_code == 401
    assert (await client.put("/api/recs/feedback/154587")).status_code == 401

    await register_user("fb-auth@example.com")
    assert (await client.put("/api/recs/feedback/154587")).status_code == 403
    assert (await client.delete("/api/recs/feedback/154587")).status_code == 403


@pytest.mark.asyncio
async def test_feedback_crud_is_idempotent(client, indexed, register_user):
    headers = {"X-CSRF-Token": await register_user("fb-crud@example.com")}

    first = await client.put("/api/recs/feedback/154587", headers=headers)
    again = await client.put("/api/recs/feedback/154587", headers=headers)
    assert first.json() == again.json() == {"anime_ids": [154587]}
    assert (await client.get("/api/recs/feedback")).json()["anime_ids"] == [154587]

    removed = await client.delete("/api/recs/feedback/154587", headers=headers)
    assert removed.json() == {"anime_ids": []}
    assert (
        await client.delete("/api/recs/feedback/154587", headers=headers)
    ).status_code == 200


@pytest.mark.asyncio
async def test_feedback_unknown_title_is_404(client, indexed, register_user):
    headers = {"X-CSRF-Token": await register_user("fb-404@example.com")}
    assert (
        await client.put("/api/recs/feedback/99999999", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_hidden_title_is_excluded_from_personal_recs(
    client, indexed, register_user
):
    headers = {"X-CSRF-Token": await register_user("fb-recs@example.com")}
    for anime_id, rating in SEEDS.items():
        saved = await client.put(
            f"/api/list/{anime_id}",
            json={"status": "completed", "rating": rating},
            headers=headers,
        )
        assert saved.status_code == 200

    before = await client.get("/api/recs/me?n=50")
    assert before.status_code == 200
    candidates = [r["id"] for r in before.json()]
    assert candidates, "expected personalised results from the seeded catalog"

    hidden = candidates[0]
    assert (
        await client.put(f"/api/recs/feedback/{hidden}", headers=headers)
    ).status_code == 200
    after = await client.get("/api/recs/me?n=50")
    assert hidden not in [r["id"] for r in after.json()]


@pytest.mark.asyncio
async def test_export_includes_hidden_titles(client, indexed, register_user):
    headers = {"X-CSRF-Token": await register_user("fb-export@example.com")}
    await client.put("/api/recs/feedback/154587", headers=headers)
    data = (await client.get("/api/auth/me/export")).json()
    assert data["not_interested_anime_ids"] == [154587]
