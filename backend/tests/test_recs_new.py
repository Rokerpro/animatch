"""Phase 8 personalized discovery recommendation endpoint tests."""

import numpy as np
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.anime import Anime
from app.models.list_entry import ListEntry
from app.models.user import User
from app.recs.engine import recommend_from_quiz
from app.recs.vectors import VectorIndex


@pytest.fixture
async def new_rec_index(seeded_catalog, db_session, monkeypatch):
    rows = (await db_session.execute(select(Anime))).scalars().all()
    items = []
    for anime in rows:
        items.append(
            {
                "id": anime.id,
                "title": anime.title_english or anime.title_romaji or "title",
                "franchise_id": 154587 if anime.id in (154587, 5114) else None,
                "average_score": anime.average_score,
                "popularity": anime.popularity,
                "episodes": anime.episodes,
                "season_year": anime.season_year,
                "is_adult": anime.is_adult,
                "format": anime.format,
                "status": anime.status,
                "genres": [genre.name for genre in anime.genres],
                "tags": [{"name": tag.name, "rank": 80} for tag in anime.tags],
            }
        )
    index = VectorIndex.build(items)
    monkeypatch.setattr("app.api.recs.get_index", lambda: index)
    return index


async def register_and_token(client, register_user, email="new@example.com"):
    token = await register_user(email)
    return {"X-CSRF-Token": token}


@pytest.mark.asyncio
async def test_new_recs_requires_login_and_csrf(client, register_user, new_rec_index):
    payload = {"quiz_answers": {"mood": "epic"}}
    assert (await client.post("/api/recs/new", json=payload)).status_code == 401
    await register_user("csrf-new@example.com")
    response = await client.post("/api/recs/new", json=payload)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_new_recs_validates_question_ids_and_answer_counts(
    client, register_user, new_rec_index
):
    headers = await register_and_token(
        client, register_user, "validation-new@example.com"
    )
    invalid = [
        {},
        {"quiz_answers": {}},
        {"quiz_answers": {"unknown": "any"}},
        {"quiz_answers": {"themes": "fantasy"}},
        {
            "quiz_answers": {
                "mood": "epic",
                "length": "short",
                "era": "recent",
                "extra": "any",
            }
        },
        {"quiz_answers": {"mood": "not-an-answer"}},
    ]
    for payload in invalid:
        response = await client.post("/api/recs/new", json=payload, headers=headers)
        assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_new_recs_user_isolation_exclusions_modes_maturity_and_determinism(
    client, register_user, new_rec_index, db_session
):
    headers = await register_and_token(
        client, register_user, "discovery-new@example.com"
    )
    user = (
        await db_session.execute(
            select(User).where(User.email == "discovery-new@example.com")
        )
    ).scalar_one()
    first = await client.post(
        "/api/recs/new?n=10", json={"quiz_answers": {"mood": "epic"}}, headers=headers
    )
    assert first.status_code == 200, first.text
    assert first.json()["mode"] == "quiz_fallback"
    first_ids = [item["id"] for item in first.json()["results"]]

    other = User(
        email="other-new@example.com", display_name="Other", taste_profile=None
    )
    db_session.add(other)
    await db_session.flush()
    db_session.add(
        ListEntry(user_id=other.id, anime_id=154587, status="completed", rating=10)
    )
    await db_session.commit()
    after_other = await client.post(
        "/api/recs/new?n=10", json={"quiz_answers": {"mood": "epic"}}, headers=headers
    )
    assert [item["id"] for item in after_other.json()["results"]] == first_ids

    user.taste_profile = {"liked_ids": [154587]}
    all_status_ids = [
        record.id
        for record in new_rec_index.records
        if record.id not in {154587, 5114, 16498, 1535}
    ][:5]
    franchise_sibling = next(
        record.id
        for record in new_rec_index.records
        if record.id not in {154587, 5114, 16498, 1535, *all_status_ids}
    )
    new_rec_index.get(16498).franchise_id = 987654
    new_rec_index.get(franchise_sibling).franchise_id = 987654
    db_session.add_all(
        [
            ListEntry(user_id=user.id, anime_id=16498, status="planning"),
            ListEntry(user_id=user.id, anime_id=1535, status="dropped"),
            *[
                ListEntry(user_id=user.id, anime_id=anime_id, status=status)
                for anime_id, status in zip(
                    all_status_ids,
                    ("planning", "watching", "completed", "dropped", "on_hold"),
                    strict=True,
                )
            ],
        ]
    )
    await db_session.commit()
    response = await client.post(
        "/api/recs/new?includeMature=false&n=10",
        json={"quiz_answers": {"mood": "epic", "length": "any", "era": "any"}},
        headers=headers,
    )
    body = response.json()
    assert response.status_code == 200, response.text
    ids = [item["id"] for item in body["results"]]
    assert body["mode"] == "novelty"
    assert not {
        154587,
        16498,
        1535,
        franchise_sibling,
        *all_status_ids,
    }.intersection(ids)
    assert all(not item["isAdult"] for item in body["results"])
    assert all(
        "because you liked" not in item["reason"].casefold() for item in body["results"]
    )
    for item in body["results"]:
        record = new_rec_index.get(item["id"])
        assert set(item["explanation"]["sharedGenres"]) <= set(record.genres)
        assert set(item["explanation"]["sharedTags"]) <= set(record.tags)
        assert all(
            answer in item["reason"] for answer in item["explanation"]["quizAnswers"]
        )
        if "different direction with " in item["reason"]:
            novelty_phrase = item["reason"].split("different direction with ", 1)[1]
            reason_features = novelty_phrase.rstrip(".").split(", ")
            assert set(reason_features) <= set(record.genres) | set(record.tags)
    repeated = await client.post(
        "/api/recs/new?includeMature=false&n=10",
        json={"quiz_answers": {"mood": "epic", "length": "any", "era": "any"}},
        headers=headers,
    )
    assert [item["id"] for item in repeated.json()["results"]] == ids


