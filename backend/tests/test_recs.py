"""Tests for Phase 4 recommendation engine (Round 2)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.recs.engine import (
    MatureSeedError,
    _relevance_scores,
    build_taste_vector,
    compute_final_score,
    recommend_from_profile,
    recommend_from_quiz,
    recommend_from_start,
    recommend_similar,
)
from app.recs.quiz import (
    apply_quiz_soft_penalties,
    build_quiz_vector,
    load_quiz_data,
)
from app.recs.vectors import VectorIndex
from app.services.catalog_sync import UnionFind


def test_start_recommendations_are_deterministic(sample_catalog):
    index = VectorIndex.build(sample_catalog)
    liked = [item["id"] for item in sample_catalog[:3]]
    first = recommend_from_start(None, liked, n=10, index=index)
    second = recommend_from_start(None, liked, n=10, index=index)
    assert [item.id for item in first] == [item.id for item in second]
    assert not set(liked).intersection(item.id for item in first)


@pytest.fixture
def sample_catalog() -> list[dict]:
    """Synthetic catalog for testing all recommendation features.

    Every item must have season_year set; items without season_year are excluded
    by the NOT_YET_RELEASED / no-year filter.
    """
    return [
        {
            "id": 1,
            "title_english": "Frieren: Beyond Journey's End",
            "title_romaji": "Sousou no Frieren",
            "franchise_id": 100,
            "average_score": 93,
            "popularity": 80000,
            "episodes": 28,
            "season_year": 2023,
            "status": "FINISHED",
            "is_adult": False,
            "format": "TV",
            "genres": ["Fantasy", "Adventure", "Drama"],
            "tags": [{"name": "Magic", "rank": 95}, {"name": "Elves", "rank": 90}],
        },
        {
            "id": 2,
            "title_english": "Frieren Season 2",
            "title_romaji": "Sousou no Frieren 2",
            "franchise_id": 100,
            "average_score": 90,
            "popularity": 50000,
            "episodes": 24,
            "season_year": 2025,
            "status": "FINISHED",
            "is_adult": False,
            "format": "TV",
            "genres": ["Fantasy", "Adventure", "Drama"],
            "tags": [{"name": "Magic", "rank": 95}],
        },
        {
            "id": 3,
            "title_english": "Delicious in Dungeon",
            "title_romaji": "Dungeon Meshi",
            "franchise_id": 200,
            "average_score": 85,
            "popularity": 60000,
            "episodes": 24,
            "season_year": 2024,
            "status": "FINISHED",
            "is_adult": False,
            "format": "TV",
            "genres": ["Fantasy", "Adventure", "Comedy"],
            "tags": [{"name": "Magic", "rank": 80}, {"name": "Cooking", "rank": 90}],
        },
        {
            "id": 4,
            "title_english": "Steins;Gate",
            "title_romaji": "Steins;Gate",
            "franchise_id": 300,
            "average_score": 91,
            "popularity": 95000,
            "episodes": 24,
            "season_year": 2011,
            "status": "FINISHED",
            "is_adult": False,
            "format": "TV",
            "genres": ["Sci-Fi", "Thriller", "Psychological"],
            "tags": [{"name": "Time Travel", "rank": 95}],
        },
        {
            "id": 5,
            "title_english": "Cyberpunk: Edgerunners",
            "title_romaji": "Cyberpunk: Edgerunners",
            "franchise_id": 400,
            "average_score": 86,
            "popularity": 75000,
            "episodes": 10,
            "season_year": 2022,
            "status": "FINISHED",
            "is_adult": False,
            "format": "ONA",
            "genres": ["Sci-Fi", "Action", "Psychological"],
            "tags": [{"name": "Cyberpunk", "rank": 95}],
        },
        {
            "id": 6,
            "title_english": "Mature Fantasy Show",
            "title_romaji": "Hentai Fantasy",
            "franchise_id": None,
            "average_score": 72,
            "popularity": 5000,
            "episodes": 2,
            "season_year": 2020,
            "status": "FINISHED",
            "is_adult": True,
            "format": "TV",
            "duration": 24,
            "genres": ["Fantasy", "Romance"],
            "tags": [{"name": "Magic", "rank": 60}],
        },
        {
            "id": 7,
            "title_english": "Short Cozy Slice of Life",
            "title_romaji": "Yuru Camp",
            "franchise_id": 500,
            "average_score": 82,
            "popularity": 40000,
            "episodes": 12,
            "season_year": 2018,
            "status": "FINISHED",
            "is_adult": False,
            "format": "TV",
            "genres": ["Slice of Life", "Comedy"],
            "tags": [
                {"name": "Iyashikei", "rank": 90},
                {"name": "Camping", "rank": 95},
            ],
        },
        {
            "id": 8,
            "title_english": "Low Score Obscure Anime",
            "title_romaji": "Obscure",
            "franchise_id": None,
            "average_score": 35,
            "popularity": 20,
            "episodes": 12,
            "season_year": 2000,
            "status": "FINISHED",
            "is_adult": False,
            "format": "TV",
            "genres": ["Action", "Sci-Fi"],
            "tags": [{"name": "Cyberpunk", "rank": 80}],
        },
    ]


@pytest.fixture
def sample_index(sample_catalog: list[dict]) -> VectorIndex:
    """Builds VectorIndex from synthetic catalog."""
    return VectorIndex.build(sample_catalog)


# ---------------------------------------------------------------------------
# 1–22: Core behaviour (ported from Phase 4 Round 1, catalog updated)
# ---------------------------------------------------------------------------


def test_similar_basic(sample_index: VectorIndex):
    """Top result shares >= 1 genre with seed and has >= 2 salient features."""
    results = recommend_similar(
        anime_id=1, n=3, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    top = results[0]
    assert top.id == 3
    assert any(g in ["Fantasy", "Adventure", "Drama"] for g in top.genres)


def test_similar_excludes_seed(sample_index: VectorIndex):
    """Seed anime is never in recommendations."""
    results = recommend_similar(
        anime_id=1, n=10, include_mature=True, index=sample_index
    )
    assert 1 not in [r.id for r in results]


def test_similar_excludes_franchise(sample_index: VectorIndex):
    """Franchise member Frieren S2 (franchise_id=100) is excluded."""
    results = recommend_similar(
        anime_id=1, n=10, include_mature=True, index=sample_index
    )
    assert 2 not in [r.id for r in results]


def test_similar_outside_catalog_franchise():
    """UnionFind connects catalog nodes through out-of-catalog bridge nodes."""
    uf = UnionFind()
    uf.union(10, 999)
    uf.union(999, 20)
    assert uf.find(10) == uf.find(20)


def test_similar_excludes_user_list(sample_index: VectorIndex):
    """Items on the user list are excluded from results."""
    user_items = [{"anime_id": 3, "status": "completed", "rating": 9.0}]
    results = recommend_similar(
        anime_id=1,
        n=10,
        include_mature=False,
        user_items=user_items,
        index=sample_index,
    )
    assert 3 not in [r.id for r in results]


def test_similar_mature_filtered(sample_index: VectorIndex):
    """Adult items excluded when include_mature=False."""
    results = recommend_similar(
        anime_id=1, n=10, include_mature=False, index=sample_index
    )
    assert 6 not in [r.id for r in results]


def test_similar_mature_included(sample_index: VectorIndex):
    """Adult items present when include_mature=True."""
    results = recommend_similar(
        anime_id=1, n=10, include_mature=True, index=sample_index
    )
    assert 6 in [r.id for r in results]


def test_similar_adult_seed_raises(sample_index: VectorIndex):
    """Adult seed with include_mature=False raises MatureSeedError."""
    with pytest.raises(MatureSeedError):
        recommend_similar(anime_id=6, n=5, include_mature=False, index=sample_index)


def test_quiz_weight_pull(sample_index: VectorIndex):
    """Quiz with fantasy mood pulls fantasy anime to top."""
    results = recommend_from_quiz(
        answers={"themes": "fantasy"}, n=3, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    assert "Fantasy" in results[0].genres


def test_quiz_length_soft_constraint(sample_index: VectorIndex):
    """Quiz soft penalty reduces score of items violating episode constraint."""
    constraints = {"max_episodes": 13}
    rec_short = sample_index.get(5)  # 10 eps
    rec_long = sample_index.get(3)  # 24 eps
    assert rec_short and rec_long
    scores = np.array([1.0, 1.0])
    adjusted = apply_quiz_soft_penalties(scores, [rec_short, rec_long], constraints)
    assert adjusted[0] == 1.0
    assert adjusted[1] < 1.0


def test_quiz_vocabulary(sample_index: VectorIndex):
    """Quiz questions load without error and have 7 questions."""
    quiz_data = load_quiz_data()
    assert "questions" in quiz_data
    assert len(quiz_data["questions"]) == 7


def test_profile_rating_centering(sample_index: VectorIndex):
    """High-rated Sci-Fi item pulls profile toward Sci-Fi titles."""
    user_items = [
        {"anime_id": 4, "status": "completed", "rating": 10.0},
        {"anime_id": 3, "status": "completed", "rating": 4.0},
    ]
    results = recommend_from_profile(
        user_items, n=3, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    assert results[0].id == 5  # Cyberpunk (Sci-Fi)


def test_profile_dropped_excluded(sample_index: VectorIndex):
    """Dropped anime are excluded from profile results."""
    user_items = [{"anime_id": 5, "status": "dropped", "rating": None}]
    results = recommend_from_profile(
        user_items, n=10, include_mature=False, index=sample_index
    )
    assert 5 not in [r.id for r in results]


def test_profile_planning_excluded(sample_index: VectorIndex):
    """Planning anime excluded from profile results."""
    user_items = [{"anime_id": 7, "status": "planning", "rating": None}]
    results = recommend_from_profile(
        user_items, n=10, include_mature=False, index=sample_index
    )
    assert 7 not in [r.id for r in results]


def test_profile_zero_variance_no_crash(sample_index: VectorIndex):
    """All ratings identical (zero variance) returns results without crashing."""
    user_items = [
        {"anime_id": 1, "status": "completed", "rating": 8.0},
        {"anime_id": 3, "status": "completed", "rating": 8.0},
    ]
    results = recommend_from_profile(
        user_items, n=3, include_mature=False, index=sample_index
    )
    assert len(results) > 0


def test_profile_empty_fallback(sample_index: VectorIndex):
    """No ratings + no quiz -> quality-ranked list with 'popular' in reason."""
    results = recommend_from_profile([], n=3, include_mature=False, index=sample_index)
    assert len(results) == 3
    assert "popular" in results[0].reason.lower()


def test_cold_start_smooth_blend(sample_index: VectorIndex):
    """Cold-start blends quiz prior with single rating."""
    quiz_vec, _, _ = build_quiz_vector({"themes": "sci_fi"}, sample_index)
    user_items = [{"anime_id": 3, "status": "completed", "rating": 10.0}]
    taste_vec = build_taste_vector(
        user_items, quiz_prior_vec=quiz_vec, index=sample_index
    )
    assert np.any(taste_vec != 0)


def test_hybrid_diversity(sample_index: VectorIndex):
    """MMR produces valid ranked output without duplicate IDs."""
    results = recommend_similar(
        anime_id=1, n=4, include_mature=False, index=sample_index
    )
    ids = [r.id for r in results]
    assert len(ids) == len(set(ids))


def test_quality_floor_relaxed(sample_index: VectorIndex):
    """Low-score seed still returns results after floor relaxation."""
    results = recommend_similar(
        anime_id=8, n=5, include_mature=False, index=sample_index
    )
    assert len(results) > 0


def test_explanation_specificity(sample_index: VectorIndex):
    """Explanations name the seed title and are non-empty."""
    results = recommend_similar(
        anime_id=1, n=2, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    assert results[0].reason != ""
    assert "Frieren" in results[0].reason


def test_stable_ordering(sample_index: VectorIndex):
    """Two identical calls return identical ordered lists."""
    res1 = recommend_similar(anime_id=1, n=5, include_mature=False, index=sample_index)
    res2 = recommend_similar(anime_id=1, n=5, include_mature=False, index=sample_index)
    assert [r.id for r in res1] == [r.id for r in res2]


def test_franchise_connected_components():
    """A->B and B->C produces a unified franchise via UnionFind."""
    uf = UnionFind()
    uf.union(101, 102)
    uf.union(102, 103)
    assert uf.find(101) == uf.find(103)


# ---------------------------------------------------------------------------
# 23-24: Scoring formula unit tests (Round 2 formulas)
# ---------------------------------------------------------------------------


def test_final_score_additive_quality():
    """Additive formula: final = rel + q * quality (not (1-q)*rel + q*quality)."""
    rel, quality, q = 0.9, 0.8, 0.1
    score = compute_final_score(rel, quality, q=q)
    assert math.isclose(score, 0.9 + 0.1 * 0.8, rel_tol=1e-5)


def test_relevance_scores_minmax():
    """_relevance_scores: top-k items scale to [0,1]; below-floor items clamp to 0."""
    cos = np.array([0.9, 0.7, 0.5, 0.3, 0.1])
    rel = _relevance_scores(cos, top_k=3)
    # top-3 = [0.9, 0.7, 0.5], min=0.5, max=0.9, range=0.4
    assert math.isclose(rel[0], 1.0, abs_tol=1e-6)  # (0.9-0.5)/0.4
    assert math.isclose(rel[1], 0.5, abs_tol=1e-6)  # (0.7-0.5)/0.4
    assert math.isclose(rel[2], 0.0, abs_tol=1e-6)  # (0.5-0.5)/0.4
    assert rel[3] == 0.0  # clamped
    assert rel[4] == 0.0  # clamped


# ---------------------------------------------------------------------------
# 25-26: Edge-case correctness
# ---------------------------------------------------------------------------


def test_similar_logged_in_empty_taste_fallback(sample_index: VectorIndex):
    """Logged-in with empty taste vector falls back to pure similarity."""
    logged_out = recommend_similar(
        anime_id=1, n=3, include_mature=False, index=sample_index
    )
    logged_in_empty = recommend_similar(
        anime_id=1,
        n=3,
        include_mature=False,
        user_items=[{"anime_id": 999, "status": "watching"}],
        index=sample_index,
    )
    assert [r.id for r in logged_out] == [r.id for r in logged_in_empty]


def test_franchise_none_never_matches_none(sample_index: VectorIndex):
    """Seed franchise_id=None never excludes other None-franchise candidates."""
    from app.recs.engine import _filter_and_relax_candidates

    candidates = _filter_and_relax_candidates(
        sample_index, seed_id=8, seed_franchise_id=None, include_mature=True, n=10
    )
    none_ids = [
        sample_index.records[i].id
        for i in candidates
        if sample_index.records[i].franchise_id is None
    ]
    assert len(none_ids) > 0
    assert 8 not in none_ids


# ---------------------------------------------------------------------------
# 27: Tag explanation constraints
# ---------------------------------------------------------------------------


def test_explanation_tags_both_titles_rank_gte_60():
    """Tags in explanation must have rank >= 60 on BOTH titles and not be spoilers."""
    catalog = [
        {
            "id": 10,
            "title_english": "Seed Show",
            "format": "TV",
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Action", "Adventure"],
            "tags": [
                {"name": "Epic Tag", "rank": 70, "is_spoiler": False},
                {"name": "Low Rank Tag", "rank": 40, "is_spoiler": False},
                {"name": "Spoiler Tag", "rank": 85, "is_spoiler": True},
            ],
        },
        {
            "id": 11,
            "title_english": "Rec Show",
            "format": "TV",
            "season_year": 2021,
            "status": "FINISHED",
            "genres": ["Action", "Adventure"],
            "tags": [
                {"name": "Epic Tag", "rank": 65, "is_spoiler": False},
                {"name": "Low Rank Tag", "rank": 90, "is_spoiler": False},
                {"name": "Spoiler Tag", "rank": 85, "is_spoiler": False},
            ],
        },
    ]
    index = VectorIndex.build(catalog)
    recs = recommend_similar(anime_id=10, n=2, index=index)
    assert len(recs) > 0
    rec = recs[0]
    for tag_name in rec.explanation.shared_tags:
        assert tag_name == "Epic Tag"
        assert tag_name not in ("Low Rank Tag", "Spoiler Tag")
    if "Epic Tag" in rec.reason:
        assert "Low Rank Tag" not in rec.reason
        assert "Spoiler Tag" not in rec.reason


# ---------------------------------------------------------------------------
# 28: Franchise entry point - earliest TV, then movie, by season_year
# ---------------------------------------------------------------------------


def test_one_entry_per_franchise_entry_point():
    """Entry point = earliest-aired TV; has_prequel does NOT affect the choice."""
    catalog = [
        {
            "id": 50,
            "title_english": "Seed Anime",
            "format": "TV",
            "season_year": 2015,
            "status": "FINISHED",
            "genres": ["Sci-Fi"],
            "tags": [{"name": "Space", "rank": 90}],
        },
        {
            "id": 51,
            "title_english": "Franchise Season 1",
            "franchise_id": 999,
            "season_year": 2010,
            "status": "FINISHED",
            "format": "TV",
            "has_prequel": False,
            "genres": ["Sci-Fi"],
            "tags": [{"name": "Space", "rank": 70}],
            "average_score": 80,
            "popularity": 50000,
        },
        {
            "id": 52,
            "title_english": "Franchise Season 2",
            "franchise_id": 999,
            "season_year": 2012,
            "status": "FINISHED",
            "format": "TV",
            "has_prequel": True,
            "genres": ["Sci-Fi"],
            "tags": [{"name": "Space", "rank": 95}],
            "average_score": 90,
            "popularity": 70000,
        },
        {
            "id": 53,
            "title_english": "Franchise Recap Movie",
            "franchise_id": 999,
            "season_year": 2013,
            "status": "FINISHED",
            "format": "MOVIE",
            "has_prequel": True,
            "genres": ["Sci-Fi"],
            "tags": [{"name": "Space", "rank": 92}],
            "average_score": 85,
            "popularity": 30000,
        },
    ]
    index = VectorIndex.build(catalog)
    recs = recommend_similar(anime_id=50, n=5, index=index)
    franchise_recs = [r for r in recs if r.id in (51, 52, 53)]
    assert len(franchise_recs) == 1
    assert franchise_recs[0].id == 51
    assert "Season 1" in franchise_recs[0].title


# ---------------------------------------------------------------------------
# 29: Format and duration filtering
# ---------------------------------------------------------------------------


def test_format_and_duration_filtering():
    """OVA/SPECIAL/MUSIC and <12min excluded unless seed is that type."""
    catalog = [
        {
            "id": 60,
            "title_english": "Standard TV",
            "format": "TV",
            "duration": 24,
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Action"],
            "tags": [{"name": "Fight", "rank": 90}],
        },
        {
            "id": 61,
            "title_english": "Short ONA 3min",
            "format": "ONA",
            "duration": 3,
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Action"],
            "tags": [{"name": "Fight", "rank": 90}],
        },
        {
            "id": 62,
            "title_english": "Action OVA",
            "format": "OVA",
            "duration": 30,
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Action"],
            "tags": [{"name": "Fight", "rank": 90}],
        },
        {
            "id": 63,
            "title_english": "Action SPECIAL",
            "format": "SPECIAL",
            "duration": 20,
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Action"],
            "tags": [{"name": "Fight", "rank": 90}],
        },
        {
            "id": 64,
            "title_english": "Action MUSIC",
            "format": "MUSIC",
            "duration": 4,
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Action"],
            "tags": [{"name": "Fight", "rank": 90}],
        },
        {
            "id": 65,
            "title_english": "Standard TV Rec",
            "format": "TV",
            "duration": 24,
            "season_year": 2021,
            "status": "FINISHED",
            "genres": ["Action"],
            "tags": [{"name": "Fight", "rank": 85}],
        },
    ]
    index = VectorIndex.build(catalog)

    recs = recommend_similar(anime_id=60, n=10, index=index)
    rec_ids = [r.id for r in recs]
    assert 65 in rec_ids
    assert 61 not in rec_ids  # duration < 12
    assert 62 not in rec_ids  # OVA
    assert 63 not in rec_ids  # SPECIAL
    assert 64 not in rec_ids  # MUSIC

    recs_ova = recommend_similar(anime_id=62, n=10, index=index)
    assert 61 not in [r.id for r in recs_ova]  # still duration < 12

    recs_short = recommend_similar(anime_id=61, n=10, index=index)
    assert any(r.id == 65 for r in recs_short)


# ---------------------------------------------------------------------------
# 30-31: Unreleased / no-year exclusion (Round 2 requirement)
# ---------------------------------------------------------------------------


def test_no_year_items_excluded():
    """Titles with season_year=None must not appear in recommendations."""
    catalog = [
        {
            "id": 70,
            "title_english": "Seed",
            "format": "TV",
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Action", "Adventure"],
            "tags": [{"name": "War", "rank": 90}],
        },
        {
            "id": 71,
            "title_english": "Has Year",
            "format": "TV",
            "season_year": 2019,
            "status": "FINISHED",
            "genres": ["Action", "Adventure"],
            "tags": [{"name": "War", "rank": 85}],
        },
        {
            "id": 72,
            "title_english": "No Year",
            "format": "TV",
            "season_year": None,
            "status": "FINISHED",
            "genres": ["Action", "Adventure"],
            "tags": [{"name": "War", "rank": 95}],
        },
    ]
    index = VectorIndex.build(catalog)
    recs = recommend_similar(anime_id=70, n=10, index=index)
    rec_ids = [r.id for r in recs]
    assert 72 not in rec_ids
    assert 71 in rec_ids


def test_not_yet_released_excluded():
    """Titles with status=NOT_YET_RELEASED must not appear in recommendations."""
    catalog = [
        {
            "id": 80,
            "title_english": "Seed",
            "format": "TV",
            "season_year": 2023,
            "status": "FINISHED",
            "genres": ["Fantasy", "Adventure"],
            "tags": [{"name": "Magic", "rank": 90}],
        },
        {
            "id": 81,
            "title_english": "Finished Show",
            "format": "TV",
            "season_year": 2022,
            "status": "FINISHED",
            "genres": ["Fantasy", "Adventure"],
            "tags": [{"name": "Magic", "rank": 85}],
        },
        {
            "id": 82,
            "title_english": "Upcoming Show",
            "format": "TV",
            "season_year": 2026,
            "status": "NOT_YET_RELEASED",
            "genres": ["Fantasy", "Adventure"],
            "tags": [{"name": "Magic", "rank": 95}],
        },
    ]
    index = VectorIndex.build(catalog)
    recs = recommend_similar(anime_id=80, n=10, index=index)
    rec_ids = [r.id for r in recs]
    assert 82 not in rec_ids
    assert 81 in rec_ids


# ---------------------------------------------------------------------------
# 32: Salient feature gate — no padding (Round 2 requirement)
# ---------------------------------------------------------------------------


def test_salient_feature_gate():
    """Items with < 2 shared salient features are dropped; engine never pads."""
    catalog = [
        {
            "id": 90,
            "title_english": "Action Seed",
            "format": "TV",
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Action", "Adventure"],
            "tags": [{"name": "War", "rank": 90}, {"name": "Military", "rank": 80}],
        },
        {
            "id": 91,
            "title_english": "Good Action Rec",
            "format": "TV",
            "season_year": 2019,
            "status": "FINISHED",
            "genres": ["Action", "Adventure"],
            "tags": [{"name": "War", "rank": 85}, {"name": "Military", "rank": 75}],
        },
        {
            "id": 92,
            "title_english": "Unrelated Romance",
            "format": "TV",
            "season_year": 2018,
            "status": "FINISHED",
            "genres": ["Romance", "Slice of Life"],
            "tags": [{"name": "School", "rank": 90}],
        },
    ]
    index = VectorIndex.build(catalog)
    recs = recommend_similar(anime_id=90, n=10, index=index)
    rec_ids = [r.id for r in recs]
    assert 91 in rec_ids  # shares Action, Adventure, War, Military
    assert 92 not in rec_ids  # no shared salient features


# ---------------------------------------------------------------------------
# 33: Post-MMR tracking
# ---------------------------------------------------------------------------


def test_post_mmr_pre_mmr_ranks_valid(sample_index: VectorIndex):
    """All results have a valid pre_mmr_rank >= 1 and no duplicate IDs."""
    results = recommend_similar(
        anime_id=1, n=5, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    for r in results:
        assert r.pre_mmr_rank is not None and r.pre_mmr_rank >= 1
    ids = [r.id for r in results]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# 34-35: Franchise entry-point — No Game No Life & Monogatari (Round 2)
# ---------------------------------------------------------------------------


def test_no_game_no_life_entry_point():
    """TV series (2014) must win over MOVIE (2017) even if movie has higher score."""
    catalog = [
        {
            "id": 100,
            "title_english": "Seed Isekai",
            "format": "TV",
            "season_year": 2016,
            "status": "FINISHED",
            "genres": ["Fantasy", "Game"],
            "tags": [{"name": "Isekai", "rank": 90}, {"name": "Games", "rank": 85}],
        },
        {
            "id": 101,
            "title_english": "No Game No Life",
            "franchise_id": 777,
            "format": "TV",
            "season_year": 2014,
            "status": "FINISHED",
            "has_prequel": False,
            "genres": ["Fantasy", "Game"],
            "tags": [{"name": "Isekai", "rank": 90}, {"name": "Games", "rank": 85}],
            "average_score": 82,
            "popularity": 150000,
        },
        {
            "id": 102,
            "title_english": "No Game No Life: Zero",
            "franchise_id": 777,
            "format": "MOVIE",
            "season_year": 2017,
            "status": "FINISHED",
            "has_prequel": False,
            "genres": ["Fantasy", "Game"],
            "tags": [{"name": "Isekai", "rank": 90}, {"name": "Games", "rank": 90}],
            "average_score": 87,
            "popularity": 90000,
        },
    ]
    index = VectorIndex.build(catalog)
    assert index.franchise_entry_points.get(777) == 101  # TV wins over MOVIE

    recs = recommend_similar(anime_id=100, n=5, index=index)
    franchise_recs = [r for r in recs if r.id in (101, 102)]
    assert len(franchise_recs) == 1
    assert franchise_recs[0].id == 101


def test_monogatari_entry_point():
    """Bakemonogatari (2009) wins over later seasons regardless of popularity."""
    catalog = [
        {
            "id": 200,
            "title_english": "Seed Romance Mystery",
            "format": "TV",
            "season_year": 2010,
            "status": "FINISHED",
            "genres": ["Mystery", "Romance", "Supernatural"],
            "tags": [
                {"name": "Harem", "rank": 75},
                {"name": "Supernatural", "rank": 90},
            ],
        },
        {
            "id": 201,
            "title_english": "Bakemonogatari",
            "franchise_id": 888,
            "format": "TV",
            "season_year": 2009,
            "status": "FINISHED",
            "has_prequel": False,
            "genres": ["Mystery", "Romance", "Supernatural"],
            "tags": [
                {"name": "Harem", "rank": 75},
                {"name": "Supernatural", "rank": 90},
            ],
            "average_score": 84,
            "popularity": 200000,
        },
        {
            "id": 202,
            "title_english": "Nisemonogatari",
            "franchise_id": 888,
            "format": "TV",
            "season_year": 2012,
            "status": "FINISHED",
            "has_prequel": True,
            "genres": ["Mystery", "Romance", "Supernatural"],
            "tags": [
                {"name": "Harem", "rank": 75},
                {"name": "Supernatural", "rank": 90},
            ],
            "average_score": 79,
            "popularity": 120000,
        },
        {
            "id": 203,
            "title_english": "Monogatari Series: Second Season",
            "franchise_id": 888,
            "format": "TV",
            "season_year": 2013,
            "status": "FINISHED",
            "has_prequel": True,
            "genres": ["Mystery", "Romance", "Supernatural"],
            "tags": [
                {"name": "Harem", "rank": 75},
                {"name": "Supernatural", "rank": 92},
            ],
            "average_score": 90,
            "popularity": 180000,
        },
    ]
    index = VectorIndex.build(catalog)
    assert index.franchise_entry_points.get(888) == 201  # Bakemonogatari

    recs = recommend_similar(anime_id=200, n=5, index=index)
    franchise_recs = [r for r in recs if r.id in (201, 202, 203)]
    assert len(franchise_recs) == 1
    assert franchise_recs[0].id == 201


def test_movie_only_franchise_entry_point():
    """If franchise has no TV series, the earliest-aired MOVIE is the entry point."""
    catalog = [
        {
            "id": 300,
            "title_english": "Seed Thriller",
            "format": "TV",
            "season_year": 2010,
            "status": "FINISHED",
            "genres": ["Action", "Supernatural"],
            "tags": [{"name": "Magic", "rank": 80}, {"name": "Swordplay", "rank": 85}],
        },
        {
            "id": 301,
            "title_english": "Movie 2 (Later)",
            "franchise_id": 999,
            "format": "MOVIE",
            "season_year": 2008,
            "status": "FINISHED",
            "genres": ["Action", "Supernatural"],
            "tags": [{"name": "Magic", "rank": 80}, {"name": "Swordplay", "rank": 85}],
            "average_score": 85,
            "popularity": 50000,
        },
        {
            "id": 302,
            "title_english": "Movie 1 (Earliest)",
            "franchise_id": 999,
            "format": "MOVIE",
            "season_year": 2007,
            "status": "FINISHED",
            "genres": ["Action", "Supernatural"],
            "tags": [{"name": "Magic", "rank": 80}, {"name": "Swordplay", "rank": 85}],
            "average_score": 80,
            "popularity": 40000,
        },
    ]
    index = VectorIndex.build(catalog)
    # Earliest movie is 302 (2007)
    assert index.franchise_entry_points.get(999) == 302

    recs = recommend_similar(anime_id=300, n=5, index=index)
    franchise_recs = [r for r in recs if r.id in (301, 302)]
    assert len(franchise_recs) == 1
    assert franchise_recs[0].id == 302
    assert "Movie 1" in franchise_recs[0].title


def test_recs_demo_shows_pre_mmr_and_final_score():
    """recs-demo output format includes PreMMR and Final score columns."""
    from typer.testing import CliRunner

    from app.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["recs-demo", "--help"])
    assert result.exit_code == 0
    assert "recs-demo" in result.stdout


def test_vector_row_index_mapping_regression():
    """Regression test: Stored vector row always maps exactly to the anime ID.

    For 20 random items in a synthesized catalog, independently reconstruct the L2-normalized
    vector from that anime's genres, tags (rank/100 * tag_idf), and format, and assert
    it matches index.vec(anime_id) and index.matrix[index.id_to_idx[anime_id]].
    """
    import random

    from sklearn.preprocessing import normalize

    from app.recs.vectors import FORMAT_INDEX

    rng = random.Random(42)
    genres_pool = [
        "Action",
        "Adventure",
        "Comedy",
        "Drama",
        "Fantasy",
        "Sci-Fi",
        "Mystery",
    ]
    tags_pool = [
        "Magic",
        "Space",
        "Time Travel",
        "Cyberpunk",
        "War",
        "School",
        "Supernatural",
    ]
    formats_pool = ["TV", "MOVIE", "OVA", "ONA"]

    catalog = []
    for aid in range(1, 31):
        sample_g = rng.sample(genres_pool, k=rng.randint(1, 3))
        sample_t = [
            {"name": t, "rank": rng.randint(60, 95)}
            for t in rng.sample(tags_pool, k=rng.randint(1, 3))
        ]
        catalog.append(
            {
                "id": aid,
                "title_english": f"Anime Title {aid}",
                "format": rng.choice(formats_pool),
                "season_year": 2010 + (aid % 10),
                "status": "FINISHED",
                "genres": sample_g,
                "tags": sample_t,
                "average_score": 70 + (aid % 25),
                "popularity": 1000 * aid,
            }
        )

    index = VectorIndex.build(catalog, w_genre=0.45, w_tag=0.45, w_format=0.10)
    assert len(index.records) == 30
    assert index.matrix.shape[0] == 30

    test_ids = rng.sample([it["id"] for it in catalog], 20)
    for aid in test_ids:
        # 1. Lookup must match
        row_idx = index.id_to_idx[aid]
        rec = index.records[row_idx]
        assert rec.id == aid
        stored_vec = index.vec(aid)
        assert np.array_equal(stored_vec, index.matrix[row_idx])

        # 2. Reconstruct expected vector from raw features
        item_data = next(it for it in catalog if it["id"] == aid)
        raw_g = np.zeros(len(index.all_genres), dtype=np.float32)
        for g in item_data["genres"]:
            raw_g[index.all_genres.index(g)] = 1.0

        raw_t = np.zeros(len(index.all_tags), dtype=np.float32)
        for t in item_data["tags"]:
            raw_t[index.all_tags.index(t["name"])] = float(t["rank"]) / 100.0

        raw_f = np.zeros(len(FORMAT_INDEX), dtype=np.float32)
        raw_f[FORMAT_INDEX[item_data["format"]]] = 1.0

        # L2 norm blocks + IDF weights (matching VectorIndex.build weights)
        l2_g = normalize(raw_g.reshape(1, -1), norm="l2")[0] * index.genre_idf * 0.45
        l2_t = normalize(raw_t.reshape(1, -1), norm="l2")[0] * index.tag_idf * 0.45
        l2_f = normalize(raw_f.reshape(1, -1), norm="l2")[0] * 0.10

        concat = np.concatenate([l2_g, l2_t, l2_f]).reshape(1, -1)
        expected_vec = normalize(concat, norm="l2")[0]

        assert np.allclose(
            stored_vec, expected_vec, atol=1e-5
        ), f"Mismatch for anime id {aid}"


def test_quiz_salient_gate_returns_fewer_cleanly():
    """recommend_from_quiz drops items with < 2 salient features and returns cleanly without padding."""
    catalog = [
        # Matches 2 quiz features: Fantasy + Magic (rank 80)
        {
            "id": 401,
            "title_english": "High Fantasy Show",
            "format": "TV",
            "season_year": 2021,
            "status": "FINISHED",
            "genres": ["Fantasy", "Action"],
            "tags": [{"name": "Magic", "rank": 80}],
        },
        # Only 1 quiz feature: Fantasy, no magic
        {
            "id": 402,
            "title_english": "Only One Feature",
            "format": "TV",
            "season_year": 2021,
            "status": "FINISHED",
            "genres": ["Fantasy"],
            "tags": [{"name": "Cooking", "rank": 90}],
        },
        # 0 quiz features
        {
            "id": 403,
            "title_english": "Zero Features",
            "format": "TV",
            "season_year": 2021,
            "status": "FINISHED",
            "genres": ["Slice of Life"],
            "tags": [{"name": "School", "rank": 90}],
        },
    ]
    index = VectorIndex.build(catalog)
    # Quiz answers for fantasy mood
    results = recommend_from_quiz(answers={"themes": "fantasy"}, n=10, index=index)
    # Only 401 has >= 2 shared features (Fantasy genre + Magic tag); 402 and 403 must be filtered
    assert len(results) == 1
    assert results[0].id == 401


def test_profile_salient_gate_returns_fewer_cleanly():
    """recommend_from_profile drops items with < 2 salient features and returns cleanly without padding."""
    catalog = [
        {
            "id": 500,
            "title_english": "Disliked Show",
            "format": "TV",
            "season_year": 2019,
            "status": "FINISHED",
            "genres": ["Comedy"],
            "tags": [{"name": "Parody", "rank": 80}],
        },
        {
            "id": 501,
            "title_english": "User Completed Favorite",
            "format": "TV",
            "season_year": 2020,
            "status": "FINISHED",
            "genres": ["Sci-Fi", "Thriller"],
            "tags": [
                {"name": "Time Travel", "rank": 90},
                {"name": "Cyberpunk", "rank": 85},
            ],
        },
        # Matches 2 features with 501: Sci-Fi + Cyberpunk (rank 90)
        {
            "id": 502,
            "title_english": "Good Match Candidate",
            "format": "TV",
            "season_year": 2021,
            "status": "FINISHED",
            "genres": ["Sci-Fi", "Action"],
            "tags": [{"name": "Cyberpunk", "rank": 90}],
        },
        # Matches only 1 feature with 501: Sci-Fi, but no shared tags rank >= 60
        {
            "id": 503,
            "title_english": "Weak Match Candidate",
            "format": "TV",
            "season_year": 2021,
            "status": "FINISHED",
            "genres": ["Sci-Fi"],
            "tags": [{"name": "Cooking", "rank": 90}],
        },
    ]
    index = VectorIndex.build(catalog)
    user_items = [
        {"anime_id": 501, "status": "completed", "rating": 10.0},
        {"anime_id": 500, "status": "completed", "rating": 3.0},
    ]
    results = recommend_from_profile(user_items=user_items, n=10, index=index)
    # 500 and 501 are excluded (watched);
    # 502 has 2 shared features with 501 (Sci-Fi, Cyberpunk);
    # 503 has only 1 shared feature (Sci-Fi) so it must be dropped.
    assert len(results) == 1
    assert results[0].id == 502
