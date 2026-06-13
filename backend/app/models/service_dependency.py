"""
ServiceDependency model – directed graph edges describing how services depend on each other.
Used by the AI layer to infer blast radius when a service degrades.
"""

import enum

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RelationshipType(str, enum.Enum):
    depends_on = "depends_on"       # hard dependency – upstream failure = downstream failure
    calls = "calls"                 # RPC / HTTP call (soft)
    reads_from = "reads_from"       # DB / cache reads
    writes_to = "writes_to"         # DB / queue writes
    publishes_to = "publishes_to"   # event streaming
    subscribes_to = "subscribes_to" # event streaming


class ServiceDependency(Base):
    __tablename__ = "service_dependencies"

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "service_name", "depends_on", "relationship_type",
            name="uq_service_dep",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Tenant scope — service topology is sensitive infrastructure metadata and
    # must never leak (or influence correlation) across organizations.
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )

    service_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    depends_on: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    relationship_type: Mapped[RelationshipType] = mapped_column(
        String(32), nullable=False, default=RelationshipType.depends_on
    )

    def __repr__(self) -> str:
        return (
            f"<ServiceDependency {self.service_name} --{self.relationship_type}--> {self.depends_on}>"
        )
