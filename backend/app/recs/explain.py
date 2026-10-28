"""Explanation dataclass and sentence templates for the rec engine.

Explanations are derived from per-feature contributions to the dot product
between the query vector and the item vector.  Format dimensions are never
named in explanations — only genres and tags that contributed above-average
to the dot product are surfaced.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.recs.vectors import AnimeRecord, VectorIndex


@dataclass
class Explanation:
    """Structured explanation for a single recommendation result.

    Fields
    ------
    shared_genres
        Genre names where the dot-product contribution exceeded the mean
        per-dimension contribution for the genre block.  Sorted by
        contribution descending.

    shared_tags
        Same, for the tag block.

    seed_titles
        Up to 3 titles from the user's rated list with the highest cosine
        similarity to the recommended item (profile mode only).

    quiz_answers
        Human-readable labels of the answered quiz questions (quiz mode only).

    reason
        A single deterministic English sentence built from the fields above.
    """

    shared_genres: list[str] = field(default_factory=list)
    shared_tags: list[str] = field(default_factory=list)
    seed_titles: list[str] = field(default_factory=list)
    quiz_answers: list[str] = field(default_factory=list)
    reason: str = ""


def _top_contributions(
    query_vec: np.ndarray,
    item_vec: np.ndarray,
    index: VectorIndex,
    query_record: AnimeRecord | None = None,
    item_record: AnimeRecord | None = None,
    min_tag_rank: int = 60,
    max_genres: int = 3,
    max_tags: int = 3,
) -> tuple[list[str], list[str]]:
    """Return genre and tag names whose contribution to the dot product exceeds
    the mean per-dimension contribution for their block.

    Edge case: when all genre contributions are identical (e.g. a 2-genre catalog
    where every genre is shared), all positive genres are returned — "above mean"
    is trivially empty in that case and would give a misleading empty list.

    Tags must have rank >= min_tag_rank on BOTH titles (when records are provided)
    and must not be flagged as spoilers on either title.

    Contribution of dimension j = query_vec[j] * item_vec[j].
    """
    contribs = query_vec * item_vec  # element-wise

    # Genre block
    g_contribs = contribs[index.genre_start : index.genre_end]
    mean_g = g_contribs.mean() if len(g_contribs) > 0 else 0.0
    max_g = g_contribs.max() if len(g_contribs) > 0 else 0.0
    # If max == mean, all shared genres are equal: return all positive ones.
    g_threshold = mean_g if max_g > mean_g else -1.0
    genre_hits = [
        (index.all_genres[j], g_contribs[j])
        for j in range(len(index.all_genres))
        if g_contribs[j] > g_threshold and g_contribs[j] > 0
    ]
    genre_hits.sort(key=lambda x: -x[1])
    top_genres = [name for name, _ in genre_hits[:max_genres]]

    # Tag block
    t_contribs = contribs[index.tag_start : index.tag_end]
    mean_t = t_contribs.mean() if len(t_contribs) > 0 else 0.0
    max_t = t_contribs.max() if len(t_contribs) > 0 else 0.0
    t_threshold = mean_t if max_t > mean_t else -1.0
    tag_hits = []
    for j in range(len(index.all_tags)):
        c = t_contribs[j]
        if c <= t_threshold or c <= 0:
            continue
        tname = index.all_tags[j]

        # Check item constraints
        if item_record is not None:
            if item_record.raw_tag_ranks.get(tname, 0) < min_tag_rank:
                continue
            if tname in item_record.tag_spoilers:
                continue

        # Check query constraints (when query is a seed anime)
        if query_record is not None:
            if query_record.raw_tag_ranks.get(tname, 0) < min_tag_rank:
                continue
            if tname in query_record.tag_spoilers:
                continue

        tag_hits.append((tname, c))

    tag_hits.sort(key=lambda x: -x[1])
    top_tags = [name for name, _ in tag_hits[:max_tags]]

    return top_genres, top_tags


def count_shared_salient(
    query_record: AnimeRecord,
    item_record: AnimeRecord,
    min_tag_rank: int = 60,
) -> int:
    """Count shared salient features between two titles using direct membership.

    A feature is shared-salient if:
    - Genre: present in both titles' genre lists.
    - Tag: rank >= min_tag_rank on BOTH titles AND not a spoiler on either.

    This is used as the engine's gate predicate (require >= REC_MIN_SALIENT_FEATURES)
    and is intentionally independent of IDF/mean-contribution math so that it
    works correctly on tiny test catalogs as well as the full production index.
    """
    seed_genres = set(query_record.genres)
    item_genres = set(item_record.genres)
    shared_genres = seed_genres & item_genres

    seed_tags_ok = {
        t
        for t, rank in query_record.raw_tag_ranks.items()
        if rank >= min_tag_rank and t not in query_record.tag_spoilers
    }
    item_tags_ok = {
        t
        for t, rank in item_record.raw_tag_ranks.items()
        if rank >= min_tag_rank and t not in item_record.tag_spoilers
    }
    shared_tags = seed_tags_ok & item_tags_ok

    return len(shared_genres) + len(shared_tags)


def count_quiz_salient(
    target_genres: set[str],
    target_tags: set[str],
    item_record: AnimeRecord,
    min_tag_rank: int = 60,
) -> int:
    """Count shared salient features between quiz targets and an item.

    - Genre: item genre is in target_genres.
    - Tag: item tag is in target_tags with rank >= min_tag_rank and not a spoiler.
    """
    shared_genres = set(item_record.genres) & target_genres
    shared_tags = {
        t
        for t in target_tags
        if item_record.raw_tag_ranks.get(t, 0) >= min_tag_rank
        and t not in item_record.tag_spoilers
    }
    return len(shared_genres) + len(shared_tags)


def count_profile_salient(
    taste_vec: np.ndarray,
    item_record: AnimeRecord,
    index: VectorIndex,
    liked_seed_records: list[AnimeRecord] | None = None,
    min_tag_rank: int = 60,
) -> int:
    """Count shared salient features between user profile and an item.

    If liked_seed_records are present, checks if the item shares >= 2 salient features
    with ANY of the user's liked seeds (or returns the max shared across seeds).
    Also checks against positive dimensions in the taste vector:
    positive genre dimensions + positive tag dimensions (rank >= min_tag_rank, no spoiler).
    """
    # 1. Direct seed overlap if user has rated/completed titles
    if liked_seed_records:
        seed_max = max(
            (
                count_shared_salient(srec, item_record, min_tag_rank=min_tag_rank)
                for srec in liked_seed_records
                if srec is not None
            ),
            default=0,
        )
        if seed_max >= 2:
            return seed_max

    # 2. Taste-vector dimension overlap
    g_contribs = taste_vec[index.genre_start : index.genre_end]
    pos_genres = {
        index.all_genres[j] for j in range(len(index.all_genres)) if g_contribs[j] > 0
    }
    shared_genres = set(item_record.genres) & pos_genres

    t_contribs = taste_vec[index.tag_start : index.tag_end]
    pos_tags = {
        index.all_tags[j] for j in range(len(index.all_tags)) if t_contribs[j] > 0
    }
    shared_tags = {
        t
        for t in pos_tags
        if item_record.raw_tag_ranks.get(t, 0) >= min_tag_rank
        and t not in item_record.tag_spoilers
    }
    return len(shared_genres) + len(shared_tags)


def _join(items: list[str], limit: int = 3) -> str:
    """Formats a list as a readable comma-separated string."""
    items = items[:limit]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def build_explanation(
    *,
    query_vec: np.ndarray,
    item_vec: np.ndarray,
    index: VectorIndex,
    query_record: AnimeRecord | None = None,
    item_record: AnimeRecord | None = None,
    seed_title: str | None = None,
    seed_titles: list[str] | None = None,
    quiz_answers: list[str] | None = None,
    has_taste: bool = False,
    taste_genres: list[str] | None = None,
    is_cold_start: bool = False,
) -> Explanation:
    """Build a structured Explanation and its reason sentence."""
    top_genres, top_tags = _top_contributions(
        query_vec,
        item_vec,
        index,
        query_record=query_record,
        item_record=item_record,
        min_tag_rank=60,
    )
    seed_titles = seed_titles or []
    quiz_answers = quiz_answers or []

    genres_str = _join(top_genres)
    tags_str = _join(top_tags)
    tag_clause = f", and both feature {tags_str}" if top_tags else ""

    if is_cold_start:
        reason = (
            f"A popular, highly rated title in {genres_str}."
            if genres_str
            else "A popular, highly rated title."
        )
    elif seed_title and not has_taste:
        # Logged-out similar_to: requires >= 1 genre or tag in reason.
        # "Similar to X" alone (no shared features) is dropped — the engine
        # salient-feature gate will exclude results with < 2 shared features.
        if genres_str:
            reason = f"Because it shares {genres_str} with {seed_title}{tag_clause}."
        else:
            reason = ""  # gate will drop this result
    elif seed_title and has_taste:
        # Logged-in similar_to
        taste_str = _join(taste_genres or [])
        if genres_str:
            if taste_str:
                reason = (
                    f"Similar to {seed_title}, shares {genres_str}"
                    f" and matches your taste in {taste_str}."
                )
            else:
                reason = (
                    f"Because it shares {genres_str} with {seed_title}{tag_clause}."
                )
        else:
            reason = ""  # gate will drop this result
    elif quiz_answers:
        # Quiz mode
        answer_str = _join(quiz_answers[:2])
        reason = (
            f"Matches your preference for {answer_str} anime" f" with {genres_str}."
            if genres_str
            else f"Matches your preference for {answer_str} anime."
        )
    elif seed_titles:
        # Profile mode with rated seeds
        seeds_str = _join(seed_titles[:3])
        reason = (
            f"Because you liked {seeds_str} and rate {genres_str} highly."
            if genres_str
            else f"Because you liked {seeds_str}."
        )
    else:
        reason = (
            f"Recommended based on your taste in {genres_str}."
            if genres_str
            else "Recommended based on your taste profile."
        )

    return Explanation(
        shared_genres=top_genres,
        shared_tags=top_tags,
        seed_titles=seed_titles[:3],
        quiz_answers=quiz_answers,
        reason=reason,
    )
