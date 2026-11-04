"""Personal recommendation endpoint behavior."""

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.anime import Anime
from app.models.list_entry import ListEntry
from app.models.user import User
from app.recs.vectors import VectorIndex


@pytest.fixture
async def rec_index(seeded_catalog, db_session, monkeypatch):
    result = await db_session.execute(select(Anime))
    rows = result.scalars().all()
    items = []
    for anime in rows:
        anime.franchise_id = 154587 if anime.id in (154587, 5114) else None
        tags = [{"name": t.name, "rank": 80} for t in anime.tags]
        tags.append({"name": settings.REC_SALIENT_TAG_STOPLIST[0], "rank": 99})
        items.append(
            {
                "id": anime.id,
                "title": anime.title_english or anime.title_romaji or "title",
                "franchise_id": anime.franchise_id,
                "average_score": anime.average_score,
                "popularity": anime.popularity,
                "episodes": anime.episodes,
                "season_year": anime.season_year,
                "is_adult": anime.is_adult,
                "format": anime.format,
                "genres": [g.name for g in anime.genres],
                "tags": tags,
            }
        )
    index = VectorIndex.build(items)
    monkeypatch.setattr("app.api.recs.get_index", lambda: index)
    return index


@pytest.mark.asyncio
async def test_recs_me_empty_has_no_fallback(client, rec_index, register_user):
    await register_user("emptyrec@example.com")
    response = await client.get("/api/recs/me")
    assert (
        response.status_code == 200 and response.json() == []
    ), f"empty profile must not fall back to popular titles: {response.text}"


@pytest.mark.asyncio
async def test_recs_me_profile_ratings_exclusions_and_maturity(
    client, rec_index, db_session, register_user
):
    await register_user("personalrec@example.com")
    user = (
        await db_session.execute(
            select(User).where(User.email == "personalrec@example.com")
        )
    ).scalar_one()
    user.taste_profile = {"liked_ids": [154587]}
    db_session.add_all(
        [
            ListEntry(user_id=user.id, anime_id=16498, status="completed", rating=9),
            ListEntry(user_id=user.id, anime_id=1535, status="completed", rating=4),
        ]
    )
    await db_session.commit()
    response = await client.get("/api/recs/me?n=50")
    assert (
        response.status_code == 200
    ), f"profile and ratings recommendation payload: {response.text}"
    ids = [item["id"] for item in response.json()]
    assert (
        16498 not in ids and 1535 not in ids and 154587 not in ids and 5114 not in ids
    ), f"already listed/liked/franchise payload: {response.json()}"
    assert all(
        not item["isAdult"] for item in response.json()
    ), f"adult recommendation payload: {response.json()}"
    assert (
        len(ids) <= len(rec_index) - 3
    ), f"too many recommendations for available candidates: {response.json()}"
    assert all(
        settings.REC_SALIENT_TAG_STOPLIST[0] not in item["reason"]
        and settings.REC_SALIENT_TAG_STOPLIST[0]
        not in item["explanation"]["sharedTags"]
        for item in response.json()
    ), f"stoplist reason payload: {response.json()}"
    seed_genres = set().union(
        *(set(rec_index.get(aid).genres) for aid in (154587, 16498, 1535))
    )
    seed_tags = set().union(
        *(set(rec_index.get(aid).tags) for aid in (154587, 16498, 1535))
    )
    for item in response.json():
        record = rec_index.get(item["id"])
        explanation = item["explanation"]
        assert (
            set(explanation["sharedGenres"]) <= set(record.genres) & seed_genres
        ), f"shared genre payload: {item}"
        assert (
            set(explanation["sharedTags"]) <= set(record.tags) & seed_tags
        ), f"shared tag payload: {item}"


@pytest.mark.asyncio
async def test_recs_me_profile_only_and_ratings_only(
    client, rec_index, db_session, register_user
):
    await register_user("branches@example.com")
    user = (
        await db_session.execute(
            select(User).where(User.email == "branches@example.com")
        )
    ).scalar_one()
    user.taste_profile = {"liked_ids": [154587]}
    await db_session.commit()
    profile = await client.get("/api/recs/me?n=3")
    assert profile.status_code == 200 and isinstance(
        profile.json(), list
    ), f"profile-only payload: {profile.text}"
    user.taste_profile = None
    db_session.add(
        ListEntry(user_id=user.id, anime_id=154587, status="completed", rating=9)
    )
    await db_session.commit()
    ratings = await client.get("/api/recs/me?n=3")
    assert ratings.status_code == 200 and isinstance(
        ratings.json(), list
    ), f"ratings-only payload: {ratings.text}"
