"""
Modelo de Change Request (Solicitação de Mudança).

Permite que usuários (role editor+) criem solicitações que são revisadas por PMs.
Após aprovação, cria automaticamente uma Issue no GitHub e adiciona ao Project.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChangeRequest(Base):
    """
    Solicitação de mudança ou melhoria proposta por um membro da equipe.

    Workflow:
    1. Editor cria request (status=pending)
    2. PM revisa e aprova/rejeita
    3. Se aprovado, cria Issue no GitHub (status=converted)
    4. Issue sincroniza como ProjectItem via webhook/sync
    """

    __tablename__ = "change_request"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )

    # Conteúdo da solicitação
    title: Mapped[str] = mapped_column(String(length=500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classificação
    priority: Mapped[str] = mapped_column(
        String(length=50), nullable=False, default="medium"
    )  # low/medium/high/urgent
    request_type: Mapped[str | None] = mapped_column(
        String(length=50), nullable=True
    )  # feature/bug/tech_debt/docs

    # Workflow de aprovação
    status: Mapped[str] = mapped_column(
        String(length=50), nullable=False, default="pending"
    )  # pending/approved/rejected/converted
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Conversão em Issue
    github_issue_node_id: Mapped[str | None] = mapped_column(
        String(length=255), nullable=True
    )
    github_issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    github_issue_url: Mapped[str | None] = mapped_column(String(length=500), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadados sugeridos (para pré-preencher Issue)
    suggested_epic: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    suggested_iteration: Mapped[str | None] = mapped_column(
        String(length=255), nullable=True
    )
    suggested_estimate: Mapped[Optional[float]] = mapped_column(
        Numeric(scale=2), nullable=True
    )

    # Anexos (JSON array de URLs/paths)
    attachments: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    account = relationship("Account", back_populates="change_requests")
    creator = relationship("AppUser", foreign_keys=[created_by], back_populates="created_requests")
    reviewer = relationship(
        "AppUser", foreign_keys=[reviewed_by], back_populates="reviewed_requests"
    )

    __table_args__ = ({"sqlite_autoincrement": True},)
