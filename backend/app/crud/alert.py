"""
CRUD operations for Alert.
All functions are async and accept an AsyncSession.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus
from app.schemas.alert import AlertCreate, AlertUpdate


async def create_alert(
    db: AsyncSession,
    payload: AlertCreate,
    org_id: int | None = None,
) -> Alert:
    alert = Alert(**payload.model_dump(), organization_id=org_id)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def get_alert(db: AsyncSession, alert_id: int) -> Alert | None:
    return (
        await db.execute(select(Alert).where(Alert.id == alert_id))
    ).scalar_one_or_none()


async def list_alerts(
    db: AsyncSession,
    *,
    org_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    status: AlertStatus | None = None,
    source: str | None = None,
    service_name: str | None = None,
    environment: str | None = None,
    since: datetime | None = None,
) -> tuple[int, list[Alert]]:
    query = select(Alert)

    if org_id is not None:
        query = query.where(Alert.organization_id == org_id)
    if status:
        query = query.where(Alert.status == status)
    if source:
        query = query.where(Alert.source == source)
    if service_name:
        query = query.where(Alert.service_name == service_name)
    if environment:
        query = query.where(Alert.environment == environment)
    if since:
        query = query.where(Alert.timestamp >= since)

    count_query = select(func.count()).select_from(query.subquery())
    total: int = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Alert.timestamp.desc()).offset(skip).limit(limit)
    rows = (await db.execute(query)).scalars().all()

    return total, list(rows)


async def update_alert(db: AsyncSession, alert: Alert, payload: AlertUpdate) -> Alert:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    await db.commit()
    await db.refresh(alert)
    return alert
