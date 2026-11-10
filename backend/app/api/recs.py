"""Recommendation API endpoints.

Endpoints:
- GET /api/quiz: Returns the public quiz questions.
- POST /api/recs/quiz: Takes quiz answers, generates recommendations, and stores quiz prior for logged-in users.
- GET /api/recs/similar/{anime_id}: Seed similarity recommendations (pure for logged-out, blended for logged-in).
- GET /api/recs/me: Personalised recommendations based on user profile.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user, verify_csrf
from app.core.config import settings
from app.db.session import get_db
from app.models.list_entry import ListEntry
from app.models.user import User
from app.recs.engine import (
    MatureSeedError,
    build_taste_vector,
    recommend_from_profile,
    recommend_from_quiz,
    recommend_from_start,
    recommend_similar,
)
from app.recs.quiz import build_quiz_vector, get_quiz_questions
from app.recs.schemas import (
    NewRecommendationsRequest,
    NewRecommendationsResponse,
    QuizAnswerRequest,
    QuizResponse,
    RecResult,
    RecStartRequest,
)
from app.recs.vectors import get_index
from app.schemas.errors import ApiErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recommendations"])


@router.post(
    "/recs/new",
    response_model=NewRecommendationsResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthenticated."},
        403: {
            "model": ApiErrorResponse,
            "description": "Missing or invalid CSRF token.",
        },
        422: {"model": ApiErrorResponse, "description": "Validation error."},
    },
)
async def post_new_recommendations(
    payload: NewRecommendationsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(verify_csrf)],
    n: Annotated[int, Query(ge=1, le=50)] = settings.REC_DEFAULT_N,
    include_mature: Annotated[bool, Query(alias="includeMature")] = False,
) -> NewRecommendationsResponse:
    """Recommend quiz-matched titles outside the user's existing taste."""
    index = get_index()
    if index.is_empty():
        return NewRecommendationsResponse(results=[], mode="quiz_fallback")

    rows = await db.execute(
        select(ListEntry).where(ListEntry.user_id == current_user.id)
    )
    entries = rows.scalars().all()
    listed_ids = {entry.anime_id for entry in entries}
    user_items: list[dict[str, Any]] = [
        {"anime_id": entry.anime_id, "status": entry.status, "rating": entry.rating}
        for entry in entries
    ]
    profile = current_user.taste_profile or {}
    liked_ids = list(profile.get("liked_ids", []))
    user_items.extend(
        {"anime_id": anime_id, "status": "completed", "rating": 10}
        for anime_id in liked_ids
        if anime_id not in listed_ids
    )
    listed_franchises = {
        record.franchise_id
        for anime_id in listed_ids
        if (record := index.get(anime_id)) is not None
        and record.franchise_id is not None
    }
    quiz_prior = None
    if profile.get("quiz_prior_vec"):
        quiz_prior = np.asarray(profile["quiz_prior_vec"], dtype=np.float32)
    elif profile.get("quiz_answers"):
        quiz_prior, _, _ = build_quiz_vector(profile["quiz_answers"], index)

    taste_vec = build_taste_vector(user_items, quiz_prior, index)
    has_profile_signal = bool(np.any(taste_vec != 0))
    novelty_weights: dict[str, float] = {}
    if has_profile_signal:
        for pos, name in enumerate(index.all_genres):
            novelty_weights[f"genre:{name}"] = float(taste_vec[index.genre_start + pos])
        for pos, name in enumerate(index.all_tags):
            novelty_weights[f"tag:{name}"] = float(taste_vec[index.tag_start + pos])

    results = recommend_from_quiz(
        answers=payload.quiz_answers,
        n=min(n, settings.REC_MAX_N),
        include_mature=include_mature or current_user.show_mature,
        index=index,
        exclude_ids=listed_ids | set(liked_ids),
        exclude_franchise_ids=listed_franchises,
        strict_quality_floor=True,
        novelty_weights=novelty_weights if has_profile_signal else None,
        novelty_weight=settings.REC_NEW_NOVELTY_WEIGHT if has_profile_signal else 0.0,
        novelty_reasons=has_profile_signal,
    )
    return NewRecommendationsResponse(
        results=results,
        mode="novelty" if has_profile_signal else "quiz_fallback",
    )


