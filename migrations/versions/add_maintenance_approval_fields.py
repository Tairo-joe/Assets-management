"""add maintenance approval fields

Revision ID: add_maint_approval
Revises: add_asset_notes
Create Date: 2025-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_maint_approval'
down_revision = 'add_asset_notes'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('maintenance', sa.Column('status', sa.String(length=20), nullable=True))
    op.add_column('maintenance', sa.Column('approved_by', sa.Integer(), nullable=True))
    op.add_column('maintenance', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'maintenance', 'user', ['approved_by'], ['id'])


def downgrade():
    op.drop_constraint(None, 'maintenance', type_='foreignkey')
    op.drop_column('maintenance', 'approved_at')
    op.drop_column('maintenance', 'approved_by')
    op.drop_column('maintenance', 'status')


