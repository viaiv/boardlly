import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint(
            "role = ANY (ARRAY['viewer','editor','pm','admin','owner'])",
            name="ck_app_user_role_valid",
        ),
        Index("ix_app_user_email", "email", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id", ondelete="CASCADE"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(length=320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(length=255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    role: Mapped[str] = mapped_column(String(length=20), nullable=False, default="viewer")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    email_verification_token: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    email_verification_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="users",
        foreign_keys=[account_id],
    )
    created_requests: Mapped[list["ChangeRequest"]] = relationship(
        "ChangeRequest",
        back_populates="creator",
        foreign_keys="ChangeRequest.created_by",
        cascade="all, delete-orphan",
    )
    reviewed_requests: Mapped[list["ChangeRequest"]] = relationship(
        "ChangeRequest",
        back_populates="reviewer",
        foreign_keys="ChangeRequest.reviewed_by",
    )
