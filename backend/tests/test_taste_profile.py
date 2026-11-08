"""Validation and persistence tests for saved taste profiles."""

import json
import time
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

CATALOG_IDS = [154587, 16498, 113425, 5114, 199, 110270, 20, 1535, 9253, 21]


@pytest.mark.asyncio
async def test_taste_profile_save_read_and_empty(
    client, seeded_catalog, db_session: AsyncSession, register_user
):
    csrf = await register_user("taste@example.com")
    empty = await client.get("/api/auth/me/taste-profile")
    assert empty.json() == {
        "quiz_answers": None,
        "liked_ids": [],
    }, f"empty profile payload: {empty.json()}"
    quiz = json.loads((Path(__file__).parents[1] / "app/data/quiz.json").read_text())
    q = quiz["questions"][0]
    answers = {q["id"]: q["answers"][0]["id"]}
    payload = {"quiz_answers": answers, "liked_ids": [154587]}
    saved = await client.put(
        "/api/auth/me/taste-profile", json=payload, headers={"X-CSRF-Token": csrf}
    )
    assert (
        saved.status_code == 200 and saved.json() == payload
    ), f"save payload {payload}: {saved.text}"
    readback = await client.get("/api/auth/me/taste-profile")
    assert readback.json() == payload, f"read-back payload: {readback.json()}"
    user = (
        await db_session.execute(select(User).where(User.email == "taste@example.com"))
    ).scalar_one()
    assert (
        user.taste_profile == payload
    ), f"stored profile should contain only validated fields: {user.taste_profile}"


@pytest.mark.asyncio
async def test_taste_profile_rejects_unknown_liked_and_invalid_quiz(
    client, seeded_catalog, db_session: AsyncSession, register_user
):
    quiz = json.loads((Path(__file__).parents[1] / "app/data/quiz.json").read_text())
    known_question = quiz["questions"][0]
    csrf = await register_user("invalidtaste@example.com")
    initial_profile = {"quiz_answers": None, "liked_ids": [154587]}
    saved = await client.put(
        "/api/auth/me/taste-profile",
        json=initial_profile,
        headers={"X-CSRF-Token": csrf},
    )
    assert saved.status_code == 200, saved.text
    user = (
        await db_session.execute(
            select(User).where(User.email == "invalidtaste@example.com")
        )
    ).scalar_one()
    initial_stored_profile = user.taste_profile
    cases = [
        ({"liked_ids": [999999]}, "unknown liked id"),
        ({"liked_ids": CATALOG_IDS[:6]}, "too many liked ids"),
        ({"liked_ids": [154587, 154587]}, "duplicate liked ids"),
        ({"liked_ids": ["not-an-integer"]}, "non-integer liked id"),
        ({"quiz_answers": {"unknown_question": "x"}}, "unknown question"),
        ({"quiz_answers": {known_question["id"]: "unknown_answer"}}, "unknown answer"),
        (
            {"quiz_answers": {known_question["id"]: "x" * 65}},
            "over-long quiz answer",
        ),
        (
            {"quiz_answers": {"unknown_question": "x" * 10000}},
            "unknown quiz question id",
        ),
        ({"quiz_answers": {"q" * 65: "x"}}, "over-long quiz question id"),
        ({"quiz_answers": {f"q{i}": "x" for i in range(21)}}, "too many quiz answers"),
    ]
    for payload, label in cases:
        res = await client.put(
            "/api/auth/me/taste-profile", json=payload, headers={"X-CSRF-Token": csrf}
        )
        assert res.status_code == 422, f"{label} payload {payload}: {res.text}"
        profile = await client.get("/api/auth/me/taste-profile")
        assert (
            profile.json() == initial_profile
        ), f"{label} changed profile: {profile.text}"
    user = (
        await db_session.execute(
            select(User).where(User.email == "invalidtaste@example.com")
        )
    ).scalar_one()
    assert user.taste_profile == initial_stored_profile


@pytest.mark.asyncio
async def test_taste_profile_accepts_answer_ids_up_to_twenty_characters(
    client, register_user, monkeypatch
):
    from app.recs import quiz as quiz_module

    answer_id = "answer-1234567890123"
    monkeypatch.setattr(
        quiz_module,
        "load_quiz_data",
        lambda: {"questions": [{"id": "question", "answers": [{"id": answer_id}]}]},
    )
    csrf = await register_user("longanswer@example.com")
    response = await client.put(
        "/api/auth/me/taste-profile",
        json={"quiz_answers": {"question": answer_id}},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    assert response.json()["quiz_answers"] == {"question": answer_id}


@pytest.mark.asyncio
async def test_taste_profile_accepts_five_distinct_liked_ids_and_empty_list(
    client, seeded_catalog, register_user
):
    csrf = await register_user("validtaste@example.com")
    five_ids = CATALOG_IDS[:5]
    saved = await client.put(
        "/api/auth/me/taste-profile",
        json={"liked_ids": five_ids},
        headers={"X-CSRF-Token": csrf},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"quiz_answers": None, "liked_ids": five_ids}

    empty = await client.put(
        "/api/auth/me/taste-profile",
        json={"liked_ids": []},
        headers={"X-CSRF-Token": csrf},
    )
    assert empty.status_code == 200, empty.text
    assert empty.json() == {"quiz_answers": None, "liked_ids": []}


@pytest.mark.asyncio
async def test_taste_profile_rejects_large_liked_ids_without_saving(
    client, db_session: AsyncSession, register_user
):
    csrf = await register_user("largeprofile@example.com")
    payload = {"liked_ids": list(range(10_000))}
    started = time.perf_counter()
    response = await client.put(
        "/api/auth/me/taste-profile", json=payload, headers={"X-CSRF-Token": csrf}
    )
    elapsed = time.perf_counter() - started
    assert response.status_code == 422, response.text
    assert elapsed < 2, f"oversized liked_ids took {elapsed:.2f}s to reject"
    profile = await client.get("/api/auth/me/taste-profile")
    assert profile.json() == {"quiz_answers": None, "liked_ids": []}
    user = (
        await db_session.execute(
            select(User).where(User.email == "largeprofile@example.com")
        )
    ).scalar_one()
    assert user.taste_profile is None


@pytest.mark.asyncio
async def test_openapi_declares_liked_id_item_limits(client):
    schemas = client._transport.app.openapi()["components"]["schemas"]
    taste = schemas["TasteProfileRequest"]["properties"]
    assert taste["liked_ids"]["maxItems"] == 5
    quiz_answers = taste["quiz_answers"]["anyOf"][0]
    assert quiz_answers["maxProperties"] == 20
    assert quiz_answers["propertyNames"]["maxLength"] == 64
    assert quiz_answers["additionalProperties"]["maxLength"] == 64
    rec_ids = schemas["RecStartRequest"]["properties"]["liked_ids"]
    assert rec_ids["anyOf"][0]["maxItems"] == 5


@pytest.mark.asyncio
async def test_taste_profile_extra_fields_not_persisted(
    client, seeded_catalog, db_session: AsyncSession, register_user
):
    csrf = await register_user("extra@example.com")
    payload = {"liked_ids": [154587], "junk": "discard-me", "quiz_answers": None}
    res = await client.put(
        "/api/auth/me/taste-profile", json=payload, headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 200, f"extra-field payload: {res.text}"
    stored = (
        (
            await db_session.execute(
                select(User).where(User.email == "extra@example.com")
            )
        )
        .scalar_one()
        .taste_profile
    )
    assert (
        stored == {"liked_ids": [154587]} and "junk" not in stored
    ), f"junk field persisted from payload {payload}: {stored}"
