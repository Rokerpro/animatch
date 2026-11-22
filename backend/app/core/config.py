import logging
import sys

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    # Optional error reporting; leave empty to disable.
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
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

    # Reverse proxies (IPs or CIDRs) whose X-Forwarded-For header is trusted for
    # per-IP rate limiting. Empty means the header is ignored entirely.
    TRUSTED_PROXIES: list[str] | str = []

    @field_validator("TRUSTED_PROXIES", mode="before")
    @classmethod
    def assemble_trusted_proxies(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                import json

                try:
                    parsed = json.loads(stripped)
                    return [str(i).strip() for i in parsed if str(i).strip()]
                except Exception:
                    return []
            return [i.strip() for i in stripped.split(",") if i.strip()]
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

    # Transactional email. "log" writes messages to the application log (development);
    # "smtp" sends through the configured server.
    EMAIL_BACKEND: str = "log"
    EMAIL_FROM: str = "AniMatch <no-reply@localhost>"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_STARTTLS: bool = True
    PASSWORD_RESET_TTL_MINUTES: int = 60
    EMAIL_VERIFY_TTL_HOURS: int = 48

    # Gemini LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    NL_MAX_CHARS: int = 300
    NL_TIMEOUT_SECONDS: float = 10.0
    NL_DAILY_LIMIT: int = 20

    # Adult-flagged tags only make a title mature when their AniList rank meets
    # this relevance percentage. isAdult, Hentai, and Ecchi remain hard rules.
    MATURE_TAG_MIN_RANK: int = 60

    # Minutes between checks for a re-synced catalog; 0 disables the refresher.
    INDEX_REFRESH_MINUTES: int = 0

    # Recommendation Engine
    REC_GENRE_DIM_WEIGHT: float = 3.0
    REC_TAG_DIM_WEIGHT: float = 2.0
    REC_FORMAT_DIM_WEIGHT: float = 1.0

    REC_WEIGHT_SIMILAR: float = 0.5
    REC_WEIGHT_QUIZ: float = 0.3
    REC_WEIGHT_PROFILE: float = 0.2

    REC_ALPHA: float = 0.6
    # Quality is a small additive bonus so relevance clearly leads.
    # Formula: final = minmax_sim + REC_QUALITY_WEIGHT * quality_pct
    REC_QUALITY_WEIGHT: float = 0.1

    # MMR parameters
    # REC_MMR_LAMBDA: balance between relevance (1.0) and diversity (0.0).
    REC_MMR_LAMBDA: float = 0.8
    # REC_TOP_CANDIDATES: blended cosine is min-max scaled over this many candidates
    # before quality is added and MMR is run.
    REC_TOP_CANDIDATES: int = 200
    # REC_MMR_POOL: MMR is run only over this many top-relevance candidates.
    # Items outside this pool are never pulled in by MMR (movement cap).
    REC_MMR_POOL: int = 40

    REC_MIN_SCORE: int = 50
    REC_MIN_POPULARITY: int = 100

    REC_COLD_START_K: int = 10

    # Penalty amount; 0.5 applies a 0.5 score multiplier outside the episode range.
    REC_QUIZ_SOFT_PENALTY_EPISODES: float = 0.5
    REC_QUIZ_SOFT_PENALTY_YEAR: float = 0.15
    # Quiz-only quality bonus, independently configurable for evaluation.
    REC_QUIZ_QUALITY_WEIGHT: float = 0.25
    # Conservative additive novelty boost for Phase 8 discovery recommendations.
    REC_NEW_NOVELTY_WEIGHT: float = 0.08

    # Minimum number of shared salient features (genres + non-spoiler tags
    # with rank >= 60 on both titles) required for a recommendation to be shown.
    # Results with fewer are dropped; we return fewer than N rather than padding.
    REC_MIN_SALIENT_FEATURES: int = 2
    REC_SALIENT_TAG_STOPLIST: list[str] = [
        "Male Protagonist",
        "Female Protagonist",
        "Primarily Male Cast",
        "Primarily Female Cast",
        "Primarily Adult Cast",
        "Primarily Teen Cast",
        "Primarily Child Cast",
        "Ensemble Cast",
        "Urban",
    ]

    REC_DEFAULT_N: int = 10
    REC_MAX_N: int = 50

    REC_START_METHOD: str = "A"
    REC_START_LIKED_WEIGHT: float = 0.7

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
        "%(asctime)s | %(levelname)-8s | %(request_id)s | "
        "%(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )

    from app.core.request_id import RequestIdFilter

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[handler],
        force=True,
    )


def setup_error_reporting() -> None:
    """Initialise Sentry when SENTRY_DSN is set. Sends no personal data by default."""
    if not settings.SENTRY_DSN:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
