"""Tests for chat file upload endpoint."""
import pytest
from fastapi.testclient import TestClient


def test_upload_endpoint_requires_auth(client):
    """Without auth token, upload should be rejected."""
    res = client.post(
        "/api/v1/chat/1/sessions/1/upload",
        files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
    )
    assert res.status_code in (401, 403)
