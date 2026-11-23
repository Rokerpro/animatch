"""Shared mature-content rules for catalog and user-list endpoints."""

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.anime import Anime, Genre, Tag, anime_genres, anime_tags

MATURE_GENRES = frozenset({"hentai", "ecchi"})


async def load_anime_tag_ranks(db: AsyncSession, anime: Anime) -> dict[str, int]:
    """Load per-title tag ranks for the synchronous maturity helper."""
    result = await db.execute(
        select(Tag.name, anime_tags.c.rank)
        .join(anime_tags, anime_tags.c.tag_id == Tag.id)
        .where(anime_tags.c.anime_id == anime.id)
    )
    return {name: rank for name, rank in result.all()}


def is_mature_anime(anime: Anime, tag_ranks: dict[str, int] | None = None) -> bool:
    """Apply the server-side mature rule to an anime ORM record."""
    return (
        anime.is_adult
        or any(
            tag.is_adult
            and (tag_ranks or {}).get(tag.name, 0) >= settings.MATURE_TAG_MIN_RANK
            for tag in anime.tags
        )
        or any(genre.name.lower() in MATURE_GENRES for genre in anime.genres)
    )


def mature_anime_clause():
    """Build the SQL predicate matching :func:`is_mature_anime`."""
    has_adult_tag = exists(
        select(1)
        .select_from(anime_tags)
        .join(Tag, anime_tags.c.tag_id == Tag.id)
        .where(
            anime_tags.c.anime_id == Anime.id,
            Tag.is_adult.is_(True),
            anime_tags.c.rank >= settings.MATURE_TAG_MIN_RANK,
        )
    )
    has_mature_genre = exists(
        select(1)
        .select_from(anime_genres)
        .join(Genre, anime_genres.c.genre_id == Genre.id)
        .where(
            anime_genres.c.anime_id == Anime.id,
            func.lower(Genre.name).in_(MATURE_GENRES),
        )
    )
    return or_(Anime.is_adult.is_(True), has_adult_tag, has_mature_genre)
