"""Anime catalog endpoints: search, filter, detail, genres, tags."""

import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.text import sanitize_fts_query
from app.db.session import get_db
from app.models.anime import Anime, Genre, Tag, anime_genres, anime_tags
from app.schemas.anime import (
    AnimeCard,
    AnimeDetail,
    AnimeListResponse,
    FiltersResponse,
    PageInfo,
    TagDetail,
)

router = APIRouter(tags=["anime"])

ALLOWED_SORTS = {"popularity", "score", "year", "title"}
MATURE_GENRES = {"hentai", "ecchi"}


def parse_comma_list(values: list[str] | None) -> list[str]:
    """Flattens list of strings that may contain comma-separated entries."""
    if not values:
        return []
    result = []
    for val in values:
        for part in val.split(","):
            cleaned = part.strip()
            if cleaned:
                result.append(cleaned)
    return result


def serialize_anime_card(anime: Anime) -> AnimeCard:
    """Serializes an Anime ORM model into AnimeCard schema."""
    display_title = (
        anime.title_english
        or anime.title_romaji
        or anime.title_native
        or "Unknown Title"
    )
    return AnimeCard(
        id=anime.id,
        title=display_title,
        title_romaji=anime.title_romaji,
        title_english=anime.title_english,
        title_native=anime.title_native,
        cover_image=anime.cover_image_url,
        banner_image=anime.banner_image_url,
        format=anime.format,
        status=anime.status,
        episodes=anime.episodes,
        duration=anime.duration,
        year=anime.season_year,
        score=anime.average_score,
        popularity=anime.popularity,
        is_adult=anime.is_adult,
        genres=[g.name for g in anime.genres],
    )


def serialize_anime_detail(
    anime: Anime, tag_details: list[TagDetail] | None = None
) -> AnimeDetail:
    """Serializes an Anime ORM model into full AnimeDetail schema."""
    card = serialize_anime_card(anime)
    tags_list = (
        [td.name for td in tag_details]
        if tag_details is not None
        else [t.name for t in anime.tags]
    )
    return AnimeDetail(
        **card.model_dump(),
        synopsis=anime.description,
        season=anime.season,
        season_year=anime.season_year,
        studio=anime.main_studio,
        source=anime.source,
        id_mal=anime.id_mal,
        synonyms=anime.synonyms or [],
        tags=tags_list,
        tag_details=tag_details or [],
    )


