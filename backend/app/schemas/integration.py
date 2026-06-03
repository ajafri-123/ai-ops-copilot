from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.integration import IntegrationProvider, IntegrationStatus


class IntegrationCreate(BaseModel):
    provider: IntegrationProvider
    name: str | None = None


class IntegrationUpdate(BaseModel):
    status: IntegrationStatus | None = None
    name: str | None = None
    config: dict[str, Any] | None = None


class IntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    provider: IntegrationProvider
    name: str
    status: IntegrationStatus
    last_sync: datetime | None
    config: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class TestAlertResponse(BaseModel):
    integration_id: int
    provider: str
    alert_id: int
    alert_title: str
    alert_severity: str
    incident_id: int
    incident_title: str
    created_new_incident: bool
    correlation_score: float
