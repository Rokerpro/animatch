import logging
import sys

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "0.1.0"
    APP_NAME: str = "AniMatch API"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS origins: in development, only the Vite dev server origin
    CORS_ORIGINS: list[str] | str = ["http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v if isinstance(v, list) else []

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./animatch.db"

    # Authentication
    JWT_SECRET_KEY: str = (
        "change-this-in-production-to-a-secure-random-secret-key-at-least-32-chars"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    SESSION_COOKIE_NAME: str = "access_token"
    CSRF_COOKIE_NAME: str = "csrf_token"
    COOKIE_SAMESITE: str = "lax"

    # Frontend URL (for OAuth redirects)
    FRONTEND_URL: str = "http://localhost:5173"

    # Google OAuth (Optional)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # Gemini LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        placeholder = (
            "change-this-in-production-to-a-secure-random-secret-key-at-least-32-chars"
        )
        if self.ENVIRONMENT == "production" and (
            not self.JWT_SECRET_KEY
            or placeholder == self.JWT_SECRET_KEY
            or len(self.JWT_SECRET_KEY) < 32
        ):
            raise ValueError(
                "In production mode, JWT_SECRET_KEY must be set, cannot equal the placeholder, and must be at least 32 characters long."
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def setup_logging() -> None:
    """Configures structured logging for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
