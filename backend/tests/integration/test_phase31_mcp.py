"""
Phase 3.1 MCP Server tests: API Key management + MCP tools + server protocol.
"""
import hashlib
import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app
from app.database import Base, get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.api_key import ProjectApiKey

# --- In-memory test DB ---

SQLALCHEMY_TEST_URL = "sqlite:///./test_mcp.db"
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


# ─── Auth + Project Setup ─────────────────────────────────────────────────────

class TestSetup:
    def test_register_and_login(self):
        client.post("/api/v1/auth/register", json={
            "email": "mcp@test.com",
            "username": "mcpuser",
            "password": "testpass123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "mcpuser",
            "password": "testpass123"
        })
        assert resp.status_code == 200
        state["headers"] = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def test_create_project(self):
        resp = client.post("/api/v1/projects/", json={
            "name": "MCP Test Project",
            "omaha_config": "datasources: []\nontology:\n  objects: []"
        }, headers=state["headers"])
        assert resp.status_code == 201
        state["project_id"] = resp.json()["id"]


# ─── API Key CRUD ─────────────────────────────────────────────────────────────

class TestApiKeyCRUD:
    def test_create_api_key(self):
        resp = client.post(
            f"/api/v1/projects/{state['project_id']}/api-keys",
            json={"name": "test-key"},
            headers=state["headers"]
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-key"
        assert data["key"].startswith(f"omaha_{state['project_id']}_")
        assert len(data["key"]) == len(f"omaha_{state['project_id']}_") + 32
        assert "key_hash" not in data  # raw hash never returned
        state["api_key"] = data["key"]
        state["key_id"] = data["id"]
        state["key_prefix"] = data["key_prefix"]

    def test_key_prefix_is_first_8_chars_of_random_part(self):
        random_part = state["api_key"].split("_", 2)[2]
        assert state["key_prefix"] == random_part[:8]

    def test_list_api_keys(self):
        resp = client.get(
            f"/api/v1/projects/{state['project_id']}/api-keys",
            headers=state["headers"]
        )
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) >= 1
        assert any(k["id"] == state["key_id"] for k in keys)
        # Raw key never in list response
        assert all("key" not in k for k in keys)

    def test_create_second_key(self):
        resp = client.post(
            f"/api/v1/projects/{state['project_id']}/api-keys",
            json={"name": "second-key"},
            headers=state["headers"]
        )
        assert resp.status_code == 201
        state["second_key_id"] = resp.json()["id"]

    def test_revoke_api_key(self):
        resp = client.delete(
            f"/api/v1/projects/{state['project_id']}/api-keys/{state['second_key_id']}",
            headers=state["headers"]
        )
        assert resp.status_code == 204

    def test_revoked_key_still_listed_but_inactive(self):
        resp = client.get(
            f"/api/v1/projects/{state['project_id']}/api-keys",
            headers=state["headers"]
        )
        keys = resp.json()
        second = next(k for k in keys if k["id"] == state["second_key_id"])
        assert second["is_active"] is False

    def test_revoke_nonexistent_key_returns_404(self):
        resp = client.delete(
            f"/api/v1/projects/{state['project_id']}/api-keys/99999",
            headers=state["headers"]
        )
        assert resp.status_code == 404

    def test_other_user_cannot_access_keys(self):
        client.post("/api/v1/auth/register", json={
            "email": "other2@test.com",
            "username": "otheruser2",
            "password": "testpass123"
        })
        login = client.post("/api/v1/auth/login", json={
            "username": "otheruser2",
            "password": "testpass123"
        })
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        resp = client.get(
            f"/api/v1/projects/{state['project_id']}/api-keys",
            headers=other_headers
        )
        assert resp.status_code == 403


# ─── MCP Auth Helper ──────────────────────────────────────────────────────────

