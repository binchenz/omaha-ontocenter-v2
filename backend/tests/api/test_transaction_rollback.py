"""Verify that endpoints return 500 and rollback when db.commit() fails."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.api.deps import get_current_user
from app.database import get_db


mock_user = Mock()
mock_user.id = 1
mock_user.email = "test@test.com"
mock_user.is_active = True


def override_get_current_user():
    return mock_user


def make_failing_db():
    """Create a mock DB session whose commit() raises IntegrityError."""
    mock_session = Mock()
    mock_session.commit.side_effect = IntegrityError("duplicate", {}, None)
    mock_session.rollback = Mock()

    mock_q = Mock()
    mock_q.filter.return_value.first.return_value = None
    mock_session.query.return_value = mock_q
    return mock_session


@pytest.fixture
def failing_client():
    db = make_failing_db()

    def override_get_db():
        yield db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), db
    app.dependency_overrides.clear()


def test_create_project_rollback_on_commit_failure(failing_client):
    client, db = failing_client
    response = client.post(
        "/api/v1/projects/",
        json={"name": "Test", "description": "test"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 500
    db.rollback.assert_called()


def test_register_rollback_on_commit_failure():
    db = make_failing_db()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "email": "new@test.com",
                  "password": "pass1234", "full_name": "New User"},
        )
        assert response.status_code == 500
        db.rollback.assert_called()
    finally:
        app.dependency_overrides.clear()
