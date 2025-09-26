from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Account(Base):
    __tablename__ = "account"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list["AppUser"]] = relationship(
        "AppUser",
        back_populates="account",
        cascade="all, delete-orphan",
        foreign_keys="AppUser.account_id",
    )
    owner_user: Mapped[Optional["AppUser"]] = relationship(
        "AppUser", foreign_keys=[owner_user_id], uselist=False, post_update=True
    )
    github_credentials: Mapped[Optional["AccountGithubCredentials"]] = relationship(
        "AccountGithubCredentials", back_populates="account", uselist=False
    )
    projects: Mapped[list["GithubProject"]] = relationship(
        "GithubProject", back_populates="account", cascade="all, delete-orphan"
    )
