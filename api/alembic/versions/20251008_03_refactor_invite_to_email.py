"""refactor project_invite to use email instead of user_id

Revision ID: 20251008_03
Revises: 20251008_02
Create Date: 2025-10-08 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251008_03"
down_revision = "20251008_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old unique index on (invited_user_id, project_id)
    op.drop_index("ix_project_invite_user_project", table_name="project_invite")

    # Drop FK constraint on invited_user_id
    op.drop_constraint(
        "project_invite_invited_user_id_fkey",
        "project_invite",
        type_="foreignkey"
    )

    # Drop the invited_user_id column
    op.drop_column("project_invite", "invited_user_id")

    # Add invited_email column
    op.add_column(
        "project_invite",
        sa.Column("invited_email", sa.String(length=255), nullable=False)
    )

    # Create new unique index on (invited_email, project_id)
    op.create_index(
        "ix_project_invite_email_project",
        "project_invite",
        ["invited_email", "project_id"],
        unique=True,
    )


def downgrade() -> None:
    # Drop new index
    op.drop_index("ix_project_invite_email_project", table_name="project_invite")

    # Drop invited_email column
    op.drop_column("project_invite", "invited_email")

    # Re-add invited_user_id column
    op.add_column(
        "project_invite",
        sa.Column("invited_user_id", postgresql.UUID(as_uuid=True), nullable=False)
    )

    # Re-add FK constraint
    op.create_foreign_key(
        "project_invite_invited_user_id_fkey",
        "project_invite",
        "app_user",
        ["invited_user_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # Re-create old unique index
    op.create_index(
        "ix_project_invite_user_project",
        "project_invite",
        ["invited_user_id", "project_id"],
        unique=True,
    )
