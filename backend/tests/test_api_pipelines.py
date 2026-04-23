"""Tests for pipeline API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_pipelines.db"
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

SAMPLE_CONFIG = """
datasources:
  - id: test_sqlite
    type: sqlite
    connection:
      database: ./test.db
ontology:
  objects:
    - name: Product
      datasource: test_sqlite
      table: products
      primary_key: id
      properties:
        - name: id
          column: id
          type: integer
        - name: name
          column: name
          type: string
"""


def _auth_headers():
    if "token" not in state:
        client.post("/api/v1/auth/register", json={
            "username": "pipetest", "email": "pipetest@test.com", "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={"username": "pipetest", "password": "testpass123"})
        state["token"] = resp.json()["access_token"]
        proj = client.post("/api/v1/projects/", json={"name": "Pipeline Test", "omaha_config": SAMPLE_CONFIG},
                           headers={"Authorization": f"Bearer {state['token']}"}).json()
        state["project_id"] = proj["id"]
    return {"Authorization": f"Bearer {state['token']}"}


class TestPipelineCRUD:
    def test_list_empty(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.get(f"/api/v1/projects/{pid}/pipelines", headers=h)
        assert resp.status_code == 200
        assert resp.json()["pipelines"] == []

    def test_create_pipeline(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.post(f"/api/v1/projects/{pid}/pipelines", json={
            "name": "Daily Sync",
            "datasource_id": "test_sqlite",
            "object_type": "Product",
            "target_table": "synced_products",
            "schedule": "0 0 * * *",
        }, headers=h)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Daily Sync"
        assert data["status"] == "active"
        assert data["schedule"] == "0 0 * * *"
        state["pipeline_id"] = data["id"]

    def test_list_after_create(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.get(f"/api/v1/projects/{pid}/pipelines", headers=h)
        assert resp.status_code == 200
        assert len(resp.json()["pipelines"]) == 1

    def test_update_pipeline(self):
        h = _auth_headers()
        pid = state["project_id"]
        plid = state["pipeline_id"]
        resp = client.put(f"/api/v1/projects/{pid}/pipelines/{plid}",
                          json={"name": "Hourly Sync", "schedule": "0 * * * *"},
                          headers=h)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Hourly Sync"
        assert resp.json()["schedule"] == "0 * * * *"

    def test_pause_pipeline(self):
        h = _auth_headers()
        pid = state["project_id"]
        plid = state["pipeline_id"]
        resp = client.put(f"/api/v1/projects/{pid}/pipelines/{plid}",
                          json={"status": "paused"}, headers=h)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_non_owner_cannot_create(self):
        client.post("/api/v1/auth/register", json={
            "username": "pipe_other", "email": "pipe_other@test.com", "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={"username": "pipe_other", "password": "testpass123"})
        other_token = resp.json()["access_token"]
        pid = state["project_id"]
        resp = client.post(f"/api/v1/projects/{pid}/pipelines", json={
            "name": "Hack", "datasource_id": "x", "object_type": "X", "target_table": "x"
        }, headers={"Authorization": f"Bearer {other_token}"})
        assert resp.status_code == 403

    def test_delete_pipeline(self):
        h = _auth_headers()
        pid = state["project_id"]
        plid = state["pipeline_id"]
        resp = client.delete(f"/api/v1/projects/{pid}/pipelines/{plid}", headers=h)
        assert resp.status_code == 204
        resp = client.get(f"/api/v1/projects/{pid}/pipelines", headers=h)
        assert resp.json()["pipelines"] == []


class TestPipelineRun:
    def test_run_pipeline_no_config(self):
        h = _auth_headers()
        # Create project without config
        proj = client.post("/api/v1/projects/", json={"name": "No Config"},
                           headers=h).json()
        pid = proj["id"]
        pl = client.post(f"/api/v1/projects/{pid}/pipelines", json={
            "name": "Test", "datasource_id": "x", "object_type": "X", "target_table": "x"
        }, headers=h).json()
        resp = client.post(f"/api/v1/projects/{pid}/pipelines/{pl['id']}/run", headers=h)
        assert resp.status_code == 400
        assert "no ontology config" in resp.json()["detail"].lower()
