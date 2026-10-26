"""Recommendation API endpoints.

Endpoints:
- GET /api/quiz: Returns the public quiz questions.
- POST /api/recs/quiz: Takes quiz answers, generates recommendations, and stores quiz prior for logged-in users.
- GET /api/recs/similar/{anime_id}: Seed similarity recommendations (pure for logged-out, blended for logged-in).
- GET /api/recs/me: Personalised recommendations based on user profile.
"""

from __future__ import annotations

import logging
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.recs.engine import (
    MatureSeedError,
    recommend_from_profile,
    recommend_from_quiz,
    recommend_similar,
)
from app.recs.quiz import build_quiz_vector, get_quiz_questions
from app.recs.schemas import QuizAnswerRequest, QuizResponse, RecResult
from app.recs.vectors import get_index

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recommendations"])


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
    results = recommend_from_quiz(
        answers=payload.answers,
        n=n,
        include_mature=include_mature,
        index=index,
    )

    stored = False
    if current_user:
        quiz_vec, _, _ = build_quiz_vector(payload.answers, index)
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
    n: Annotated[int, Query(ge=1, le=50)] = settings.REC_DEFAULT_N,
    include_mature: Annotated[bool, Query(alias="includeMature")] = False,
) -> list[RecResult]:
    """Personalised recommendations for the authenticated user based on their taste vector.

    Falls back to a quality-ranked popular list if the user has neither ratings nor a quiz prior.
    """
    index = get_index()
    if index.is_empty():
        return []

    effective_mature = include_mature or current_user.show_mature

    user_items = []
    quiz_prior = None

    if current_user.taste_profile:
        tp = current_user.taste_profile
        user_items = tp.get("items", [])
        if "quiz_prior_vec" in tp:
            quiz_prior = np.array(tp["quiz_prior_vec"], dtype=np.float32)

    return recommend_from_profile(
        user_items=user_items,
        n=n,
        include_mature=effective_mature,
        quiz_prior_vec=quiz_prior,
        index=index,
    )
