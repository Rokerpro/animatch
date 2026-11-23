import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.recs.schemas import FeaturesResponse
from app.recs.vectors import get_index

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/features", response_model=FeaturesResponse)
async def get_features() -> FeaturesResponse:
    """Return public feature availability without exposing configuration."""
    return FeaturesResponse(natural_language=bool(settings.GEMINI_API_KEY.strip()))


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


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Process is up. Never touches the database, so orchestrators avoid restart loops."""
    return {"status": "ok"}


class ReadinessResponse(BaseModel):
    status: str
    database: str
    index: str


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(
    response: Response, db: Annotated[AsyncSession, Depends(get_db)]
) -> ReadinessResponse:
    """Ready to take traffic: database reachable and recommendation index loaded."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(f"Readiness database check failed: {exc}")
        db_status = "disconnected"
    index_status = "empty" if get_index().is_empty() else "loaded"
    ready = db_status == "connected" and index_status == "loaded"
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        database=db_status,
        index=index_status,
    )
