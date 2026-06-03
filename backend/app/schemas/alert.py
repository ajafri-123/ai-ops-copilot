"""
Pydantic schemas for Alert – used for request validation and response serialisation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert import AlertSeverity, AlertStatus


# ─────────────────────────────────────────────
# Shared base
# ─────────────────────────────────────────────

class AlertBase(BaseModel):
    source: str = Field(..., max_length=64, examples=["aws", "datadog", "sentry"])
    severity: AlertSeverity
    title: str = Field(..., max_length=512)
    description: str | None = None
    service_name: str = Field(..., max_length=128)
    environment: str = Field(default="production", max_length=64)
    timestamp: datetime
    raw_payload: dict[str, Any] | None = None
    status: AlertStatus = AlertStatus.open


# ─────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────

class AlertCreate(AlertBase):
    """Payload accepted by POST /alerts."""
    pass


class AlertUpdate(BaseModel):
    """Partial update for status transitions."""
    status: AlertStatus | None = None
    description: str | None = None


# ─────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────

class AlertRead(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class AlertListResponse(BaseModel):
    total: int
    items: list[AlertRead]
