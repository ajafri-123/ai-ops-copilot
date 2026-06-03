"""
Import all models here so that SQLAlchemy's metadata registry is populated
before create_all / Alembic autogenerate runs.
"""

from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.membership import Membership, MemberRole  # noqa: F401
from app.models.alert import Alert, AlertSeverity, AlertStatus  # noqa: F401
from app.models.incident import Incident, IncidentEvent, IncidentSeverity, IncidentStatus, EventType  # noqa: F401
from app.models.service_dependency import ServiceDependency, RelationshipType  # noqa: F401
from app.models.integration import Integration, IntegrationProvider, IntegrationStatus  # noqa: F401

__all__ = [
    "Organization",
    "User",
    "Membership",
    "MemberRole",
    "Alert",
    "AlertSeverity",
    "AlertStatus",
    "Incident",
    "IncidentEvent",
    "IncidentSeverity",
    "IncidentStatus",
    "EventType",
    "ServiceDependency",
    "RelationshipType",
    "Integration",
    "IntegrationProvider",
    "IntegrationStatus",
]
