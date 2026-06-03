"""
AI Analysis endpoints
  POST /api/v1/incidents/{id}/analyze          – run synchronously (blocks)
  POST /api/v1/incidents/{id}/analyze?async=1  – enqueue Celery task, return 202
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import AuthContext, get_auth
from app.schemas.analysis import AnalyzeResponse
from app.services.analysis_pipeline import run_analysis_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Analysis"])


@router.post(
    "/incidents/{incident_id}/analyze",
    response_model=AnalyzeResponse,
    responses={
        202: {"description": "Analysis queued as background task; results arrive via WebSocket."},
        404: {"description": "Incident not found"},
    },
    summary="Run AI root-cause analysis (sync or async)",
)
async def analyze_incident(
    incident_id: int,
    background: bool = Query(
        default=False,
        alias="async",
        description="Set to true to enqueue as a background Celery task and return immediately.",
    ),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
):
    """
    Runs the full AI analysis pipeline for an incident.

    - **Default (sync)**: blocks until analysis completes (~1–3 s for mock, longer for OpenAI).
    - **`?async=true`**: enqueues a Celery task and returns HTTP 202 immediately.
      Results are pushed to the dashboard via WebSocket when the task finishes.
    """
    if background:
        from app.workers.tasks import analyze_incident_bg

        task = analyze_incident_bg.apply_async(
            args=[incident_id],
            queue="analysis",
        )
        logger.info(
            "[analyze] incident=#%d enqueued as Celery task %s", incident_id, task.id
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Analysis queued. Results will be pushed via WebSocket.",
                "task_id": task.id,
                "incident_id": incident_id,
            },
        )

    # ── Synchronous path ──────────────────────────────────────
    try:
        return await run_analysis_pipeline(incident_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
