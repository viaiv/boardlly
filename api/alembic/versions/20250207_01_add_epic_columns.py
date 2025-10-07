"""add epic columns to project_item

Revision ID: 20250207_01
Revises: 
Create Date: 2025-02-07 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250207_01"
down_revision = "20240926_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_item",
        sa.Column("epic_option_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "project_item",
        sa.Column("epic_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_item", "epic_name")
    op.drop_column("project_item", "epic_option_id")
