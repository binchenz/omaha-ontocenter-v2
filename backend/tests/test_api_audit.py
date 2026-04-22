"""Tests for audit log API and service."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.services.audit import log_action, get_audit_logs

SQLALCHEMY_TEST_URL = "sqlite:///./test_audit.db"
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


def _auth_headers():
    if "token" not in state:
        client.post("/api/v1/auth/register", json={
            "username": "audituser", "email": "audit@test.com", "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={"username": "audituser", "password": "testpass123"})
        state["token"] = resp.json()["access_token"]
        proj = client.post("/api/v1/projects/", json={"name": "Audit Test"},
                           headers={"Authorization": f"Bearer {state['token']}"}).json()
        state["project_id"] = proj["id"]
    return {"Authorization": f"Bearer {state['token']}"}


class TestAuditService:
    def test_log_action_creates_record(self):
        db = TestingSessionLocal()
        try:
            entry = log_action(db, action="test.action", user_id=1, project_id=1,
                               resource_type="test", resource_id="42",
                               detail={"key": "value"})
            assert entry.id is not None
            assert entry.action == "test.action"
            assert entry.detail == {"key": "value"}
        finally:
            db.close()

    def test_get_audit_logs_filters_by_project(self):
        db = TestingSessionLocal()
        try:
            log_action(db, action="query.run", project_id=999, user_id=1)
            log_action(db, action="query.run", project_id=888, user_id=1)
            logs = get_audit_logs(db, project_id=999)
            assert all(log.project_id == 999 for log in logs)
        finally:
            db.close()

    def test_get_audit_logs_filters_by_action(self):
        db = TestingSessionLocal()
        try:
            log_action(db, action="config.save", project_id=777, user_id=1)
            log_action(db, action="query.run", project_id=777, user_id=1)
            logs = get_audit_logs(db, project_id=777, action="config.save")
            assert all(log.action == "config.save" for log in logs)
        finally:
            db.close()

    def test_get_audit_logs_limit(self):
        db = TestingSessionLocal()
        try:
            for _ in range(5):
                log_action(db, action="test.limit", project_id=666, user_id=1)
            logs = get_audit_logs(db, project_id=666, limit=3)
            assert len(logs) <= 3
        finally:
            db.close()


class TestAuditAPI:
    def test_list_audit_logs(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.get(f"/api/v1/projects/{pid}/audit-logs", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert "total" in data

    def test_project_create_generates_audit_log(self):
        h = _auth_headers()
        # Create a new project — should generate project.create audit entry
        proj = client.post("/api/v1/projects/", json={"name": "Audit Tracked"},
                           headers=h).json()
        pid = proj["id"]
        resp = client.get(f"/api/v1/projects/{pid}/audit-logs", headers=h)
        assert resp.status_code == 200
        actions = [log["action"] for log in resp.json()["logs"]]
        assert "project.create" in actions

    def test_config_save_generates_audit_log(self):
        h = _auth_headers()
        pid = state["project_id"]
        client.put(f"/api/v1/projects/{pid}",
                   json={"name": "Audit Test", "omaha_config": "datasources: []"},
                   headers=h)
        resp = client.get(f"/api/v1/projects/{pid}/audit-logs", headers=h)
        actions = [log["action"] for log in resp.json()["logs"]]
        assert "config.save" in actions

    def test_filter_by_action(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.get(f"/api/v1/projects/{pid}/audit-logs?action=config.save", headers=h)
        assert resp.status_code == 200
        for log in resp.json()["logs"]:
            assert log["action"] == "config.save"

    def test_non_owner_cannot_access_audit_logs(self):
        # Register another user
        client.post("/api/v1/auth/register", json={
            "username": "audit_other", "email": "audit_other@test.com", "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={"username": "audit_other", "password": "testpass123"})
        other_token = resp.json()["access_token"]
        pid = state["project_id"]
        resp = client.get(f"/api/v1/projects/{pid}/audit-logs",
                          headers={"Authorization": f"Bearer {other_token}"})
        assert resp.status_code == 403
