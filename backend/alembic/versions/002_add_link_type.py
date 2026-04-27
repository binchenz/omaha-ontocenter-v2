"""add Link type support to ObjectProperty

Revision ID: 002_add_link_type
Revises: 001_add_ontology_slugs
Create Date: 2026-04-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_link_type'
down_revision = '001_add_ontology_slugs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('object_properties') as batch_op:
        batch_op.add_column(sa.Column('link_target_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('link_foreign_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('link_target_key', sa.String(), nullable=True, server_default='id'))
        batch_op.create_index('ix_object_properties_link_target_id', ['link_target_id'])
        batch_op.create_foreign_key('fk_object_properties_link_target', 'ontology_objects', ['link_target_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('object_properties') as batch_op:
        batch_op.drop_constraint('fk_object_properties_link_target', type_='foreignkey')
        batch_op.drop_index('ix_object_properties_link_target_id')
        batch_op.drop_column('link_target_key')
        batch_op.drop_column('link_foreign_key')
        batch_op.drop_column('link_target_id')
