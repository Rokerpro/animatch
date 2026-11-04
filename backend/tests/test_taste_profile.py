"""Validation and persistence tests for saved taste profiles."""

import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


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
    client, seeded_catalog, register_user
):
    csrf = await register_user("invalidtaste@example.com")
    quiz = json.loads((Path(__file__).parents[1] / "app/data/quiz.json").read_text())
    known_question = quiz["questions"][0]
    cases = [
        ({"liked_ids": [999999]}, "unknown liked id"),
        ({"liked_ids": [154587] * 6}, "too many liked ids"),
        ({"liked_ids": [154587, 154587]}, "duplicate liked ids"),
        ({"liked_ids": ["not-an-integer"]}, "non-integer liked id"),
        ({"quiz_answers": {"unknown_question": "x"}}, "unknown question"),
        ({"quiz_answers": {known_question["id"]: "unknown_answer"}}, "unknown answer"),
    ]
    for payload, label in cases:
        res = await client.put(
            "/api/auth/me/taste-profile", json=payload, headers={"X-CSRF-Token": csrf}
        )
        assert res.status_code == 422, f"{label} payload {payload}: {res.text}"


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
