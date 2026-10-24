import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import create_app
from app.services.catalog_sync import CatalogSyncService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def anilist_page1_data() -> dict[str, Any]:
    with open(FIXTURES_DIR / "anilist_page1.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def anilist_page2_data() -> dict[str, Any]:
    with open(FIXTURES_DIR / "anilist_page2.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite engine initialized with tables and FTS5 triggers."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await init_db(engine)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session bound to the test engine."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(
    test_engine: AsyncEngine, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient, None]:
    """Provides an asynchronous HTTP test client with database dependency override."""
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def seeded_catalog(
    db_session: AsyncSession,
    anilist_page1_data: dict[str, Any],
    anilist_page2_data: dict[str, Any],
) -> None:
    """Seeds test database with both page 1 and page 2 fixtures (10 anime total)."""
    service = CatalogSyncService()
    # Parse media from page 1
    p1_media = anilist_page1_data["data"]["Page"]["media"]
    p2_media = anilist_page2_data["data"]["Page"]["media"]

    # Parse and upsert items using client's parsing logic
    all_raw = p1_media + p2_media
    parsed_items = []
    for item in all_raw:
        title_dict = item.get("title") or {}
        cover_dict = item.get("coverImage") or {}
        studios = (item.get("studios") or {}).get("nodes") or []
        main_studio = studios[0].get("name") if studios else None
        from app.core.text import strip_html_tags

        parsed = {
            "id": item["id"],
            "id_mal": item.get("idMal"),
            "title_romaji": title_dict.get("romaji"),
            "title_english": title_dict.get("english"),
            "title_native": title_dict.get("native"),
            "synonyms": item.get("synonyms") or [],
            "description": strip_html_tags(item.get("description")),
            "cover_image_url": cover_dict.get("extraLarge") or cover_dict.get("large"),
            "banner_image_url": item.get("bannerImage"),
            "format": item.get("format"),
            "episodes": item.get("episodes"),
            "duration": item.get("duration"),
            "status": item.get("status"),
            "season": item.get("season"),
            "season_year": item.get("seasonYear"),
            "average_score": item.get("averageScore"),
            "popularity": item.get("popularity") or 0,
            "is_adult": bool(item.get("isAdult", False)),
            "source": item.get("source"),
            "main_studio": main_studio,
            "updated_at_anilist": item.get("updatedAt"),
            "genres": [g for g in item.get("genres") or [] if g],
            "tags": [
                {
                    "name": t["name"],
                    "category": t.get("category"),
                    "is_adult": bool(t.get("isAdult", False)),
                    "rank": int(t.get("rank") or 0),
                }
                for t in item.get("tags") or []
                if t.get("name")
            ],
        }
        parsed_items.append(parsed)

    await service.upsert_batch(db_session, parsed_items)
