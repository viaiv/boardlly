"""iteration snapshot table and duration

Revision ID: 20250207_02
Revises: 20250207_01
Create Date: 2025-02-07 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20250207_02"
down_revision = "20250207_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iteration_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["github_project.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "option_id", name="uq_snapshot_project_option"),
    )

    op.create_index(
        "ix_iteration_snapshot_option_id",
        "iteration_snapshot",
        ["option_id"],
    )

    op.add_column("project_item", sa.Column("iteration_duration_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("project_item", "iteration_duration_days")
    op.drop_index("ix_iteration_snapshot_option_id", table_name="iteration_snapshot")
    op.drop_table("iteration_snapshot")
