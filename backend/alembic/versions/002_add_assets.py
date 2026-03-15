"""
Add dataset assets and data lineage tables.

Revision ID: 002
Revises: 001
Create Date: 2026-03-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create dataset_assets table
    op.create_table(
        'dataset_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_object', sa.String(), nullable=False),
        sa.Column('selected_columns', sa.Text(), nullable=True),
        sa.Column('filters', sa.Text(), nullable=True),
        sa.Column('joins', sa.Text(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_assets_id'), 'dataset_assets', ['id'], unique=False)
    op.create_index(op.f('ix_dataset_assets_name'), 'dataset_assets', ['name'], unique=False)

    # Create data_lineage table
    op.create_table(
        'data_lineage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('lineage_type', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=True),
        sa.Column('source_name', sa.String(), nullable=True),
        sa.Column('transformation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['dataset_assets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_lineage_id'), 'data_lineage', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_data_lineage_id'), table_name='data_lineage')
    op.drop_table('data_lineage')
    op.drop_index(op.f('ix_dataset_assets_name'), table_name='dataset_assets')
    op.drop_index(op.f('ix_dataset_assets_id'), table_name='dataset_assets')
    op.drop_table('dataset_assets')
