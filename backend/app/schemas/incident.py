"""
Pydantic schemas for Incident and IncidentEvent.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.incident import EventType, IncidentSeverity, IncidentStatus


# ─────────────────────────────────────────────
# IncidentEvent schemas
# ─────────────────────────────────────────────

class IncidentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    alert_id: int | None
    event_type: EventType
    message: str
    timestamp: datetime


# ─────────────────────────────────────────────
# Incident schemas
# ─────────────────────────────────────────────

class IncidentBase(BaseModel):
    title: str = Field(..., max_length=512)
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.open
    affected_services: list[str] | None = None
    summary: str | None = None
    root_cause: str | None = None
    remediation_steps: list[str] | None = None


class IncidentCreate(IncidentBase):
    """Internal schema – incidents are usually created by the correlation engine."""
    pass


class IncidentUpdate(BaseModel):
    """PATCH payload – all fields optional."""
    title: str | None = Field(default=None, max_length=512)
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    affected_services: list[str] | None = None
    summary: str | None = None
    root_cause: str | None = None
    remediation_steps: list[str] | None = None


class IncidentRead(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    events: list[IncidentEventRead] = []


class IncidentListResponse(BaseModel):
    total: int
    items: list[IncidentRead]
