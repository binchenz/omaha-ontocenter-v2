"""E2E environment setup and provider error detection.

Ensures:
1. Test DB is seeded from main repo DB if needed
2. Slug columns exist for Stage 1 code
3. Provider errors (502, etc.) are clearly reported
4. .env is loaded so LLM API keys are available
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

# Force DATABASE_URL to test.db before any app module reads it
os.environ["DATABASE_URL"] = f"sqlite:///{TARGET_DB}"

# Load .env so ProviderFactory can find API keys (override=False keeps DATABASE_URL above)
_env_file = WORKTREE_BACKEND / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file, override=False)


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
    _ensure_project_config()


def _ensure_slug_columns() -> None:
    """Add slug columns if missing and populate them with proper ASCII slugs.

    Uses slugify_name() for correct Chinese→pinyin transliteration instead of
    naive lower(name) which would produce invalid tool names.
    """
    from app.services.ontology.slug import slugify_name

    conn = sqlite3.connect(TARGET_DB)
    try:
        cur = conn.execute("PRAGMA table_info(ontology_objects)")
        cols = {row[1] for row in cur.fetchall()}
        if "slug" not in cols:
            print("[_env] adding slug to ontology_objects")
            conn.execute("ALTER TABLE ontology_objects ADD COLUMN slug VARCHAR")
            conn.commit()

        # Always re-slugify to fix any Chinese slugs from previous runs
        rows = conn.execute("SELECT id, name FROM ontology_objects").fetchall()
        for row_id, name in rows:
            slug = slugify_name(name or "")
            conn.execute("UPDATE ontology_objects SET slug = ? WHERE id = ?", (slug, row_id))
        conn.commit()

        cur = conn.execute("PRAGMA table_info(object_properties)")
        cols = {row[1] for row in cur.fetchall()}
        if "slug" not in cols:
            print("[_env] adding slug to object_properties")
            conn.execute("ALTER TABLE object_properties ADD COLUMN slug VARCHAR")
            conn.commit()

        rows = conn.execute("SELECT id, name FROM object_properties").fetchall()
        for row_id, name in rows:
            slug = slugify_name(name or "")
            conn.execute("UPDATE object_properties SET slug = ? WHERE id = ?", (slug, row_id))
        conn.commit()
    finally:
        conn.close()


def _ensure_project_config() -> None:
    """Ensure E2E project 10 has omaha_config copied from project 4 (金融股票分析)."""
    conn = sqlite3.connect(TARGET_DB)
    try:
        cur = conn.execute("SELECT omaha_config FROM projects WHERE id = 10")
        row = cur.fetchone()
        if row and row[0]:
            return
        cur = conn.execute("SELECT omaha_config FROM projects WHERE id = 4")
        src = cur.fetchone()
        if src and src[0]:
            conn.execute(
                "UPDATE projects SET omaha_config = ?, setup_stage = 'ready' WHERE id = 10",
                (src[0],),
            )
            conn.commit()
            print("[_env] copied omaha_config from project 4 to project 10")
    finally:
        conn.close()


def is_provider_error(exc: Exception) -> bool:
    """Check if exception is a provider error (502, 401, etc.)."""
    err_str = str(exc).lower()
    err_type = type(exc).__name__.lower()
    return (
        any(x in err_str for x in ["502", "bad gateway", "401", "unauthorized"])
        or "internalservererror" in err_type
        or "authenticationerror" in err_type
    )
