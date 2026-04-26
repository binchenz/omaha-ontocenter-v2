import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_ontology_gen.db"
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
            "username": "gentest", "email": "gentest@test.com", "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={"username": "gentest", "password": "testpass123"})
        state["token"] = resp.json()["access_token"]
    return {"Authorization": f"Bearer {state['token']}"}


class TestGenerateYaml:
    def test_generate_empty_model(self):
        resp = client.post("/api/v1/ontology/generate",
            json={"model": {"datasources": [], "objects": []}},
            headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "yaml" in data
        assert data["valid"] is True

    def test_generate_with_datasource(self):
        resp = client.post("/api/v1/ontology/generate", json={"model": {
            "datasources": [{"id": "db1", "type": "sqlite", "connection": {"database": "./test.db"}}],
            "objects": []
        }}, headers=_auth_headers())
        assert resp.status_code == 200
        yaml_str = resp.json()["yaml"]
        assert "db1" in yaml_str
        assert "sqlite" in yaml_str

    def test_generate_with_object_and_properties(self):
        resp = client.post("/api/v1/ontology/generate", json={"model": {
            "datasources": [{"id": "ds1", "type": "sqlite", "connection": {}}],
            "objects": [{
                "name": "Product",
                "datasource": "ds1",
                "table": "products",
                "primary_key": "id",
                "properties": [
                    {"name": "id", "type": "integer", "column": "id"},
                    {"name": "name", "type": "string", "column": "name", "semantic_type": "text"}
                ],
                "relationships": []
            }]
        }}, headers=_auth_headers())
        assert resp.status_code == 200
        yaml_str = resp.json()["yaml"]
        assert "Product" in yaml_str
        assert "products" in yaml_str
        assert "properties" in yaml_str

    def test_generate_with_relationship(self):
        resp = client.post("/api/v1/ontology/generate", json={"model": {
            "datasources": [{"id": "ds1", "type": "sqlite", "connection": {}}],
            "objects": [{
                "name": "Order",
                "datasource": "ds1",
                "table": "orders",
                "primary_key": "id",
                "properties": [{"name": "id", "type": "integer"}],
                "relationships": [{
                    "name": "items",
                    "to_object": "OrderItem",
                    "type": "one_to_many",
                    "join_condition": {"from_field": "id", "to_field": "order_id"}
                }]
            }]
        }}, headers=_auth_headers())
        assert resp.status_code == 200
        yaml_str = resp.json()["yaml"]
        assert "relationships" in yaml_str
        assert "OrderItem" in yaml_str

    def test_generate_requires_auth(self):
        resp = client.post("/api/v1/ontology/generate",
            json={"model": {"datasources": [], "objects": []}})
        assert resp.status_code == 401
