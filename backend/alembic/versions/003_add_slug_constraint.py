"""add slug constraint

Revision ID: 003_add_slug_constraint
Revises: 002_add_link_type
Create Date: 2026-04-28 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_slug_constraint'
down_revision = '002_add_link_type'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite doesn't support CHECK constraints via ALTER TABLE
    # This migration documents the constraint for future reference
    # Enforcement is done at application layer via OntologyStore
    pass


def downgrade():
    pass
