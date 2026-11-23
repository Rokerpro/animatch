import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.recs import refresh
from app.recs.refresh import catalog_fingerprint, refresh_if_changed


@pytest.mark.asyncio
async def test_fingerprint_changes_when_catalog_is_seeded(
    db_session: AsyncSession, seeded_catalog
):
    count, newest = await catalog_fingerprint(db_session)
    assert count == 10 and newest is not None


@pytest.mark.asyncio
async def test_rebuilds_only_when_fingerprint_changes(
    db_session: AsyncSession, seeded_catalog, monkeypatch: pytest.MonkeyPatch
):
    rebuilds: list[int] = []

    async def fake_rebuild(session: AsyncSession) -> None:
        rebuilds.append(1)

    monkeypatch.setattr(refresh, "rebuild_index_from_db", fake_rebuild)

    first = await refresh_if_changed(db_session, None)
    assert len(rebuilds) == 1

    same = await refresh_if_changed(db_session, first)
    assert same == first and len(rebuilds) == 1
