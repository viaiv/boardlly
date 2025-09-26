"""Add status columns to github_project

Revision ID: 20240926_0004
Revises: 20240926_0003
Create Date: 2025-09-26 17:05:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20240926_0004"
down_revision = "20240926_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("github_project", sa.Column("status_columns", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("github_project", "status_columns")
