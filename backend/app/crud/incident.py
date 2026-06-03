"""
CRUD operations for Incident and IncidentEvent.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentEvent, IncidentStatus
from app.schemas.incident import IncidentCreate, IncidentUpdate


async def create_incident(
    db: AsyncSession,
    payload: IncidentCreate,
    org_id: int | None = None,
) -> Incident:
    incident = Incident(**payload.model_dump(), organization_id=org_id)
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident


async def get_incident(db: AsyncSession, incident_id: int) -> Incident | None:
    result = await db.execute(
        select(Incident)
        .options(selectinload(Incident.events))
        .where(Incident.id == incident_id)
    )
    return result.scalar_one_or_none()


async def list_incidents(
    db: AsyncSession,
    *,
    org_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    status: IncidentStatus | None = None,
) -> tuple[int, list[Incident]]:
    base = select(Incident)
    if org_id is not None:
        base = base.where(Incident.organization_id == org_id)
    if status:
        base = base.where(Incident.status == status)

    count_query = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_query)).scalar_one()

    query = (
        base.options(selectinload(Incident.events))
        .order_by(Incident.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(query)).scalars().all()

    return total, list(rows)


async def update_incident(
    db: AsyncSession, incident: Incident, payload: IncidentUpdate
) -> Incident:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)
    await db.commit()
    await db.refresh(incident)
    return incident


async def add_event(
    db: AsyncSession,
    *,
    incident_id: int,
    event_type: str,
    message: str,
    alert_id: int | None = None,
) -> IncidentEvent:
    event = IncidentEvent(
        incident_id=incident_id,
        alert_id=alert_id,
        event_type=event_type,
        message=message,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
