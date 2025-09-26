from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GithubProjectField(Base):
    __tablename__ = "github_project_field"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("github_project.id", ondelete="CASCADE"), nullable=False)
    field_id: Mapped[str] = mapped_column(String(length=255), nullable=False)
    field_name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    field_type: Mapped[str] = mapped_column(String(length=50), nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("GithubProject", back_populates="fields")

    __table_args__ = (
        UniqueConstraint("project_id", "field_id", name="uq_github_project_field_project_field"),
        {
            "sqlite_autoincrement": True,
        },
    )

