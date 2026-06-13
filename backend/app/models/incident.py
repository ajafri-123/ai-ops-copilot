"""
Incident model – a correlated group of alerts that represent a single operational event.
IncidentEvent is the audit trail of everything that happens during the incident lifecycle.
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text  # noqa: F401
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

# Postgres-native types with SQLite fallbacks so the test suite
# (sqlite+aiosqlite) can create the schema.
JSONBType = JSONB().with_variant(JSON(), "sqlite")
StringArrayType = ARRAY(String).with_variant(JSON(), "sqlite")


class IncidentSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class IncidentStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    identified = "identified"   # root cause known
    monitoring = "monitoring"   # fix deployed, watching
    resolved = "resolved"
    closed = "closed"


class EventType(str, enum.Enum):
    alert_added = "alert_added"
    status_changed = "status_changed"
    comment = "comment"
    ai_analysis = "ai_analysis"
    remediation_applied = "remediation_applied"
    escalated = "escalated"
    resolved = "resolved"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)

    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, name="incident_severity"), nullable=False, index=True
    )

    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"),
        nullable=False,
        default=IncidentStatus.open,
        index=True,
    )

    # Environment this incident belongs to (from its triggering alert).
    # Used as a hard correlation guard: alerts never correlate across environments.
    environment: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )

    # List of service names involved (stored as Postgres ARRAY for easy querying)
    affected_services: Mapped[list[str] | None] = mapped_column(
        StringArrayType, nullable=True
    )

    # Human-readable one-paragraph incident summary
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI-generated root cause (populated by AI service)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI-generated remediation steps stored as JSON array of strings
    remediation_steps: Mapped[list | None] = mapped_column(JSONBType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    events: Mapped[list["IncidentEvent"]] = relationship(
        "IncidentEvent", back_populates="incident", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Incident id={self.id} status={self.status} title={self.title!r}>"


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    incident_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Optional – which alert triggered this event
    alert_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type"), nullable=False, index=True
    )

    message: Mapped[str] = mapped_column(Text, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="events")

    def __repr__(self) -> str:
        return f"<IncidentEvent id={self.id} type={self.event_type} incident={self.incident_id}>"
