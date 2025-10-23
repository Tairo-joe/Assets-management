"""add notes column to asset

Revision ID: add_asset_notes
Revises: 30eea1b2109e
Create Date: 2025-10-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_asset_notes'
down_revision = '30eea1b2109e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('asset', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('asset', 'notes')


