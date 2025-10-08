"""add email verification fields to app_user

Revision ID: 20251008_04
Revises: 20251008_03
Create Date: 2025-10-08 17:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251008_04"
down_revision = "20251008_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add email_verified column (default false for existing users)
    op.add_column(
        "app_user",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false")
    )

    # Add email_verification_token column (nullable)
    op.add_column(
        "app_user",
        sa.Column("email_verification_token", sa.String(length=255), nullable=True)
    )

    # Add email_verification_token_expires column (nullable)
    op.add_column(
        "app_user",
        sa.Column("email_verification_token_expires", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    # Drop columns in reverse order
    op.drop_column("app_user", "email_verification_token_expires")
    op.drop_column("app_user", "email_verification_token")
    op.drop_column("app_user", "email_verified")
