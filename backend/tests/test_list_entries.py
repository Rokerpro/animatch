"""Tests for authenticated watchlist CRUD and isolation."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.list_entry import ListEntry
from app.models.user import User


@pytest.mark.asyncio
async def test_list_crud_filters_sort_and_pagination(
    client, seeded_catalog, db_session, register_user
):
    csrf = await register_user("list@example.com")
    headers = {"X-CSRF-Token": csrf}
    ids = [154587, 16498, 5114, 199]
    payloads = [
        {"status": "completed", "rating": 8},
        {"status": "watching", "rating": 10},
        {"status": "completed", "rating": 6},
        {"status": "planning", "rating": 9},
    ]
    for anime_id, payload in zip(ids, payloads, strict=True):
        res = await client.put(f"/api/list/{anime_id}", json=payload, headers=headers)
        assert res.status_code == 200, f"create payload {payload}: {res.text}"
        assert "coverImage" in res.json()["anime"], f"missing coverImage: {res.json()}"
    updated = await client.put(
        f"/api/list/{ids[0]}", json={"status": "watching", "rating": 7}, headers=headers
    )
    assert updated.status_code == 200, f"update payload failed: {updated.text}"
    filtered = await client.get("/api/list?status=completed")
    assert filtered.status_code == 200 and [
        x["anime_id"] for x in filtered.json()["items"]
    ] == [ids[2]], f"status filter payload: {filtered.json()}"
    by_rating = await client.get("/api/list?sort=rating")
    assert [x["rating"] for x in by_rating.json()["items"]] == [
        10,
        9,
        7,
        6,
    ], f"rating sort payload: {by_rating.json()}"
    rows = (
        (await db_session.execute(select(ListEntry).order_by(ListEntry.anime_id)))
        .scalars()
        .all()
    )
    for rank, row in enumerate(rows):
        row.updated_at = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=rank)
    await db_session.commit()
    by_updated = await client.get("/api/list?sort=updated")
    assert [x["anime_id"] for x in by_updated.json()["items"]] == [
        row.anime_id for row in reversed(rows)
    ], f"updated sort payload: {by_updated.json()}"
    by_title = await client.get("/api/list?sort=title")
    titles = [x["anime"]["title"] for x in by_title.json()["items"]]
    assert titles == sorted(titles), f"title sort payload: {by_title.json()}"
    page = await client.get("/api/list?page=1&pageSize=2")
    assert (
        page.json()["page_info"]["total"] == 4 and len(page.json()["items"]) == 2
    ), f"pagination payload: {page.json()}"
    assert (await client.get("/api/list?pageSize=51")).status_code == 422
    deleted = await client.delete(f"/api/list/{ids[1]}", headers=headers)
    assert deleted.status_code == 200, f"delete payload failed: {deleted.text}"
    missing = await client.delete(f"/api/list/{ids[1]}", headers=headers)
    assert missing.status_code == 404, f"missing delete payload: {missing.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize("rating", [0, 11, -1, 5.5])
async def test_invalid_rating_rejected(client, seeded_catalog, register_user, rating):
    csrf = await register_user(f"rating{str(rating).replace('.', '')}@example.com")
    payload = {"rating": rating}
    response = await client.put(
        "/api/list/154587", json=payload, headers={"X-CSRF-Token": csrf}
    )
    assert (
        response.status_code == 422
    ), f"invalid rating payload {payload}: {response.text}"


@pytest.mark.asyncio
async def test_invalid_status_unknown_and_mature_titles(
    client, seeded_catalog, register_user
):
    csrf = await register_user("validation@example.com")
    headers = {"X-CSRF-Token": csrf}
    for payload, expected in [
        ({"status": "finished"}, 422),
        ({"status": "planning"}, 200),
    ]:
        if payload["status"] == "planning":
            response = await client.put(
                "/api/list/999999", json=payload, headers=headers
            )
            assert (
                response.status_code == 404
            ), f"unknown anime payload {payload}: {response.text}"
        else:
            response = await client.put(
                "/api/list/154587", json=payload, headers=headers
            )
            assert (
                response.status_code == expected
            ), f"status payload {payload}: {response.text}"
    adult = await client.put("/api/list/113425", json={}, headers=headers)
    detail = await client.get("/api/anime/113425")
    assert (
        adult.status_code == detail.status_code == 404
    ), f"mature payload/list/detail: {adult.text} / {detail.text}"
    bad_path = await client.put("/api/list/not-an-integer", json={}, headers=headers)
    assert bad_path.status_code == 422, f"non-integer list id payload: {bad_path.text}"


@pytest.mark.asyncio
async def test_auth_csrf_and_user_isolation(client, seeded_catalog, register_user):
    anonymous_cases = [
        ("get", "/api/list", None),
        ("put", "/api/list/154587", {}),
        ("delete", "/api/list/154587", None),
        ("get", "/api/auth/me/taste-profile", None),
        ("put", "/api/auth/me/taste-profile", {}),
        ("get", "/api/recs/me", None),
    ]
    for method, path, body in anonymous_cases:
        response = (
            await getattr(client, method)(path, json=body)
            if body is not None
            else await getattr(client, method)(path)
        )
        assert (
            response.status_code == 401
        ), f"anonymous {method} {path} payload={body}: {response.text}"
    csrf_a = await register_user("owner@example.com")
    for method, path, body in [
        ("put", "/api/list/154587", {}),
        ("delete", "/api/list/154587", None),
        ("put", "/api/auth/me/taste-profile", {}),
    ]:
        for token in (None, "wrong"):
            headers = {} if token is None else {"X-CSRF-Token": token}
            res = (
                await getattr(client, method)(path, json=body, headers=headers)
                if body is not None
                else await client.delete(path, headers=headers)
            )
            assert (
                res.status_code == 403
            ), f"CSRF {method} {path} token={token} payload={body}: {res.text}"
    await client.put(
        "/api/list/154587",
        json={"status": "completed"},
        headers={"X-CSRF-Token": csrf_a},
    )
    owner_cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
    owner_csrf = csrf_a
    csrf_b = await register_user("other@example.com")
    other_cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
    other_csrf = csrf_b
    client.cookies.set(settings.SESSION_COOKIE_NAME, owner_cookie)
    client.cookies.set(settings.CSRF_COOKIE_NAME, owner_csrf)
    owner_before = (await client.get("/api/list")).json()["items"]
    assert (
        len(owner_before) == 1 and owner_before[0]["status"] == "completed"
    ), f"owner list before isolation checks: {owner_before}"
    client.cookies.set(settings.SESSION_COOKIE_NAME, other_cookie)
    client.cookies.set(settings.CSRF_COOKIE_NAME, other_csrf)
    assert not (await client.get("/api/list")).json()["items"]
    for method, payload in [("put", {"rating": 1}), ("delete", None)]:
        res = (
            await getattr(client, method)(
                "/api/list/154587", json=payload, headers={"X-CSRF-Token": other_csrf}
            )
            if payload is not None
            else await client.delete(
                "/api/list/154587", headers={"X-CSRF-Token": other_csrf}
            )
        )
        assert (
            res.status_code == 200
        ), f"cross-user upsert/delete should remain scoped to caller: {res.text}"
    client.cookies.set(settings.SESSION_COOKIE_NAME, owner_cookie)
    owner_list = await client.get("/api/list")
    assert (
        owner_list.json()["items"] == owner_before
    ), f"other user's upsert/delete changed owner's row: {owner_list.json()}"


@pytest.mark.asyncio
async def test_account_deletion_cascades_list_and_profile_only_for_deleted_user(
    client, seeded_catalog, db_session: AsyncSession, register_user
):
    csrf_a = await register_user("delete-owner@example.com")
    owner_cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
    await client.put(
        "/api/list/154587",
        json={"status": "completed"},
        headers={"X-CSRF-Token": csrf_a},
    )
    await client.put(
        "/api/auth/me/taste-profile",
        json={"liked_ids": [154587]},
        headers={"X-CSRF-Token": csrf_a},
    )
    csrf_b = await register_user("survivor@example.com")
    await client.put(
        "/api/list/16498", json={"status": "watching"}, headers={"X-CSRF-Token": csrf_b}
    )
    survivor = (
        await db_session.execute(
            select(User).where(User.email == "survivor@example.com")
        )
    ).scalar_one()
    owner = (
        await db_session.execute(
            select(User).where(User.email == "delete-owner@example.com")
        )
    ).scalar_one()
    owner_id, survivor_id = owner.id, survivor.id
    # Restore the first user's authenticated cookies, then delete that account.
    client.cookies.set(settings.SESSION_COOKIE_NAME, owner_cookie)
    client.cookies.set(settings.CSRF_COOKIE_NAME, csrf_a)
    deleted = await client.delete("/api/auth/me", headers={"X-CSRF-Token": csrf_a})
    assert deleted.status_code == 200, f"account deletion payload: {deleted.text}"
    remaining = (await db_session.execute(select(ListEntry))).scalars().all()
    assert [(row.user_id, row.anime_id) for row in remaining] == [
        (survivor_id, 16498)
    ], f"cascade deletion payload: {remaining}"
    assert (
        await db_session.execute(select(User).where(User.id == owner_id))
    ).scalar_one_or_none() is None, "deleted user profile must be removed"
