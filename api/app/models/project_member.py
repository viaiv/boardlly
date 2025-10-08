import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectMember(Base):
    """
    Permissões granulares por projeto.

    Permite que um usuário tenha diferentes níveis de acesso em diferentes projetos.
    """
    __tablename__ = "project_member"
    __table_args__ = (
        CheckConstraint(
            "role = ANY (ARRAY['viewer','editor','pm','admin'])",
            name="ck_project_member_role_valid",
        ),
        Index("ix_project_member_user_project", "user_id", "project_id", unique=True),
        Index("ix_project_member_project", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False
    )

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("github_project.id", ondelete="CASCADE"),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(length=20),
        nullable=False,
        default="viewer"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user: Mapped["AppUser"] = relationship(
        "AppUser",
        foreign_keys=[user_id],
    )

    project: Mapped["GithubProject"] = relationship(
        "GithubProject",
        foreign_keys=[project_id],
    )
