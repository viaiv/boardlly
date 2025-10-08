"""add change_request table

Revision ID: 20250208_01
Revises: 20250207_02
Create Date: 2025-02-08 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "20250208_01"
down_revision = "20250207_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Cria tabela change_request para gerenciar solicitações de mudança.

    Fluxo:
    1. Editor cria request (status=pending)
    2. PM aprova/rejeita
    3. Se aprovado, cria Issue automaticamente no GitHub
    """
    op.create_table(
        "change_request",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Conteúdo
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("impact", sa.Text, nullable=True),
        # Classificação
        sa.Column("priority", sa.String(50), nullable=False, server_default="medium"),
        sa.Column("request_type", sa.String(50), nullable=True),
        # Workflow
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column(
            "reviewed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        # Conversão em Issue
        sa.Column("github_issue_node_id", sa.String(255), nullable=True),
        sa.Column("github_issue_number", sa.Integer, nullable=True),
        sa.Column("github_issue_url", sa.String(500), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        # Metadados sugeridos
        sa.Column("suggested_epic", sa.String(255), nullable=True),
        sa.Column("suggested_iteration", sa.String(255), nullable=True),
        sa.Column("suggested_estimate", sa.Numeric(scale=2), nullable=True),
        # Anexos
        sa.Column("attachments", sa.JSON, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Índices para performance
    op.create_index(
        "ix_change_request_account_id", "change_request", ["account_id"]
    )
    op.create_index("ix_change_request_status", "change_request", ["status"])
    op.create_index(
        "ix_change_request_created_by", "change_request", ["created_by"]
    )
    op.create_index(
        "ix_change_request_priority", "change_request", ["priority"]
    )

    # Índice composto para queries comuns (lista pendentes por conta)
    op.create_index(
        "ix_change_request_account_status",
        "change_request",
        ["account_id", "status"],
    )


def downgrade() -> None:
    """Remove tabela change_request e índices"""
    op.drop_index("ix_change_request_account_status", table_name="change_request")
    op.drop_index("ix_change_request_priority", table_name="change_request")
    op.drop_index("ix_change_request_created_by", table_name="change_request")
    op.drop_index("ix_change_request_status", table_name="change_request")
    op.drop_index("ix_change_request_account_id", table_name="change_request")
    op.drop_table("change_request")
