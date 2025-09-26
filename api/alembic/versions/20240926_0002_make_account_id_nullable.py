"""Make app_user.account_id nullable

Revision ID: 20240926_0002
Revises: 20240926_0001
Create Date: 2025-09-26 14:40:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20240926_0002"
down_revision = "20240926_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "app_user",
        "account_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "app_user",
        "account_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
