"""Tests for public auth API endpoints."""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, InviteCode, PublicApiKey


def test_register_with_valid_invite_code(client: TestClient, db: Session):
    """Test user registration with valid invite code."""
    invite = InviteCode(code="TEST123", is_used=False)
    db.add(invite)
    db.commit()

    response = client.post(
        "/api/public/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "invite_code": "TEST123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data

    db.refresh(invite)
    assert invite.is_used is True
    assert invite.used_by is not None


def test_register_with_invalid_invite_code(client: TestClient):
    """Test registration fails with invalid invite code."""
    response = client.post(
        "/api/public/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "invite_code": "INVALID"
        }
    )

    assert response.status_code == 400


def test_register_with_used_invite_code(client: TestClient, db: Session):
    """Test registration fails with already used invite code."""
    invite = InviteCode(code="USED123", is_used=True)
    db.add(invite)
    db.commit()

    response = client.post(
        "/api/public/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "invite_code": "USED123"
        }
    )

    assert response.status_code == 400


def test_register_with_expired_invite_code(client: TestClient, db: Session):
    """Test registration fails with expired invite code."""
    invite = InviteCode(
        code="EXPIRED123",
        is_used=False,
        expires_at=datetime.utcnow() - timedelta(days=1)
    )
    db.add(invite)
    db.commit()

    response = client.post(
        "/api/public/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "invite_code": "EXPIRED123"
        }
    )

    assert response.status_code == 400


def test_generate_api_key(client: TestClient, db: Session):
    """Test API key generation for registered user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=""
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    response = client.post(
        "/api/public/auth/api-key",
        json={
            "email": "test@example.com",
            "username": "testuser"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert data["api_key"].startswith("omaha_")

    api_key_record = db.query(PublicApiKey).filter_by(user_id=user.id).first()
    assert api_key_record is not None
    assert api_key_record.is_active is True


def test_generate_api_key_for_nonexistent_user(client: TestClient):
    """Test API key generation fails for non-existent user."""
    response = client.post(
        "/api/public/auth/api-key",
        json={
            "email": "nonexistent@example.com",
            "username": "nonexistent"
        }
    )

    assert response.status_code == 404
