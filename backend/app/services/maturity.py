"""Shared mature-content rules for catalog and user-list endpoints."""

from sqlalchemy import exists, func, or_, select

from app.models.anime import Anime, Genre, Tag, anime_genres, anime_tags

MATURE_GENRES = frozenset({"hentai", "ecchi"})


def is_mature_anime(anime: Anime) -> bool:
    """Return whether an anime is adult, has an adult tag, or mature genre."""
    return (
        anime.is_adult
        or any(tag.is_adult for tag in anime.tags)
        or any(genre.name.lower() in MATURE_GENRES for genre in anime.genres)
    )


def mature_anime_clause():
    """Build the SQL predicate matching :func:`is_mature_anime`."""
    has_adult_tag = exists(
        select(1)
        .select_from(anime_tags)
        .join(Tag, anime_tags.c.tag_id == Tag.id)
        .where(anime_tags.c.anime_id == Anime.id, Tag.is_adult.is_(True))
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