@router.post("/recs/start", response_model=list[RecResult])
async def post_recs_start(payload: RecStartRequest) -> list[RecResult]:
    """Start recommendations from quiz answers and/or liked anime."""
    liked_ids = payload.liked_ids or []
    if not payload.quiz_answers and not liked_ids:
        raise HTTPException(422, "Provide quiz_answers, liked_ids, or both.")
    if len(liked_ids) > 5:
        raise HTTPException(422, "liked_ids may contain at most 5 titles.")
    if len(set(liked_ids)) != len(liked_ids):
        raise HTTPException(422, "liked_ids must not contain duplicates.")
    index = get_index()
    seeds = [index.get(aid) for aid in liked_ids]
    if any(seed is None for seed in seeds):
        raise HTTPException(404, "One or more liked_ids were not found.")
    if (
        any(seed.is_adult for seed in seeds if seed is not None)
        and not payload.include_mature
    ):
        raise HTTPException(404, "Anime not found or is restricted content.")
    if not payload.quiz_answers and len(liked_ids) < 3:
        raise HTTPException(
            422, "At least 3 liked titles from 3 different franchises are required."
        )
    if not payload.quiz_answers:
        franchise_keys = [
            seed.franchise_id if seed.franchise_id is not None else ("title", seed.id)
            for seed in seeds
            if seed is not None
        ]
        if len(set(franchise_keys)) < 3:
            raise HTTPException(
                422,
                "liked_ids must cover at least 3 different franchises; some selected titles share a franchise.",
            )
    if index.is_empty():
        return []
    return recommend_from_start(
        payload.quiz_answers,
        liked_ids,
        n=payload.limit,
        include_mature=payload.include_mature,
        index=index,
    )


@router.get("/quiz", response_model=list[dict])
async def get_quiz() -> list[dict]:
    """Returns the recommendation quiz questions."""
    return get_quiz_questions()


@router.post("/recs/quiz", response_model=QuizResponse)
async def post_quiz_recommendations(
    payload: QuizAnswerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)] = None,
) -> QuizResponse:
    """Computes recommendations from quiz answers.

    If the caller is authenticated, the resulting quiz vector is saved
    to the user's taste_profile as quiz_prior_vec.
    """
    index = get_index()
    if index.is_empty():
        return QuizResponse(results=[], quizVecStored=False)

    include_mature = payload.include_mature
    if current_user and current_user.show_mature:
        include_mature = True

    n = max(1, min(payload.n, settings.REC_MAX_N))
    quiz_vec, _, _ = build_quiz_vector(payload.answers, index)
    results = recommend_from_quiz(
        answers=payload.answers,
        n=n,
        include_mature=include_mature,
        index=index,
        query_vec=quiz_vec,
    )

    stored = False
    if current_user:
        taste_prof = dict(current_user.taste_profile or {})
        taste_prof["quiz_prior_vec"] = [float(x) for x in quiz_vec]
        taste_prof["quiz_answers"] = payload.answers
        current_user.taste_profile = taste_prof
        await db.commit()
        stored = True

    return QuizResponse(results=results, quizVecStored=stored)


