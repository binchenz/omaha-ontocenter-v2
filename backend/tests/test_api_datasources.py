import csv
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_datasources.db"
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
"""


def _auth_headers():
    if "token" not in state:
        client.post("/api/v1/auth/register", json={
            "username": "dstest", "email": "dstest@test.com", "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "dstest", "password": "testpass123"
        })
        state["token"] = resp.json()["access_token"]
        proj = client.post("/api/v1/projects/", json={
            "name": "DS Test", "omaha_config": SAMPLE_CONFIG
        }, headers={"Authorization": f"Bearer {state['token']}"}).json()
        state["project_id"] = proj["id"]
    return {"Authorization": f"Bearer {state['token']}"}


class TestDatasourceList:
    def test_list_datasources(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.get(f"/api/v1/datasources/{pid}/list", headers=h)
        assert resp.status_code == 200
        ds = resp.json()["datasources"]
        assert len(ds) >= 1
        assert ds[0]["id"] == "test_sqlite"
        assert ds[0]["type"] == "sqlite"


class TestDatasourceTest:
    def test_test_connection_sqlite(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.post(f"/api/v1/datasources/{pid}/test", json={
            "type": "sqlite",
            "connection": {"database": "./test.db"}
        }, headers=h)
        assert resp.status_code == 200
        assert "connected" in resp.json()


class TestDatasourceUpload:
    def test_upload_csv(self, tmp_path):
        h = _auth_headers()
        pid = state["project_id"]
        csv_path = str(tmp_path / "test.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "value"])
            writer.writerow(["1", "A", "100"])
            writer.writerow(["2", "B", "200"])

        with open(csv_path, "rb") as f:
            resp = client.post(
                f"/api/v1/datasources/{pid}/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"table_name": "uploaded_test"},
                headers=h,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["columns"]) == 3
