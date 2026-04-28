from unittest.mock import Mock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db


def test_health_returns_healthy():
    mock_db = Mock()
    mock_db.execute = Mock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["database"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data
    finally:
        app.dependency_overrides.clear()


def test_health_returns_unhealthy_on_db_failure():
    mock_db = Mock()
    mock_db.execute.side_effect = Exception("connection refused")

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"] == "error"
    finally:
        app.dependency_overrides.clear()
