"""create epic_option table

Revision ID: 20251008_06
Revises: 20251008_05
Create Date: 2025-10-08 17:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251008_06"
down_revision = "20251008_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create epic_option table
    op.create_table(
        "epic_option",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.String(length=255), nullable=False),
        sa.Column("option_name", sa.String(length=255), nullable=False),
        sa.Column("color", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["github_project.id"],
            ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "project_id",
            "option_id",
            name="uq_epic_option_project_option"
        ),
        sqlite_autoincrement=True,
    )

    # Create indexes
    op.create_index(
        "ix_epic_option_project_id",
        "epic_option",
        ["project_id"]
    )

    op.create_index(
        "ix_epic_option_option_id",
        "epic_option",
        ["option_id"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_epic_option_option_id", table_name="epic_option")
    op.drop_index("ix_epic_option_project_id", table_name="epic_option")

    # Drop table
    op.drop_table("epic_option")
