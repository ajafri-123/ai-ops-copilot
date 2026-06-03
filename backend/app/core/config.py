import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "AI Ops Copilot"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    SECRET_KEY: str = "change-me"

    # Allowed CORS origins — use "*" only for local dev without credentials
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    @model_validator(mode="after")
    def _check_secret_key(self) -> "Settings":
        if not self.DEBUG and self.SECRET_KEY == "change-me":
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if self.SECRET_KEY == "change-me":
            logger.warning("Using insecure default SECRET_KEY — set SECRET_KEY in .env before deploying.")
        return self

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://aiops:aiops@localhost:5432/aiops"

    # ── Redis / Celery ────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_CONCURRENCY: int = 4          # worker processes per container
    CELERY_TASK_SOFT_TIME_LIMIT: int = 60   # seconds before soft timeout
    CELERY_TASK_TIME_LIMIT: int = 120        # hard kill after this many seconds

    # ── Background-job behaviour ──────────────────────────────
    # Set to true to fire random demo alerts on a Beat schedule
    DEMO_PERIODIC_ALERTS: bool = False
    # How often the Beat task fires (seconds)
    DEMO_ALERT_INTERVAL_SECONDS: int = 120

    # When true, newly-created incidents automatically get AI analysis
    # queued as a background Celery task (low-priority queue)
    AUTO_ANALYZE_NEW_INCIDENTS: bool = False

    # ── JWT ───────────────────────────────────────────────────
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ── AI integrations ───────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"


settings = Settings()
