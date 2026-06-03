import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MemberRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "org_id", name="uq_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="member_role"), nullable=False, default=MemberRole.member
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="memberships")  # noqa: F821
    organization: Mapped["Organization"] = relationship("Organization")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Membership user={self.user_id} org={self.org_id} role={self.role}>"
