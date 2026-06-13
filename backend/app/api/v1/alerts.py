"""
Alert endpoints
  POST   /api/v1/alerts               – ingest alert (sync correlation default)
  POST   /api/v1/alerts?async=true    – save alert, enqueue Celery job, return 202
  GET    /api/v1/alerts               – list alerts (filterable, paginated)
  GET    /api/v1/alerts/{id}          – get single alert
  POST   /api/v1/alerts/demo-generate – fire a realistic multi-alert scenario
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import AuthContext, get_auth
from app.core.ratelimit import ALERT_INGEST_LIMIT, DEMO_GENERATE_LIMIT, limiter
from app.core.ws_manager import ws_manager
from app.crud.alert import create_alert, get_alert, list_alerts
from app.models.alert import AlertStatus
from app.schemas.alert import AlertCreate, AlertListResponse, AlertRead
from app.services.correlation_engine import correlation_engine
from app.services.demo_generator import AVAILABLE_SCENARIOS, build_alerts_for_scenario
from app.workers.tasks import process_alert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertIngestResponse(BaseModel):
    alert: AlertRead
    incident_id: int
    incident_title: str
    incident_severity: str
    incident_status: str
    created_new_incident: bool
    correlation_reason: str
    correlation_score: float
    correlation_signals: list[str]


class AlertIngestAsyncResponse(BaseModel):
    alert: AlertRead
    task_id: str
    message: str


class DemoGenerateResponse(BaseModel):
    scenario: str
    alerts_created: int
    incidents_touched: list[int]
    new_incidents_created: int
    detail: list[dict[str, Any]]


# ── POST /alerts/demo-generate ────────────────────────────────────────────────

@router.post(
    "/demo-generate",
    response_model=DemoGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fire a realistic multi-alert scenario",
)
@limiter.limit(DEMO_GENERATE_LIMIT)
async def demo_generate(
    request: Request,
    scenario: str = Body(
        default="database_overload",
        embed=True,
        description=f"Scenario name. One of: {', '.join(AVAILABLE_SCENARIOS)}",
    ),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> DemoGenerateResponse:
    try:
        alert_dicts = build_alerts_for_scenario(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    incidents_touched: set[int] = set()
    new_incidents = 0
    detail: list[dict[str, Any]] = []

    for alert_data in alert_dicts:
        alert = await create_alert(db, AlertCreate(**alert_data), org_id=ctx.org_id)
        result = await correlation_engine.correlate(db, alert)

        incidents_touched.add(result.incident.id)
        if result.created_new:
            new_incidents += 1

        detail.append({
            "alert_id": alert.id,
            "alert_title": alert.title,
            "service": alert.service_name,
            "severity": alert.severity.value,
            "incident_id": result.incident.id,
            "created_new_incident": result.created_new,
            "correlation_reason": result.match_reason,
            "correlation_score": round(result.score, 2),
        })

    return DemoGenerateResponse(
        scenario=scenario,
        alerts_created=len(detail),
        incidents_touched=sorted(incidents_touched),
        new_incidents_created=new_incidents,
        detail=detail,
    )


# ── POST /alerts ──────────────────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new alert",
)
@limiter.limit(ALERT_INGEST_LIMIT)
async def ingest_alert(
    request: Request,
    payload: AlertCreate,
    run_async: bool = Query(default=False, alias="async"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
):
    alert = await create_alert(db, payload, org_id=ctx.org_id)
    alert_read = AlertRead.model_validate(alert)

    await ws_manager.emit_alert_created(ctx.org_id, alert_read.model_dump())
    logger.info(
        "[ingest_alert] alert_id=%d org_id=%d mode=%s",
        alert.id, ctx.org_id, "async" if run_async else "sync",
    )

    if run_async:
        task = process_alert.apply_async(args=[alert.id], queue="alerts")
        return AlertIngestAsyncResponse(
            alert=alert_read,
            task_id=task.id,
            message="Alert saved. Correlation is running in the background.",
        )

    result = await correlation_engine.correlate(db, alert)
    return AlertIngestResponse(
        alert=alert_read,
        incident_id=result.incident.id,
        incident_title=result.incident.title,
        incident_severity=result.incident.severity.value,
        incident_status=result.incident.status.value,
        created_new_incident=result.created_new,
        correlation_reason=result.match_reason,
        correlation_score=round(result.score, 2),
        correlation_signals=result.signals,
    )


# ── GET /alerts ───────────────────────────────────────────────────────────────

@router.get("", response_model=AlertListResponse, summary="List alerts with optional filters")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: AlertStatus | None = Query(default=None),
    source: str | None = Query(default=None),
    service_name: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    since: datetime | None = Query(default=None, description="ISO-8601 lower-bound"),
) -> AlertListResponse:
    total, items = await list_alerts(
        db,
        org_id=ctx.org_id,
        skip=skip,
        limit=limit,
        status=status,
        source=source,
        service_name=service_name,
        environment=environment,
        since=since,
    )
    return AlertListResponse(
        total=total,
        items=[AlertRead.model_validate(a) for a in items],
    )


# ── GET /alerts/{id} ──────────────────────────────────────────────────────────

@router.get("/{alert_id}", response_model=AlertRead, summary="Fetch a single alert by ID")
async def get_alert_by_id(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> AlertRead:
    alert = await get_alert(db, alert_id)
    if not alert or alert.organization_id != ctx.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    return AlertRead.model_validate(alert)
