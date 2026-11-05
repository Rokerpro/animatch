"""Authenticated watchlist endpoints with explicit request and response models."""

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
from app.models.list_entry import ListEntry
from app.models.user import User
from app.schemas.anime import AnimeCard
from app.schemas.errors import ApiErrorResponse
from app.schemas.list_entries import (
    ListAnimeStatus,
    ListDeleteResponse,
    ListEntryPut,
    ListEntryResponse,
    ListPageInfo,
    ListResponse,
    ListSort,
    ListStatus,
    ListStatusesResponse,
)
from app.services.maturity import is_mature_anime, mature_anime_clause

router = APIRouter(tags=["list"])

LIST_ERRORS = {
    401: {"model": ApiErrorResponse, "description": "Unauthenticated."},
    403: {"model": ApiErrorResponse, "description": "Missing or invalid CSRF token."},
    404: {"model": ApiErrorResponse, "description": "Requested resource not found."},
    422: {"model": ApiErrorResponse, "description": "Validation error."},
}
READ_ERRORS = {
    401: LIST_ERRORS[401],
    422: LIST_ERRORS[422],
}


def serialize_anime_card(anime: Anime) -> AnimeCard:
    """Serialize catalog fields while retaining the existing camelCase card keys."""
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
        genres=[genre.name for genre in anime.genres],
    )


def serialize_list_entry(entry: ListEntry) -> ListEntryResponse:
    """Serialize a list row with legacy snake_case entry keys."""
    return ListEntryResponse(
        id=entry.id,
        anime_id=entry.anime_id,
        anime=serialize_anime_card(entry.anime),
        status=entry.status,
        rating=entry.rating,
        source=entry.source,
        added_at=entry.added_at,
        updated_at=entry.updated_at,
    )


