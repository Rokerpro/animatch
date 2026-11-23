"""Tests for list statistics and export."""

import pytest

from app.services.mal_import import build_mal_xml, parse_mal_xml

IDS = {154587: ("completed", 8), 16498: ("watching", None), 5114: ("completed", 10)}


async def fill(client, csrf: str) -> None:
    for anime_id, (status, rating) in IDS.items():
        body = {"status": status, "rating": rating} if rating else {"status": status}
        res = await client.put(
            f"/api/list/{anime_id}", json=body, headers={"X-CSRF-Token": csrf}
        )
        assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_stats_and_export_require_auth(client):
    assert (await client.get("/api/list/stats")).status_code == 401
    assert (await client.get("/api/list/export")).status_code == 401


@pytest.mark.asyncio
async def test_stats_summarise_the_list(client, seeded_catalog, register_user):
    await fill(client, await register_user("stats@example.com"))
    data = (await client.get("/api/list/stats")).json()
    assert data["total"] == 3
    assert data["by_status"]["completed"] == 2
    assert data["by_status"]["watching"] == 1
    assert data["by_status"]["dropped"] == 0
    assert data["rated_count"] == 2
    assert data["mean_rating"] == 9.0
    assert data["rating_distribution"]["8"] == 1
    assert data["rating_distribution"]["10"] == 1
    assert len(data["top_genres"]) <= 5


@pytest.mark.asyncio
async def test_stats_are_empty_for_new_user(client, register_user):
    await register_user("empty-stats@example.com")
    data = (await client.get("/api/list/stats")).json()
    assert data["total"] == 0 and data["mean_rating"] is None
    assert data["top_genres"] == []


@pytest.mark.asyncio
async def test_json_export_is_a_download_of_own_list(
    client, seeded_catalog, register_user
):
    await fill(client, await register_user("json-export@example.com"))
    response = await client.get("/api/list/export")
    assert response.status_code == 200
    assert "animatch-list.json" in response.headers["content-disposition"]
    assert {row["anime_id"] for row in response.json()} == set(IDS)


@pytest.mark.asyncio
async def test_xml_export_round_trips_through_the_importer(
    client, seeded_catalog, register_user
):
    await fill(client, await register_user("xml-export@example.com"))
    response = await client.get("/api/list/export?format=xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    _, parsed = parse_mal_xml(response.content)
    assert len(parsed) >= 1
    assert (await client.get("/api/list/export?format=csv")).status_code == 422


def test_build_mal_xml_escapes_titles_and_parses_back():
    xml = build_mal_xml([(1, "Tom & <Jerry>", "completed", 9)])
    assert "Tom &amp; &lt;Jerry&gt;" in xml
    _, parsed = parse_mal_xml(xml.encode())
    assert parsed[0].status == "completed" and parsed[0].rating == 9
