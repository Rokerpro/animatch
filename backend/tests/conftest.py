import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.main import create_app
from app.models.anime import Anime
from app.services.anilist import parse_media_item
from app.services.catalog_sync import CatalogSyncService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _reset_throttle():
    from app.api.recs import _similar_cache
    from app.core.throttle import reset_throttle_state

    reset_throttle_state()
    _similar_cache.clear()
    yield
    reset_throttle_state()
    _similar_cache.clear()


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
def register_user(client: AsyncClient) -> Callable[[str], Awaitable[str]]:
    """Register a user through the auth route and return its CSRF token."""

    async def register(email: str) -> str:
        response = await client.post(
            "/api/auth/register",
            json={"email": email, "password": "secure_password_12345"},
        )
        assert (
            response.status_code == 201
        ), f"registration payload failed: {response.text}"
        return response.cookies[settings.CSRF_COOKIE_NAME]

    return register


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

    parsed_items = [parse_media_item(item) for item in p1_media + p2_media]

    await service.upsert_batch(db_session, parsed_items)
    franchise_members = await db_session.execute(
        select(Anime).where(Anime.id.in_([154587, 5114]))
    )
    for anime in franchise_members.scalars():
        anime.franchise_id = 154587
    await db_session.commit()
