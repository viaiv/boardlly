"""add project_invite table for invitation system

Revision ID: 20251008_02
Revises: 20251008_01
Create Date: 2025-10-08 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251008_02"
down_revision = "20251008_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create project_invite table
    op.create_table(
        "project_invite",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("invited_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role = ANY (ARRAY['viewer','editor','pm','admin'])",
            name="ck_project_invite_role_valid",
        ),
        sa.CheckConstraint(
            "status = ANY (ARRAY['pending','accepted','rejected','cancelled'])",
            name="ck_project_invite_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["github_project.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_user_id"],
            ["app_user.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["app_user.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_project_invite_user_project",
        "project_invite",
        ["invited_user_id", "project_id"],
        unique=True,
    )
    op.create_index(
        "ix_project_invite_status",
        "project_invite",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_invite_status", table_name="project_invite")
    op.drop_index("ix_project_invite_user_project", table_name="project_invite")
    op.drop_table("project_invite")
