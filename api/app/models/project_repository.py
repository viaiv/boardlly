from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectRepository(Base):
    """
    Vincula um projeto do GitHub Projects a um ou mais repositórios.
    Necessário para gerenciar labels (épicos) via REST API do GitHub.
    """
    __tablename__ = "project_repository"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("github_project.id", ondelete="CASCADE"), nullable=False
    )

    # Identificadores do repositório
    owner: Mapped[str] = mapped_column(String(length=255), nullable=False)  # ex: "tactyo"
    repo_name: Mapped[str] = mapped_column(String(length=255), nullable=False)  # ex: "api"
    repo_node_id: Mapped[str | None] = mapped_column(String(length=255), nullable=True)  # GitHub node ID

    # Configurações
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Repositório principal

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project = relationship("GithubProject", back_populates="repositories")

    __table_args__ = (
        UniqueConstraint("project_id", "owner", "repo_name", name="uq_project_repository"),
        {
            "sqlite_autoincrement": True,
        },
    )
