"""Add GitHub project and project item tables

Revision ID: 20240926_0003
Revises: 20240926_0002
Create Date: 2025-09-26 15:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20240926_0003"
down_revision = "20240926_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_project",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_login", sa.String(length=255), nullable=False),
        sa.Column("project_number", sa.Integer(), nullable=False),
        sa.Column("project_node_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("field_mappings", sa.JSON(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_node_id"),
    )
    op.create_index(
        "ix_github_project_account_owner_number",
        "github_project",
        ["account_id", "owner_login", "project_number"],
        unique=True,
    )

    op.create_table(
        "project_item",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("item_node_id", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=True),
        sa.Column("content_node_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("assignees", sa.JSON(), nullable=True),
        sa.Column("iteration", sa.String(length=255), nullable=True),
        sa.Column("estimate", sa.Numeric(scale=2), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("field_values", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["github_project.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("item_node_id"),
    )
    op.create_index("ix_project_item_project", "project_item", ["project_id"])
    op.create_index("ix_project_item_status", "project_item", ["status"])
    op.create_index("ix_project_item_updated_at", "project_item", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_project_item_updated_at", table_name="project_item")
    op.drop_index("ix_project_item_status", table_name="project_item")
    op.drop_index("ix_project_item_project", table_name="project_item")
    op.drop_table("project_item")
    op.drop_index("ix_github_project_account_owner_number", table_name="github_project")
    op.drop_table("github_project")
