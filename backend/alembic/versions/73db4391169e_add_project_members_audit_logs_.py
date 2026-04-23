"""add project_members audit_logs pipelines tables

Revision ID: 73db4391169e
Revises: a4f96a91a3dc
Create Date: 2026-04-23 08:36:02.670546

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73db4391169e'
down_revision = 'a4f96a91a3dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('resource_type', sa.String(length=50), nullable=True),
    sa.Column('resource_id', sa.String(length=100), nullable=True),
    sa.Column('detail', sa.JSON(), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_project_id'), 'audit_logs', ['project_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_table('pipelines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('datasource_id', sa.String(length=100), nullable=False),
    sa.Column('object_type', sa.String(length=100), nullable=False),
    sa.Column('filters', sa.JSON(), nullable=True),
    sa.Column('target_table', sa.String(length=100), nullable=False),
    sa.Column('schedule', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_run_status', sa.String(length=20), nullable=True),
    sa.Column('last_run_rows', sa.Integer(), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pipelines_id'), 'pipelines', ['id'], unique=False)
    op.create_index(op.f('ix_pipelines_project_id'), 'pipelines', ['project_id'], unique=False)
    op.create_table('project_members',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )
    op.create_index(op.f('ix_project_members_id'), 'project_members', ['id'], unique=False)
    # Note: alter_column for JSON types and foreign key on users.invited_by
    # are SQLite-incompatible and not needed (SQLite stores JSON as TEXT natively)


def downgrade() -> None:
    op.drop_index(op.f('ix_project_members_id'), table_name='project_members')
    op.drop_table('project_members')
    op.drop_index(op.f('ix_pipelines_project_id'), table_name='pipelines')
    op.drop_index(op.f('ix_pipelines_id'), table_name='pipelines')
    op.drop_table('pipelines')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_project_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
