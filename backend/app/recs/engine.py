"""Recommendation engine core: feature vectors, scoring, ranking, and MMR.

Scoring Formulas
----------------
1. Logged-out similar:
   final_score(x) = (1 - q) * rank_norm(cos(seed_vec, x)) + q * quality_pct(x)

2. Logged-in similar:
   combined(x) = alpha * rank_norm(cos(seed_vec, x)) + (1 - alpha) * rank_norm(cos(taste_vec, x))
   final_score(x) = (1 - q) * combined(x) + q * quality_pct(x)
   Fallback: if taste_vec is empty/all-zeros, falls back to pure similarity (formula 1).

3. Quiz:
   final_score(x) = (1 - q) * rank_norm(cos(quiz_vec, x)) + q * quality_pct(x)
   Followed by soft score penalties for length and era constraints.

4. Profile (recs/me):
   final_score(x) = (1 - q) * rank_norm(cos(taste_vec, x)) + q * quality_pct(x)
   Fallback: if no ratings and no quiz prior, returns quality_pct-ranked list.

Dropped Weight Documentation:
-----------------------------
DROPPED_WEIGHT = -1.0 is intentionally weaker than a low rating after normalization.
When ratings are centered on the user's mean:
- If a user has a mean rating of 7.5 and rates a hated anime 1/10, the centered
  pull is (1 - 7.5) = -6.5.
- Relative to a typical max_abs scale of ~6-7, this normalizes to ~ -1.0.
- In contrast, DROPPED_WEIGHT applies a fixed un-amplified -1.0 before normalization,
  meaning an explicit 1-star rating from a generous rater pushes away even harder
  than dropping without a rating. Dropping indicates disinterest, whereas an explicit
  rock-bottom rating indicates active dislike.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.anime import Anime, Tag
from app.recs.explain import build_explanation
from app.recs.quiz import apply_quiz_soft_penalties, build_quiz_vector
from app.recs.schemas import ExplanationSchema, RecResult
from app.recs.vectors import (
    VectorIndex,
    get_index,
    set_index,
)

logger = logging.getLogger(__name__)

# Plain documented constant for dropped titles (scale is [-1, 1] after normalization)
DROPPED_WEIGHT: float = -1.0


class MatureSeedError(Exception):
    """Raised when an adult seed is requested with include_mature=False."""


def rank_norm(
    scores: np.ndarray | float, pool: np.ndarray | list[float] | None = None
) -> np.ndarray | float:
    """Rank-normalise scores into the [0, 1] interval.

    Higher input scores map to higher normalised values (top score -> 1.0).
    If a single scalar is provided with no pool, and 0 <= scores <= 1, it is returned as-is.
    """
    if isinstance(scores, (int, float)):
        if pool is None:
            return float(scores)
        pool_arr = np.asarray(pool, dtype=np.float64)
        if len(pool_arr) <= 1:
            return 1.0
        sorted_pool = np.sort(pool_arr)
        idx = np.searchsorted(sorted_pool, scores, side="left")
        return float(idx) / (len(pool_arr) - 1)

    scores_arr = np.asarray(scores, dtype=np.float64)
    n = len(scores_arr)
    if n == 0:
        return scores_arr
    if n == 1:
        return np.ones(1, dtype=np.float64)

    # If all values are identical, return ones
    min_v, max_v = float(np.min(scores_arr)), float(np.max(scores_arr))
    if math.isclose(min_v, max_v):
        return np.ones(n, dtype=np.float64)

    # Fractional ranking using searchsorted on sorted array
    sorted_s = np.sort(scores_arr)
    ranks = np.searchsorted(sorted_s, scores_arr, side="left").astype(np.float64)
    return ranks / (n - 1)


def compute_final_score(
    sim_score: float | np.ndarray,
    quality_score: float | np.ndarray,
    q: float = settings.REC_QUALITY_WEIGHT,
) -> float | np.ndarray:
    """Computes (1 - q) * sim_score + q * quality_score."""
    return (1.0 - q) * sim_score + q * quality_score


def build_taste_vector(
    user_items: list[dict[str, Any]],
    quiz_prior_vec: np.ndarray | None = None,
    index: VectorIndex | None = None,
) -> np.ndarray:
    """Constructs a user taste vector from user list items and optional quiz prior.

    Rating Status Rules:
    - Completed with rating: centered around user mean, pulls towards item
    - Completed without rating: weight 0
    - Dropped: DROPPED_WEIGHT = -1.0, pushes away (even if unrated)
    - Planning / Watching: weight 0
    """
    if index is None:
        index = get_index()

    d = index.matrix.shape[1] if not index.is_empty() else 0
    if d == 0:
        return np.zeros(0, dtype=np.float32)

    # 1. Separate rated completed items and dropped items
    completed_rated: list[tuple[int, float]] = []
    dropped_ids: list[int] = []

    for item in user_items:
        aid = item.get("anime_id") or item.get("id")
        status = (item.get("status") or "").lower()
        rating = item.get("rating")

        if status == "completed" and rating is not None:
            completed_rated.append((aid, float(rating)))
        elif status == "dropped":
            dropped_ids.append(aid)

    # 2. Rating centering
    taste_raw = np.zeros(d, dtype=np.float32)

    if completed_rated:
        ratings = np.array([r for _, r in completed_rated], dtype=np.float32)
        mean_r = float(np.mean(ratings))
        std_r = float(np.std(ratings))

        for aid, rating in completed_rated:
            vec = index.vec(aid)
            if vec is not None:
                centered = (rating - mean_r) if std_r > 0 else 0.0
                taste_raw += centered * vec

    # 3. Dropped penalty
    for aid in dropped_ids:
        vec = index.vec(aid)
        if vec is not None:
            taste_raw += DROPPED_WEIGHT * vec

    # 4. Normalise taste_raw by max absolute value to [-1, 1]
    max_abs = float(np.max(np.abs(taste_raw))) if len(taste_raw) > 0 else 0.0
    taste_vec = taste_raw / max_abs if max_abs > 0 else np.zeros(d, dtype=np.float32)

    # 5. Cold-start blend with quiz prior
    n = len(completed_rated)
    if (
        quiz_prior_vec is not None
        and len(quiz_prior_vec) == d
        and np.any(quiz_prior_vec != 0)
    ):
        w_r = n / (n + settings.REC_COLD_START_K)
        w_prior = 1.0 - w_r
        taste_vec_blended = w_r * taste_vec + w_prior * quiz_prior_vec
        norm = np.linalg.norm(taste_vec_blended)
        if norm > 0:
            taste_vec_blended = (taste_vec_blended / norm).astype(np.float32)
        return taste_vec_blended

    return taste_vec


def mmr_rerank(
    candidate_indices: list[int],
    final_scores: np.ndarray,
    index: VectorIndex,
    n: int,
    lambda_param: float = settings.REC_MMR_LAMBDA,
) -> list[int]:
    """Maximal Marginal Relevance (MMR) re-ranking.

    Selects n items that maximise relevance while penalising cosine similarity
    to already selected items.
    """
    if len(candidate_indices) <= n:
        return candidate_indices

    # Truncate to top candidate pool for efficiency
    pool_size = min(len(candidate_indices), settings.REC_CANDIDATE_POOL)
    top_pool_order = np.argsort(-final_scores)[:pool_size]

    pool_indices = [candidate_indices[i] for i in top_pool_order]
    pool_scores = final_scores[top_pool_order]
    pool_matrix = index.matrix[pool_indices]  # (P, D)

    selected: list[int] = []
    selected_pool_idxs: list[int] = []
    remaining = list(range(len(pool_indices)))

    while len(selected) < n and remaining:
        best_idx = -1
        best_mmr = -float("inf")
        best_id = float("inf")

        for r in remaining:
            score = pool_scores[r]
            if not selected_pool_idxs:
                diversity_penalty = 0.0
            else:
                sims = pool_matrix[r] @ pool_matrix[selected_pool_idxs].T
                diversity_penalty = float(np.max(sims))

            mmr = lambda_param * score - (1.0 - lambda_param) * diversity_penalty
            rec_id = index.records[pool_indices[r]].id

            # Tiebreaker: higher MMR, then lower anime ID
            if mmr > best_mmr or (
                math.isclose(mmr, best_mmr, abs_tol=1e-6) and rec_id < best_id
            ):
                best_mmr = mmr
                best_idx = r
                best_id = rec_id

        selected.append(pool_indices[best_idx])
        selected_pool_idxs.append(best_idx)
        remaining.remove(best_idx)

    return selected


def _filter_and_relax_candidates(
    index: VectorIndex,
    *,
    seed_id: int | None = None,
    seed_franchise_id: int | None = None,
    exclude_ids: set[int] | None = None,
    include_mature: bool = False,
    n: int = 10,
) -> list[int]:
    """Filters candidates based on exclusions and mature filter, then relaxes
    score and popularity floors if candidate count is below n.
    """
    exclude = set(exclude_ids or set())
    if seed_id is not None:
        exclude.add(seed_id)

    base_candidates: list[int] = []
    for idx, rec in enumerate(index.records):
        # Mature filter
        if rec.is_adult and not include_mature:
            continue
        # Excluded items (user list, seed)
        if rec.id in exclude:
            continue
        # Franchise exclusion: same franchise as seed
        if (
            seed_franchise_id is not None
            and rec.franchise_id is not None
            and rec.franchise_id == seed_franchise_id
        ):
            continue
        base_candidates.append(idx)

    if len(base_candidates) <= n:
        return base_candidates

    # Step 0: Apply quality floor
    filtered = [
        idx
        for idx in base_candidates
        if (index.records[idx].average_score or 0) >= settings.REC_MIN_SCORE
        and index.records[idx].popularity >= settings.REC_MIN_POPULARITY
    ]
    if len(filtered) >= n:
        return filtered

    # Relaxation 1: Drop score requirement
    filtered = [
        idx
        for idx in base_candidates
        if index.records[idx].popularity >= settings.REC_MIN_POPULARITY
    ]
    if len(filtered) >= n:
        return filtered

    # Relaxation 2: Drop popularity requirement
    return base_candidates


def recommend_similar(
    anime_id: int,
    n: int = settings.REC_DEFAULT_N,
    include_mature: bool = False,
    user_items: list[dict[str, Any]] | None = None,
    quiz_prior_vec: np.ndarray | None = None,
    index: VectorIndex | None = None,
) -> list[RecResult]:
    """Endpoint 4a / 4b: Recommends similar anime given a seed anime_id.

    - Logged-out: pure seed similarity + quality re-rank.
    - Logged-in: combines seed similarity (alpha=0.6) and taste vector (0.4) + quality re-rank.
    - Empty taste vector fallback: pure similarity.
    """
    if index is None:
        index = get_index()
    if index.is_empty():
        return []

    seed_record = index.get(anime_id)
    if seed_record is None:
        return []

    if seed_record.is_adult and not include_mature:
        raise MatureSeedError(f"Seed anime {anime_id} is mature content.")

    seed_vec = index.vec(anime_id)
    if seed_vec is None:
        return []

    # Collect exclude IDs from user list
    exclude_ids = {
        item.get("anime_id") or item.get("id")
        for item in (user_items or [])
        if item.get("anime_id") or item.get("id")
    }

    candidates = _filter_and_relax_candidates(
        index,
        seed_id=anime_id,
        seed_franchise_id=seed_record.franchise_id,
        exclude_ids=exclude_ids,
        include_mature=include_mature,
        n=n,
    )
    if not candidates:
        return []

    cand_matrix = index.matrix[candidates]
    cand_records = [index.records[i] for i in candidates]
    cand_q_scores = np.array([r.quality_pct for r in cand_records], dtype=np.float64)

    # 1. Cosine similarity to seed
    seed_cos = cand_matrix @ seed_vec
    sim_scores = rank_norm(seed_cos)

    # Check for taste signal
    taste_vec = None
    has_taste = False
    taste_genres: list[str] = []

    if user_items:
        taste_vec = build_taste_vector(user_items, quiz_prior_vec, index)
        if np.any(taste_vec != 0):
            has_taste = True
            # Extract top taste genres for explanation
            g_taste = taste_vec[index.genre_start : index.genre_end]
            if len(g_taste) > 0:
                top_g_idxs = np.argsort(-g_taste)[:3]
                taste_genres = [
                    index.all_genres[gi] for gi in top_g_idxs if g_taste[gi] > 0
                ]

    # Combine signals
    if has_taste and taste_vec is not None:
        taste_cos = cand_matrix @ taste_vec
        taste_scores = rank_norm(taste_cos)
        combined = (
            settings.REC_ALPHA * sim_scores + (1.0 - settings.REC_ALPHA) * taste_scores
        )
        final_scores = compute_final_score(combined, cand_q_scores)
    else:
        # Fallback to pure similarity (logged-out or empty taste)
        final_scores = compute_final_score(sim_scores, cand_q_scores)

    # MMR re-ranking
    selected_indices = mmr_rerank(candidates, final_scores, index, n)

    results: list[RecResult] = []
    for cand_idx in selected_indices:
        rec = index.records[cand_idx]
        pos = candidates.index(cand_idx)
        sim_val = float(seed_cos[pos])

        explanation = build_explanation(
            query_vec=seed_vec,
            item_vec=index.matrix[cand_idx],
            index=index,
            seed_title=seed_record.title,
            has_taste=has_taste,
            taste_genres=taste_genres,
        )

        results.append(
            RecResult(
                id=rec.id,
                title=rec.title,
                title_english=rec.title,
                title_romaji=rec.title,
                title_native=rec.title,
                format=rec.format,
                episodes=rec.episodes,
                year=rec.season_year,
                score=rec.average_score,
                popularity=rec.popularity,
                is_adult=rec.is_adult,
                genres=rec.genres,
                reason=explanation.reason,
                similarity=min(max(sim_val, 0.0), 1.0),
                explanation=ExplanationSchema(
                    shared_genres=explanation.shared_genres,
                    shared_tags=explanation.shared_tags,
                    seed_titles=explanation.seed_titles,
                    quiz_answers=explanation.quiz_answers,
                ),
            )
        )

    return results


def recommend_from_quiz(
    answers: dict[str, str],
    n: int = settings.REC_DEFAULT_N,
    include_mature: bool = False,
    index: VectorIndex | None = None,
) -> list[RecResult]:
    """Endpoint 4c: Recommends anime based on quiz answers with soft penalties."""
    if index is None:
        index = get_index()
    if index.is_empty():
        return []

    quiz_vec, labels, constraints = build_quiz_vector(answers, index)

    candidates = _filter_and_relax_candidates(
        index,
        include_mature=include_mature,
        n=n,
    )
    if not candidates:
        return []

    cand_matrix = index.matrix[candidates]
    cand_records = [index.records[i] for i in candidates]
    cand_q_scores = np.array([r.quality_pct for r in cand_records], dtype=np.float64)

    cos_sim = cand_matrix @ quiz_vec
    sim_scores = rank_norm(cos_sim)
    final_scores = compute_final_score(sim_scores, cand_q_scores)

    # Apply soft penalties for episode / year constraints
    final_scores = apply_quiz_soft_penalties(final_scores, cand_records, constraints)

    selected_indices = mmr_rerank(candidates, final_scores, index, n)

    results: list[RecResult] = []
    for cand_idx in selected_indices:
        rec = index.records[cand_idx]
        pos = candidates.index(cand_idx)
        sim_val = float(cos_sim[pos])

        explanation = build_explanation(
            query_vec=quiz_vec,
            item_vec=index.matrix[cand_idx],
            index=index,
            quiz_answers=labels,
        )

        results.append(
            RecResult(
                id=rec.id,
                title=rec.title,
                title_english=rec.title,
                title_romaji=rec.title,
                title_native=rec.title,
                format=rec.format,
                episodes=rec.episodes,
                year=rec.season_year,
                score=rec.average_score,
                popularity=rec.popularity,
                is_adult=rec.is_adult,
                genres=rec.genres,
                reason=explanation.reason,
                similarity=min(max(sim_val, 0.0), 1.0),
                explanation=ExplanationSchema(
                    shared_genres=explanation.shared_genres,
                    shared_tags=explanation.shared_tags,
                    seed_titles=explanation.seed_titles,
                    quiz_answers=explanation.quiz_answers,
                ),
            )
        )

    return results


def recommend_from_profile(
    user_items: list[dict[str, Any]],
    n: int = settings.REC_DEFAULT_N,
    include_mature: bool = False,
    quiz_prior_vec: np.ndarray | None = None,
    index: VectorIndex | None = None,
) -> list[RecResult]:
    """Endpoint 4d: Personalised recommendations from user profile (recs/me).

    Fallback: if no ratings and no quiz prior, returns the quality-ranked list.
    """
    if index is None:
        index = get_index()
    if index.is_empty():
        return []

    exclude_ids = {
        item.get("anime_id") or item.get("id")
        for item in user_items
        if item.get("anime_id") or item.get("id")
    }

    candidates = _filter_and_relax_candidates(
        index,
        exclude_ids=exclude_ids,
        include_mature=include_mature,
        n=n,
    )
    if not candidates:
        return []

    cand_records = [index.records[i] for i in candidates]
    cand_q_scores = np.array([r.quality_pct for r in cand_records], dtype=np.float64)

    taste_vec = build_taste_vector(user_items, quiz_prior_vec, index)
    is_empty_taste = not np.any(taste_vec != 0)

    # Empty case fallback: return quality-ranked list
    if is_empty_taste:
        sorted_pos = np.argsort(-cand_q_scores)[:n]
        results: list[RecResult] = []
        for p in sorted_pos:
            rec = cand_records[p]
            cand_idx = candidates[p]
            explanation = build_explanation(
                query_vec=np.zeros(index.matrix.shape[1], dtype=np.float32),
                item_vec=index.matrix[cand_idx],
                index=index,
                is_cold_start=True,
            )
            results.append(
                RecResult(
                    id=rec.id,
                    title=rec.title,
                    title_english=rec.title,
                    title_romaji=rec.title,
                    title_native=rec.title,
                    format=rec.format,
                    episodes=rec.episodes,
                    year=rec.season_year,
                    score=rec.average_score,
                    popularity=rec.popularity,
                    is_adult=rec.is_adult,
                    genres=rec.genres,
                    reason=explanation.reason,
                    similarity=rec.quality_pct,
                    explanation=ExplanationSchema(
                        shared_genres=explanation.shared_genres,
                        shared_tags=explanation.shared_tags,
                        seed_titles=[],
                        quiz_answers=[],
                    ),
                )
            )
        return results

    # Non-empty taste vector
    cand_matrix = index.matrix[candidates]
    taste_cos = cand_matrix @ taste_vec
    taste_scores = rank_norm(taste_cos)
    final_scores = compute_final_score(taste_scores, cand_q_scores)

    selected_indices = mmr_rerank(candidates, final_scores, index, n)

    # Collect top-3 liked seed titles for explanations
    liked_seeds = [
        item
        for item in user_items
        if (item.get("status") or "").lower() == "completed"
        and (item.get("rating") or 0) >= 7.0
    ]
    top_seed_titles: list[str] = []
    if liked_seeds:
        seed_tuples = []
        for s in liked_seeds:
            sid = s.get("anime_id") or s.get("id")
            srec = index.get(sid)
            svec = index.vec(sid)
            if srec and svec is not None:
                sim = float(svec @ taste_vec)
                seed_tuples.append((sim, srec.title))
        seed_tuples.sort(key=lambda x: -x[0])
        top_seed_titles = [t for _, t in seed_tuples[:3]]

    results = []
    for cand_idx in selected_indices:
        rec = index.records[cand_idx]
        pos = candidates.index(cand_idx)
        sim_val = float(taste_cos[pos])

        explanation = build_explanation(
            query_vec=taste_vec,
            item_vec=index.matrix[cand_idx],
            index=index,
            seed_titles=top_seed_titles,
        )

        results.append(
            RecResult(
                id=rec.id,
                title=rec.title,
                title_english=rec.title,
                title_romaji=rec.title,
                title_native=rec.title,
                format=rec.format,
                episodes=rec.episodes,
                year=rec.season_year,
                score=rec.average_score,
                popularity=rec.popularity,
                is_adult=rec.is_adult,
                genres=rec.genres,
                reason=explanation.reason,
                similarity=min(max(sim_val, 0.0), 1.0),
                explanation=ExplanationSchema(
                    shared_genres=explanation.shared_genres,
                    shared_tags=explanation.shared_tags,
                    seed_titles=explanation.seed_titles,
                    quiz_answers=explanation.quiz_answers,
                ),
            )
        )

    return results


async def rebuild_index_from_db(session: AsyncSession) -> VectorIndex:
    """Loads all catalog anime with genres and tags, builds VectorIndex,
    and sets it globally.
    """
    stmt = select(Anime).options(
        selectinload(Anime.genres),
        selectinload(Anime.tags),
    )
    result = await session.execute(stmt)
    anime_rows = result.scalars().all()

    # Load tag ranks from anime_tags association table
    from collections import defaultdict

    from app.models.anime import anime_tags

    tag_stmt = select(anime_tags.c.anime_id, Tag.name, anime_tags.c.rank).join(
        Tag, anime_tags.c.tag_id == Tag.id
    )
    tag_res = await session.execute(tag_stmt)
    anime_to_tags: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for aid, tname, trank in tag_res.fetchall():
        anime_to_tags[aid].append({"name": tname, "rank": trank or 0})

    items = []
    for a in anime_rows:
        items.append(
            {
                "id": a.id,
                "title_english": a.title_english,
                "title_romaji": a.title_romaji,
                "title_native": a.title_native,
                "franchise_id": a.franchise_id,
                "average_score": a.average_score,
                "popularity": a.popularity,
                "episodes": a.episodes,
                "season_year": a.season_year,
                "is_adult": a.is_adult,
                "format": a.format,
                "genres": [g.name for g in a.genres],
                "tags": anime_to_tags.get(a.id, []),
            }
        )

    idx = VectorIndex.build(
        items,
        w_genre=settings.REC_GENRE_DIM_WEIGHT,
        w_tag=settings.REC_TAG_DIM_WEIGHT,
        w_format=settings.REC_FORMAT_DIM_WEIGHT,
    )
    set_index(idx)
    return idx
