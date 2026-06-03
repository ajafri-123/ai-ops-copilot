"""
Integration endpoints
  GET    /api/v1/integrations           – list all integrations for the org
  POST   /api/v1/integrations           – create an integration record
  PATCH  /api/v1/integrations/{id}      – update status / config (connect / disconnect)
  POST   /api/v1/integrations/{id}/test-alert  – fire a realistic alert through the correlation engine
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import AuthContext, get_auth
from app.core.ws_manager import ws_manager
from app.crud.alert import create_alert
from app.crud.integration import (
    create_integration,
    get_integration,
    list_integrations,
    touch_last_sync,
    update_integration,
)
from app.models.integration import IntegrationStatus
from app.schemas.alert import AlertCreate, AlertRead
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationRead,
    IntegrationUpdate,
    TestAlertResponse,
)
from app.services.correlation_engine import correlation_engine
from app.services.integration_alerts import pick_test_alert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("", response_model=list[IntegrationRead], summary="List integrations for the org")
async def get_integrations(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> list[IntegrationRead]:
    rows = await list_integrations(db, org_id=ctx.org_id)
    return [IntegrationRead.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=IntegrationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an integration record",
)
async def post_integration(
    payload: IntegrationCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> IntegrationRead:
    integration = await create_integration(db, payload, org_id=ctx.org_id)
    return IntegrationRead.model_validate(integration)


@router.patch(
    "/{integration_id}",
    response_model=IntegrationRead,
    summary="Update integration (connect / disconnect / rename)",
)
async def patch_integration(
    integration_id: int,
    payload: IntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> IntegrationRead:
    integration = await get_integration(db, integration_id)
    if not integration or integration.organization_id != ctx.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_id} not found",
        )
    updated = await update_integration(db, integration, payload)
    return IntegrationRead.model_validate(updated)


@router.post(
    "/{integration_id}/test-alert",
    response_model=TestAlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fire a realistic test alert from this integration through the correlation engine",
)
async def test_alert(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> TestAlertResponse:
    integration = await get_integration(db, integration_id)
    if not integration or integration.organization_id != ctx.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_id} not found",
        )
    if integration.status != IntegrationStatus.connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration must be connected before sending a test alert",
        )

    alert_data = pick_test_alert(integration.provider)
    alert = await create_alert(db, AlertCreate(**alert_data), org_id=ctx.org_id)

    alert_read = AlertRead.model_validate(alert)
    await ws_manager.emit_alert_created(alert_read.model_dump())

    result = await correlation_engine.correlate(db, alert)

    await touch_last_sync(db, integration)

    logger.info(
        "[test-alert] integration_id=%d provider=%s alert_id=%d incident_id=%d",
        integration_id,
        integration.provider,
        alert.id,
        result.incident.id,
    )

    return TestAlertResponse(
        integration_id=integration_id,
        provider=integration.provider.value,
        alert_id=alert.id,
        alert_title=alert.title,
        alert_severity=alert.severity.value,
        incident_id=result.incident.id,
        incident_title=result.incident.title,
        created_new_incident=result.created_new,
        correlation_score=round(result.score, 2),
    )
