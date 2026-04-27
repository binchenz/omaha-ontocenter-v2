"""add slug columns to ontology objects and properties

Revision ID: 001_add_ontology_slugs
Revises: eae86371d799
Create Date: 2026-04-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '001_add_ontology_slugs'
down_revision = 'eae86371d799'
branch_labels = None
depends_on = None


def _slugify_sql(col: str) -> str:
    """
    Return a SQL expression that produces a basic ASCII slug from `col`.
    Handles spaces, underscores, and strips non-ASCII-alphanumeric chars.
    This mirrors the Python slugify_name() logic for pure-ASCII names.
    Non-ASCII characters are stripped; if the result is empty the row will
    be caught by the Python post-pass below.
    """
    # SQLite / PostgreSQL compatible via LOWER + REPLACE
    return (
        f"LOWER("
        f"REPLACE(REPLACE(REPLACE(REPLACE({col}, ' ', '-'), '_', '-'), '%', ''), '/', '-')"
        f")"
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Add nullable slug columns first
    op.add_column('ontology_objects', sa.Column('slug', sa.String(), nullable=True))
    op.add_column('object_properties', sa.Column('slug', sa.String(), nullable=True))

    # Best-effort SQL backfill for ASCII names
    conn.execute(text(
        f"UPDATE ontology_objects SET slug = {_slugify_sql('name')} WHERE slug IS NULL"
    ))
    conn.execute(text(
        f"UPDATE object_properties SET slug = {_slugify_sql('name')} WHERE slug IS NULL"
    ))

    # Python post-pass: fix empty slugs (non-ASCII names) and resolve duplicates
    import hashlib
    import re

    def _py_slugify(name: str) -> str:
        try:
            from pypinyin import lazy_pinyin
            working = "-".join(lazy_pinyin(name))
        except ImportError:
            working = name.encode("ascii", errors="ignore").decode()
        s = working.lower()
        s = re.sub(r'[\s_]+', '-', s)
        s = re.sub(r'[^a-z0-9-]', '', s)
        s = s.strip('-')
        s = re.sub(r'-+', '-', s)
        if not s:
            h = hashlib.sha1(name.encode()).hexdigest()[:8]
            s = f"obj_{h}"
        return s

    # Fix empty slugs
    rows = conn.execute(text("SELECT id, name FROM ontology_objects WHERE slug = '' OR slug IS NULL")).fetchall()
    for row_id, name in rows:
        conn.execute(text("UPDATE ontology_objects SET slug = :s WHERE id = :id"),
                     {"s": _py_slugify(name), "id": row_id})

    rows = conn.execute(text("SELECT id, name FROM object_properties WHERE slug = '' OR slug IS NULL")).fetchall()
    for row_id, name in rows:
        conn.execute(text("UPDATE object_properties SET slug = :s WHERE id = :id"),
                     {"s": _py_slugify(name), "id": row_id})

    # Resolve duplicate (tenant_id, slug) for ontology_objects
    dupes = conn.execute(text("""
        SELECT tenant_id, slug, COUNT(*) as cnt
        FROM ontology_objects
        GROUP BY tenant_id, slug
        HAVING cnt > 1
    """)).fetchall()
    for tenant_id, slug, _ in dupes:
        rows = conn.execute(text(
            "SELECT id FROM ontology_objects WHERE tenant_id = :t AND slug = :s ORDER BY id"
        ), {"t": tenant_id, "s": slug}).fetchall()
        for i, (row_id,) in enumerate(rows[1:], start=1):
            conn.execute(text("UPDATE ontology_objects SET slug = :s WHERE id = :id"),
                         {"s": f"{slug}-{i}", "id": row_id})

    # Resolve duplicate (object_id, slug) for object_properties
    dupes = conn.execute(text("""
        SELECT object_id, slug, COUNT(*) as cnt
        FROM object_properties
        GROUP BY object_id, slug
        HAVING cnt > 1
    """)).fetchall()
    for object_id, slug, _ in dupes:
        rows = conn.execute(text(
            "SELECT id FROM object_properties WHERE object_id = :o AND slug = :s ORDER BY id"
        ), {"o": object_id, "s": slug}).fetchall()
        for i, (row_id,) in enumerate(rows[1:], start=1):
            conn.execute(text("UPDATE object_properties SET slug = :s WHERE id = :id"),
                         {"s": f"{slug}-{i}", "id": row_id})

    # Make NOT NULL
    op.alter_column('ontology_objects', 'slug', nullable=False)
    op.alter_column('object_properties', 'slug', nullable=False)

    # Add unique constraints
    op.create_unique_constraint('uq_tenant_object_slug', 'ontology_objects', ['tenant_id', 'slug'])
    op.create_unique_constraint('uq_object_property_slug', 'object_properties', ['object_id', 'slug'])


def downgrade() -> None:
    op.drop_constraint('uq_object_property_slug', 'object_properties', type_='unique')
    op.drop_constraint('uq_tenant_object_slug', 'ontology_objects', type_='unique')
    op.drop_column('object_properties', 'slug')
    op.drop_column('ontology_objects', 'slug')
