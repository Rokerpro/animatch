import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.anime import router as anime_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.core.config import settings, setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handles startup and shutdown events."""
    setup_logging()
    placeholder = (
        "change-this-in-production-to-a-secure-random-secret-key-at-least-32-chars"
    )
    if settings.ENVIRONMENT == "production" and (
        not settings.JWT_SECRET_KEY
        or placeholder == settings.JWT_SECRET_KEY
        or len(settings.JWT_SECRET_KEY) < 32
    ):
        raise RuntimeError(
            "In production mode, JWT_SECRET_KEY must be set, cannot equal the placeholder, and must be at least 32 characters long."
        )
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


def create_app() -> FastAPI:
    """Application factory for AniMatch FastAPI backend."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=None,
    )

    # Session middleware for OAuth state management
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.JWT_SECRET_KEY,
        same_site="lax",
        https_only=(settings.ENVIRONMENT == "production"),
    )

    # CORS configured for the Vite dev origin (or configured origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routes
    app.include_router(health_router, prefix="/api")
    app.include_router(anime_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")

    return app


app = create_app()