def test_new_recs_novelty_ranks_underexplored_genre_and_cannot_bypass_quality(
    monkeypatch,
):
    items = [
        {
            "id": 703,
            "title": "Underexplored Mystery",
            "franchise_id": None,
            "average_score": 80,
            "popularity": 500,
            "season_year": 2020,
            "status": "FINISHED",
            "format": "TV",
            "genres": ["Action", "Adventure", "Mystery"],
        },
        {
            "id": 704,
            "title": "Familiar Fantasy",
            "franchise_id": None,
            "average_score": 80,
            "popularity": 500,
            "season_year": 2020,
            "status": "FINISHED",
            "format": "TV",
            "genres": ["Action", "Adventure", "Fantasy"],
        },
        {
            "id": 705,
            "title": "Underexplored Drama",
            "franchise_id": None,
            "average_score": 80,
            "popularity": 500,
            "season_year": 2020,
            "status": "FINISHED",
            "format": "TV",
            "genres": ["Action", "Adventure", "Drama"],
        },
        {
            "id": 706,
            "title": "Mature Action",
            "franchise_id": None,
            "average_score": 80,
            "popularity": 500,
            "season_year": 2020,
            "status": "FINISHED",
            "format": "TV",
            "is_adult": True,
            "genres": ["Action", "Adventure", "Mystery"],
        },
    ]
    index = VectorIndex.build(items)
    monkeypatch.setattr(settings, "REC_MIN_SALIENT_FEATURES", 2)
    monkeypatch.setattr(settings, "REC_MMR_LAMBDA", 1.0)
    monkeypatch.setattr(
        "app.recs.engine._relevance_scores", lambda scores: np.ones(len(scores))
    )
    ranked = recommend_from_quiz(
        {"mood": "epic"},
        n=2,
        index=index,
        strict_quality_floor=True,
        novelty_weights={"genre:Mystery": 0.0, "genre:Fantasy": 1.0},
        novelty_weight=1.0,
    )
    assert ranked
    # If both controlled candidates survive, underexplored Mystery ranks first.
    ids = [item.id for item in ranked]
    if 703 in ids and 704 in ids:
        assert ids.index(703) < ids.index(704)
    regular = recommend_from_quiz(
        {"mood": "epic"}, n=10, index=index, strict_quality_floor=True
    )
    mature = recommend_from_quiz(
        {"mood": "epic"},
        n=10,
        index=index,
        strict_quality_floor=True,
        include_mature=True,
    )
    assert 706 not in [item.id for item in regular]
    assert 706 in [item.id for item in mature]

    monkeypatch.setattr(settings, "REC_MIN_SCORE", 101)
    blocked = recommend_from_quiz(
        {"mood": "epic"},
        n=2,
        index=index,
        strict_quality_floor=True,
        novelty_weights={"genre:Mystery": 0.0},
        novelty_weight=100.0,
    )
    assert blocked == []