@router.get("/recs/similar/{anime_id}", response_model=list[RecResult])
async def get_similar_anime(
    anime_id: int,
    n: Annotated[int, Query(ge=1, le=50)] = settings.REC_DEFAULT_N,
    include_mature: Annotated[bool, Query(alias="includeMature")] = False,
    current_user: Annotated[User | None, Depends(get_optional_user)] = None,
) -> list[RecResult]:
    """Recommends anime similar to the specified anime_id.

    - Excludes the seed anime and any same-franchise titles.
    - Logged-out users get pure content similarity + quality re-rank.
    - Logged-in users get a blend of seed similarity and their own taste profile.
    - If seed is mature and include_mature=False, returns 404.
    """
    index = get_index()
    if index.is_empty():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Catalog is empty"
        )

    seed = index.get(anime_id)
    if not seed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime {anime_id} not found in catalog",
        )

    effective_mature = include_mature or (
        bool(current_user.show_mature) if current_user else False
    )

    user_items = None
    quiz_prior = None

    if current_user and current_user.taste_profile:
        tp = current_user.taste_profile
        user_items = tp.get("items", [])
        if "quiz_prior_vec" in tp:
            quiz_prior = np.array(tp["quiz_prior_vec"], dtype=np.float32)

    try:
        results = recommend_similar(
            anime_id=anime_id,
            n=n,
            include_mature=effective_mature,
            user_items=user_items,
            quiz_prior_vec=quiz_prior,
            index=index,
        )
    except MatureSeedError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anime not found or is restricted content.",
        ) from err

    return results


@router.get("/recs/me", response_model=list[RecResult])
async def get_my_recommendations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    n: Annotated[int, Query(ge=1, le=50)] = settings.REC_DEFAULT_N,
    include_mature: Annotated[bool, Query(alias="includeMature")] = False,
) -> list[RecResult]:
    """Personalised recommendations for the authenticated user based on their list.

    Builds recommendations from:
    - Saved taste profile (quiz_answers and liked_ids via the same logic as /api/recs/start)
    - User's ratings on their list (completed with rating)
    - Blended with n/(n+10) weighting, centered on user's own mean
    - Excludes everything already on their list
    - With no profile and no ratings, returns empty list with clear message (no popular fallback)
    """
    index = get_index()
    if index.is_empty():
        return []

    effective_mature = include_mature or current_user.show_mature

    # Get user's list entries
    stmt = select(ListEntry).where(ListEntry.user_id == current_user.id)
    result = await db.execute(stmt)
    list_entries = result.scalars().all()

    # Build user_items from list entries (only completed with rating, and dropped)
    user_items = []
    for entry in list_entries:
        item = {
            "anime_id": entry.anime_id,
            "status": entry.status,
        }
        if entry.rating is not None:
            item["rating"] = entry.rating
        user_items.append(item)

    # Get quiz prior from taste_profile (if any)
    quiz_prior = None
    liked_ids = []
    if current_user.taste_profile:
        tp = current_user.taste_profile
        if "quiz_prior_vec" in tp:
            quiz_prior = np.array(tp["quiz_prior_vec"], dtype=np.float32)
        elif tp.get("quiz_answers"):
            quiz_prior, _, _ = build_quiz_vector(tp["quiz_answers"], index)
        liked_ids = tp.get("liked_ids", [])

    listed_ids = {item["anime_id"] for item in user_items}
    user_items.extend(
        {"anime_id": anime_id, "status": "completed", "rating": 10}
        for anime_id in liked_ids
        if anime_id not in listed_ids
    )
    liked_franchises = {
        record.franchise_id
        for anime_id in liked_ids
        if (record := index.get(anime_id)) is not None
        and record.franchise_id is not None
    }
    excluded_ids = listed_ids | set(liked_ids)
    user_items.extend(
        {"anime_id": record.id, "status": "planning"}
        for record in index.records
        if record.franchise_id in liked_franchises and record.id not in excluded_ids
    )

    # If no profile and no ratings, return empty list with message
    has_ratings = any(
        item.get("rating") is not None
        for item in user_items
        if item.get("status") == "completed"
    )
    has_profile = bool(
        current_user.taste_profile
        and (current_user.taste_profile.get("quiz_answers") or liked_ids)
    )

    if not has_ratings and not has_profile:
        return []

    # Use the engine's recommend_from_profile which already handles:
    # - Rating centering with n/(n+10) weighting
    # - Quiz prior blending
    # - Excluding list entries
    # - Salient feature gate
    return recommend_from_profile(
        user_items=user_items,
        n=n,
        include_mature=effective_mature,
        quiz_prior_vec=quiz_prior,
        index=index,
    )