@router.get(
    "/list",
    response_model=ListResponse,
    responses=READ_ERRORS,
    description=(
        "Returns the authenticated user's list. `includeMature` controls filtering "
        "directly and does not use the account's `show_mature` setting. Entry fields "
        "remain snake_case; nested anime card fields are camelCase."
    ),
)
async def get_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Annotated[
        ListStatus | None,
        Query(alias="status", description="Filter by watchlist status."),
    ] = None,
    sort: Annotated[
        ListSort, Query(description="Sort by updated time, rating, or title.")
    ] = ListSort.UPDATED,
    page: Annotated[int, Query(ge=1, description="Page number.")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=50, alias="pageSize", description="Items per page (max 50)."),
    ] = 24,
    include_mature: Annotated[
        bool,
        Query(
            alias="includeMature",
            description="Include adult content; defaults to false, independent of account setting.",
        ),
    ] = False,
) -> ListResponse:
    """Return an accurately counted, paginated list for the authenticated user."""
    query = (
        select(ListEntry)
        .join(ListEntry.anime)
        .where(ListEntry.user_id == current_user.id)
        .options(selectinload(ListEntry.anime).selectinload(Anime.genres))
    )
    if status_filter is not None:
        query = query.where(ListEntry.status == status_filter.value)
    if not include_mature:
        query = query.where(~mature_anime_clause())

    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    if sort is ListSort.RATING:
        query = query.order_by(
            ListEntry.rating.desc().nulls_last(), ListEntry.updated_at.desc()
        )
    elif sort is ListSort.TITLE:
        query = query.order_by(
            func.coalesce(
                Anime.title_english, Anime.title_romaji, Anime.title_native
            ).asc()
        )
    else:
        query = query.order_by(ListEntry.updated_at.desc())

    entries = (
        (await db.execute(query.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    last_page = max(1, math.ceil(total / page_size))
    return ListResponse(
        items=[serialize_list_entry(entry) for entry in entries],
        page_info=ListPageInfo(
            total=total,
            current_page=page,
            last_page=last_page,
            per_page=page_size,
            has_next_page=page < last_page,
        ),
    )


@router.get(
    "/list/statuses",
    response_model=ListStatusesResponse,
    responses=READ_ERRORS,
    description=(
        "Returns only the authenticated user's matching list entries. Unknown anime "
        "IDs and IDs absent from the caller's list are omitted. `includeMature` "
        "controls filtering directly, matching GET /api/list."
    ),
)
async def get_list_statuses(
    ids: Annotated[
        str,
        Query(
            description="Comma-separated anime IDs (1–50). Empty or non-integer values are rejected."
        ),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    include_mature: Annotated[
        bool,
        Query(
            alias="includeMature",
            description="Include adult content; defaults to false, independent of account setting.",
        ),
    ] = False,
) -> ListStatusesResponse:
    """Return this user's list state for up to 50 anime IDs in one query."""
    raw_ids = ids.split(",")
    if not ids.strip() or len(raw_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ids must contain between 1 and 50 comma-separated integer IDs",
        )
    try:
        anime_ids = [int(value.strip()) for value in raw_ids]
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ids must contain only comma-separated integers",
        ) from err

    query = (
        select(ListEntry)
        .join(ListEntry.anime)
        .where(
            ListEntry.user_id == current_user.id,
            ListEntry.anime_id.in_(anime_ids),
        )
    )
    if not include_mature:
        query = query.where(~mature_anime_clause())
    entries = (await db.execute(query)).scalars().all()
    return ListStatusesResponse(
        items=[
            ListAnimeStatus(
                anime_id=entry.anime_id,
                status=entry.status,
                rating=entry.rating,
            )
            for entry in entries
        ]
    )


@router.put(
    "/list/{anime_id}",
    status_code=status.HTTP_200_OK,
    response_model=ListEntryResponse,
    responses=LIST_ERRORS,
    description=(
        "Create or partially update the caller's list entry. Omitted fields retain "
        "their existing values; an explicit `rating: null` clears the rating. A "
        "rating-only request for a missing entry creates it with status `planning`. "
        "Mature anime are allowed only when the account's `show_mature` setting is "
        "true; this operation has no `includeMature` query parameter. Entry fields "
        "remain snake_case and nested anime card fields are camelCase."
    ),
)
async def put_list_entry(
    anime_id: int,
    payload: ListEntryPut,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(verify_csrf)],
) -> ListEntryResponse:
    """Create or update a list entry while preserving documented partial semantics."""
    stmt = (
        select(Anime)
        .where(Anime.id == anime_id)
        .options(selectinload(Anime.genres), selectinload(Anime.tags))
    )
    anime = (await db.execute(stmt)).scalar_one_or_none()
    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime with id {anime_id} not found",
        )
    if not current_user.show_mature and is_mature_anime(anime):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime with id {anime_id} not found",
        )

    provided = payload.model_fields_set
    new_status = payload.status if "status" in provided else None
    new_rating = payload.rating if "rating" in provided else None
    result = await db.execute(
        select(ListEntry).where(
            ListEntry.user_id == current_user.id,
            ListEntry.anime_id == anime_id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        entry = ListEntry(
            user_id=current_user.id,
            anime_id=anime_id,
            status=(new_status.value if new_status is not None else "planning"),
            rating=new_rating,
            source="manual",
        )
        db.add(entry)
    else:
        if new_status is not None:
            entry.status = new_status.value
        if "rating" in provided:
            entry.rating = new_rating

    await db.commit()
    await db.refresh(entry)
    await db.refresh(entry, attribute_names=["anime"])
    return serialize_list_entry(entry)


@router.delete(
    "/list/{anime_id}",
    status_code=status.HTTP_200_OK,
    response_model=ListDeleteResponse,
    responses=LIST_ERRORS,
    description=(
        "Delete one of the caller's entries. No maturity check is performed on "
        "purpose: users can always remove anything from their own list, including "
        "entries hidden by mature-content settings."
    ),
)
async def delete_list_entry(
    anime_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(verify_csrf)],
) -> ListDeleteResponse:
    """Delete a list entry, even if its anime is currently hidden as mature."""
    result = await db.execute(
        select(ListEntry).where(
            ListEntry.user_id == current_user.id,
            ListEntry.anime_id == anime_id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"List entry for anime {anime_id} not found",
        )
    await db.delete(entry)
    await db.commit()
    return ListDeleteResponse(message=f"List entry for anime {anime_id} deleted")
