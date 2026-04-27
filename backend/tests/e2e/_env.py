"""E2E environment setup and provider error detection.

Ensures:
1. Test DB is seeded from main repo DB if needed
2. Slug columns exist for Stage 1 code
3. Provider errors (502, etc.) are clearly reported
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

# Paths
WORKTREE_BACKEND = Path(__file__).resolve().parents[2]
MAIN_REPO_BACKEND = Path("/Users/wangfushuaiqi/omaha_ontocenter/backend")
SOURCE_DB = MAIN_REPO_BACKEND / "omaha.db"
TARGET_DB = WORKTREE_BACKEND / "test.db"


class ProviderError(Exception):
    """Raised when LLM provider returns transient error (502, etc.)."""
    pass


def ensure_test_db() -> None:
    """Copy source DB to worktree if target is empty or missing project 10."""
    if not TARGET_DB.exists():
        print(f"[_env] test.db not found, copying from {SOURCE_DB}")
        shutil.copy2(SOURCE_DB, TARGET_DB)
        _ensure_slug_columns()
        return

    # Check if project 10 exists
    conn = sqlite3.connect(TARGET_DB)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM projects WHERE id = 10")
        count = cur.fetchone()[0]
        if count == 0:
            print(f"[_env] project 10 missing, re-copying from {SOURCE_DB}")
            conn.close()
            shutil.copy2(SOURCE_DB, TARGET_DB)
            _ensure_slug_columns()
        else:
            _ensure_slug_columns()
    finally:
        conn.close()


def _ensure_slug_columns() -> None:
    """Add slug columns if missing and populate them."""
    conn = sqlite3.connect(TARGET_DB)
    try:
        # Check ontology_objects
        cur = conn.execute("PRAGMA table_info(ontology_objects)")
        cols = {row[1] for row in cur.fetchall()}
        if "slug" not in cols:
            print("[_env] adding slug to ontology_objects")
            conn.execute("ALTER TABLE ontology_objects ADD COLUMN slug VARCHAR")
            conn.execute("UPDATE ontology_objects SET slug = lower(name)")
            conn.commit()

        # Check projects (if needed in future)
        cur = conn.execute("PRAGMA table_info(projects)")
        cols = {row[1] for row in cur.fetchall()}
        if "slug" not in cols:
            print("[_env] adding slug to projects")
            conn.execute("ALTER TABLE projects ADD COLUMN slug VARCHAR")
            conn.execute("UPDATE projects SET slug = lower(name)")
            conn.commit()
    finally:
        conn.close()


def wrap_provider_errors(func):
    """Decorator to catch and re-raise provider errors clearly."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            err_type = type(e).__name__.lower()
            # Check for 502, bad gateway, or InternalServerError
            if any(x in err_str for x in ["502", "bad gateway"]) or "internalservererror" in err_type:
                raise ProviderError(
                    f"LLM provider error (502/transient): {type(e).__name__}: {e}\n"
                    "This is an infrastructure/provider issue, not a product regression."
                ) from e
            raise
    return wrapper


def is_provider_error(exc: Exception) -> bool:
    """Check if exception is a provider error (502, etc.)."""
    err_str = str(exc).lower()
    err_type = type(exc).__name__.lower()
    return any(x in err_str for x in ["502", "bad gateway"]) or "internalservererror" in err_type
