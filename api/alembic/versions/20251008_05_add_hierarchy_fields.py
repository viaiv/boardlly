"""add hierarchy fields to project_item

Revision ID: 20251008_05
Revises: 20251008_04
Create Date: 2025-10-08 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = "20251008_05"
down_revision = "20251008_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add item_type column (story, task, feature, bug)
    op.add_column(
        "project_item",
        sa.Column("item_type", sa.String(length=50), nullable=True)
    )

    # Add parent_item_id column (self-referential FK)
    op.add_column(
        "project_item",
        sa.Column("parent_item_id", sa.Integer(), nullable=True)
    )

    # Add labels column (JSON array)
    op.add_column(
        "project_item",
        sa.Column("labels", JSON, nullable=True)
    )

    # Create foreign key constraint for parent_item_id
    op.create_foreign_key(
        "fk_project_item_parent_item_id",
        "project_item",
        "project_item",
        ["parent_item_id"],
        ["id"],
        ondelete="SET NULL"
    )

    # Create index for parent_item_id to improve hierarchy queries
    op.create_index(
        "ix_project_item_parent_item_id",
        "project_item",
        ["parent_item_id"]
    )

    # Create index for item_type to improve filtering
    op.create_index(
        "ix_project_item_item_type",
        "project_item",
        ["item_type"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_project_item_item_type", table_name="project_item")
    op.drop_index("ix_project_item_parent_item_id", table_name="project_item")

    # Drop foreign key
    op.drop_constraint("fk_project_item_parent_item_id", "project_item", type_="foreignkey")

    # Drop columns in reverse order
    op.drop_column("project_item", "labels")
    op.drop_column("project_item", "parent_item_id")
    op.drop_column("project_item", "item_type")
