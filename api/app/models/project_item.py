from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectItem(Base):
    __tablename__ = "project_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("github_project.id", ondelete="CASCADE"), nullable=False
    )
    item_node_id: Mapped[str] = mapped_column(String(length=255), unique=True, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(length=50), nullable=True)
    content_node_id: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(length=500), nullable=True)
    status: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    assignees: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    iteration: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    iteration_id: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    iteration_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    iteration_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimate: Mapped[Optional[float]] = mapped_column(Numeric(scale=2), nullable=True)
    url: Mapped[str | None] = mapped_column(String(length=500), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    field_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remote_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_local_edit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_local_edit_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )

    account = relationship("Account")
    project = relationship("GithubProject", back_populates="items")
    last_editor = relationship("AppUser", foreign_keys=[last_local_edit_by])

    __table_args__ = (
        {
            "sqlite_autoincrement": True,
        },
    )
