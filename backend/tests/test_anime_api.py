"""Tests for Anime API catalog endpoints, filters, FTS search, and mature rules."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_browse_paginated(client: AsyncClient, seeded_catalog: None):
    """GET /api/anime returns paginated results with pageInfo."""
    response = await client.get("/api/anime?page=1&pageSize=3")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pageInfo" in data
    items = data["items"]
    page_info = data["pageInfo"]

    assert len(items) <= 3
    assert page_info["currentPage"] == 1
    assert page_info["perPage"] == 3
    assert page_info["total"] > 0
    assert page_info["hasNextPage"] is True

    # Card fields check
    card = items[0]
    assert "id" in card
    assert "title" in card
    assert "format" in card
    assert "genres" in card


@pytest.mark.asyncio
async def test_filter_genres_all_must_match(client: AsyncClient, seeded_catalog: None):
    """Filter by multiple genres: only animes matching ALL selected genres return."""
    # Both Action AND Fantasy
    response = await client.get("/api/anime?genres=Action&genres=Fantasy")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    for item in items:
        assert "Action" in item["genres"]
        assert "Fantasy" in item["genres"]


@pytest.mark.asyncio
async def test_filter_exclude_genres(client: AsyncClient, seeded_catalog: None):
    """Filter by exclude_genres: excluded genres must not appear in any item."""
    # Action genres, but exclude Mystery
    response = await client.get("/api/anime?genres=Action&excludeGenres=Mystery")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    for item in items:
        assert "Action" in item["genres"]
        assert "Mystery" not in item["genres"]


@pytest.mark.asyncio
async def test_filter_tags(client: AsyncClient, seeded_catalog: None):
    """Filter by tags: returns only anime with the specified tag."""
    response = await client.get("/api/anime?tags=Ninja")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == 20  # Naruto


@pytest.mark.asyncio
async def test_filter_format(client: AsyncClient, seeded_catalog: None):
    """Filter by format e.g. MOVIE."""
    response = await client.get("/api/anime?format=MOVIE")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == 199  # Spirited Away
    assert items[0]["format"] == "MOVIE"


@pytest.mark.asyncio
async def test_filter_year_range(client: AsyncClient, seeded_catalog: None):
    """Filter by release year range (yearMin and yearMax)."""
    response = await client.get("/api/anime?yearMin=2010&yearMax=2015")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    for item in items:
        assert item["year"] is not None
        assert 2010 <= item["year"] <= 2015


@pytest.mark.asyncio
async def test_filter_min_score(client: AsyncClient, seeded_catalog: None):
    """Filter by minScore."""
    response = await client.get("/api/anime?minScore=90")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    for item in items:
        assert item["score"] is not None
        assert item["score"] >= 90


@pytest.mark.asyncio
async def test_filter_max_episodes(client: AsyncClient, seeded_catalog: None):
    """Filter by maxEpisodes."""
    response = await client.get("/api/anime?maxEpisodes=25")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    for item in items:
        assert item["episodes"] is not None
        assert item["episodes"] <= 25


@pytest.mark.asyncio
async def test_filter_status(client: AsyncClient, seeded_catalog: None):
    """Filter by status e.g. RELEASING."""
    response = await client.get("/api/anime?status=RELEASING")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == 21  # One Piece


@pytest.mark.asyncio
async def test_sort_options(client: AsyncClient, seeded_catalog: None):
    """Test whitelisted sorts: popularity, score, year, title."""
    for sort_param in ["popularity", "score", "year", "title"]:
        resp = await client.get(f"/api/anime?sort={sort_param}&pageSize=5")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0

    # Verify score sort order is descending
    resp_score = await client.get("/api/anime?sort=score&pageSize=5")
    items_score = resp_score.json()["items"]
    scores = [it["score"] for it in items_score if it["score"] is not None]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_fts_prefix_and_synonyms_search(
    client: AsyncClient, seeded_catalog: None
):
    """FTS prefix match and synonyms match."""
    # Prefix match "frie" -> Frieren
    res_prefix = await client.get("/api/anime?q=frie")
    assert res_prefix.status_code == 200
    items_prefix = res_prefix.json()["items"]
    assert len(items_prefix) > 0
    assert items_prefix[0]["id"] == 154587

    # Synonym match "slayer" -> Frieren (synonym: "Frieren the Slayer")
    res_synonym = await client.get("/api/anime?q=slayer")
    assert res_synonym.status_code == 200
    items_syn = res_synonym.json()["items"]
    assert len(items_syn) > 0
    assert items_syn[0]["id"] == 154587

    # Native title match
    res_native = await client.get("/api/anime?q=葬送")
    assert res_native.status_code == 200
    assert len(res_native.json()["items"]) > 0


@pytest.mark.asyncio
async def test_fts_exact_title_match_boost(client: AsyncClient, seeded_catalog: None):
    """Exact title match is boosted to the top of search results."""
    # Searching exact title 'Attack on Titan'
    res = await client.get("/api/anime?q=Attack on Titan")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    assert items[0]["id"] == 16498  # Attack on Titan


@pytest.mark.asyncio
async def test_fts_sanitizing_prevents_500(client: AsyncClient, seeded_catalog: None):
    """Malformed syntax (quotes, parens, operators) does not cause 500."""
    malformed_queries = [
        '"""""',
        "AND OR NOT NEAR",
        'frieren) ("* ^:; -+ <>=',
        "***",
        "(((((((",
        "!@#$%^&*()",
    ]
    for q in malformed_queries:
        res = await client.get(f"/api/anime?q={q}")
        assert res.status_code == 200, f"Query '{q}' raised status {res.status_code}"


