"""
Incident endpoints
  GET    /api/v1/incidents         – list incidents (filterable, paginated)
  GET    /api/v1/incidents/{id}    – get single incident with events
  PATCH  /api/v1/incidents/{id}    – update status / root cause / remediation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import AuthContext, get_auth
from app.core.ws_manager import ws_manager
from app.crud.incident import add_event, get_incident, list_incidents, update_incident
from app.models.incident import EventType, IncidentStatus
from app.schemas.incident import IncidentListResponse, IncidentRead, IncidentUpdate

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentListResponse, summary="List incidents")
async def get_incidents(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: IncidentStatus | None = Query(default=None),
) -> IncidentListResponse:
    total, items = await list_incidents(
        db, org_id=ctx.org_id, skip=skip, limit=limit, status=status
    )
    return IncidentListResponse(
        total=total,
        items=[IncidentRead.model_validate(i) for i in items],
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentRead,
    summary="Fetch a single incident with full event timeline",
)
async def get_incident_by_id(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> IncidentRead:
    incident = await get_incident(db, incident_id)
    if not incident or incident.organization_id != ctx.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return IncidentRead.model_validate(incident)


@router.patch(
    "/{incident_id}",
    response_model=IncidentRead,
    summary="Update incident status, root cause, remediation steps, etc.",
)
async def patch_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> IncidentRead:
    incident = await get_incident(db, incident_id)
    if not incident or incident.organization_id != ctx.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    old_status = incident.status
    old_severity = incident.severity
    changed_fields: list[str] = []

    updated = await update_incident(db, incident, payload)

    if payload.status and payload.status != old_status:
        changed_fields.append("status")
        await add_event(
            db,
            incident_id=incident_id,
            event_type=EventType.status_changed,
            message=f"Status changed from {old_status} → {payload.status}",
        )

    if payload.root_cause:
        changed_fields.append("root_cause")
        await add_event(
            db,
            incident_id=incident_id,
            event_type=EventType.ai_analysis,
            message=f"Root cause updated: {payload.root_cause[:200]}",
        )

    if payload.severity and payload.severity != old_severity:
        changed_fields.append("severity")

    refreshed = await get_incident(db, incident_id)
    result = IncidentRead.model_validate(refreshed)

    if changed_fields:
        await ws_manager.emit_incident_updated(
            incident=result.model_dump(),
            changed_fields=changed_fields,
        )

    return result
