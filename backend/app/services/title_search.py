"""Shared FTS title lookup and close-match suggestions."""

from difflib import SequenceMatcher

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import TextClause

from app.core.text import normalize_title_search, sanitize_fts_query
from app.models.anime import Anime


def title_search_clause(query: str | None) -> TextClause | None:
    """Build the parameterized SQLite FTS predicate shared by API and CLI."""
    expression = sanitize_fts_query(normalize_title_search(query))
    if not expression:
        return None
    return text(
        "anime.id IN (SELECT rowid FROM anime_fts "
        "WHERE anime_fts MATCH :match_q)"
    ).bindparams(match_q=expression)


def normalized_title_column(column):
    """Return a SQL expression matching title apostrophe normalization."""
    expression = column
    for mark in ("‘", "’", "ʼ", "`"):
        expression = func.replace(expression, mark, "'")
    return func.replace(expression, "'", "")


async def find_title_matches(
    db: AsyncSession, query: str, limit: int = 5
) -> list[Anime]:
    """Find title matches using the same normalized FTS clause as the API."""
    clause = title_search_clause(query)
    if clause is None:
        return []
    statement = (
        select(Anime)
        .where(clause)
        .order_by(Anime.popularity.desc(), Anime.id.asc())
        .limit(limit)
    )
    result = await db.execute(statement)
    return list(result.scalars().all())


async def closest_title_matches(
    db: AsyncSession, query: str, limit: int = 5
) -> list[Anime]:
    """Return the closest catalog title names for a failed title lookup."""
    normalized_query = normalize_title_search(query)
    result = await db.execute(select(Anime))
    rows = list(result.scalars().all())

    def similarity(anime: Anime) -> tuple[float, int, int]:
        titles = [anime.title_english, anime.title_romaji, anime.title_native]
        ratio = max(
            (
                SequenceMatcher(
                    None, normalized_query, normalize_title_search(title)
                ).ratio()
                for title in titles
                if title
            ),
            default=0.0,
        )
        return (-ratio, -(anime.popularity or 0), anime.id)

    return sorted(rows, key=similarity)[:limit]
