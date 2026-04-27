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
        q = f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = :slug"
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
