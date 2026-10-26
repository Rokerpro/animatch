"""Explanation dataclass and sentence templates for the rec engine.

Explanations are derived from per-feature contributions to the dot product
between the query vector and the item vector.  Format dimensions are never
named in explanations — only genres and tags that contributed above-average
to the dot product are surfaced.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.recs.vectors import VectorIndex


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
    max_genres: int = 3,
    max_tags: int = 3,
) -> tuple[list[str], list[str]]:
    """Return genre and tag names whose contribution to the dot product exceeds
    the mean per-dimension contribution for their block.

    Contribution of dimension j = query_vec[j] * item_vec[j].

    Format dims are deliberately skipped — format is too coarse to name in
    a meaningful explanation.
    """
    contribs = query_vec * item_vec  # element-wise

    # Genre block
    g_contribs = contribs[index.genre_start : index.genre_end]
    mean_g = g_contribs.mean() if len(g_contribs) > 0 else 0.0
    genre_hits = [
        (index.all_genres[j], g_contribs[j])
        for j in range(len(index.all_genres))
        if g_contribs[j] > mean_g and g_contribs[j] > 0
    ]
    genre_hits.sort(key=lambda x: -x[1])
    top_genres = [name for name, _ in genre_hits[:max_genres]]

    # Tag block
    t_contribs = contribs[index.tag_start : index.tag_end]
    mean_t = t_contribs.mean() if len(t_contribs) > 0 else 0.0
    tag_hits = [
        (index.all_tags[j], t_contribs[j])
        for j in range(len(index.all_tags))
        if t_contribs[j] > mean_t and t_contribs[j] > 0
    ]
    tag_hits.sort(key=lambda x: -x[1])
    top_tags = [name for name, _ in tag_hits[:max_tags]]

    return top_genres, top_tags


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
    seed_title: str | None = None,
    seed_titles: list[str] | None = None,
    quiz_answers: list[str] | None = None,
    has_taste: bool = False,
    taste_genres: list[str] | None = None,
    is_cold_start: bool = False,
) -> Explanation:
    """Build a structured Explanation and its reason sentence.

    Parameters
    ----------
    query_vec
        The query vector used for this result (seed, quiz, taste, or hybrid).
    item_vec
        The normalised item feature vector from the index.
    seed_title
        Primary seed anime title (similar_to mode).
    seed_titles
        Top-3 user-rated titles most similar to this result (profile mode).
    quiz_answers
        Human-readable labels of quiz answers submitted.
    has_taste
        True when a taste vector contributed to the query.
    taste_genres
        Top genres from the taste vector (for logged-in similar_to).
    is_cold_start
        True when no taste or quiz signal was available.
    """
    top_genres, top_tags = _top_contributions(query_vec, item_vec, index)
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
        # Logged-out similar_to
        reason = (
            f"Because it shares {genres_str} with {seed_title}{tag_clause}."
            if genres_str
            else f"Similar to {seed_title}."
        )
    elif seed_title and has_taste:
        # Logged-in similar_to
        taste_str = _join(taste_genres or [])
        if taste_str and genres_str:
            reason = (
                f"Similar to {seed_title}, shares {genres_str}"
                f" and matches your taste in {taste_str}."
            )
        elif genres_str:
            reason = f"Because it shares {genres_str} with {seed_title}{tag_clause}."
        else:
            reason = f"Similar to {seed_title} and matches your taste."
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