@router.get("/anime", response_model=AnimeListResponse)
async def list_anime(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[
        str | None, Query(description="Search across title fields and synonyms")
    ] = None,
    genres: Annotated[
        list[str] | None, Query(description="Must match all selected genres")
    ] = None,
    exclude_genres: Annotated[
        list[str] | None,
        Query(alias="excludeGenres", description="Must exclude these genres"),
    ] = None,
    tags: Annotated[
        list[str] | None, Query(description="Must match all selected tags")
    ] = None,
    format: Annotated[
        str | None, Query(description="Format e.g. TV, MOVIE, OVA")
    ] = None,
    year_min: Annotated[
        int | None, Query(alias="yearMin", description="Minimum release year")
    ] = None,
    year_max: Annotated[
        int | None, Query(alias="yearMax", description="Maximum release year")
    ] = None,
    min_score: Annotated[
        int | None, Query(alias="minScore", description="Minimum average score 0-100")
    ] = None,
    max_episodes: Annotated[
        int | None, Query(alias="maxEpisodes", description="Maximum episode count")
    ] = None,
    status: Annotated[
        str | None, Query(description="Status e.g. FINISHED, RELEASING")
    ] = None,
    sort: Annotated[
        str, Query(description="Sort by: popularity, score, year, title")
    ] = "popularity",
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=50, alias="pageSize", description="Items per page (max 50)")
    ] = 24,
    per_page: Annotated[
        int | None, Query(ge=1, le=50, alias="perPage", include_in_schema=False)
    ] = None,
    include_mature: Annotated[
        bool, Query(alias="includeMature", description="Include adult content")
    ] = False,
) -> AnimeListResponse:
    """Browse catalog with filters, FTS search, and pagination."""
    effective_page_size = per_page if per_page is not None else page_size
    sort_key = sort.lower().strip()
    if sort_key not in ALLOWED_SORTS:
        sort_key = "popularity"

    query = select(Anime)

    # 1. Search filter via FTS5
    clean_q = q.strip().lower() if q and q.strip() else ""
    if clean_q:
        fts_expr = sanitize_fts_query(clean_q)
        if fts_expr:
            try:
                fts_subquery = text(
                    "anime.id IN (SELECT rowid FROM anime_fts WHERE anime_fts MATCH :match_q)"
                )
                query = query.where(fts_subquery).params(match_q=fts_expr)
            except Exception:
                # Malformed queries never cause 500
                pass
        else:
            # Fallback substring if no valid alphanumeric tokens
            ilike_pat = f"%{clean_q}%"
            query = query.where(
                (Anime.title_romaji.ilike(ilike_pat))
                | (Anime.title_english.ilike(ilike_pat))
                | (Anime.title_native.ilike(ilike_pat))
            )

    # 2. Mature content server-side exclusion
    if not include_mature:
        query = query.where(Anime.is_adult.is_(False))
        # Exclude anime linked to any adult tags
        has_adult_tag = exists(
            select(1)
            .select_from(anime_tags)
            .join(Tag, anime_tags.c.tag_id == Tag.id)
            .where(
                anime_tags.c.anime_id == Anime.id,
                Tag.is_adult.is_(True),
            )
        )
        query = query.where(~has_adult_tag)
        # Exclude anime linked to Hentai or Ecchi genres
        has_mature_genre = exists(
            select(1)
            .select_from(anime_genres)
            .join(Genre, anime_genres.c.genre_id == Genre.id)
            .where(
                anime_genres.c.anime_id == Anime.id,
                func.lower(Genre.name).in_(list(MATURE_GENRES)),
            )
        )
        query = query.where(~has_mature_genre)

    # 3. Genre filters (EXISTS: all selected genres must match)
    parsed_genres = parse_comma_list(genres)
    for gname in parsed_genres:
        has_genre = exists(
            select(1)
            .select_from(anime_genres)
            .join(Genre, anime_genres.c.genre_id == Genre.id)
            .where(
                anime_genres.c.anime_id == Anime.id,
                func.lower(Genre.name) == gname.lower(),
            )
        )
        query = query.where(has_genre)

    # 4. Exclude genres filter (~EXISTS: excluded genres must not match)
    parsed_exclude = parse_comma_list(exclude_genres)
    if parsed_exclude:
        has_excluded_genre = exists(
            select(1)
            .select_from(anime_genres)
            .join(Genre, anime_genres.c.genre_id == Genre.id)
            .where(
                anime_genres.c.anime_id == Anime.id,
                func.lower(Genre.name).in_([eg.lower() for eg in parsed_exclude]),
            )
        )
        query = query.where(~has_excluded_genre)

    # 5. Tag filters (EXISTS: all selected tags must match)
    parsed_tags = parse_comma_list(tags)
    for tname in parsed_tags:
        has_tag = exists(
            select(1)
            .select_from(anime_tags)
            .join(Tag, anime_tags.c.tag_id == Tag.id)
            .where(
                anime_tags.c.anime_id == Anime.id,
                func.lower(Tag.name) == tname.lower(),
            )
        )
        query = query.where(has_tag)

    # 6. Metadata filters
    if format:
        query = query.where(func.upper(Anime.format) == format.strip().upper())
    if year_min is not None:
        query = query.where(Anime.season_year >= year_min)
    if year_max is not None:
        query = query.where(Anime.season_year <= year_max)
    if min_score is not None:
        query = query.where(Anime.average_score >= min_score)
    if max_episodes is not None:
        query = query.where(Anime.episodes <= max_episodes)
    if status:
        query = query.where(func.upper(Anime.status) == status.strip().upper())

    # 7. Total count query
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # 8. Sorting & Ordering
    order_criteria = []

    # Exact title match boost if search term given
    if clean_q:
        exact_match_score = case(
            (func.lower(Anime.title_romaji) == clean_q, 1),
            (func.lower(Anime.title_english) == clean_q, 1),
            (func.lower(Anime.title_native) == clean_q, 1),
            else_=0,
        )
        order_criteria.append(exact_match_score.desc())

    if sort_key == "score":
        order_criteria.append(Anime.average_score.desc().nulls_last())
    elif sort_key == "year":
        order_criteria.append(Anime.season_year.desc().nulls_last())
    elif sort_key == "title":
        order_criteria.append(
            func.coalesce(
                Anime.title_english, Anime.title_romaji, Anime.title_native
            ).asc()
        )
    else:  # popularity
        order_criteria.append(Anime.popularity.desc())

    # Tiebreaker
    order_criteria.append(Anime.id.asc())
    query = query.order_by(*order_criteria)

    # 9. Pagination
    offset = (page - 1) * effective_page_size
    query = (
        query.offset(offset)
        .limit(effective_page_size)
        .options(selectinload(Anime.genres), selectinload(Anime.tags))
    )

    result = await db.execute(query)
    items = result.scalars().all()

    last_page = max(1, math.ceil(total / effective_page_size)) if total > 0 else 1
    has_next_page = page < last_page

    return AnimeListResponse(
        items=[serialize_anime_card(item) for item in items],
        page_info=PageInfo(
            total=total,
            current_page=page,
            last_page=last_page,
            per_page=effective_page_size,
            has_next_page=has_next_page,
        ),
    )


