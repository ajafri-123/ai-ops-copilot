"""
Alert model – represents a single raw infrastructure alert ingested from any source
(AWS CloudWatch, Datadog, Sentry, GitHub Actions, Kubernetes, etc.)
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

# Postgres JSONB with a SQLite fallback so the test suite can create the schema
JSONBType = JSONB().with_variant(JSON(), "sqlite")


class AlertSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class AlertStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"
    suppressed = "suppressed"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Where the alert came from (e.g. "aws", "datadog", "sentry")
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Logical service that fired the alert
    service_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # e.g. production, staging, dev
    environment: Mapped[str] = mapped_column(
        String(64), nullable=False, default="production", index=True
    )

    # When the alert actually fired (not when we received it)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Full original payload stored as JSONB for forensics / AI ingestion
    raw_payload: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)

    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"),
        nullable=False,
        default=AlertStatus.open,
        index=True,
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Alert id={self.id} source={self.source} severity={self.severity} title={self.title!r}>"
