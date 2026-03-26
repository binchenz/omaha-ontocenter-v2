"""Tests for public API authentication dependency."""
import pytest
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.api.public_deps import verify_api_key
from app.models.user import User
from app.models.public_api_key import PublicApiKey
import hashlib


def test_verify_api_key_valid(db: Session, test_user: User):
    """Test valid API key authentication."""
    # Create API key
    raw_key = "omaha_test_1234567890abcdef"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = PublicApiKey(
        user_id=test_user.id,
        key_hash=key_hash,
        key_prefix="omaha_test",
        is_active=True
    )
    db.add(api_key)
    db.commit()

    # Verify key
    user = verify_api_key(f"Bearer {raw_key}", db)

    assert user.id == test_user.id
    db.refresh(api_key)
    assert api_key.last_used_at is not None


def test_verify_api_key_invalid(db: Session):
    """Test invalid API key."""
    with pytest.raises(HTTPException) as exc:
        verify_api_key("Bearer invalid_key", db)
    assert exc.value.status_code == 401


def test_verify_api_key_inactive(db: Session, test_user: User):
    """Test inactive API key."""
    raw_key = "omaha_test_inactive"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = PublicApiKey(
        user_id=test_user.id,
        key_hash=key_hash,
        key_prefix="omaha_test",
        is_active=False
    )
    db.add(api_key)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        verify_api_key(f"Bearer {raw_key}", db)
    assert exc.value.status_code == 401


def test_verify_api_key_missing_bearer(db: Session):
    """Test missing Bearer prefix."""
    with pytest.raises(HTTPException) as exc:
        verify_api_key("invalid_format", db)
    assert exc.value.status_code == 401
