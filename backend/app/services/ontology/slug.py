"""
Slug generation and uniqueness helpers for ontology objects and properties.
"""
import re
import hashlib
from sqlalchemy.orm import Session


def slugify_name(name: str) -> str:
    """
    Convert a name to a URL-safe ASCII slug.

    For ASCII names:
        "Customer Order" -> "customer-order"
        "Order_Item"     -> "order-item"
        "ROE %"          -> "roe"

    For non-ASCII / Chinese names, attempt transliteration via the `pinyin`
    library if available; otherwise fall back to obj_<sha1[:8]>.
    """
    if not name or not name.strip():
        return ""

    # Try to transliterate non-ASCII characters
    has_non_ascii = any(ord(c) > 127 for c in name)
    working = name

    if has_non_ascii:
        try:
            from pypinyin import lazy_pinyin
            working = "-".join(lazy_pinyin(name))
        except ImportError:
            # Strip non-ASCII entirely; if nothing remains use hash fallback
            working = name.encode("ascii", errors="ignore").decode()

    slug = working.lower()
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = slug.strip('-')
    slug = re.sub(r'-+', '-', slug)

    if not slug:
        # Fallback: obj_<first 8 hex chars of sha1(original name)>
        h = hashlib.sha1(name.encode()).hexdigest()[:8]
        slug = f"obj_{h}"

    return slug


_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_sql_identifier(name: str) -> str:
    if not name or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


def ensure_unique_slug(db: Session, base_slug: str, table_name: str,
                       column_name: str, exclude_id: int = None,
                       tenant_id: int = None,
                       object_id: int = None) -> str:
    """
    Ensure a slug is unique within the appropriate scope.

    Scope rules:
      - ontology_objects: scoped by tenant_id
      - object_properties: scoped by object_id
    """
    from sqlalchemy import text

    def _count(slug_candidate: str) -> int:
        safe_table = _validate_sql_identifier(table_name)
        safe_column = _validate_sql_identifier(column_name)
        q = f"SELECT COUNT(*) FROM {safe_table} WHERE {safe_column} = :slug"
        params: dict = {"slug": slug_candidate}
        if exclude_id is not None:
            q += " AND id != :exclude_id"
            params["exclude_id"] = exclude_id
        if tenant_id is not None:
            q += " AND tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id
        if object_id is not None:
            q += " AND object_id = :object_id"
            params["object_id"] = object_id
        return db.execute(text(q), params).scalar()

    if _count(base_slug) == 0:
        return base_slug

    counter = 1
    while True:
        candidate = f"{base_slug}-{counter}"
        if _count(candidate) == 0:
            return candidate
        counter += 1
