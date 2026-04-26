"""Tests for CSV upload auto-patch and tables endpoint."""
import csv
import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_csv_query.db"
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
            "username": "csvtest", "email": "csvtest@test.com", "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={"username": "csvtest", "password": "testpass123"})
        state["token"] = resp.json()["access_token"]
        proj = client.post("/api/v1/projects/", json={"name": "CSV Test"},
                           headers={"Authorization": f"Bearer {state['token']}"}).json()
        state["project_id"] = proj["id"]
    return {"Authorization": f"Bearer {state['token']}"}


class TestTablesEndpoint:
    def test_list_tables_empty(self):
        h = _auth_headers()
        # Use project_id=99999 which will never have a data directory
        resp = client.get("/api/v1/datasources/99999/tables", headers=h)
        # Either 404 (project not found) or 200 with empty list
        assert resp.status_code in (200, 403, 404)
        if resp.status_code == 200:
            assert resp.json()["tables"] == []

    def test_upload_and_list_tables(self, tmp_path):
        h = _auth_headers()
        pid = state["project_id"]

        csv_path = str(tmp_path / "products.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "price"])
            writer.writerow(["1", "Widget", "9.99"])
            writer.writerow(["2", "Gadget", "19.99"])

        with open(csv_path, "rb") as f:
            resp = client.post(
                f"/api/v1/datasources/{pid}/upload",
                files={"file": ("products.csv", f, "text/csv")},
                data={"table_name": "products"},
                headers=h,
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Table should now appear
        resp = client.get(f"/api/v1/datasources/{pid}/tables", headers=h)
        assert resp.status_code == 200
        assert "products" in resp.json()["tables"]


class TestYamlAutoPatch:
    def test_upload_patches_yaml_config(self, tmp_path):
        h = _auth_headers()
        pid = state["project_id"]

        csv_path = str(tmp_path / "orders.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["order_id", "amount", "status"])
            writer.writerow(["1", "100", "paid"])

        with open(csv_path, "rb") as f:
            client.post(
                f"/api/v1/datasources/{pid}/upload",
                files={"file": ("orders.csv", f, "text/csv")},
                data={"table_name": "orders"},
                headers=h,
            )

        # Check project config was patched
        proj = client.get(f"/api/v1/projects/{pid}", headers=h).json()
        config = yaml.safe_load(proj["omaha_config"])

        # csv_imported datasource should exist
        ds_ids = [ds["id"] for ds in config.get("datasources", [])]
        assert "csv_imported" in ds_ids

        # orders object should exist
        obj_names = [o["name"] for o in config.get("ontology", {}).get("objects", [])]
        assert "orders" in obj_names

    def test_upload_adds_to_existing_config(self, tmp_path):
        """Uploading to a project with existing YAML config preserves existing objects."""
        h = _auth_headers()
        # Create a new project with existing config
        existing_config = """
datasources:
  - id: my_db
    type: sqlite
    connection:
      database: ./test.db
ontology:
  objects:
    - name: ExistingObject
      datasource: my_db
      table: existing
      primary_key: id
      properties:
        - name: id
          column: id
          type: integer
"""
        proj = client.post("/api/v1/projects/", json={"name": "Patch Test", "omaha_config": existing_config},
                           headers=h).json()
        pid2 = proj["id"]

        csv_path = str(tmp_path / "new_data.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["col1", "col2"])
            writer.writerow(["a", "b"])

        with open(csv_path, "rb") as f:
            client.post(
                f"/api/v1/datasources/{pid2}/upload",
                files={"file": ("new_data.csv", f, "text/csv")},
                data={"table_name": "new_table"},
                headers=h,
            )

        proj = client.get(f"/api/v1/projects/{pid2}", headers=h).json()
        config = yaml.safe_load(proj["omaha_config"])

        # Both datasources should exist
        ds_ids = [ds["id"] for ds in config.get("datasources", [])]
        assert "my_db" in ds_ids
        assert "csv_imported" in ds_ids

        # Both objects should exist
        obj_names = [o["name"] for o in config.get("ontology", {}).get("objects", [])]
        assert "ExistingObject" in obj_names
        assert "new_table" in obj_names
