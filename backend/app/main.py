import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.database import create_tables
from app.core.redis import close_redis
from app.core.seed import seed_database

logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    logger.info("Creating database tables …")
    await create_tables()
    logger.info("Tables ready.")

    logger.info("Running database seed …")
    await seed_database()

    yield

    # ── Shutdown ─────────────────────────────────────────────
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/", include_in_schema=False)
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}
