"""
Pydantic schemas for Alert – used for request validation and response serialisation.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.alert import AlertSeverity, AlertStatus

# Ingestion guards
MAX_RAW_PAYLOAD_BYTES = 32_768
MAX_TIMESTAMP_FUTURE = timedelta(minutes=5)
MAX_TIMESTAMP_AGE = timedelta(days=90)


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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    raw_payload: dict[str, Any] | None = None
    status: AlertStatus = AlertStatus.open


# ─────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────

class AlertCreate(AlertBase):
    """Payload accepted by POST /alerts (validation on ingestion only)."""

    @field_validator("timestamp")
    @classmethod
    def _timestamp_in_sane_window(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        if v > now + MAX_TIMESTAMP_FUTURE:
            raise ValueError("timestamp must not be in the future")
        if v < now - MAX_TIMESTAMP_AGE:
            raise ValueError(f"timestamp must be within the last {MAX_TIMESTAMP_AGE.days} days")
        return v

    @field_validator("raw_payload")
    @classmethod
    def _raw_payload_size_cap(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None and len(json.dumps(v, default=str)) > MAX_RAW_PAYLOAD_BYTES:
            raise ValueError(f"raw_payload must be under {MAX_RAW_PAYLOAD_BYTES} bytes")
        return v

    @field_validator("source", "service_name", "environment")
    @classmethod
    def _strip_identifiers(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


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