@pytest.mark.asyncio
async def test_mature_exclusion_by_default(client: AsyncClient, seeded_catalog: None):
    """Server-side mature content exclusion: isAdult, adult tags, and Hentai/Ecchi genres."""
    # Default browse: includeMature=false
    res = await client.get("/api/anime?pageSize=50")
    assert res.status_code == 200
    items = res.json()["items"]

    # None of the items should be adult or contain mature genres
    for it in items:
        assert it["isAdult"] is False
        assert "Ecchi" not in it["genres"]
        assert "Hentai" not in it["genres"]

    # Redo of Healer (id 113425) and Interspecies Reviewers (id 110270) must not be in items
    returned_ids = {it["id"] for it in items}
    assert 113425 not in returned_ids
    assert 110270 not in returned_ids

    # Detail endpoint must return 404 when mature item requested without includeMature=true
    detail_res = await client.get("/api/anime/113425")
    assert detail_res.status_code == 404

    detail_res_2 = await client.get("/api/anime/110270")
    assert detail_res_2.status_code == 404


@pytest.mark.asyncio
async def test_mature_included_when_flag_enabled(
    client: AsyncClient, seeded_catalog: None
):
    """When includeMature=true, adult anime are accessible."""
    res = await client.get("/api/anime?includeMature=true&pageSize=50")
    assert res.status_code == 200
    items = res.json()["items"]
    returned_ids = {it["id"] for it in items}
    assert 113425 in returned_ids

    # Detail endpoint with includeMature=true returns the item
    detail_res = await client.get("/api/anime/113425?includeMature=true")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == 113425
    assert detail_res.json()["isAdult"] is True


@pytest.mark.asyncio
async def test_genres_endpoint_mature_filtering(
    client: AsyncClient, seeded_catalog: None
):
    """GET /api/genres filters out Hentai and Ecchi when includeMature=false."""
    res_sfw = await client.get("/api/genres")
    assert res_sfw.status_code == 200
    genres_sfw = res_sfw.json()
    assert "Ecchi" not in genres_sfw
    assert "Hentai" not in genres_sfw
    assert "Action" in genres_sfw

    # With includeMature=true
    res_all = await client.get("/api/genres?includeMature=true")
    assert res_all.status_code == 200
    genres_all = res_all.json()
    assert "Ecchi" in genres_all


@pytest.mark.asyncio
async def test_tags_endpoint_mature_filtering(
    client: AsyncClient, seeded_catalog: None
):
    """GET /api/tags filters out adult tags when includeMature=false."""
    res_sfw = await client.get("/api/tags")
    assert res_sfw.status_code == 200
    tags_sfw = res_sfw.json()
    assert "Explicit Violence" not in tags_sfw
    assert "Prostitution" not in tags_sfw
    assert "Magic" in tags_sfw

    # With includeMature=true
    res_all = await client.get("/api/tags?includeMature=true")
    assert res_all.status_code == 200
    tags_all = res_all.json()
    assert "Explicit Violence" in tags_all
    assert "Prostitution" in tags_all


@pytest.mark.asyncio
async def test_anime_detail_full_and_404(client: AsyncClient, seeded_catalog: None):
    """GET /api/anime/{id} returns full details with studio, synopsis, tags, and 404 for unknown."""
    # Unknown ID -> 404
    res_404 = await client.get("/api/anime/999999")
    assert res_404.status_code == 404

    # Known ID -> full detail
    res = await client.get("/api/anime/154587")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 154587
    assert data["title"] == "Frieren: Beyond Journey's End"
    assert data["studio"] == "MADHOUSE"
    assert data["synopsis"] is not None
    assert "<p>" not in data["synopsis"]
    assert "Magic" in data["tags"]
    assert "Fantasy" in data["genres"]
    assert data["idMal"] == 52991
    assert "tagDetails" in data
    assert isinstance(data["tagDetails"], list)
    assert len(data["tagDetails"]) > 0
    first_tag = data["tagDetails"][0]
    assert "name" in first_tag
    assert "rank" in first_tag
    assert "isSpoiler" in first_tag
    assert isinstance(first_tag["isSpoiler"], bool)



@pytest.mark.asyncio
async def test_anime_filters_endpoint(client: AsyncClient, seeded_catalog: None):
    """GET /api/anime/filters is routed correctly before /api/anime/{id} and returns filters object."""
    res = await client.get("/api/anime/filters")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "genres" in data
    assert "tags" in data
    assert isinstance(data["genres"], list)
    assert isinstance(data["tags"], list)
    assert "Action" in data["genres"]
    assert "Ecchi" not in data["genres"]
    assert "Magic" in data["tags"]
    assert "Explicit Violence" not in data["tags"]

    # With includeMature=true
    res_mature = await client.get("/api/anime/filters?includeMature=true")
    assert res_mature.status_code == 200
    data_mature = res_mature.json()
    assert "Ecchi" in data_mature["genres"]
    assert "Explicit Violence" in data_mature["tags"]
