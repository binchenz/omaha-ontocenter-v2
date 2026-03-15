"""
End-to-end integration tests covering the full user workflow:
Register → Login → Create Project → Configure YAML → Query → Save Asset → Chat
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.api.deps import get_current_user

# --- In-memory SQLite test database ---

SQLALCHEMY_TEST_URL = "sqlite:///./test_e2e.db"
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

# Shared state across tests
state = {}

SAMPLE_OMAHA_CONFIG = """
datasources:
  - id: test_db
    type: sqlite
    connection:
      database: ./test_data.db

ontology:
  objects:
    - name: Product
      datasource: test_db
      table: products
      primary_key: id
      properties:
        - name: id
          column: id
          type: integer
        - name: name
          column: name
          type: string
        - name: price
          column: price
          type: decimal
"""


# ─── Auth Tests ───────────────────────────────────────────────────────────────

class TestAuth:
    def test_register(self):
        response = client.post("/api/v1/auth/register", json={
            "email": "e2e@test.com",
            "username": "e2euser",
            "password": "testpass123",
            "full_name": "E2E User"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "e2e@test.com"
        assert data["username"] == "e2euser"
        state["user_id"] = data["id"]

    def test_register_duplicate_fails(self):
        response = client.post("/api/v1/auth/register", json={
            "email": "e2e@test.com",
            "username": "e2euser",
            "password": "testpass123",
        })
        assert response.status_code == 400

    def test_login(self):
        response = client.post("/api/v1/auth/login", json={
            "username": "e2euser",
            "password": "testpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        state["token"] = data["access_token"]
        state["headers"] = {"Authorization": f"Bearer {data['access_token']}"}

    def test_login_wrong_password(self):
        response = client.post("/api/v1/auth/login", json={
            "username": "e2euser",
            "password": "wrongpass"
        })
        assert response.status_code == 401

    def test_unauthenticated_access_denied(self):
        response = client.get("/api/v1/projects/")
        assert response.status_code == 403


# ─── Project Tests ────────────────────────────────────────────────────────────

class TestProjects:
    def test_create_project(self):
        response = client.post("/api/v1/projects/", json={
            "name": "E2E Test Project",
            "description": "End-to-end test project",
            "omaha_config": SAMPLE_OMAHA_CONFIG
        }, headers=state["headers"])
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "E2E Test Project"
        state["project_id"] = data["id"]

    def test_list_projects(self):
        response = client.get("/api/v1/projects/", headers=state["headers"])
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(p["id"] == state["project_id"] for p in data)

    def test_get_project(self):
        response = client.get(f"/api/v1/projects/{state['project_id']}", headers=state["headers"])
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == state["project_id"]
        assert data["name"] == "E2E Test Project"

    def test_other_user_cannot_access_project(self):
        # Register second user
        client.post("/api/v1/auth/register", json={
            "email": "other@test.com",
            "username": "otheruser",
            "password": "testpass123"
        })
        login = client.post("/api/v1/auth/login", json={
            "username": "otheruser",
            "password": "testpass123"
        })
        other_token = login.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.get(f"/api/v1/projects/{state['project_id']}", headers=other_headers)
        assert response.status_code == 403


# ─── Object Explorer Tests ────────────────────────────────────────────────────

class TestObjectExplorer:
    def test_list_objects(self):
        response = client.get(
            f"/api/v1/query/{state['project_id']}/objects",
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "objects" in data
        assert "Product" in data["objects"]

    def test_get_schema(self):
        response = client.get(
            f"/api/v1/query/{state['project_id']}/schema/Product",
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "columns" in data

    def test_get_relationships(self):
        response = client.get(
            f"/api/v1/query/{state['project_id']}/relationships/Product",
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "relationships" in data

    def test_query_objects(self):
        with patch('app.services.omaha.OmahaService.query_objects') as mock_query:
            mock_query.return_value = {
                "success": True,
                "data": [{"id": 1, "name": "Widget", "price": 9.99}],
                "count": 1
            }
            response = client.post(
                f"/api/v1/query/{state['project_id']}/query",
                json={
                    "object_type": "Product",
                    "selected_columns": ["Product.id", "Product.name"],
                    "limit": 10
                },
                headers=state["headers"]
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1

    def test_query_history(self):
        response = client.get(
            f"/api/v1/query/{state['project_id']}/history",
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ─── Asset Management Tests ───────────────────────────────────────────────────

class TestAssets:
    def test_save_asset(self):
        response = client.post(
            f"/api/v1/assets/{state['project_id']}/assets",
            json={
                "name": "E2E Test Asset",
                "description": "Asset created during E2E test",
                "base_object": "Product",
                "selected_columns": ["Product.id", "Product.name"],
                "filters": [],
                "joins": [],
                "row_count": 1
            },
            headers=state["headers"]
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "E2E Test Asset"
        state["asset_id"] = data["id"]

    def test_list_assets(self):
        response = client.get(
            f"/api/v1/assets/{state['project_id']}/assets",
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(a["id"] == state["asset_id"] for a in data)

    def test_get_asset(self):
        response = client.get(
            f"/api/v1/assets/{state['project_id']}/assets/{state['asset_id']}",
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == state["asset_id"]
        assert data["base_object"] == "Product"

    def test_get_lineage(self):
        response = client.get(
            f"/api/v1/assets/{state['project_id']}/assets/{state['asset_id']}/lineage",
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_delete_asset(self):
        response = client.delete(
            f"/api/v1/assets/{state['project_id']}/assets/{state['asset_id']}",
            headers=state["headers"]
        )
        assert response.status_code == 204

        # Verify deleted
        response = client.get(
            f"/api/v1/assets/{state['project_id']}/assets/{state['asset_id']}",
            headers=state["headers"]
        )
        assert response.status_code == 404


# ─── Chat Agent Tests ─────────────────────────────────────────────────────────

class TestChatAgent:
    def test_create_session(self):
        response = client.post(
            f"/api/v1/chat/{state['project_id']}/sessions",
            json={"title": "E2E Chat Session"},
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == state["project_id"]
        state["session_id"] = data["id"]

    def test_list_sessions(self):
        response = client.get(
            f"/api/v1/chat/{state['project_id']}/sessions",
            headers=state["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["id"] == state["session_id"] for s in data)

    def test_send_message(self):
        with patch('app.services.chat.ChatService.send_message') as mock_send:
            mock_send.return_value = {
                "message": "找到 1 条 Product 记录",
                "data_table": [{"id": 1, "name": "Widget"}],
                "chart_config": None,
                "sql": "SELECT id, name FROM products LIMIT 10"
            }
            response = client.post(
                f"/api/v1/chat/{state['project_id']}/sessions/{state['session_id']}/message",
                json={"message": "查询所有商品"},
                headers=state["headers"]
            )
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"] == "找到 1 条 Product 记录"
            assert data["data_table"] is not None

    def test_send_second_message_multi_turn(self):
        with patch('app.services.chat.ChatService.send_message') as mock_send:
            mock_send.return_value = {
                "message": "价格最高的商品是 Widget，价格 99.99",
                "data_table": [{"name": "Widget", "price": 99.99}],
                "chart_config": {"series": [{"type": "bar", "data": [99.99]}]},
                "sql": None
            }
            response = client.post(
                f"/api/v1/chat/{state['project_id']}/sessions/{state['session_id']}/message",
                json={"message": "哪个商品价格最高？"},
                headers=state["headers"]
            )
            assert response.status_code == 200
            data = response.json()
            assert data["chart_config"] is not None

    def test_session_not_accessible_by_other_user(self):
        login = client.post("/api/v1/auth/login", json={
            "username": "otheruser",
            "password": "testpass123"
        })
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response = client.post(
            f"/api/v1/chat/{state['project_id']}/sessions/{state['session_id']}/message",
            json={"message": "test"},
            headers=other_headers
        )
        assert response.status_code in (403, 404)

    def test_delete_session_cascades_messages(self):
        response = client.delete(
            f"/api/v1/chat/{state['project_id']}/sessions/{state['session_id']}",
            headers=state["headers"]
        )
        assert response.status_code == 200

        # Verify session gone
        response = client.get(
            f"/api/v1/chat/{state['project_id']}/sessions",
            headers=state["headers"]
        )
        assert response.status_code == 200
        sessions = response.json()
        assert not any(s["id"] == state["session_id"] for s in sessions)
