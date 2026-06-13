import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.database import create_tables
from app.core.ratelimit import limiter
from app.core.redis import close_redis
from app.core.seed import seed_database
from app.core.ws_manager import ws_manager

logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """Bring the schema to head via Alembic (production / Postgres path)."""
    import os

    from alembic import command
    from alembic.config import Config

    here = os.path.dirname(__file__)
    cfg = Config(os.path.join(here, "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "..", "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    # SQLite (tests/local) can't run the Postgres-oriented migrations, so it
    # falls back to create_all. Real databases go through Alembic so the schema
    # has a versioned upgrade path instead of silent create_all drift.
    if settings.DATABASE_URL.startswith("sqlite"):
        logger.info("SQLite detected — creating tables directly …")
        await create_tables()
    else:
        logger.info("Running database migrations (alembic upgrade head) …")
        _run_migrations()
    logger.info("Schema ready.")

    logger.info("Running database seed …")
    await seed_database()

    # Relay WS events published to Redis (by Celery workers or other API
    # replicas) to this process's connected clients.
    ws_manager.start_relay()

    yield

    # ── Shutdown ─────────────────────────────────────────────
    await ws_manager.stop_relay()
    await close_redis()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description=(
        "AI Operations Copilot – incident response platform. "
        "Ingests infrastructure alerts, correlates events, and provides "
        "AI-assisted root-cause analysis and remediation guidance."
    ),
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


app.include_router(v1_router)


@app.get("/", include_in_schema=False)
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}
