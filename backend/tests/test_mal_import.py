"""Tests for MyAnimeList XML list imports."""

import gzip
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
XML = (FIXTURES / "mal_import.xml").read_bytes()


@pytest.mark.asyncio
async def test_plain_and_gzip_xml_imports(client, seeded_catalog, register_user):
    csrf = await register_user("mal-import@example.com")
    headers = {"X-CSRF-Token": csrf}
    plain = await client.post("/api/list/import", content=XML, headers=headers)
    assert plain.status_code == 200, plain.text
    summary = plain.json()
    assert summary["total_entries"] == 2
    assert summary["to_import"] == 2
    assert summary["skipped_existing"] == 0
    assert summary["unmatched_count"] == 0

    items = (await client.get("/api/list")).json()["items"]
    by_id = {item["anime_id"]: item for item in items}
    assert by_id[16498]["status"] == "completed"
    assert by_id[16498]["rating"] == 9
    assert by_id[16498]["source"] == "mal_import"
    assert by_id[5114]["status"] == "planning"
    assert by_id[5114]["rating"] is None

    csrf_gzip = await register_user("mal-gzip-import@example.com")
    gzip_xml = gzip.compress(XML)
    response = await client.post(
        "/api/list/import", content=gzip_xml, headers={"X-CSRF-Token": csrf_gzip}
    )
    assert response.status_code == 200, response.text
    assert response.json()["to_import"] == 2
    rows = (await client.get("/api/list")).json()["items"]
    by_id = {row["anime_id"]: row for row in rows}
    assert by_id[16498]["status"] == "completed" and by_id[16498]["rating"] == 9
    assert by_id[5114]["status"] == "planning" and by_id[5114]["rating"] is None


@pytest.mark.asyncio
async def test_dry_run_and_existing_entries_are_not_changed(
    client, seeded_catalog, register_user
):
    csrf = await register_user("mal-dry-run@example.com")
    headers = {"X-CSRF-Token": csrf}
    created = await client.put(
        "/api/list/16498",
        json={"status": "dropped", "rating": 2},
        headers=headers,
    )
    assert created.status_code == 200

    response = await client.post(
        "/api/list/import?dry_run=true", content=XML, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "total_entries": 2,
        "to_import": 1,
        "skipped_existing": 1,
        "unmatched_count": 0,
        "unmatched": [],
    }
    rows = (await client.get("/api/list")).json()["items"]
    assert len(rows) == 1 and rows[0]["status"] == "dropped" and rows[0]["rating"] == 2

    committed = await client.post("/api/list/import", content=XML, headers=headers)
    assert committed.status_code == 200
    rows = {
        row["anime_id"]: row for row in (await client.get("/api/list")).json()["items"]
    }
    assert rows[16498]["status"] == "dropped" and rows[16498]["rating"] == 2
    assert rows[5114]["status"] == "planning"


