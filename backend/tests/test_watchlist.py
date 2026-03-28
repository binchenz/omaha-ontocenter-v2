"""Test watchlist API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_add_to_watchlist():
    """Test adding stock to watchlist."""
    # Login first
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "testpass"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add to watchlist
    response = client.post(
        "/api/v1/watchlist/",
        json={"ts_code": "000001.SZ", "note": "等待回调"},
        headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ts_code"] == "000001.SZ"
    assert data["note"] == "等待回调"


def test_list_watchlist():
    """Test listing watchlist."""
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "testpass"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/watchlist/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
