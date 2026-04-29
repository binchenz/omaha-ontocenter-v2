"""Repo-level path constants — single source of truth for filesystem layout."""
from pathlib import Path

# this file lives at backend/app/_paths.py → repo root is 3 parents up
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = REPO_ROOT / "configs"
TEMPLATES_DIR = CONFIGS_DIR / "templates"
