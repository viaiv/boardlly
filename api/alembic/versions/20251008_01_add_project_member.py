"""add project_member table for granular permissions

Revision ID: 20251008_01
Revises: 20250208_01
Create Date: 2025-10-08 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251008_01"
down_revision = "20250208_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create project_member table
    op.create_table(
        "project_member",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
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
            name="ck_project_member_role_valid",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_user.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["github_project.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_project_member_user_project",
        "project_member",
        ["user_id", "project_id"],
        unique=True,
    )
    op.create_index(
        "ix_project_member_project",
        "project_member",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_member_project", table_name="project_member")
    op.drop_index("ix_project_member_user_project", table_name="project_member")
    op.drop_table("project_member")
