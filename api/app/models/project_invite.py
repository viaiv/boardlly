import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectInvite(Base):
    """
    Convites para adicionar membros a projetos.

    Um convite é criado por admin/owner e pode ser aceito ou rejeitado pelo usuário convidado.
    """
    __tablename__ = "project_invite"
    __table_args__ = (
        CheckConstraint(
            "role = ANY (ARRAY['viewer','editor','pm','admin'])",
            name="ck_project_invite_role_valid",
        ),
        CheckConstraint(
            "status = ANY (ARRAY['pending','accepted','rejected','cancelled'])",
            name="ck_project_invite_status_valid",
        ),
        Index("ix_project_invite_user_project", "invited_user_id", "project_id", unique=True),
        Index("ix_project_invite_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("github_project.id", ondelete="CASCADE"),
        nullable=False
    )

    invited_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False
    )

    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(length=20),
        nullable=False,
        default="viewer"
    )

    status: Mapped[str] = mapped_column(
        String(length=20),
        nullable=False,
        default="pending"
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
    project: Mapped["GithubProject"] = relationship(
        "GithubProject",
        foreign_keys=[project_id],
    )

    invited_user: Mapped["AppUser"] = relationship(
        "AppUser",
        foreign_keys=[invited_user_id],
    )

    invited_by: Mapped["AppUser"] = relationship(
        "AppUser",
        foreign_keys=[invited_by_user_id],
    )
