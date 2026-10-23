import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str


@router.get("/health", response_model=HealthResponse)
async def check_health(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HealthResponse:
    """Returns application health status, version, and database connectivity."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        db_status = "disconnected"

    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
    )
