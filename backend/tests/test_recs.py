"""Tests for Phase 4 recommendation engine."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.recs.engine import (
    MatureSeedError,
    build_taste_vector,
    compute_final_score,
    rank_norm,
    recommend_from_profile,
    recommend_from_quiz,
    recommend_similar,
)
from app.recs.quiz import (
    apply_quiz_soft_penalties,
    build_quiz_vector,
    load_quiz_data,
)
from app.recs.vectors import VectorIndex
from app.services.catalog_sync import UnionFind


@pytest.fixture
def sample_catalog() -> list[dict]:
    """Synthetic catalog for testing all recommendation features."""
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
            "is_adult": False,
            "format": "TV",
            "genres": ["Fantasy", "Adventure", "Drama"],
            "tags": [{"name": "Magic", "rank": 95}, {"name": "Elves", "rank": 90}],
        },
        {
            "id": 2,
            "title_english": "Frieren Season 2",
            "title_romaji": "Sousou no Frieren 2",
            "franchise_id": 100,  # Same franchise as 1!
            "average_score": 90,
            "popularity": 50000,
            "episodes": 24,
            "season_year": 2025,
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
            "is_adult": False,
            "format": "ONA",
            "genres": ["Sci-Fi", "Action"],
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
            "is_adult": True,  # Adult content!
            "format": "OVA",
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
            "is_adult": False,
            "format": "TV",
            "genres": ["Action"],
            "tags": [],
        },
    ]


@pytest.fixture
def sample_index(sample_catalog: list[dict]) -> VectorIndex:
    """Builds VectorIndex from synthetic catalog."""
    return VectorIndex.build(sample_catalog)


# 1. test_similar_basic
def test_similar_basic(sample_index: VectorIndex):
    """Top result shares >= 1 genre with seed."""
    results = recommend_similar(
        anime_id=1, n=3, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    top = results[0]
    # Seed 1 is Fantasy/Adventure. Top result should be Dungeon Meshi (id=3)
    assert top.id == 3
    assert any(g in ["Fantasy", "Adventure", "Drama"] for g in top.genres)


# 2. test_similar_excludes_seed
def test_similar_excludes_seed(sample_index: VectorIndex):
    """Seed anime is never in recommendations."""
    results = recommend_similar(
        anime_id=1, n=10, include_mature=True, index=sample_index
    )
    rec_ids = [r.id for r in results]
    assert 1 not in rec_ids


# 3. test_similar_excludes_franchise
def test_similar_excludes_franchise(sample_index: VectorIndex):
    """Franchise members (e.g. Sequel with franchise_id=100) are excluded."""
    results = recommend_similar(
        anime_id=1, n=10, include_mature=True, index=sample_index
    )
    rec_ids = [r.id for r in results]
    assert 2 not in rec_ids  # Frieren Season 2 shares franchise_id 100!


# 4. test_similar_outside_catalog_franchise
def test_similar_outside_catalog_franchise():
    """Union-Find over edges to non-catalog nodes still connects catalog nodes."""
    # A=10, B=999 (not in catalog), C=20
    uf = UnionFind()
    uf.union(10, 999)
    uf.union(999, 20)
    assert uf.find(10) == uf.find(20)


# 5. test_similar_excludes_user_list
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
    rec_ids = [r.id for r in results]
    assert 3 not in rec_ids


# 6. test_similar_mature_filtered
def test_similar_mature_filtered(sample_index: VectorIndex):
    """Adult items are excluded when include_mature=False."""
    results = recommend_similar(
        anime_id=1, n=10, include_mature=False, index=sample_index
    )
    rec_ids = [r.id for r in results]
    assert 6 not in rec_ids


# 7. test_similar_mature_included
def test_similar_mature_included(sample_index: VectorIndex):
    """Adult items are present when include_mature=True."""
    results = recommend_similar(
        anime_id=1, n=10, include_mature=True, index=sample_index
    )
    rec_ids = [r.id for r in results]
    assert 6 in rec_ids


# 8. test_similar_adult_seed_404
def test_similar_adult_seed_404(sample_index: VectorIndex):
    """Requesting similar for an adult seed when include_mature=False raises MatureSeedError."""
    with pytest.raises(MatureSeedError):
        recommend_similar(anime_id=6, n=5, include_mature=False, index=sample_index)


# 9. test_quiz_weight_pull
def test_quiz_weight_pull(sample_index: VectorIndex):
    """Quiz with fantasy/adventure mood pulls fantasy anime to top."""
    answers = {"themes": "fantasy"}
    results = recommend_from_quiz(
        answers=answers, n=3, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    assert "Fantasy" in results[0].genres


# 10. test_quiz_length_soft_constraint
def test_quiz_length_soft_constraint(sample_index: VectorIndex):
    """Quiz soft penalty reduces score of items violating episode constraint."""
    # Short length: max 13 episodes
    constraints = {"max_episodes": 13}
    rec_short = sample_index.get(5)  # 10 eps
    rec_long = sample_index.get(3)  # 24 eps
    assert rec_short and rec_long

    scores = np.array([1.0, 1.0])
    adjusted = apply_quiz_soft_penalties(scores, [rec_short, rec_long], constraints)
    # Short show receives no penalty (1.0), long show is scaled down (0.85)
    assert adjusted[0] == 1.0
    assert adjusted[1] < 1.0


# 11. test_quiz_vocabulary
def test_quiz_vocabulary(sample_index: VectorIndex):
    """Quiz questions load without error and have valid structure."""
    quiz_data = load_quiz_data()
    assert "questions" in quiz_data
    assert len(quiz_data["questions"]) == 7


# 12. test_profile_rating_centering
def test_profile_rating_centering(sample_index: VectorIndex):
    """High-rated Sci-Fi item pulls profile toward Sci-Fi titles."""
    user_items = [
        {"anime_id": 4, "status": "completed", "rating": 10.0},  # Steins;Gate (Sci-Fi)
        {
            "anime_id": 3,
            "status": "completed",
            "rating": 4.0,
        },  # Dungeon Meshi (low rating)
    ]
    results = recommend_from_profile(
        user_items, n=3, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    top = results[0]
    # Steins;Gate rated 10, mean is 7.0, centered is +3.0 Sci-Fi; Dungeon Meshi is -3.0 Fantasy.
    # Top rec should be Sci-Fi (Cyberpunk id=5)
    assert top.id == 5


# 13. test_profile_dropped_excluded
def test_profile_dropped_excluded(sample_index: VectorIndex):
    """Dropped anime are excluded from profile results."""
    user_items = [{"anime_id": 5, "status": "dropped", "rating": None}]
    results = recommend_from_profile(
        user_items, n=10, include_mature=False, index=sample_index
    )
    rec_ids = [r.id for r in results]
    assert 5 not in rec_ids


# 14. test_profile_planning_excluded
def test_profile_planning_excluded(sample_index: VectorIndex):
    """Planning anime are excluded from profile results."""
    user_items = [{"anime_id": 7, "status": "planning", "rating": None}]
    results = recommend_from_profile(
        user_items, n=10, include_mature=False, index=sample_index
    )
    rec_ids = [r.id for r in results]
    assert 7 not in rec_ids


# 15. test_profile_zero_variance_no_crash
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


# 16. test_profile_empty_fallback
def test_profile_empty_fallback(sample_index: VectorIndex):
    """Empty cases: no ratings and no quiz gives the quality-ranked list."""
    results = recommend_from_profile([], n=3, include_mature=False, index=sample_index)
    assert len(results) == 3
    # Check that results are sorted by quality / popular
    assert (
        results[0].popularity >= results[1].popularity
        or results[0].similarity >= results[1].similarity
    )
    assert "popular" in results[0].reason.lower()


# 17. test_cold_start_smooth_blend
def test_cold_start_smooth_blend(sample_index: VectorIndex):
    """Cold-start blend smooths ratings with quiz prior."""
    quiz_vec, _, _ = build_quiz_vector({"themes": "sci_fi"}, sample_index)
    user_items = [{"anime_id": 3, "status": "completed", "rating": 10.0}]  # 1 rating
    # With K=10, w_r = 1/11 ~ 0.091, quiz prior is ~ 0.909
    taste_vec = build_taste_vector(
        user_items, quiz_prior_vec=quiz_vec, index=sample_index
    )
    assert np.any(taste_vec != 0)


# 18. test_hybrid_diversity
def test_hybrid_diversity(sample_index: VectorIndex):
    """MMR produces valid ranked output without duplicates."""
    results = recommend_similar(
        anime_id=1, n=4, include_mature=False, index=sample_index
    )
    ids = [r.id for r in results]
    assert len(ids) == len(set(ids))


# 19. test_quality_floor_relaxed
def test_quality_floor_relaxed(sample_index: VectorIndex):
    """When all candidate items are below MIN_SCORE or MIN_POPULARITY, floors relax."""
    # Seed 8 is low score (35) and low pop (20)
    results = recommend_similar(
        anime_id=8, n=5, include_mature=False, index=sample_index
    )
    assert len(results) > 0


# 20. test_explanation_specificity
def test_explanation_specificity(sample_index: VectorIndex):
    """Explanations identify shared genres and format proper sentences."""
    results = recommend_similar(
        anime_id=1, n=2, include_mature=False, index=sample_index
    )
    assert len(results) > 0
    top = results[0]
    assert top.reason != ""
    assert "Frieren" in top.reason


# 21. test_stable_ordering
def test_stable_ordering(sample_index: VectorIndex):
    """Two identical calls return identical ordered lists."""
    res1 = recommend_similar(anime_id=1, n=5, include_mature=False, index=sample_index)
    res2 = recommend_similar(anime_id=1, n=5, include_mature=False, index=sample_index)
    assert [r.id for r in res1] == [r.id for r in res2]


# 22. test_franchise_connected_components
def test_franchise_connected_components():
    """A->B and B->C builds unified franchise."""
    uf = UnionFind()
    uf.union(101, 102)
    uf.union(102, 103)
    assert uf.find(101) == uf.find(103)


# 23. test_final_score_logged_out
def test_final_score_logged_out():
    """Unit: 0.85 * rank_norm(0.9) + 0.15 * 0.8 equals expected value."""
    sim_score = rank_norm(0.9)
    quality_score = 0.8
    score = compute_final_score(sim_score, quality_score, q=0.15)
    expected = 0.85 * 0.9 + 0.15 * 0.8
    assert math.isclose(score, expected, rel_tol=1e-5)


# 24. test_final_score_logged_in
def test_final_score_logged_in():
    """Unit: alpha blend then quality blend equals expected value."""
    alpha = 0.6
    q = 0.15
    sim_score = 0.8
    taste_score = 0.6
    quality_score = 0.9
    combined = alpha * sim_score + (1.0 - alpha) * taste_score
    final = compute_final_score(combined, quality_score, q=q)
    expected = (1.0 - q) * (0.6 * 0.8 + 0.4 * 0.6) + q * 0.9
    assert math.isclose(final, expected, rel_tol=1e-5)


# 25. test_similar_logged_in_empty_taste_fallback
def test_similar_logged_in_empty_taste_fallback(sample_index: VectorIndex):
    """Empty cases: logged-in similar_to with an empty taste vector falls back to pure similarity."""
    logged_out = recommend_similar(
        anime_id=1, n=3, include_mature=False, index=sample_index
    )
    # Empty taste: user with no rated/dropped items
    logged_in_empty = recommend_similar(
        anime_id=1,
        n=3,
        include_mature=False,
        user_items=[{"anime_id": 999, "status": "watching"}],  # watching has 0 weight
        index=sample_index,
    )
    assert [r.id for r in logged_out] == [r.id for r in logged_in_empty]
