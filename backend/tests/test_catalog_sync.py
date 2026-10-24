"""Tests for AniList catalog sync, upsert idempotency, backoff, and relations."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.text import strip_html_tags
from app.models.anime import Anime, Tag
from app.services.anilist import ANILIST_GRAPHQL_URL, AniListClient
from app.services.catalog_sync import CatalogSyncService


@pytest.mark.asyncio
async def test_html_stripping():
    """HTML tags must be stripped and entities unescaped."""
    raw = "<p><b>Elf</b> mage <i>Frieren</i> &amp; party.<br><br>Defeated the Demon King.</p>"
    clean = strip_html_tags(raw)
    assert "<" not in clean
    assert ">" not in clean
    assert "&amp;" not in clean
    assert "&" in clean
    assert "Elf mage Frieren & party." in clean


@pytest.mark.asyncio
async def test_upsert_idempotency_no_duplicates(
    db_session: AsyncSession, anilist_page1_data: dict[str, Any]
):
    """Running upsert twice with the same data creates no duplicate rows."""
    service = CatalogSyncService()
    raw_media = anilist_page1_data["data"]["Page"]["media"]

    parsed_items = []
    for m in raw_media:
        parsed_items.append(
            {
                "id": m["id"],
                "id_mal": m.get("idMal"),
                "title_romaji": m["title"]["romaji"],
                "title_english": m["title"]["english"],
                "title_native": m["title"]["native"],
                "synonyms": m.get("synonyms") or [],
                "description": strip_html_tags(m.get("description")),
                "cover_image_url": m["coverImage"]["large"],
                "banner_image_url": m.get("bannerImage"),
                "format": m.get("format"),
                "episodes": m.get("episodes"),
                "duration": m.get("duration"),
                "status": m.get("status"),
                "season": m.get("season"),
                "season_year": m.get("seasonYear"),
                "average_score": m.get("averageScore"),
                "popularity": m.get("popularity", 0),
                "is_adult": m.get("isAdult", False),
                "source": m.get("source"),
                "main_studio": "TestStudio",
                "updated_at_anilist": m.get("updatedAt"),
                "genres": m.get("genres", []),
                "tags": [
                    {
                        "name": t["name"],
                        "category": t.get("category"),
                        "is_adult": t.get("isAdult", False),
                        "rank": t.get("rank", 0),
                    }
                    for t in m.get("tags", [])
                ],
            }
        )

    # First upsert
    count1 = await service.upsert_batch(db_session, parsed_items)
    assert count1 == len(parsed_items)

    stmt = select(Anime)
    res1 = await db_session.execute(stmt)
    total_animes_1 = len(res1.scalars().all())

    # Second upsert (idempotent run)
    count2 = await service.upsert_batch(db_session, parsed_items)
    assert count2 == len(parsed_items)

    res2 = await db_session.execute(stmt)
    total_animes_2 = len(res2.scalars().all())

    assert total_animes_1 == total_animes_2 == len(parsed_items)


@pytest.mark.asyncio
async def test_link_replacement_on_update(db_session: AsyncSession):
    """On update, removed genres and tags disappear, and ranks refresh."""
    service = CatalogSyncService()
    aid = 9999

    # Initial insert with Action, Fantasy and Magic (rank 80)
    initial_data = [
        {
            "id": aid,
            "title_romaji": "Test Anime",
            "title_english": "Test Anime",
            "title_native": "テスト",
            "synonyms": [],
            "description": "Initial synopsis",
            "popularity": 100,
            "genres": ["Action", "Fantasy"],
            "tags": [
                {"name": "Magic", "category": "Theme", "is_adult": False, "rank": 80}
            ],
        }
    ]
    await service.upsert_batch(db_session, initial_data)

    # Verify initial links
    stmt = (
        select(Anime)
        .where(Anime.id == aid)
        .options(selectinload(Anime.genres), selectinload(Anime.tags))
    )
    res = await db_session.execute(stmt)
    anime = res.scalar_one()
    assert {g.name for g in anime.genres} == {"Action", "Fantasy"}
    assert {t.name for t in anime.tags} == {"Magic"}

    # Update: remove Action and Fantasy, add Drama; update Magic rank to 95, add Travel (rank 90)
    updated_data = [
        {
            "id": aid,
            "title_romaji": "Test Anime Updated",
            "title_english": "Test Anime Updated",
            "title_native": "テスト",
            "synonyms": [],
            "description": "Updated synopsis",
            "popularity": 200,
            "genres": ["Drama"],
            "tags": [
                {"name": "Magic", "category": "Theme", "is_adult": False, "rank": 95},
                {"name": "Travel", "category": "Theme", "is_adult": False, "rank": 90},
            ],
        }
    ]
    await service.upsert_batch(db_session, updated_data)

    res_updated = await db_session.execute(stmt)
    anime_updated = res_updated.scalar_one()

    # Old genres Action and Fantasy must be gone; Drama present
    genre_names = {g.name for g in anime_updated.genres}
    assert genre_names == {"Drama"}
    assert "Action" not in genre_names
    assert "Fantasy" not in genre_names

    # Tags refreshed: Magic and Travel present
    tag_names = {t.name for t in anime_updated.tags}
    assert tag_names == {"Magic", "Travel"}

    # Check rank refreshed to 95 in anime_tags table
    from app.models.anime import anime_tags

    tag_rank_stmt = select(anime_tags.c.rank).where(
        anime_tags.c.anime_id == aid,
        anime_tags.c.tag_id.in_(select(Tag.id).where(Tag.name == "Magic")),
    )
    rank_res = await db_session.execute(tag_rank_stmt)
    assert rank_res.scalar() == 95


@pytest.mark.asyncio
@respx.mock
async def test_sync_backoff_on_429():
    """Client handles 429 and Retry-After header with retry."""
    # First response: 429 with Retry-After: 0.05
    respx.post(ANILIST_GRAPHQL_URL).mock(
        side_effect=[
            httpx.Response(
                status_code=429,
                headers={"Retry-After": "0.05"},
                content=b"Too Many Requests",
            ),
            httpx.Response(
                status_code=200,
                headers={"X-RateLimit-Remaining": "50"},
                json={
                    "data": {
                        "Page": {
                            "pageInfo": {"hasNextPage": False, "total": 1},
                            "media": [
                                {
                                    "id": 100,
                                    "title": {"romaji": "Retry Anime"},
                                    "isAdult": False,
                                    "genres": [],
                                    "tags": [],
                                }
                            ],
                        }
                    }
                },
            ),
        ]
    )

    async with AniListClient(requests_per_minute=300) as client:
        items, page_info = await client.fetch_media_page(page=1)
        assert len(items) == 1
        assert items[0]["id"] == 100


@pytest.mark.asyncio
@respx.mock
async def test_sync_pagination_and_incremental(
    anilist_page1_data: dict[str, Any], anilist_page2_data: dict[str, Any]
):
    """Client correctly passes page and updatedAt_greater arguments."""
    route = respx.post(ANILIST_GRAPHQL_URL).mock(
        side_effect=[
            httpx.Response(200, json=anilist_page1_data),
            httpx.Response(200, json=anilist_page2_data),
        ]
    )

    async with AniListClient(requests_per_minute=300) as client:
        # Page 1
        items1, info1 = await client.fetch_media_page(
            page=1, updated_at_greater=1600000000
        )
        assert len(items1) == 5
        assert info1["hasNextPage"] is True

        # Page 2
        items2, info2 = await client.fetch_media_page(
            page=2, updated_at_greater=1600000000
        )
        assert len(items2) == 5
        assert info2["hasNextPage"] is False

    # Check request payloads included variables
    req1 = route.calls[0].request
    req1_data = json.loads(req1.content)
    assert req1_data["variables"]["page"] == 1
    assert req1_data["variables"]["sort"] == ["UPDATED_AT_DESC"]

    req2 = route.calls[1].request
    req2_data = json.loads(req2.content)
    assert req2_data["variables"]["page"] == 2


@pytest.mark.asyncio
async def test_sync_service_state_management(tmp_path: Path):
    """Resume state file saves parameters and checkpoints."""
    state_file = tmp_path / ".test_sync_state.json"
    service = CatalogSyncService(state_file=state_file)

    assert service.load_state() is None

    test_state = {
        "limit": 50,
        "since": None,
        "sort": "POPULARITY_DESC",
        "sfw_page": 2,
        "total_synced": 40,
    }
    service.save_state(test_state)

    loaded = service.load_state()
    assert loaded is not None
    assert loaded["limit"] == 50
    assert loaded["sfw_page"] == 2
    assert "last_updated" in loaded

    service.clear_state()
    assert service.load_state() is None