@pytest.mark.asyncio
async def test_unmatched_ids_are_reported_and_not_created(
    client, seeded_catalog, register_user
):
    csrf = await register_user("mal-unmatched@example.com")
    xml = b"""<myanimelist><anime><series_animedb_id>99999999</series_animedb_id><series_title>Unknown show</series_title><my_score>8</my_score><my_status>Watching</my_status></anime></myanimelist>"""
    response = await client.post(
        "/api/list/import", content=xml, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    assert response.json()["unmatched_count"] == 1
    assert response.json()["unmatched"] == [
        {"title": "Unknown show", "mal_id": 99999999}
    ]
    assert (await client.get("/api/list")).json()["items"] == []


@pytest.mark.asyncio
async def test_imports_mature_titles_even_when_hidden_by_default(
    client, seeded_catalog, db_session, register_user
):
    from sqlalchemy import select

    from app.models.anime import Anime

    anime = await db_session.scalar(select(Anime).where(Anime.id == 16498))
    anime.is_adult = True
    await db_session.commit()
    csrf = await register_user("mal-mature@example.com")
    response = await client.post(
        "/api/list/import", content=XML, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    assert response.json()["to_import"] == 2
    visible = (await client.get("/api/list")).json()["items"]
    assert {item["anime_id"] for item in visible} == {5114}
    all_items = (await client.get("/api/list?includeMature=true")).json()["items"]
    assert {item["anime_id"] for item in all_items} == {16498, 5114}


@pytest.mark.asyncio
async def test_status_forms_and_out_of_range_scores(
    client, seeded_catalog, register_user
):
    csrf = await register_user("mal-status-mapping@example.com")
    xml = b"""<myanimelist>
      <anime><series_animedb_id>52991</series_animedb_id><series_title>One</series_title><my_score>11</my_score><my_status>1</my_status></anime>
      <anime><series_animedb_id>16498</series_animedb_id><series_title>Two</series_title><my_score>8</my_score><my_status>Completed</my_status></anime>
      <anime><series_animedb_id>40750</series_animedb_id><series_title>Three</series_title><my_score>7</my_score><my_status>On-Hold</my_status></anime>
      <anime><series_animedb_id>5114</series_animedb_id><series_title>Four</series_title><my_score>5</my_score><my_status>Dropped</my_status></anime>
      <anime><series_animedb_id>199</series_animedb_id><series_title>Five</series_title><my_score>3</my_score><my_status>6</my_status></anime>
    </myanimelist>"""
    response = await client.post(
        "/api/list/import", content=xml, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200, response.text
    rows = {
        row["anime_id"]: row
        for row in (await client.get("/api/list?includeMature=true")).json()["items"]
    }
    assert rows[154587]["status"] == "watching" and rows[154587]["rating"] is None
    assert rows[16498]["status"] == "completed" and rows[16498]["rating"] == 8
    assert rows[113425]["status"] == "on_hold" and rows[113425]["rating"] == 7
    assert rows[5114]["status"] == "dropped" and rows[5114]["rating"] == 5
    assert rows[199]["status"] == "planning" and rows[199]["rating"] == 3


@pytest.mark.asyncio
async def test_requires_login_csrf_and_keeps_user_lists_isolated(
    client, seeded_catalog, register_user
):
    response = await client.post("/api/list/import", content=XML)
    assert response.status_code == 401

    csrf_a = await register_user("mal-owner@example.com")
    bad_csrf = await client.post("/api/list/import", content=XML)
    assert bad_csrf.status_code == 403
    owner_import = await client.post(
        "/api/list/import", content=XML, headers={"X-CSRF-Token": csrf_a}
    )
    assert owner_import.status_code == 200

    csrf_b = await register_user("mal-other@example.com")
    other_list = await client.get("/api/list")
    assert other_list.status_code == 200 and other_list.json()["items"] == []
    assert csrf_b


@pytest.mark.asyncio
async def test_duplicate_mal_ids_keep_last_entry(client, seeded_catalog, register_user):
    csrf = await register_user("mal-duplicate@example.com")
    xml = (FIXTURES / "mal_import_duplicate.xml").read_bytes()
    response = await client.post(
        "/api/list/import", content=xml, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    assert response.json()["total_entries"] == 2
    rows = (await client.get("/api/list")).json()["items"]
    assert (
        len(rows) == 1 and rows[0]["status"] == "completed" and rows[0]["rating"] == 10
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("xml", "message"),
    [
        (b"<!DOCTYPE myanimelist><myanimelist/>", "DOCTYPE"),
        (b"<!ENTITY x 'y'><myanimelist/>", "ENTITY"),
        (b"<myanimelist>", "Invalid XML"),
        (b"<root/>", "root"),
        (b"<myanimelist><manga/></myanimelist>", "no <anime>"),
    ],
)
async def test_invalid_xml_is_rejected(client, register_user, xml, message):
    csrf = await register_user(f"invalid-xml-{len(xml)}@example.com")
    response = await client.post(
        "/api/list/import", content=xml, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 400
    assert message in response.json()["detail"]


@pytest.mark.asyncio
async def test_size_and_entry_limits(client, register_user):
    csrf = await register_user("mal-limits@example.com")
    headers = {"X-CSRF-Token": csrf}
    oversized = await client.post(
        "/api/list/import", content=b" " * (25 * 1024 * 1024 + 1), headers=headers
    )
    assert oversized.status_code == 413

    bomb = gzip.compress(
        b"<myanimelist>" + b" " * (25 * 1024 * 1024 + 1) + b"</myanimelist>"
    )
    decompressed_oversized = await client.post(
        "/api/list/import", content=bomb, headers=headers
    )
    assert decompressed_oversized.status_code == 413

    one_entry = (
        "<anime><series_animedb_id>1</series_animedb_id>"
        "<my_status>1</my_status></anime>"
    )
    many_entries = "<myanimelist>" + one_entry * 5001 + "</myanimelist>"
    too_many = await client.post(
        "/api/list/import", content=many_entries, headers=headers
    )
    assert too_many.status_code == 413


@pytest.mark.asyncio
async def test_gzip_compressed_size_limit(client, register_user):
    csrf = await register_user("mal-compressed-limit@example.com")
    # A deliberately incompressible payload over the cap is rejected before parsing.
    payload = b"\x1f\x8b" + b"x" * (5 * 1024 * 1024)
    response = await client.post(
        "/api/list/import", content=payload, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_only_dry_run_query_parameter_is_supported(client, register_user):
    csrf = await register_user("mal-query@example.com")
    response = await client.post(
        "/api/list/import?other=true", content=XML, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 422