@router.get("/anime/filters", response_model=FiltersResponse)
async def get_filters(
    db: Annotated[AsyncSession, Depends(get_db)],
    include_mature: Annotated[bool, Query(alias="includeMature")] = False,
) -> FiltersResponse:
    """Returns available genres and tags for filter controls."""
    # Genres
    genre_stmt = select(Genre.name).order_by(Genre.name.asc())
    if not include_mature:
        genre_stmt = genre_stmt.where(~func.lower(Genre.name).in_(list(MATURE_GENRES)))
    genre_res = await db.execute(genre_stmt)
    genres = list(genre_res.scalars().all())

    # Tags
    tag_stmt = select(Tag.name).order_by(Tag.name.asc())
    if not include_mature:
        tag_stmt = tag_stmt.where(Tag.is_adult.is_(False))
    tag_res = await db.execute(tag_stmt)
    tags = list(tag_res.scalars().all())

    return FiltersResponse(genres=genres, tags=tags)


@router.get("/genres", response_model=list[str])
async def list_genres(
    db: Annotated[AsyncSession, Depends(get_db)],
    include_mature: Annotated[bool, Query(alias="includeMature")] = False,
) -> list[str]:
    """Returns list of genre names, filtering mature genres when include_mature=false."""
    stmt = select(Genre.name).order_by(Genre.name.asc())
    if not include_mature:
        stmt = stmt.where(~func.lower(Genre.name).in_(list(MATURE_GENRES)))
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/tags", response_model=list[str])
async def list_tags(
    db: Annotated[AsyncSession, Depends(get_db)],
    include_mature: Annotated[bool, Query(alias="includeMature")] = False,
) -> list[str]:
    """Returns list of tag names, filtering adult tags when include_mature=false."""
    stmt = select(Tag.name).order_by(Tag.name.asc())
    if not include_mature:
        stmt = stmt.where(Tag.is_adult.is_(False))
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/anime/{id}", response_model=AnimeDetail)
async def get_anime_detail(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_mature: Annotated[bool, Query(alias="includeMature")] = False,
) -> AnimeDetail:
    """Returns detailed information for a single anime."""
    stmt = (
        select(Anime)
        .where(Anime.id == id)
        .options(selectinload(Anime.genres), selectinload(Anime.tags))
    )
    res = await db.execute(stmt)
    anime = res.scalar_one_or_none()

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime with id {id} not found",
        )

    # Server-side mature content check
    if not include_mature:
        if anime.is_adult:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anime with id {id} not found",
            )
        if any(t.is_adult for t in anime.tags):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anime with id {id} not found",
            )
        if any(g.name.lower() in MATURE_GENRES for g in anime.genres):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anime with id {id} not found",
            )

    tag_stmt = (
        select(Tag.name, anime_tags.c.rank, anime_tags.c.is_spoiler)
        .join(anime_tags, anime_tags.c.tag_id == Tag.id)
        .where(anime_tags.c.anime_id == id)
        .order_by(anime_tags.c.rank.desc())
    )
    tag_res = await db.execute(tag_stmt)
    tag_rows = tag_res.all()
    tag_details = [
        TagDetail(name=row[0], rank=row[1], is_spoiler=row[2])
        for row in tag_rows
    ]

    return serialize_anime_detail(anime, tag_details=tag_details)
