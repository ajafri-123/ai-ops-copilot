import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class IntegrationProvider(str, enum.Enum):
    aws_cloudwatch = "aws_cloudwatch"
    datadog = "datadog"
    sentry = "sentry"
    github_actions = "github_actions"
    kubernetes = "kubernetes"
    slack = "slack"


class IntegrationStatus(str, enum.Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)

    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, name="integration_status"),
        nullable=False,
        default=IntegrationStatus.disconnected,
    )

    last_sync: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Stores mock config: webhook_url, api_key_hint, region, etc.
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

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
        return f"<Integration id={self.id} provider={self.provider} status={self.status}>"
