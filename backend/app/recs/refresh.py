"""Keep the in-memory recommendation index in step with catalog syncs.

`sync-catalog` runs as a separate process, so the API server would otherwise keep
serving a stale index until restart. A cheap fingerprint of the catalog (row count
and newest sync time) is polled; the index is rebuilt only when it changes.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.anime import Anime
from app.recs.engine import rebuild_index_from_db

logger = logging.getLogger(__name__)

Fingerprint = tuple[int, str | None]


async def catalog_fingerprint(session: AsyncSession) -> Fingerprint:
    """Return (anime count, newest synced_at as text) for change detection."""
    result = await session.execute(
        select(func.count(Anime.id), func.max(Anime.synced_at))
    )
    count, newest = result.one()
    return int(count), str(newest) if newest is not None else None


async def refresh_if_changed(
    session: AsyncSession, last: Fingerprint | None
) -> Fingerprint:
    """Rebuild the index when the catalog changed since `last`; return the new value."""
    current = await catalog_fingerprint(session)
    if current != last:
        await rebuild_index_from_db(session)
        logger.info("Recommendation index rebuilt (titles=%d)", current[0])
    return current


async def _refresh_loop(interval_seconds: float, last: Fingerprint | None) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with AsyncSessionLocal() as session:
                last = await refresh_if_changed(session, last)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Recommendation index refresh failed")


@asynccontextmanager
async def index_refresher(last: Fingerprint | None) -> AsyncGenerator[None, None]:
    """Run the periodic refresh while the app is up (no-op when disabled)."""
    minutes = settings.INDEX_REFRESH_MINUTES
    if minutes <= 0:
        yield
        return
    task = asyncio.create_task(_refresh_loop(minutes * 60, last))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
