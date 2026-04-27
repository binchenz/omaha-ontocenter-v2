"""E2E environment setup and provider error detection.

Ensures:
1. Test DB is seeded from main repo DB if needed
2. Slug columns exist for Stage 1 code
3. Provider errors (502, etc.) are clearly reported
"""
from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

# Paths
WORKTREE_BACKEND = Path(__file__).resolve().parents[2]
DEFAULT_MAIN_DB = WORKTREE_BACKEND.parent.parent.parent / "backend" / "omaha.db"
SOURCE_DB = Path(os.environ.get("E2E_MAIN_DB", str(DEFAULT_MAIN_DB)))
TARGET_DB = WORKTREE_BACKEND / "test.db"


def ensure_test_db() -> None:
    """Copy source DB to worktree if target is empty or missing project 10."""
    recopy = not TARGET_DB.exists()
    if recopy:
        print(f"[_env] test.db not found, copying from {SOURCE_DB}")
    else:
        conn = sqlite3.connect(TARGET_DB)
        try:
            cur = conn.execute("SELECT COUNT(*) FROM projects WHERE id = 10")
            recopy = cur.fetchone()[0] == 0
        finally:
            conn.close()
        if recopy:
            print(f"[_env] project 10 missing, re-copying from {SOURCE_DB}")

    if recopy:
        shutil.copy2(SOURCE_DB, TARGET_DB)

    _ensure_slug_columns()


def _ensure_slug_columns() -> None:
    """Add slug columns if missing and populate them for Stage 1 E2E runs.

    E2E uses a copied SQLite DB rather than invoking Alembic so the suites can run
    from a worktree without mutating the main repo database.
    """
    conn = sqlite3.connect(TARGET_DB)
    try:
        cur = conn.execute("PRAGMA table_info(ontology_objects)")
        cols = {row[1] for row in cur.fetchall()}
        if "slug" not in cols:
            print("[_env] adding slug to ontology_objects")
            conn.execute("ALTER TABLE ontology_objects ADD COLUMN slug VARCHAR")
            conn.execute("UPDATE ontology_objects SET slug = lower(name)")
            conn.commit()

        cur = conn.execute("PRAGMA table_info(object_properties)")
        cols = {row[1] for row in cur.fetchall()}
        if "slug" not in cols:
            print("[_env] adding slug to object_properties")
            conn.execute("ALTER TABLE object_properties ADD COLUMN slug VARCHAR")
            conn.execute("UPDATE object_properties SET slug = lower(name)")
            conn.commit()
    finally:
        conn.close()


def is_provider_error(exc: Exception) -> bool:
    """Check if exception is a provider error (502, etc.)."""
    err_str = str(exc).lower()
    err_type = type(exc).__name__.lower()
    return any(x in err_str for x in ["502", "bad gateway"]) or "internalservererror" in err_type
