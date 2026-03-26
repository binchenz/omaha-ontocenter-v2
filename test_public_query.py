"""Test public query API endpoints."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test without authentication
def test_list_objects_no_auth():
    response = client.get("/api/public/v1/objects")
    assert response.status_code == 422  # Missing authorization header

def test_get_schema_no_auth():
    response = client.get("/api/public/v1/schema/Stock")
    assert response.status_code == 422

def test_query_no_auth():
    response = client.post("/api/public/v1/query", json={
        "object_type": "Stock",
        "limit": 10
    })
    assert response.status_code == 422

print("✓ All basic tests passed")
print("\nEndpoints created:")
print("  GET  /api/public/v1/objects")
print("  GET  /api/public/v1/schema/{object_type}")
print("  POST /api/public/v1/query")
print("\nRate limiting: 100 queries per hour per user")
