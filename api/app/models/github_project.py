from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GithubProject(Base):
    __tablename__ = "github_project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    owner_login: Mapped[str] = mapped_column(String(length=255), nullable=False)
    project_number: Mapped[int] = mapped_column(Integer, nullable=False)
    project_node_id: Mapped[str] = mapped_column(String(length=255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    field_mappings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status_columns: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    account = relationship("Account", back_populates="projects")
    items = relationship("ProjectItem", back_populates="project", cascade="all, delete-orphan")
    fields = relationship(
        "GithubProjectField", back_populates="project", cascade="all, delete-orphan"
    )
    epic_options = relationship(
        "EpicOption", back_populates="project", cascade="all, delete-orphan"
    )
    repositories = relationship(
        "ProjectRepository", back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "owner_login",
            "project_number",
            name="uq_github_project_account_owner_number",
        ),
        {
            "sqlite_autoincrement": True,
        },
    )