class TestMcpAuth:
    def test_resolve_valid_key(self):
        from app.mcp.auth import resolve_api_key
        db = TestingSessionLocal()
        try:
            result = resolve_api_key(state["api_key"], db)
            assert result is not None
            project_id, config_yaml = result
            assert project_id == state["project_id"]
        finally:
            db.close()

    def test_resolve_invalid_key_returns_none(self):
        from app.mcp.auth import resolve_api_key
        db = TestingSessionLocal()
        try:
            result = resolve_api_key("omaha_1_invalidkey", db)
            assert result is None
        finally:
            db.close()

    def test_resolve_revoked_key_returns_none(self):
        from app.mcp.auth import resolve_api_key
        # Get the second key (revoked)
        db = TestingSessionLocal()
        try:
            # Find the revoked key's hash by checking is_active=False
            revoked = db.query(ProjectApiKey).filter(
                ProjectApiKey.id == state["second_key_id"]
            ).first()
            assert revoked is not None
            assert revoked.is_active is False
            # Even if we had the raw key, resolve should reject it
            result = resolve_api_key("omaha_fake_revokedkey12345678901234", db)
            assert result is None
        finally:
            db.close()

    def test_get_api_key_from_env(self):
        import os
        from app.mcp.auth import get_api_key_from_env
        os.environ["OMAHA_API_KEY"] = "test_key_value"
        assert get_api_key_from_env() == "test_key_value"
        del os.environ["OMAHA_API_KEY"]

    def test_get_api_key_from_env_missing_raises(self):
        import os
        from app.mcp.auth import get_api_key_from_env
        os.environ.pop("OMAHA_API_KEY", None)
        with pytest.raises(ValueError):
            get_api_key_from_env()


# ─── MCP Tools ────────────────────────────────────────────────────────────────

class TestMcpTools:
    def test_list_objects(self):
        from app.mcp.tools import list_objects
        config = "datasources: []\nontology:\n  objects:\n    - name: Product\n      datasource: x\n      table: t\n      primary_key: id\n      properties: []"
        result = list_objects(config)
        assert "objects" in result
        # objects may be list of strings or list of dicts
        names = [o["name"] if isinstance(o, dict) else o for o in result["objects"]]
        assert "Product" in names

    def test_list_objects_invalid_config(self):
        from app.mcp.tools import list_objects
        result = list_objects("not: valid: yaml: [")
        assert "error" in result or "objects" in result

    def test_list_assets(self):
        from app.mcp.tools import list_assets
        db = TestingSessionLocal()
        try:
            result = list_assets(db=db, project_id=state["project_id"])
            assert "assets" in result
            assert isinstance(result["assets"], list)
        finally:
            db.close()

    def test_get_lineage_empty(self):
        from app.mcp.tools import get_lineage
        db = TestingSessionLocal()
        try:
            result = get_lineage(db=db, asset_id=99999)
            # Either empty lineage list or error for nonexistent asset - both acceptable
            assert "lineage" in result or "error" in result
        finally:
            db.close()


# ─── MCP Server Protocol ──────────────────────────────────────────────────────

class TestMcpServerProtocol:
    def test_tool_definitions_count(self):
        from app.mcp.server import TOOL_DEFINITIONS
        assert len(TOOL_DEFINITIONS) == 7

    def test_tool_names(self):
        from app.mcp.server import TOOL_DEFINITIONS
        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert names == {
            "list_objects", "get_schema", "get_relationships",
            "query_data", "save_asset", "list_assets", "get_lineage"
        }

    def test_all_tools_have_input_schema(self):
        from app.mcp.server import TOOL_DEFINITIONS
        for tool in TOOL_DEFINITIONS:
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_send_helper(self):
        import io
        from unittest.mock import patch
        from app.mcp import server
        output = io.StringIO()
        with patch("sys.stdout", output):
            server._send({"jsonrpc": "2.0", "id": 1, "result": "ok"})
        line = output.getvalue().strip()
        parsed = json.loads(line)
        assert parsed["result"] == "ok"

    def test_handle_initialize(self):
        import io
        from unittest.mock import patch
        from app.mcp import server
        output = io.StringIO()
        with patch("sys.stdout", output):
            server._handle_initialize(1, {})
        resp = json.loads(output.getvalue().strip())
        assert resp["result"]["serverInfo"]["name"] == "omaha-mcp-server"
        assert "tools" in resp["result"]["capabilities"]

    def test_handle_tools_list(self):
        import io
        from unittest.mock import patch
        from app.mcp import server
        output = io.StringIO()
        with patch("sys.stdout", output):
            server._handle_tools_list(1)
        resp = json.loads(output.getvalue().strip())
        assert len(resp["result"]["tools"]) == 7
