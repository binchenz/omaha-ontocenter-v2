"""add_api_keys

Revision ID: 003
Revises: 5b5c13c2ec06
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '5b5c13c2ec06'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('key_prefix', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
    )
    op.create_index('ix_project_api_keys_id', 'project_api_keys', ['id'])
    op.create_index('ix_project_api_keys_project_id', 'project_api_keys', ['project_id'])


def downgrade():
    op.drop_index('ix_project_api_keys_project_id', 'project_api_keys')
    op.drop_index('ix_project_api_keys_id', 'project_api_keys')
    op.drop_table('project_api_keys')
