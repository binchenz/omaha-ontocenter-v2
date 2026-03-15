"""MCP Server authentication helpers."""
import hashlib
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.api_key import ProjectApiKey
from app.models.project import Project


def _hash_key(key: str) -> str:
    """SHA256 hash of an API key."""
    return hashlib.sha256(key.encode()).hexdigest()


def resolve_api_key(key: str, db: Session) -> Optional[Tuple[int, str]]:
    """Validate an API key and return (project_id, omaha_config) or None.

    Returns None if the key does not exist, is inactive, or has expired.
    Returns None if the associated project has no omaha_config.
    """
    key_hash = _hash_key(key)
    api_key = db.query(ProjectApiKey).filter(
        ProjectApiKey.key_hash == key_hash,
        ProjectApiKey.is_active == True,  # noqa: E712
    ).first()

    if not api_key:
        return None

    # Check expiry
    if api_key.expires_at is not None:
        now = datetime.now(timezone.utc)
        expires = api_key.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            return None

    project = db.query(Project).filter(Project.id == api_key.project_id).first()
    if not project or not project.omaha_config:
        return None

    return (project.id, project.omaha_config)


def get_api_key_from_env() -> str:
    """Read the OMAHA_API_KEY environment variable.

    Raises:
        ValueError: if the variable is not set or empty.
    """
    key = os.environ.get("OMAHA_API_KEY", "").strip()
    if not key:
        raise ValueError("OMAHA_API_KEY environment variable is not set")
    return key
