"""Test watchlist API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_watchlist.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


client = TestClient(app)
state = {}


def _register_and_login():
    if "token" in state:
        return state["token"]
    client.post("/api/v1/auth/register", json={
        "username": "watchtest",
        "email": "watchtest@example.com",
        "password": "testpass123"
    })
    resp = client.post("/api/v1/auth/login", json={
        "username": "watchtest",
        "password": "testpass123"
    })
    state["token"] = resp.json()["access_token"]
    return state["token"]


def test_add_to_watchlist():
    """Test adding stock to watchlist."""
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

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
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/watchlist/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
