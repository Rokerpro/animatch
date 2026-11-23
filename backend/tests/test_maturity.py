"""Mature visibility rules for rank-qualified adult tags."""

import pytest
from sqlalchemy import insert, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.anime import Anime, Tag, anime_tags
from app.services.maturity import (
    is_mature_anime,
    load_anime_tag_ranks,
    mature_anime_clause,
)


@pytest.mark.asyncio
async def test_maturity_helper_and_sql_clause_share_rank_boundary(
    db_session, seeded_catalog: None, monkeypatch
):
    monkeypatch.setattr(settings, "MATURE_TAG_MIN_RANK", 60)
    tag = Tag(name="Adult incidental fixture", category="Theme", is_adult=True)
    db_session.add(tag)
    await db_session.flush()

    anime = await db_session.get(Anime, 20)
    for rank, expected in ((59, False), (60, True)):
        await db_session.execute(
            insert(anime_tags)
            .values(anime_id=anime.id, tag_id=tag.id, rank=rank, is_spoiler=False)
            .prefix_with("OR REPLACE")
        )
        await db_session.flush()
        loaded = await db_session.scalar(
            select(Anime)
            .where(Anime.id == anime.id)
            .options(selectinload(Anime.genres), selectinload(Anime.tags))
            .execution_options(populate_existing=True)
        )
        ranks = await load_anime_tag_ranks(db_session, loaded)
        assert is_mature_anime(loaded, ranks) is expected
        mature_ids = set(
            (
                await db_session.scalars(select(Anime.id).where(mature_anime_clause()))
            ).all()
        )
        assert (anime.id in mature_ids) is expected
