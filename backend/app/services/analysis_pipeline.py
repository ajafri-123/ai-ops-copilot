"""
Analysis Pipeline
=================
Pure async function that runs the full AI root-cause analysis workflow
and persists results.  Shared between:

  • FastAPI endpoint  (app/api/v1/analysis.py)  – called directly
  • Celery task       (app/workers/tasks.py)     – called via asyncio.run()

Having this logic in one place ensures the two paths stay in sync.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ws_manager import ws_manager
from app.crud.incident import add_event, get_incident
from app.models.alert import Alert
from app.models.incident import EventType
from app.schemas.analysis import AnalyzeResponse
from app.schemas.incident import IncidentRead
from app.services.ai_service import IncidentContext, ai_service

logger = logging.getLogger(__name__)


async def run_analysis_pipeline(
    incident_id: int,
    db: AsyncSession,
    org_id: int | None = None,
) -> AnalyzeResponse:
    """
    1. Fetch incident + correlated alerts from the database.
    2. Build IncidentContext.
    3. Call the AI service (OpenAI or deterministic mock).
    4. Persist root_cause, summary, remediation_steps to the Incident row.
    5. Record an ai_analysis IncidentEvent.
    6. Broadcast incident.updated over WebSocket.
    7. Return a typed AnalyzeResponse.

    Raises ValueError if the incident does not exist or does not belong to
    `org_id` (when provided — defense in depth on top of the API-layer check).
    """
    # ── 1. Fetch incident ─────────────────────────────────────
    incident = await get_incident(db, incident_id)
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")
    if org_id is not None and incident.organization_id != org_id:
        raise ValueError(f"Incident {incident_id} not found")

    # ── 2. Collect alerts referenced by incident events ───────
    alert_ids: list[int] = []
    for ev in incident.events:
        if ev.alert_id is not None and ev.alert_id not in alert_ids:
            alert_ids.append(ev.alert_id)

    alerts: list[Alert] = []
    if alert_ids:
        result = await db.execute(select(Alert).where(Alert.id.in_(alert_ids)))
        alerts = list(result.scalars().all())

    alert_dicts = [
        {
            "id": a.id,
            "source": a.source,
            "severity": a.severity.value,
            "title": a.title,
            "description": a.description,
            "service_name": a.service_name,
            "environment": a.environment,
            "timestamp": a.timestamp.isoformat(),
            "status": a.status.value,
        }
        for a in alerts
    ]

    event_dicts = [
        {
            "id": e.id,
            "event_type": e.event_type.value,
            "message": e.message,
            "alert_id": e.alert_id,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in sorted(incident.events, key=lambda x: x.timestamp)
    ]

    # ── 3. Build context ──────────────────────────────────────
    ctx = IncidentContext(
        incident_id=incident.id,
        title=incident.title,
        severity=incident.severity.value,
        status=incident.status.value,
        affected_services=list(incident.affected_services or []),
        existing_summary=incident.summary,
        alerts=alert_dicts,
        events=event_dicts,
    )

    logger.info(
        "[analysis_pipeline] incident=#%d alerts=%d events=%d provider=auto",
        incident_id, len(alert_dicts), len(event_dicts),
    )

    # ── 4. Run AI analysis ────────────────────────────────────
    rca = await ai_service.analyze_incident(ctx)

    # ── 5. Persist results ────────────────────────────────────
    incident.summary = rca.summary
    incident.root_cause = rca.root_cause
    incident.remediation_steps = rca.remediation_steps
    await db.flush()
    await db.commit()
    await db.refresh(incident)

    # ── 6. Record timeline event ──────────────────────────────
    # Build a concise timeline message; the full root_cause is stored on the
    # Incident row itself so nothing is lost — we just keep events readable.
    root_cause_preview = rca.root_cause[:180] + "…" if len(rca.root_cause) > 180 else rca.root_cause
    await add_event(
        db,
        incident_id=incident_id,
        event_type=EventType.ai_analysis,
        message=(
            f"AI analysis completed by {rca.provider}/{rca.model}. "
            f"Confidence: {rca.confidence:.0%}. "
            f"Risk: {rca.risk_level.upper()}. "
            f"Root cause: {root_cause_preview}"
        ),
    )

    # ── 7. Broadcast WS ──────────────────────────────────────
    refreshed = await get_incident(db, incident_id)
    inc_dict = IncidentRead.model_validate(refreshed).model_dump()
    await ws_manager.emit_incident_updated(
        org_id=refreshed.organization_id,
        incident=inc_dict,
        changed_fields=["summary", "root_cause", "remediation_steps"],
    )

    logger.info(
        "[analysis_pipeline] done incident=#%d provider=%s confidence=%.2f",
        incident_id, rca.provider, rca.confidence,
    )

    return AnalyzeResponse(
        incident_id=incident_id,
        analysis=rca,
        alerts_analyzed=len(alert_dicts),
        events_analyzed=len(event_dicts),
    )
