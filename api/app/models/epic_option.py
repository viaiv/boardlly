from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EpicOption(Base):
    """
    Armazena épicos como labels do GitHub (ex: "epic:setup-config").
    Metadados adicionais (descrição, ordem) são gerenciados apenas no Tactyo.
    Labels são criadas/atualizadas em todos repositórios vinculados ao projeto.
    """
    __tablename__ = "epic_option"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("github_project.id", ondelete="CASCADE"), nullable=False
    )

    # Identificadores do GitHub
    option_id: Mapped[str | None] = mapped_column(String(length=255), nullable=True)  # Node ID do GitHub (Single Select - deprecated)
    option_name: Mapped[str] = mapped_column(String(length=255), nullable=False)  # Nome amigável do épico
    label_name: Mapped[str] = mapped_column(String(length=255), nullable=False, unique=False)  # Nome da label no GitHub (ex: "epic:setup-config")

    # Metadados do épico
    color: Mapped[str | None] = mapped_column(String(length=50), nullable=True)  # Cor hex ou nome
    description: Mapped[str | None] = mapped_column(String(length=500), nullable=True)  # Descrição

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project = relationship("GithubProject", back_populates="epic_options")

    __table_args__ = (
        UniqueConstraint("project_id", "label_name", name="uq_epic_option_project_label"),
        {
            "sqlite_autoincrement": True,
        },
    )
