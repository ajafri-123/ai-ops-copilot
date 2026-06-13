import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    services: dict[str, str] = {}

    # Detailed errors go to logs only — exception text can disclose
    # internal hostnames / connection strings.

    # Postgres
    try:
        await db.execute(text("SELECT 1"))
        services["postgres"] = "ok"
    except Exception:
        logger.exception("Health check: postgres unreachable")
        services["postgres"] = "error"

    # Redis
    try:
        redis = get_redis()
        await redis.ping()
        services["redis"] = "ok"
    except Exception:
        logger.exception("Health check: redis unreachable")
        services["redis"] = "error"

    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    return HealthResponse(status=overall, version="0.1.0", services=services)
