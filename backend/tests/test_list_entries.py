"""Tests for authenticated watchlist CRUD and isolation."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.main import create_app
from app.models.anime import Anime
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
        assert "anime_id" in res.json() and "animeId" not in res.json()
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
    assert (await client.get("/api/list?sort=unknown")).status_code == 422
    deleted = await client.delete(f"/api/list/{ids[1]}", headers=headers)
    assert deleted.status_code == 200, f"delete payload failed: {deleted.text}"
    missing = await client.delete(f"/api/list/{ids[1]}", headers=headers)
    assert missing.status_code == 404, f"missing delete payload: {missing.text}"


@pytest.mark.asyncio
async def test_put_null_rating_clears_and_omission_keeps_rating(
    client, seeded_catalog, register_user
):
    csrf = await register_user("rating-partial@example.com")
    headers = {"X-CSRF-Token": csrf}
    created = await client.put(
        "/api/list/154587", json={"status": "completed", "rating": 8}, headers=headers
    )
    assert created.status_code == 200 and created.json()["rating"] == 8

    status_only = await client.put(
        "/api/list/154587", json={"status": "watching"}, headers=headers
    )
    assert status_only.json()["status"] == "watching"
    assert status_only.json()["rating"] == 8

    cleared = await client.put(
        "/api/list/154587", json={"rating": None}, headers=headers
    )
    assert cleared.status_code == 200 and cleared.json()["rating"] is None


@pytest.mark.asyncio
async def test_rating_only_new_entry_defaults_to_planning(
    client, seeded_catalog, register_user
):
    csrf = await register_user("rating-only@example.com")
    response = await client.put(
        "/api/list/154587", json={"rating": 7}, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "planning"
    assert response.json()["rating"] == 7


@pytest.mark.asyncio
async def test_put_rejects_empty_body_and_unknown_keys(
    client, seeded_catalog, register_user
):
    csrf = await register_user("strict-payload@example.com")
    headers = {"X-CSRF-Token": csrf}
    empty = await client.put("/api/list/154587", json={}, headers=headers)
    unknown = await client.put(
        "/api/list/154587", json={"sttaus": "watching"}, headers=headers
    )
    assert empty.status_code == 422
    assert unknown.status_code == 422
    assert not (await client.get("/api/list")).json()["items"]


@pytest.mark.asyncio
async def test_list_pagination_counts_and_pages_only_visible_entries(
    client, db_session: AsyncSession, register_user
):
    await register_user("mature-pagination@example.com")
    user = (
        await db_session.execute(
            select(User).where(User.email == "mature-pagination@example.com")
        )
    ).scalar_one()
    animes = [
        Anime(
            id=990000 + index,
            title_romaji=f"Pagination test {index:02d}",
            is_adult=index < 6,
        )
        for index in range(30)
    ]
    db_session.add_all(animes)
    await db_session.flush()
    db_session.add_all(
        [
            ListEntry(user_id=user.id, anime_id=anime.id, status="planning")
            for anime in animes
        ]
    )
    await db_session.commit()

    pages = [
        (
            await client.get(f"/api/list?page={page}&pageSize=10&includeMature=false")
        ).json()
        for page in (1, 2, 3)
    ]
    assert [page["page_info"]["total"] for page in pages] == [24, 24, 24]
    assert [len(page["items"]) for page in pages] == [10, 10, 4]
    assert [page["page_info"]["last_page"] for page in pages] == [3, 3, 3]
    assert [page["page_info"]["has_next_page"] for page in pages] == [True, True, False]


@pytest.mark.asyncio
async def test_delete_hidden_mature_entry_is_allowed(
    client, db_session: AsyncSession, seeded_catalog, register_user
):
    csrf = await register_user("delete-hidden-mature@example.com")
    user = (
        await db_session.execute(
            select(User).where(User.email == "delete-hidden-mature@example.com")
        )
    ).scalar_one()
    db_session.add(
        ListEntry(user_id=user.id, anime_id=113425, status="completed", rating=8)
    )
    await db_session.commit()
    response = await client.delete("/api/list/113425", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    assert response.json() == {"message": "List entry for anime 113425 deleted"}


@pytest.mark.asyncio
async def test_list_statuses_validation_ownership_and_mature_filter(
    client, db_session: AsyncSession, seeded_catalog, register_user
):
    assert (await client.get("/api/list/statuses?ids=154587")).status_code == 401
    csrf = await register_user("statuses-owner@example.com")
    headers = {"X-CSRF-Token": csrf}
    assert (await client.get("/api/list/statuses?ids=")).status_code == 422
    assert (await client.get("/api/list/statuses?ids=1,not-an-id")).status_code == 422
    assert (
        await client.get("/api/list/statuses?ids=" + ",".join(map(str, range(51))))
    ).status_code == 422

    await client.put(
        "/api/list/154587", json={"status": "watching", "rating": 8}, headers=headers
    )
    await client.put("/api/list/16498", json={"status": "completed"}, headers=headers)
    user = (
        await db_session.execute(
            select(User).where(User.email == "statuses-owner@example.com")
        )
    ).scalar_one()
    db_session.add(
        ListEntry(user_id=user.id, anime_id=113425, status="dropped", rating=2)
    )
    await db_session.commit()

    own = await client.get("/api/list/statuses?ids=154587,999999,16498")
    own_items = own.json()["items"]
    assert {item["animeId"] for item in own_items} == {154587, 16498}
    assert all("anime_id" not in item for item in own_items)
    visible = await client.get("/api/list/statuses?ids=154587,113425")
    assert {item["animeId"] for item in visible.json()["items"]} == {154587}
    mature_visible = await client.get(
        "/api/list/statuses?ids=154587,113425&includeMature=true"
    )
    assert {item["animeId"] for item in mature_visible.json()["items"]} == {
        154587,
        113425,
    }

    await register_user("statuses-other@example.com")
    other = await client.get("/api/list/statuses?ids=154587,16498,113425")
    assert other.json()["items"] == []
    assert (await client.get("/api/list/statuses?ids=999999")).json() == {"items": []}


def test_list_openapi_has_explicit_contract_models():
    schema = create_app().openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]
    assert paths["/api/list"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/ListResponse")
    assert paths["/api/list/{anime_id}"]["put"]["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/ListEntryPut")
    assert paths["/api/list/{anime_id}"]["put"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/ListEntryResponse")
    assert paths["/api/list/statuses"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/ListStatusesResponse")
    assert paths["/api/list/{anime_id}"]["delete"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/ListDeleteResponse")
    assert components["ListStatus"]["enum"] == [
        "planning",
        "watching",
        "completed",
        "dropped",
        "on_hold",
    ]
    assert components["ListSort"]["enum"] == ["updated", "rating", "title"]
    rating_schema = components["ListEntryPut"]["properties"]["rating"]
    rating_value = next(
        item for item in rating_schema["anyOf"] if item.get("type") == "integer"
    )
    assert rating_value["minimum"] == 1 and rating_value["maximum"] == 10
    for code in ("401", "403", "404", "422"):
        assert code in paths["/api/list/{anime_id}"]["put"]["responses"]
    assert "additionalProperties" not in components["ListResponse"]


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
    adult = await client.put(
        "/api/list/113425", json={"status": "planning"}, headers=headers
    )
    detail = await client.get("/api/anime/113425")
    assert (
        adult.status_code == detail.status_code == 404
    ), f"mature payload/list/detail: {adult.text} / {detail.text}"
    bad_path = await client.put(
        "/api/list/not-an-integer", json={"status": "planning"}, headers=headers
    )
    assert bad_path.status_code == 422, f"non-integer list id payload: {bad_path.text}"


@pytest.mark.asyncio
async def test_auth_csrf_and_user_isolation(client, seeded_catalog, register_user):
    anonymous_cases = [
        ("get", "/api/list", None),
        ("put", "/api/list/154587", {"status": "planning"}),
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
        ("put", "/api/list/154587", {"status": "planning"}),
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
