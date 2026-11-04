"""User watchlist endpoints.

GET /api/list?status=&sort=&page=&pageSize=&includeMature=
PUT /api/list/{anime_id}
DELETE /api/list/{anime_id}

All endpoints require authentication. State-changing endpoints require CSRF.
Users can only access their own list entries.
Mature content follows the same include_mature rule as /api/anime/{id}.
"""

from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.anime import Anime
from app.models.list_entry import LIST_STATUSES, ListEntry
from app.models.user import User
from app.schemas.anime import AnimeCard

router = APIRouter(tags=["list"])

ALLOWED_SORTS = {"updated", "rating", "title"}
VALID_STATUSES = set(LIST_STATUSES)
MATURE_GENRES = {"hentai", "ecchi"}


def is_mature_anime(anime: Anime) -> bool:
    """Check if an anime should be filtered as mature content."""
    if anime.is_adult:
        return True
    if any(t.is_adult for t in anime.tags):
        return True
    return any(g.name.lower() in MATURE_GENRES for g in anime.genres)


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


@router.get("/list")
async def get_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by watchlist status")
    ] = None,
    sort: Annotated[
        str, Query(description="Sort by: updated, rating, title")
    ] = "updated",
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=50, alias="pageSize", description="Items per page (max 50)")
    ] = 24,
    include_mature: Annotated[
        bool, Query(alias="includeMature", description="Include adult content")
    ] = False,
) -> dict:
    """Returns paginated watchlist entries for the authenticated user.

    - Filter by status
    - Sort by updated_at (desc), rating (desc), or title (asc)
    - Pagination with total count
    - Each item includes the same card fields as the catalog
    """
    if status_filter and status_filter not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    sort_key = sort.lower().strip()
    if sort_key not in ALLOWED_SORTS:
        sort_key = "updated"

    # Base query
    query = (
        select(ListEntry)
        .join(ListEntry.anime)
        .where(ListEntry.user_id == current_user.id)
        .options(selectinload(ListEntry.anime).selectinload(Anime.genres))
    )

    # Status filter
    if status_filter:
        query = query.where(ListEntry.status == status_filter)

    # Total count (before mature filtering)
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Sorting
    if sort_key == "rating":
        query = query.order_by(
            ListEntry.rating.desc().nulls_last(), ListEntry.updated_at.desc()
        )
    elif sort_key == "title":
        query = query.order_by(
            func.coalesce(
                Anime.title_english, Anime.title_romaji, Anime.title_native
            ).asc()
        )
    else:  # "updated" default
        query = query.order_by(ListEntry.updated_at.desc())

    # Pagination - fetch one extra to check mature filtering
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size + 1)

    result = await db.execute(query)
    entries = result.scalars().all()

    # Filter mature content and build response items
    items = []
    for entry in entries:
        anime = entry.anime
        if not include_mature and is_mature_anime(anime):
            continue
        items.append(
            {
                "id": entry.id,
                "anime_id": entry.anime_id,
                "anime": serialize_anime_card(anime),
                "status": entry.status,
                "rating": entry.rating,
                "source": entry.source,
                "added_at": entry.added_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }
        )

    # Trim to page_size
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]

    last_page = max(1, math.ceil(total / page_size)) if total > 0 else 1
    has_next_page = page < last_page or has_more

    return {
        "items": items,
        "page_info": {
            "total": total,
            "current_page": page,
            "last_page": last_page,
            "per_page": page_size,
            "has_next_page": has_next_page,
        },
    }


@router.put("/list/{anime_id}", status_code=status.HTTP_200_OK)
async def put_list_entry(
    anime_id: int,
    payload: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(verify_csrf)],
) -> dict:
    """Create or update a list entry for the current user.

    - Validates rating 1-10
    - Validates status
    - 404 if anime not found
    - Mature titles follow include_mature rule
    """
    # Check anime exists and mature rule
    stmt = (
        select(Anime)
        .where(Anime.id == anime_id)
        .options(selectinload(Anime.genres), selectinload(Anime.tags))
    )
    result = await db.execute(stmt)
    anime = result.scalar_one_or_none()

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime with id {anime_id} not found",
        )

    # Mature content check (same as /api/anime/{id})
    include_mature = current_user.show_mature
    if not include_mature and is_mature_anime(anime):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime with id {anime_id} not found",
        )

    # Validate status
    new_status = payload.get("status")
    if new_status is not None and new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    # Validate rating
    new_rating = payload.get("rating")
    if new_rating is not None and (
        not isinstance(new_rating, int) or not (1 <= new_rating <= 10)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rating must be an integer between 1 and 10",
        )

    # Check if entry exists
    stmt = select(ListEntry).where(
        ListEntry.user_id == current_user.id,
        ListEntry.anime_id == anime_id,
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry is None:
        # Create new entry
        entry = ListEntry(
            user_id=current_user.id,
            anime_id=anime_id,
            status=new_status or "planning",
            rating=new_rating,
            source="manual",
        )
        db.add(entry)
    else:
        # Update existing entry
        if new_status is not None:
            entry.status = new_status
        if new_rating is not None:
            entry.rating = new_rating

    await db.commit()
    await db.refresh(entry)
    await db.refresh(entry, attribute_names=["anime"])

    return {
        "id": entry.id,
        "anime_id": entry.anime_id,
        "anime": serialize_anime_card(entry.anime),
        "status": entry.status,
        "rating": entry.rating,
        "source": entry.source,
        "added_at": entry.added_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


@router.delete("/list/{anime_id}", status_code=status.HTTP_200_OK)
async def delete_list_entry(
    anime_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(verify_csrf)],
) -> dict[str, str]:
    """Delete a list entry for the current user.

    Returns 404 if entry doesn't exist.
    """
    stmt = select(ListEntry).where(
        ListEntry.user_id == current_user.id,
        ListEntry.anime_id == anime_id,
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"List entry for anime {anime_id} not found",
        )

    await db.delete(entry)
    await db.commit()

    return {"message": f"List entry for anime {anime_id} deleted"}
