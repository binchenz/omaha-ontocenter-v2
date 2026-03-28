"""add watchlist table

Revision ID: a4f96a91a3dc
Revises: eae86371d799
Create Date: 2026-03-28 14:06:37.725262

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4f96a91a3dc'
down_revision = 'eae86371d799'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ts_code', sa.String(20), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_watchlist_user_id', 'watchlist', ['user_id'])
    op.create_index('ix_watchlist_ts_code', 'watchlist', ['ts_code'])


def downgrade() -> None:
    op.drop_index('ix_watchlist_ts_code', 'watchlist')
    op.drop_index('ix_watchlist_user_id', 'watchlist')
    op.drop_table('watchlist')
