"""Seasons and related entries for one anime, read from AniList relation edges.

Edges are stored only for catalog titles, but they may point at titles outside
the catalog. The main-story walk follows PREQUEL/SEQUEL edges in both
directions (outgoing and incoming), so a missing or hidden entry in the middle
of a chain is skipped in the output without splitting the chain.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anime import Anime, anime_relations
from app.services.maturity import mature_anime_clause

MAIN_TYPES = ("PREQUEL", "SEQUEL")
EXTRA_TYPES = ("SIDE_STORY", "SPIN_OFF", "SUMMARY", "ALTERNATIVE")
SEASON_RANK = {"WINTER": 0, "SPRING": 1, "SUMMER": 2, "FALL": 3}
# AniList often links OVAs and specials as sequels; they read as extras.
EXTRA_FORMATS = frozenset({"OVA", "SPECIAL", "MUSIC"})
# shortcut: stops the walk on very large PREQUEL/SEQUEL graphs; raise it if a
# real franchise gets cut off.
MAX_CHAIN = 200


def release_key(anime: Anime) -> tuple[bool, int, int, int]:
    """Release order from season_year and season; no start date is stored.

    Titles without a year go last; ties fall back to the AniList id.
    """
    return (
        anime.season_year is None,
        anime.season_year or 0,
        SEASON_RANK.get(anime.season or "", len(SEASON_RANK)),
        anime.id,
    )


async def main_story_ids(db: AsyncSession, anime_id: int) -> set[int]:
    """All ids reachable over PREQUEL/SEQUEL edges, in either direction."""
    seen = {anime_id}
    frontier = [anime_id]
    while frontier and len(seen) < MAX_CHAIN:
        rows = await db.execute(
            select(anime_relations.c.anime_id, anime_relations.c.related_id).where(
                anime_relations.c.rel_type.in_(MAIN_TYPES),
                or_(
                    anime_relations.c.anime_id.in_(frontier),
                    anime_relations.c.related_id.in_(frontier),
                ),
            )
        )
        frontier = []
        for pair in rows.all():
            for node in pair:
                if node not in seen:  # the seen set is what stops loops
                    seen.add(node)
                    frontier.append(node)
    return seen


async def load_seasons(
    db: AsyncSession, anime_id: int, include_mature: bool
) -> tuple[list[Anime], list[tuple[Anime, str]]]:
    """Return the visible main story in release order and the visible extras.

    OVAs, specials and music videos found in the PREQUEL/SEQUEL chain are
    listed as side stories, unless one is the requested title.

    Linked titles outside the catalog are left out: only their id is known.
    """
    chain = await main_story_ids(db, anime_id)
    extra_rows = await db.execute(
        select(anime_relations.c.related_id, anime_relations.c.rel_type).where(
            anime_relations.c.anime_id.in_(chain),
            anime_relations.c.rel_type.in_(EXTRA_TYPES),
            anime_relations.c.related_id.not_in(chain),
        )
    )
    extra_types: dict[int, str] = {}
    for related_id, rel_type in sorted(extra_rows.all()):
        extra_types.setdefault(related_id, rel_type)

    query = select(Anime).where(Anime.id.in_(chain | extra_types.keys()))
    if not include_mature:
        query = query.where(~mature_anime_clause())
    found = {anime.id: anime for anime in (await db.execute(query)).scalars()}

    main: list[Anime] = []
    extras: list[tuple[Anime, str]] = [
        (found[i], rel_type) for i, rel_type in extra_types.items() if i in found
    ]
    for i in chain:
        anime = found.get(i)
        if anime is None:
            continue
        if i != anime_id and anime.format in EXTRA_FORMATS:
            extras.append((anime, "SIDE_STORY"))
        else:
            main.append(anime)
    main.sort(key=release_key)
    extras.sort(key=lambda pair: release_key(pair[0]))
    return main, extras
