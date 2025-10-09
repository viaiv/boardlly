"""add project_repository and update epic_option for labels

Revision ID: 20251009_01
Revises: 20251008_06
Create Date: 2025-10-09 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251009_01"
down_revision = "20251008_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create project_repository table
    op.create_table(
        "project_repository",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("repo_name", sa.String(length=255), nullable=False),
        sa.Column("repo_node_id", sa.String(length=255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
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
            "owner",
            "repo_name",
            name="uq_project_repository"
        ),
        sqlite_autoincrement=True,
    )

    # Update epic_option table
    # Drop old indexes
    op.drop_index("ix_epic_option_option_id", table_name="epic_option")
    op.drop_index("ix_epic_option_project_id", table_name="epic_option")

    # Drop old unique constraint
    op.drop_constraint("uq_epic_option_project_option", "epic_option", type_="unique")

    # Add new column
    op.add_column("epic_option", sa.Column("label_name", sa.String(length=255), nullable=True))

    # Make option_id nullable
    op.alter_column("epic_option", "option_id", nullable=True)

    # For existing rows, generate label_name from option_name
    # This is a data migration - convert existing epic names to label format
    op.execute("""
        UPDATE epic_option
        SET label_name = 'epic:' || LOWER(REPLACE(REPLACE(option_name, ' ', '-'), '&', 'and'))
        WHERE label_name IS NULL
    """)

    # Now make label_name NOT NULL
    op.alter_column("epic_option", "label_name", nullable=False)

    # Add new unique constraint
    op.create_unique_constraint(
        "uq_epic_option_project_label",
        "epic_option",
        ["project_id", "label_name"]
    )


def downgrade() -> None:
    # Revert epic_option changes
    op.drop_constraint("uq_epic_option_project_label", "epic_option", type_="unique")
    op.drop_column("epic_option", "label_name")
    op.alter_column("epic_option", "option_id", nullable=False)

    # Recreate old constraint and indexes
    op.create_unique_constraint(
        "uq_epic_option_project_option",
        "epic_option",
        ["project_id", "option_id"]
    )
    op.create_index("ix_epic_option_project_id", "epic_option", ["project_id"])
    op.create_index("ix_epic_option_option_id", "epic_option", ["option_id"])

    # Drop project_repository table
    op.drop_table("project_repository")
