"""add invite_token to project_invite

Revision ID: 20251009_02
Revises: 20251009_01
Create Date: 2025-10-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251009_02'
down_revision = '20251009_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add invite_token column
    op.add_column('project_invite', sa.Column('invite_token', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_project_invite_invite_token'), 'project_invite', ['invite_token'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_project_invite_invite_token'), table_name='project_invite')
    op.drop_column('project_invite', 'invite_token')
