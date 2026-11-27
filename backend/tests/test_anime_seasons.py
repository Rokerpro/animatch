"""Tests for GET /api/anime/{id}/seasons (main story and related extras)."""

import copy
from typing import Any

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anime import Anime, anime_relations
from app.services.anilist import parse_media_item
from app.services.catalog_sync import CatalogSyncService

# High ids so nothing clashes with the AniList fixture catalog.
BASE = 900_000


async def add_anime(db: AsyncSession, *rows: tuple[int, int | None, str | None]):
    """Add (id offset, season_year, season) rows as plain catalog titles."""
    for offset, year, season in rows:
        db.add(
            Anime(
                id=BASE + offset,
                title_english=f"Title {offset}",
                cover_image_url=f"https://img.test/{offset}.jpg",
                cover_color="#336699",
                format="TV",
                episodes=12,
                season_year=year,
                season=season,
                synonyms=[],
                popularity=0,
                is_adult=False,
            )
        )
    await db.commit()


async def link(db: AsyncSession, *edges: tuple[int, int, str]):
    """Store (from offset, to offset, type) edges as the sync would."""
    await db.execute(
        insert(anime_relations),
        [
            {"anime_id": BASE + a, "related_id": BASE + b, "rel_type": rel}
            for a, b, rel in edges
        ],
    )
    await db.commit()


def chain(a: int, b: int) -> list[tuple[int, int, str]]:
    """b is the sequel of a, stored from both sides like AniList does."""
    return [(a, b, "SEQUEL"), (b, a, "PREQUEL")]


async def seasons(client, offset: int, mature: bool = False) -> dict[str, Any]:
    response = await client.get(
        f"/api/anime/{BASE + offset}/seasons?includeMature={str(mature).lower()}"
    )
    assert response.status_code == 200, response.text
    return response.json()


def main_ids(body: dict[str, Any]) -> list[int]:
    return [item["id"] - BASE for item in body["main"]]


@pytest.mark.asyncio
async def test_sync_stores_relation_edges_including_titles_outside_catalog(
    db_session: AsyncSession, anilist_page1_data: dict[str, Any]
):
    item = copy.deepcopy(anilist_page1_data["data"]["Page"]["media"][0])
    item["relations"] = {
        "edges": [
            {"relationType": "SEQUEL", "node": {"id": 99_999_991, "type": "ANIME"}},
            {"relationType": "SOURCE", "node": {"id": 99_999_992, "type": "MANGA"}},
        ]
    }
    await CatalogSyncService().upsert_batch(db_session, [parse_media_item(item)])
    rows = (
        await db_session.execute(
            select(anime_relations.c.related_id, anime_relations.c.rel_type).where(
                anime_relations.c.anime_id == item["id"]
            )
        )
    ).all()
    assert rows == [(99_999_991, "SEQUEL")]


@pytest.mark.asyncio
async def test_normal_chain_in_release_order_with_extras(client, db_session):
    await add_anime(
        db_session,
        (1, 2019, "WINTER"),
        (2, 2019, "FALL"),
        (3, 2021, "SPRING"),
        (4, 2020, None),  # side story
        (5, 2020, None),  # summary
        (6, 2022, None),  # adaptation: left out
    )
    await link(
        db_session,
        *chain(1, 2),
        *chain(2, 3),
        (1, 4, "SIDE_STORY"),
        (3, 5, "SUMMARY"),
        (2, 6, "ADAPTATION"),
        (2, 6, "CHARACTER"),
        (2, 6, "OTHER"),
        (2, 6, "SOURCE"),
    )
    body = await seasons(client, 2)
    assert main_ids(body) == [1, 2, 3]
    assert [item["position"] for item in body["main"]] == [1, 2, 3]
    assert [item["isCurrent"] for item in body["main"]] == [False, True, False]
    assert body["main"][0] == {
        "id": BASE + 1,
        "title": "Title 1",
        "coverImage": "https://img.test/1.jpg",
        "coverColor": "#336699",
        "format": "TV",
        "year": 2019,
        "episodes": 12,
        "position": 1,
        "isCurrent": False,
    }
    assert [(item["id"] - BASE, item["relation"]) for item in body["extras"]] == [
        (4, "SIDE_STORY"),
        (5, "SUMMARY"),
    ]
    # Every entry in the chain sees the same story.
    assert main_ids(await seasons(client, 3)) == [1, 2, 3]


@pytest.mark.asyncio
async def test_branching_chain_includes_every_branch(client, db_session):
    await add_anime(
        db_session, (1, 2010, None), (2, 2012, None), (3, 2011, None), (4, 2013, None)
    )
    # 1 has two sequels; 3 continues into 4.
    await link(db_session, *chain(1, 2), *chain(1, 3), *chain(3, 4))
    body = await seasons(client, 4)
    assert main_ids(body) == [1, 3, 2, 4]
    assert [item["isCurrent"] for item in body["main"]] == [False, False, False, True]


@pytest.mark.asyncio
async def test_loop_in_relation_graph_terminates(client, db_session):
    await add_anime(db_session, (1, 2001, None), (2, 2002, None), (3, 2003, None))
    await link(db_session, *chain(1, 2), *chain(2, 3), *chain(3, 1), (2, 2, "SEQUEL"))
    assert main_ids(await seasons(client, 1)) == [1, 2, 3]


@pytest.mark.asyncio
async def test_missing_middle_entry_is_skipped_without_breaking_chain(
    client, db_session
):
    await add_anime(db_session, (1, 2015, None), (3, 2017, None), (4, 2016, None))
    # 2 is not in the catalog, so only edges pointing at it exist.
    await link(
        db_session,
        (1, 2, "SEQUEL"),
        (3, 2, "PREQUEL"),
        (1, 4, "SPIN_OFF"),
        (1, 50, "SIDE_STORY"),  # extra outside the catalog: left out
    )
    body = await seasons(client, 1)
    assert main_ids(body) == [1, 3]
    assert [item["position"] for item in body["main"]] == [1, 2]
    assert [(item["id"] - BASE, item["relation"]) for item in body["extras"]] == [
        (4, "SPIN_OFF")
    ]
    assert main_ids(await seasons(client, 3)) == [1, 3]


@pytest.mark.asyncio
async def test_adult_entries_are_filtered_on_the_server(client, db_session):
    await add_anime(
        db_session, (1, 2001, None), (2, 2002, None), (3, 2003, None), (4, 2004, None)
    )
    for offset in (2, 4):
        anime = await db_session.get(Anime, BASE + offset)
        anime.is_adult = True
    await db_session.commit()
    await link(db_session, *chain(1, 2), *chain(2, 3), (3, 4, "SIDE_STORY"))

    body = await seasons(client, 1)
    assert main_ids(body) == [1, 3]
    assert body["extras"] == []
    shown = await seasons(client, 1, mature=True)
    assert main_ids(shown) == [1, 2, 3]
    assert [item["id"] - BASE for item in shown["extras"]] == [4]
    hidden = await client.get(f"/api/anime/{BASE + 2}/seasons")
    assert hidden.status_code == 404


@pytest.mark.asyncio
async def test_standalone_show_returns_nothing(client, db_session):
    await add_anime(db_session, (1, 2020, None), (2, 2021, None))
    await link(db_session, (1, 2, "ADAPTATION"), (1, 60, "OTHER"))
    assert await seasons(client, 1) == {"main": [], "extras": []}
    assert await seasons(client, 2) == {"main": [], "extras": []}
    missing = await client.get(f"/api/anime/{BASE + 99}/seasons")
    assert missing.status_code == 404
