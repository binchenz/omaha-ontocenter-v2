"""Tests for project membership API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_members.db"
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


def _register_login(username: str, email: str, password: str = "testpass123") -> str:
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def setup_users():
    owner_token = _register_login("mem_owner", "mem_owner@test.com")
    editor_token = _register_login("mem_editor", "mem_editor@test.com")
    viewer_token = _register_login("mem_viewer", "mem_viewer@test.com")
    outsider_token = _register_login("mem_outsider", "mem_outsider@test.com")

    proj = client.post("/api/v1/projects/", json={"name": "Member Test Project"},
                       headers=_headers(owner_token)).json()
    return {
        "owner": owner_token,
        "editor": editor_token,
        "viewer": viewer_token,
        "outsider": outsider_token,
        "project_id": proj["id"],
    }


class TestListMembers:
    def test_owner_can_list(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.get(f"/api/v1/projects/{pid}/members", headers=_headers(setup_users["owner"]))
        assert resp.status_code == 200
        assert "members" in resp.json()

    def test_outsider_cannot_list(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.get(f"/api/v1/projects/{pid}/members", headers=_headers(setup_users["outsider"]))
        assert resp.status_code == 403


class TestAddMember:
    def test_owner_can_add_editor(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.post(f"/api/v1/projects/{pid}/members",
                           json={"username": "mem_editor", "role": "editor"},
                           headers=_headers(setup_users["owner"]))
        assert resp.status_code == 200
        assert resp.json()["role"] == "editor"

    def test_owner_can_add_viewer(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.post(f"/api/v1/projects/{pid}/members",
                           json={"username": "mem_viewer", "role": "viewer"},
                           headers=_headers(setup_users["owner"]))
        assert resp.status_code == 200

    def test_duplicate_add_fails(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.post(f"/api/v1/projects/{pid}/members",
                           json={"username": "mem_editor", "role": "editor"},
                           headers=_headers(setup_users["owner"]))
        assert resp.status_code == 409

    def test_invalid_role_fails(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.post(f"/api/v1/projects/{pid}/members",
                           json={"username": "mem_outsider", "role": "superadmin"},
                           headers=_headers(setup_users["owner"]))
        assert resp.status_code == 400

    def test_unknown_user_fails(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.post(f"/api/v1/projects/{pid}/members",
                           json={"username": "nobody_xyz", "role": "viewer"},
                           headers=_headers(setup_users["owner"]))
        assert resp.status_code == 404

    def test_non_owner_cannot_add(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.post(f"/api/v1/projects/{pid}/members",
                           json={"username": "mem_outsider", "role": "viewer"},
                           headers=_headers(setup_users["editor"]))
        assert resp.status_code == 403


class TestMemberAccess:
    def test_member_can_list_members(self, setup_users):
        pid = setup_users["project_id"]
        resp = client.get(f"/api/v1/projects/{pid}/members", headers=_headers(setup_users["editor"]))
        assert resp.status_code == 200
        usernames = [m["username"] for m in resp.json()["members"]]
        assert "mem_editor" in usernames
        assert "mem_viewer" in usernames


class TestUpdateRole:
    def test_owner_can_update_role(self, setup_users):
        pid = setup_users["project_id"]
        # Get viewer's user_id
        members = client.get(f"/api/v1/projects/{pid}/members",
                             headers=_headers(setup_users["owner"])).json()["members"]
        viewer = next(m for m in members if m["username"] == "mem_viewer")
        resp = client.put(f"/api/v1/projects/{pid}/members/{viewer['user_id']}",
                          json={"role": "editor"},
                          headers=_headers(setup_users["owner"]))
        assert resp.status_code == 200
        assert resp.json()["role"] == "editor"

    def test_non_owner_cannot_update_role(self, setup_users):
        pid = setup_users["project_id"]
        members = client.get(f"/api/v1/projects/{pid}/members",
                             headers=_headers(setup_users["owner"])).json()["members"]
        viewer = next(m for m in members if m["username"] == "mem_viewer")
        resp = client.put(f"/api/v1/projects/{pid}/members/{viewer['user_id']}",
                          json={"role": "viewer"},
                          headers=_headers(setup_users["editor"]))
        assert resp.status_code == 403


class TestRemoveMember:
    def test_owner_can_remove_member(self, setup_users):
        pid = setup_users["project_id"]
        # Add outsider first
        client.post(f"/api/v1/projects/{pid}/members",
                    json={"username": "mem_outsider", "role": "viewer"},
                    headers=_headers(setup_users["owner"]))
        members = client.get(f"/api/v1/projects/{pid}/members",
                             headers=_headers(setup_users["owner"])).json()["members"]
        outsider = next(m for m in members if m["username"] == "mem_outsider")
        resp = client.delete(f"/api/v1/projects/{pid}/members/{outsider['user_id']}",
                             headers=_headers(setup_users["owner"]))
        assert resp.status_code == 200
        assert resp.json()["removed"] is True
