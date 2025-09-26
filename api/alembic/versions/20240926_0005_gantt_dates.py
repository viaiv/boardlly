"""Add timeline support fields

Revision ID: 20240926_0005
Revises: 20240926_0004
Create Date: 2025-09-26 22:40:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20240926_0005"
down_revision = "20240926_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_project_field",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("field_id", sa.String(length=255), nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.Column("field_type", sa.String(length=50), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["github_project.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "field_id", name="uq_github_project_field_project_field"),
    )

    op.add_column("project_item", sa.Column("iteration_id", sa.String(length=255), nullable=True))
    op.add_column("project_item", sa.Column("iteration_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("project_item", sa.Column("iteration_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("project_item", sa.Column("start_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("project_item", sa.Column("end_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("project_item", sa.Column("due_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("project_item", sa.Column("remote_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("project_item", sa.Column("last_local_edit_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "project_item",
        sa.Column("last_local_edit_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_project_item_last_local_edit_by",
        "project_item",
        "app_user",
        ["last_local_edit_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_project_item_start_date", "project_item", ["start_date"])
    op.create_index("ix_project_item_end_date", "project_item", ["end_date"])


def downgrade() -> None:
    op.drop_index("ix_project_item_end_date", table_name="project_item")
    op.drop_index("ix_project_item_start_date", table_name="project_item")
    op.drop_constraint("fk_project_item_last_local_edit_by", "project_item", type_="foreignkey")
    op.drop_column("project_item", "last_local_edit_by")
    op.drop_column("project_item", "last_local_edit_at")
    op.drop_column("project_item", "remote_updated_at")
    op.drop_column("project_item", "due_date")
    op.drop_column("project_item", "end_date")
    op.drop_column("project_item", "start_date")
    op.drop_column("project_item", "iteration_end")
    op.drop_column("project_item", "iteration_start")
    op.drop_column("project_item", "iteration_id")
    op.drop_table("github_project_field")
