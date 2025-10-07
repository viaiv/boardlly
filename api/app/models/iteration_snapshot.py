from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IterationSnapshot(Base):
    __tablename__ = "iteration_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(length=255), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("github_project.id", ondelete="CASCADE"), nullable=False)
    option_id: Mapped[str] = mapped_column(String(length=255), nullable=False)
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("GithubProject")

    __table_args__ = (
        {
            "sqlite_autoincrement": True,
        },
    )
