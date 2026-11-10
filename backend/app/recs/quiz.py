"""Quiz loader, answer-to-vector mapping, and soft constraint penalties.

The quiz consists of 7 questions defined in app/data/quiz.json:
- Questions 1-5 (mood, pacing, tone, themes, intensity): map to genre and tag weights.
- Questions 6-7 (length, era): length is a candidate gate with relaxation, while
  length and era can also adjust scores; neither is a feature vector dimension.

Soft Penalty Formula:
---------------------
When a recommended candidate violates the user's selected length or era constraints,
its final score is scaled down by a configurable soft penalty factor:
  score = score * (1.0 - penalty_episode) * (1.0 - penalty_year)

Default settings:
  REC_QUIZ_SOFT_PENALTY_EPISODES = 0.5 (outside-range multiplier = 0.5)
  REC_QUIZ_SOFT_PENALTY_YEAR = 0.15

This ensures that strong semantic matches outside the preferred length/era can
still appear, but titles matching all criteria will be ranked above them.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import settings
from app.recs.vectors import AnimeRecord, VectorIndex

logger = logging.getLogger(__name__)

QUIZ_PATH = Path(__file__).resolve().parent.parent / "data" / "quiz.json"

THEME_GENRES: dict[str, tuple[str, ...]] = {
    "sci_fi": ("Sci-Fi", "Mecha"),
    "fantasy": ("Fantasy",),
    "mystery": ("Mystery",),
    "sports": ("Sports",),
    "slice_of_life": ("Slice of Life",),
    "action": ("Action", "Adventure"),
}
NEW_QUIZ_QUESTION_IDS = frozenset({"mood", "length", "era"})

_CACHED_QUIZ: dict[str, Any] | None = None


def load_quiz_data() -> dict[str, Any]:
    """Load and cache the quiz.json definition."""
    global _CACHED_QUIZ
    if _CACHED_QUIZ is None:
        with open(QUIZ_PATH, encoding="utf-8") as f:
            _CACHED_QUIZ = json.load(f)
    return _CACHED_QUIZ


def get_quiz_questions() -> list[dict[str, Any]]:
    """Return the list of quiz questions stripped of private comments."""
    quiz_data = load_quiz_data()
    clean_questions = []
    for q in quiz_data.get("questions", []):
        clean_q = {
            "id": q["id"],
            "label": q["label"],
            "answers": [
                {"id": a["id"], "label": a["label"]} for a in q.get("answers", [])
            ],
        }
        clean_questions.append(clean_q)
    return clean_questions


def validate_quiz_answers(
    answers: dict[str, str], allowed_question_ids: set[str] | None = None
) -> dict[str, str]:
    """Validate question and answer ids using the canonical quiz vocabulary."""
    q_map = {q["id"]: q for q in load_quiz_data().get("questions", [])}
    for qid, aid in answers.items():
        q = q_map.get(qid)
        if q is None:
            raise ValueError(f"Invalid quiz question id: {qid}")
        if allowed_question_ids is not None and qid not in allowed_question_ids:
            raise ValueError(f"Question is not allowed for this quiz: {qid}")
        if not any(a["id"] == aid for a in q.get("answers", [])):
            raise ValueError(f"Invalid answer id '{aid}' for question '{qid}'")
    return answers


def parse_quiz_answers(
    answers: dict[str, str],
) -> tuple[dict[str, float], dict[str, float], list[str], dict[str, Any]]:
    """Parse answer IDs into aggregated genre weights, tag weights, labels, and constraints.

    Parameters
    ----------
    answers : dict[str, str]
        Mapping from question_id to answer_id.

    Returns
    -------
    genre_weights : dict[str, float]
        Aggregated weights for genres.
    tag_weights : dict[str, float]
        Aggregated weights for tags.
    answer_labels : list[str]
        Human-readable labels of selected answers (for explanations).
    constraints : dict[str, Any]
        Merged constraints (e.g. min_episodes, max_episodes, min_year, max_year).
    """
    quiz_data = load_quiz_data()
    q_map = {q["id"]: q for q in quiz_data.get("questions", [])}

    genre_weights: dict[str, float] = defaultdict(float)
    tag_weights: dict[str, float] = defaultdict(float)
    answer_labels: list[str] = []
    constraints: dict[str, Any] = {}

    for qid, aid in answers.items():
        q = q_map.get(qid)
        if not q:
            continue
        ans = next((a for a in q.get("answers", []) if a["id"] == aid), None)
        if not ans:
            continue

        answer_labels.append(ans.get("label", aid))

        # Vector weights
        weights = ans.get("weights")
        if weights:
            for g, w in weights.get("genres", {}).items():
                genre_weights[g] += float(w)
            for t, w in weights.get("tags", {}).items():
                tag_weights[t] += float(w)

        # Soft constraints
        constraint = ans.get("constraint")
        if constraint:
            constraints.update(constraint)

    return dict(genre_weights), dict(tag_weights), answer_labels, constraints


def selected_theme_genres(answers: dict[str, str]) -> set[str]:
    """Return genre requirements for the selected theme answer, if any."""
    return set(THEME_GENRES.get(answers.get("themes", ""), ()))


def apply_quiz_length_gate(
    candidates: list[int],
    index: VectorIndex,
    constraints: dict[str, Any],
    limit: int,
) -> list[int]:
    """Filter to the requested episode range, widening it only when needed.

    The first relaxation adds one adjacent length range. For a medium request,
    the lower or upper adjacent range is chosen based on which yields more
    franchise-distinct candidates. If that still cannot fill ``limit``, the
    episode gate is dropped.
    """
    min_episodes = constraints.get("min_episodes")
    max_episodes = constraints.get("max_episodes")
    if min_episodes is None and max_episodes is None:
        return candidates

    low = 1 if min_episodes is None else int(min_episodes)
    high = None if max_episodes is None else int(max_episodes)

    def matching(minimum: int, maximum: int | None) -> list[int]:
        return [
            idx
            for idx in candidates
            if index.records[idx].episodes is not None
            and index.records[idx].episodes >= minimum
            and (maximum is None or index.records[idx].episodes <= maximum)
        ]

    def franchise_capacity(indices: list[int]) -> int:
        groups = {
            (
                ("item", index.records[idx].id)
                if index.records[idx].franchise_id is None
                else ("franchise", index.records[idx].franchise_id)
            )
            for idx in indices
        }
        return len(groups)

    strict = matching(low, high)
    if franchise_capacity(strict) >= limit:
        return strict

    adjacent_ranges: list[tuple[int, int | None]] = []
    if low == 1 and high == 13:
        adjacent_ranges.append((1, 26))
    elif low == 14 and high == 26:
        adjacent_ranges.extend(((1, 26), (14, None)))
    elif low == 27 and high is None:
        adjacent_ranges.append((14, None))

    widened = [matching(minimum, maximum) for minimum, maximum in adjacent_ranges]
    if widened:
        best = max(widened, key=franchise_capacity)
        if franchise_capacity(best) >= limit:
            return best

    return candidates


def build_quiz_vector(
    answers: dict[str, str],
    index: VectorIndex,
) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    """Build a normalised query vector from quiz answers.

    Validates that vocabulary terms in the quiz match the index.
    """
    genre_weights, tag_weights, answer_labels, constraints = parse_quiz_answers(answers)

    # Vocabulary guard
    missing = index.validate_vocabulary(
        list(genre_weights.keys()) + list(tag_weights.keys())
    )
    if missing:
        logger.warning("Quiz answers contain unknown vocabulary terms: %s", missing)

    query_vec = index.build_query_vec(genre_weights, tag_weights)
    return query_vec, answer_labels, constraints


def apply_quiz_soft_penalties(
    scores: np.ndarray,
    candidate_records: list[AnimeRecord],
    constraints: dict[str, Any],
    penalty_episodes: float = settings.REC_QUIZ_SOFT_PENALTY_EPISODES,
    penalty_year: float = settings.REC_QUIZ_SOFT_PENALTY_YEAR,
) -> np.ndarray:
    """Apply soft score penalties to candidate scores according to quiz constraints.

    Does NOT filter out candidates. Length range filtering and relaxation happen
    separately in ``apply_quiz_length_gate``. Titles outside the requested range
    receive the configured fixed multiplier (0.5 by default); year penalties
    continue to use the configured factor.
    """
    if not constraints or len(candidate_records) == 0:
        return scores

    adjusted_scores = scores.copy()

    min_ep = constraints.get("min_episodes")
    max_ep = constraints.get("max_episodes")
    min_yr = constraints.get("min_year")
    max_yr = constraints.get("max_year")

    for i, rec in enumerate(candidate_records):
        penalty_mult = 1.0

        # Episode check
        if rec.episodes is not None and (
            (min_ep is not None and rec.episodes < min_ep)
            or (max_ep is not None and rec.episodes > max_ep)
        ):
            penalty_mult *= 1.0 - penalty_episodes

        # Year check
        if rec.season_year is not None and (
            (min_yr is not None and rec.season_year < min_yr)
            or (max_yr is not None and rec.season_year > max_yr)
        ):
            penalty_mult *= 1.0 - penalty_year

        adjusted_scores[i] *= penalty_mult

    return adjusted_scores
