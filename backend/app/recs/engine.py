"""Recommendation engine core: feature vectors, scoring, ranking, and MMR.

Scoring Formulas (Phase 4 Round 2)
------------------------------------
Relevance-leading design: blended cosine similarity is min-max scaled over the
top REC_TOP_CANDIDATES (200) so the similarity distribution is not compressed by
global rank-normalisation.  Quality is then added as a small bonus.

1. Logged-out similar:
   sim200     = top-200 blended cosine scores
   rel(x)     = minmax(cos(seed_vec, x), over sim200)
   final(x)   = rel(x) + q * quality_pct(x)

2. Logged-in similar:
   blended(x) = alpha * cos(seed_vec, x) + (1-alpha) * cos(taste_vec, x)
   rel(x)     = minmax(blended(x), over top-200 blended scores)
   final(x)   = rel(x) + q * quality_pct(x)
   Fallback: if taste_vec is empty/all-zeros, falls back to formula 1.

3. Quiz:
   rel(x)     = minmax(cos(quiz_vec, x), over top-200 scores)
   final(x)   = rel(x) + q * quality_pct(x)
   Followed by soft score penalties for length and era constraints.

4. Profile (recs/me):
   rel(x)     = minmax(cos(taste_vec, x), over top-200 scores)
   final(x)   = rel(x) + q * quality_pct(x)
   Fallback: if no ratings and no quiz prior, returns quality_pct-ranked list.

MMR movement cap:
   MMR is run only over the top REC_MMR_POOL (40) candidates by final_score.
   Items outside this pool are never pulled in — this prevents a distant low-
   relevance item from displacing a near-top result just for diversity.

Candidate exclusion:
   Titles with no start year (season_year IS NULL) or AniList status
   NOT_YET_RELEASED are excluded from all recommendation lists.

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
from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.anime import Anime, Tag
from app.recs.explain import (
    build_explanation,
    count_profile_salient,
    count_quiz_salient,
    count_shared_salient,
)
from app.recs.quiz import (
    apply_quiz_soft_penalties,
    build_quiz_vector,
    parse_quiz_answers,
)
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


def _minmax_scale(scores: np.ndarray) -> np.ndarray:
    """Min-max scale an array to [0, 1].

    All-identical arrays return all-ones (best rank for tied items).
    """
    if len(scores) == 0:
        return scores
    min_v, max_v = float(np.min(scores)), float(np.max(scores))
    if math.isclose(min_v, max_v):
        return np.ones(len(scores), dtype=np.float64)
    return (scores - min_v) / (max_v - min_v)


def _relevance_scores(
    cos_scores: np.ndarray,
    top_k: int = settings.REC_TOP_CANDIDATES,
) -> np.ndarray:
    """Compute relevance by min-max scaling cosine scores over the top-k candidates.

    Steps:
    1. Select the top-k cosine scores.
    2. Compute min/max from those top-k values.
    3. Scale all scores by that range so items inside top-k map to [0,1] and
       items below the top-k minimum are clamped to 0.

    This prevents global rank-normalisation from compressing the similarity
    distribution when the full candidate pool is large.
    """
    n = len(cos_scores)
    if n == 0:
        return cos_scores.copy()

    k = min(top_k, n)
    # Compute min/max from the top-k scores only
    top_k_vals = np.partition(cos_scores, -k)[-k:]
    min_v = float(np.min(top_k_vals))
    max_v = float(np.max(top_k_vals))

    if math.isclose(min_v, max_v):
        # All top-k are identical — give them all 1.0
        return np.where(cos_scores >= min_v, 1.0, 0.0).astype(np.float64)

    scaled = (cos_scores - min_v) / (max_v - min_v)
    # Items below the top-k min floor get 0
    return np.clip(scaled, 0.0, 1.0).astype(np.float64)


def rank_norm(
    scores: np.ndarray | float, pool: np.ndarray | list[float] | None = None
) -> np.ndarray | float:
    """Rank-normalise scores into the [0, 1] interval.

    Kept for quiz soft-penalty compatibility and unit-test parity.
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
    rel_score: float | np.ndarray,
    quality_score: float | np.ndarray,
    q: float = settings.REC_QUALITY_WEIGHT,
) -> float | np.ndarray:
    """Computes rel_score + q * quality_score (relevance-leading additive blend).

    `rel_score` is expected to be in [0, 1] from min-max scaling over the
    top-200 candidates.  `q` is a small additive bonus (default 0.1) so that
    a high-quality item cannot outrank a much more relevant but slightly lower
    quality item.
    """
    return rel_score + q * quality_score


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

    Movement cap: MMR is run only over the top REC_MMR_POOL candidates by
    final_score.  Items outside the pool are never considered, preventing a
    distant low-relevance item from being pulled in purely for diversity.
    """
    if len(candidate_indices) <= n:
        return candidate_indices

    # Hard cap: MMR pool is the top REC_MMR_POOL by final_score
    pool_size = min(len(candidate_indices), settings.REC_MMR_POOL)
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


@dataclass
class CandidateScore:
    """Internal score and ranking container for candidate items during recommendation."""

    cand_idx: int
    final_score: float
    raw_cosine: float
    rank_sim: float
    quality_score: float
    rank_taste: float | None = None
    pre_mmr_rank: int = 0


def _filter_and_relax_candidates(
    index: VectorIndex,
    *,
    seed_id: int | None = None,
    seed_franchise_id: int | None = None,
    seed_format: str | None = None,
    seed_duration: int | None = None,
    exclude_ids: set[int] | None = None,
    include_mature: bool = False,
    n: int = 10,
) -> list[int]:
    """Filters candidates based on exclusions, format, duration, mature filter,
    unreleased / no-year titles, then relaxes score and popularity floors if
    candidate count is below n.
    """
    exclude = set(exclude_ids or set())
    if seed_id is not None:
        exclude.add(seed_id)

    allow_formats = set()
    seed_fmt_upper = (seed_format or "").upper()
    if seed_fmt_upper in {"OVA", "SPECIAL", "MUSIC"}:
        allow_formats.add(seed_fmt_upper)

    allow_short = False
    if seed_duration is not None and seed_duration < 12:
        allow_short = True

    base_candidates: list[int] = []
    for idx, rec in enumerate(index.records):
        # Mature filter
        if rec.is_adult and not include_mature:
            continue
        # Excluded items (user list, seed)
        if rec.id in exclude:
            continue
        # Franchise exclusion: same franchise as seed (None never matches None)
        if (
            seed_franchise_id is not None
            and rec.franchise_id is not None
            and rec.franchise_id == seed_franchise_id
        ):
            continue

        # Exclude titles with no start year (season_year is NULL)
        if rec.season_year is None:
            continue

        # Exclude titles that are not yet released
        if (rec.status or "").upper() == "NOT_YET_RELEASED":
            continue

        # Format filter: exclude OVA, SPECIAL, MUSIC unless seed is that format
        rec_fmt = (rec.format or "").upper()
        if rec_fmt in {"OVA", "SPECIAL", "MUSIC"} and rec_fmt not in allow_formats:
            continue

        # Duration filter: exclude under 12 min unless seed is under 12 min
        if not allow_short and rec.duration is not None and rec.duration < 12:
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


def _collapse_franchises(
    candidate_indices: list[int],
    final_scores: np.ndarray,
    raw_cosines: np.ndarray,
    rank_sims: np.ndarray,
    quality_scores: np.ndarray,
    index: VectorIndex,
    rank_tastes: np.ndarray | None = None,
) -> list[CandidateScore]:
    """Collapses candidate items by franchise: one entry per franchise per list.

    Ranks each franchise by its best-scoring member, but presents the franchise's
    canonical entry point (the earliest-aired TV title, or the earliest movie if
    no TV title exists).  If the canonical entry point is not in the candidate list
    (e.g. excluded or filtered), falls back to the earliest-aired available title
    of the preferred format.  Standalone items (franchise_id is None) are
    preserved individually.
    """
    from collections import defaultdict

    groups: dict[Any, list[int]] = defaultdict(list)
    for pos, cand_idx in enumerate(candidate_indices):
        rec = index.records[cand_idx]
        if rec.franchise_id is None:
            groups[("item", rec.id)].append(pos)
        else:
            groups[("franchise", rec.franchise_id)].append(pos)

    collapsed: list[CandidateScore] = []
    for group_key, positions in groups.items():
        # Find best-scoring member in this group
        best_pos = positions[0]
        best_score = float(final_scores[best_pos])
        for p in positions[1:]:
            sc = float(final_scores[p])
            if sc > best_score:
                best_score = sc
                best_pos = p

        best_raw_cos = float(raw_cosines[best_pos])
        best_rank_sim = float(rank_sims[best_pos])
        best_rank_taste = (
            float(rank_tastes[best_pos]) if rank_tastes is not None else None
        )
        best_quality = float(quality_scores[best_pos])

        if group_key[0] == "franchise":
            fid = group_key[1]
            canonical_id = index.franchise_entry_points.get(fid)
            # Check if canonical entry point is among the available candidate positions
            canonical_pos = next(
                (
                    p
                    for p in positions
                    if index.records[candidate_indices[p]].id == canonical_id
                ),
                None,
            )
            if canonical_pos is not None:
                rep_cand_idx = candidate_indices[canonical_pos]
            else:
                # Fallback: earliest-aired TV, then movie, then any available title.
                # Sort by (season_year or 9999, id) — same rule as VectorIndex.build.
                group_cand_indices = [candidate_indices[p] for p in positions]
                tv_cands = [
                    idx
                    for idx in group_cand_indices
                    if (index.records[idx].format or "").upper() == "TV"
                ]
                if tv_cands:
                    cands = tv_cands
                else:
                    movie_cands = [
                        idx
                        for idx in group_cand_indices
                        if (index.records[idx].format or "").upper() == "MOVIE"
                    ]
                    cands = movie_cands if movie_cands else group_cand_indices
                cands.sort(
                    key=lambda idx: (
                        (
                            index.records[idx].season_year
                            if index.records[idx].season_year is not None
                            else 9999
                        ),
                        index.records[idx].id,
                    )
                )
                rep_cand_idx = cands[0]
        else:
            rep_cand_idx = candidate_indices[positions[0]]

        collapsed.append(
            CandidateScore(
                cand_idx=rep_cand_idx,
                final_score=best_score,
                raw_cosine=best_raw_cos,
                rank_sim=best_rank_sim,
                quality_score=best_quality,
                rank_taste=best_rank_taste,
            )
        )

    # Sort pre-MMR by final_score descending (tiebreak: quality_score, then lowest anime id)
    collapsed.sort(
        key=lambda c: (
            -c.final_score,
            -c.quality_score,
            index.records[c.cand_idx].id,
        )
    )

    # Assign pre-MMR ranks (1-indexed)
    for rank_i, c in enumerate(collapsed, start=1):
        c.pre_mmr_rank = rank_i

    return collapsed


def recommend_similar(
    anime_id: int,
    n: int = settings.REC_DEFAULT_N,
    include_mature: bool = False,
    user_items: list[dict[str, Any]] | None = None,
    quiz_prior_vec: np.ndarray | None = None,
    index: VectorIndex | None = None,
) -> list[RecResult]:
    """Endpoint 4a / 4b: Recommends similar anime given a seed anime_id.

    - Logged-out: pure seed similarity (min-max scaled) + additive quality bonus.
    - Logged-in: combines seed similarity (alpha=0.6) and taste vector (0.4),
      min-max scaled, + additive quality bonus.
    - Empty taste vector fallback: pure similarity.
    - Requires >= REC_MIN_SALIENT_FEATURES shared salient features per result;
      returns fewer than N rather than padding.
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
        seed_format=seed_record.format,
        seed_duration=seed_record.duration,
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

    # Check for taste signal
    taste_vec = None
    has_taste = False
    taste_genres: list[str] = []
    taste_scores: np.ndarray | None = None

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

    # Combine signals then min-max scale over top-200
    if has_taste and taste_vec is not None:
        taste_cos = cand_matrix @ taste_vec
        blended_cos = (
            settings.REC_ALPHA * seed_cos + (1.0 - settings.REC_ALPHA) * taste_cos
        )
        sim_scores = _relevance_scores(blended_cos)
        taste_scores = _relevance_scores(taste_cos)
        final_scores = compute_final_score(sim_scores, cand_q_scores)
    else:
        # Fallback to pure similarity (logged-out or empty taste)
        sim_scores = _relevance_scores(seed_cos)
        final_scores = compute_final_score(sim_scores, cand_q_scores)
        taste_cos = seed_cos  # alias so raw_cosines below is always seed_cos

    # Collapse franchises to one entry per franchise
    collapsed = _collapse_franchises(
        candidates,
        final_scores=final_scores,
        raw_cosines=seed_cos,
        rank_sims=sim_scores,
        quality_scores=cand_q_scores,
        index=index,
        rank_tastes=taste_scores,
    )

    collapsed_cand_indices = [c.cand_idx for c in collapsed]
    collapsed_scores = np.array([c.final_score for c in collapsed], dtype=np.float64)
    cand_score_lookup = {c.cand_idx: c for c in collapsed}

    # MMR re-ranking (capped to top REC_MMR_POOL = 40 by final_score)
    selected_indices = mmr_rerank(collapsed_cand_indices, collapsed_scores, index, n)

    results: list[RecResult] = []
    for cand_idx in selected_indices:
        rec = index.records[cand_idx]
        cand_score = cand_score_lookup[cand_idx]

        explanation = build_explanation(
            query_vec=seed_vec,
            item_vec=index.matrix[cand_idx],
            index=index,
            query_record=seed_record,
            item_record=rec,
            seed_title=seed_record.title,
            has_taste=has_taste,
            taste_genres=taste_genres,
        )

        # Salient feature gate: require >= REC_MIN_SALIENT_FEATURES shared features.
        # Uses direct genre/tag membership rather than above-mean contribution so
        # that the gate is robust on tiny catalogs as well as the full index.
        # Never pad — return fewer than N rather than showing filler.
        if count_shared_salient(seed_record, rec) < settings.REC_MIN_SALIENT_FEATURES:
            continue

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
                similarity=min(max(cand_score.raw_cosine, 0.0), 1.0),
                raw_cosine=round(float(cand_score.raw_cosine), 4),
                rank_sim=round(float(cand_score.rank_sim), 4),
                rank_taste=(
                    round(float(cand_score.rank_taste), 4)
                    if cand_score.rank_taste is not None
                    else None
                ),
                quality_score=round(float(cand_score.quality_score), 4),
                final_score=round(float(cand_score.final_score), 4),
                pre_mmr_rank=cand_score.pre_mmr_rank,
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

    genre_weights, tag_weights, labels, constraints = parse_quiz_answers(answers)
    quiz_vec, _, _ = build_quiz_vector(answers, index)

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
    sim_scores = _relevance_scores(cos_sim)
    final_scores = compute_final_score(sim_scores, cand_q_scores)

    # Apply soft penalties for episode / year constraints
    final_scores = apply_quiz_soft_penalties(final_scores, cand_records, constraints)

    # Collapse franchises to one entry per franchise
    collapsed = _collapse_franchises(
        candidates,
        final_scores=final_scores,
        raw_cosines=cos_sim,
        rank_sims=sim_scores,
        quality_scores=cand_q_scores,
        index=index,
    )

    collapsed_cand_indices = [c.cand_idx for c in collapsed]
    collapsed_scores = np.array([c.final_score for c in collapsed], dtype=np.float64)
    cand_score_lookup = {c.cand_idx: c for c in collapsed}

    selected_indices = mmr_rerank(collapsed_cand_indices, collapsed_scores, index, n)

    target_genres = set(genre_weights.keys())
    target_tags = set(tag_weights.keys())

    results: list[RecResult] = []
    for cand_idx in selected_indices:
        rec = index.records[cand_idx]
        cand_score = cand_score_lookup[cand_idx]

        # Salient feature gate: require >= REC_MIN_SALIENT_FEATURES shared features with quiz targets
        if (target_genres or target_tags) and count_quiz_salient(
            target_genres, target_tags, rec
        ) < settings.REC_MIN_SALIENT_FEATURES:
            continue

        explanation = build_explanation(
            query_vec=quiz_vec,
            item_vec=index.matrix[cand_idx],
            index=index,
            item_record=rec,
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
                similarity=min(max(cand_score.raw_cosine, 0.0), 1.0),
                raw_cosine=round(float(cand_score.raw_cosine), 4),
                rank_sim=round(float(cand_score.rank_sim), 4),
                quality_score=round(float(cand_score.quality_score), 4),
                final_score=round(float(cand_score.final_score), 4),
                pre_mmr_rank=cand_score.pre_mmr_rank,
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

    # Empty case fallback: return quality-ranked list with franchise collapsing
    if is_empty_taste:
        dummy_zeros = np.zeros(len(candidates), dtype=np.float64)
        collapsed = _collapse_franchises(
            candidates,
            final_scores=cand_q_scores,
            raw_cosines=dummy_zeros,
            rank_sims=dummy_zeros,
            quality_scores=cand_q_scores,
            index=index,
        )
        selected_scores = collapsed[:n]
        results: list[RecResult] = []
        for cs in selected_scores:
            rec = index.records[cs.cand_idx]
            explanation = build_explanation(
                query_vec=np.zeros(index.matrix.shape[1], dtype=np.float32),
                item_vec=index.matrix[cs.cand_idx],
                index=index,
                item_record=rec,
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
                    similarity=round(float(rec.quality_pct), 4),
                    quality_score=round(float(cs.quality_score), 4),
                    final_score=round(float(cs.final_score), 4),
                    pre_mmr_rank=cs.pre_mmr_rank,
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
    taste_scores = _relevance_scores(taste_cos)
    final_scores = compute_final_score(taste_scores, cand_q_scores)

    # Collapse franchises to one entry per franchise
    collapsed = _collapse_franchises(
        candidates,
        final_scores=final_scores,
        raw_cosines=taste_cos,
        rank_sims=taste_scores,
        quality_scores=cand_q_scores,
        index=index,
        rank_tastes=taste_scores,
    )

    collapsed_cand_indices = [c.cand_idx for c in collapsed]
    collapsed_scores = np.array([c.final_score for c in collapsed], dtype=np.float64)
    cand_score_lookup = {c.cand_idx: c for c in collapsed}

    selected_indices = mmr_rerank(collapsed_cand_indices, collapsed_scores, index, n)

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

    liked_seed_records = [
        index.get(item.get("anime_id") or item.get("id"))
        for item in (
            liked_seeds
            if liked_seeds
            else [it for it in user_items if (it.get("rating") or 0) >= 6.0]
        )
    ]
    liked_seed_records = [r for r in liked_seed_records if r is not None]

    results = []
    for cand_idx in selected_indices:
        rec = index.records[cand_idx]
        cand_score = cand_score_lookup[cand_idx]

        # Salient feature gate: require >= REC_MIN_SALIENT_FEATURES shared features with profile / liked seeds
        if (
            count_profile_salient(
                taste_vec, rec, index, liked_seed_records=liked_seed_records
            )
            < settings.REC_MIN_SALIENT_FEATURES
        ):
            continue

        explanation = build_explanation(
            query_vec=taste_vec,
            item_vec=index.matrix[cand_idx],
            index=index,
            item_record=rec,
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
                similarity=min(max(cand_score.raw_cosine, 0.0), 1.0),
                raw_cosine=round(float(cand_score.raw_cosine), 4),
                rank_taste=(
                    round(float(cand_score.rank_taste), 4)
                    if cand_score.rank_taste is not None
                    else None
                ),
                quality_score=round(float(cand_score.quality_score), 4),
                final_score=round(float(cand_score.final_score), 4),
                pre_mmr_rank=cand_score.pre_mmr_rank,
                explanation=ExplanationSchema(
                    shared_genres=explanation.shared_genres,
                    shared_tags=explanation.shared_tags,
                    seed_titles=explanation.seed_titles,
                    quiz_answers=explanation.quiz_answers,
                ),
            )
        )

    return results


def explain_pair_debug(
    id_a: int,
    id_b: int,
    index: VectorIndex,
    top_k: int = 10,
) -> tuple[list[dict[str, Any]], float, str, str]:
    """Return the top-k contributing features for the cosine dot product between
    two anime vectors, expressed as vec_a[j] * vec_b[j] (IDF already baked in).

    Used for diagnosing spurious high-similarity pairs (e.g., Fate/Zero vs
    Laid-Back Camp, Lupin III vs Death Note).

    Returns (rows, cosine, title_a, title_b) where rows is a list of dicts
    with keys: feature, block, contrib, q_val, i_val.
    """
    from app.recs.vectors import FORMAT_VOCAB

    rec_a = index.get(id_a)
    rec_b = index.get(id_b)
    if rec_a is None or rec_b is None:
        return [], 0.0, str(id_a), str(id_b)

    vec_a = index.vec(id_a)
    vec_b = index.vec(id_b)
    if vec_a is None or vec_b is None:
        return [], 0.0, rec_a.title, rec_b.title

    contribs = (vec_a * vec_b).astype(np.float64)  # element-wise
    cosine = float(np.dot(vec_a, vec_b))

    # Build feature name list parallel to vector dimensions
    feature_names: list[tuple[str, str]] = []  # (name, block)
    for g in index.all_genres:
        feature_names.append((g, "genre"))
    for t in index.all_tags:
        feature_names.append((t, "tag"))
    for f in FORMAT_VOCAB:
        feature_names.append((f, "format"))

    rows = [
        {
            "feature": name,
            "block": block,
            "contrib": float(contribs[i]),
            "q_val": float(vec_a[i]),
            "i_val": float(vec_b[i]),
        }
        for i, (name, block) in enumerate(feature_names)
        if contribs[i] > 0
    ]
    rows.sort(key=lambda r: -r["contrib"])
    return rows[:top_k], cosine, rec_a.title, rec_b.title


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

    # Load prequel relations to identify which catalog items have a prequel in catalog
    from collections import defaultdict

    from app.models.anime import anime_relations, anime_tags

    catalog_ids_set = {a.id for a in anime_rows}
    rel_stmt = select(
        anime_relations.c.anime_id,
        anime_relations.c.related_id,
        anime_relations.c.rel_type,
    ).where(anime_relations.c.rel_type.in_(["PREQUEL", "SEQUEL", "PARENT"]))
    rel_res = await session.execute(rel_stmt)
    has_prequel: set[int] = set()
    for aid, rid, rtype in rel_res.fetchall():
        if rtype in ("PREQUEL", "PARENT") and rid in catalog_ids_set:
            has_prequel.add(aid)
        elif rtype == "SEQUEL" and aid in catalog_ids_set:
            has_prequel.add(rid)

    # Load tag ranks and spoiler flags from anime_tags association table
    tag_stmt = select(
        anime_tags.c.anime_id,
        Tag.name,
        anime_tags.c.rank,
        anime_tags.c.is_spoiler,
    ).join(Tag, anime_tags.c.tag_id == Tag.id)
    tag_res = await session.execute(tag_stmt)
    anime_to_tags: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for aid, tname, trank, is_sp in tag_res.fetchall():
        anime_to_tags[aid].append(
            {"name": tname, "rank": trank or 0, "is_spoiler": bool(is_sp)}
        )

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
                "duration": a.duration,
                "season_year": a.season_year,
                "status": a.status,
                "is_adult": a.is_adult,
                "format": a.format,
                "genres": [g.name for g in a.genres],
                "tags": anime_to_tags.get(a.id, []),
                "has_prequel": a.id in has_prequel,
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
