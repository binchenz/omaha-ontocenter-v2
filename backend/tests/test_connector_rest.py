import pytest
from unittest.mock import patch, MagicMock
import httpx
from app.connectors.rest_connector import RESTConnector


@pytest.fixture
def rest_config():
    return {
        "base_url": "https://api.example.com/v1",
        "auth_type": "bearer",
        "token": "test_token",
    }


def mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


class TestRESTConnector:
    @patch("app.connectors.rest_connector.httpx.get")
    def test_query_basic(self, mock_get, rest_config):
        mock_get.return_value = mock_response([
            {"id": 1, "name": "Order A"},
            {"id": 2, "name": "Order B"},
        ])
        conn = RESTConnector(rest_config)
        rows = conn.query("orders")
        assert len(rows) == 2
        assert rows[0]["name"] == "Order A"

    @patch("app.connectors.rest_connector.httpx.get")
    def test_query_with_response_path(self, mock_get, rest_config):
        rest_config["response_path"] = "data.items"
        mock_get.return_value = mock_response({
            "data": {"items": [{"id": 1}, {"id": 2}], "total": 2}
        })
        conn = RESTConnector(rest_config)
        rows = conn.query("orders")
        assert len(rows) == 2

    @patch("app.connectors.rest_connector.httpx.get")
    def test_query_with_columns(self, mock_get, rest_config):
        mock_get.return_value = mock_response([{"id": 1, "name": "A", "price": 10}])
        conn = RESTConnector(rest_config)
        rows = conn.query("orders", columns=["id", "name"])
        assert set(rows[0].keys()) == {"id", "name"}

    @patch("app.connectors.rest_connector.httpx.get")
    def test_query_with_limit(self, mock_get, rest_config):
        mock_get.return_value = mock_response([{"id": i} for i in range(10)])
        conn = RESTConnector(rest_config)
        rows = conn.query("orders", limit=3)
        assert len(rows) == 3

    @patch("app.connectors.rest_connector.httpx.get")
    def test_auth_bearer(self, mock_get, rest_config):
        mock_get.return_value = mock_response([])
        conn = RESTConnector(rest_config)
        conn.query("orders")
        headers = mock_get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test_token"

    @patch("app.connectors.rest_connector.httpx.get")
    def test_auth_api_key(self, mock_get):
        config = {
            "base_url": "https://api.example.com",
            "auth_type": "api_key",
            "api_key_header": "X-API-Key",
            "token": "my_key",
        }
        mock_get.return_value = mock_response([])
        conn = RESTConnector(config)
        conn.query("data")
        headers = mock_get.call_args[1]["headers"]
        assert headers["X-API-Key"] == "my_key"

    @patch("app.connectors.rest_connector.httpx.get")
    def test_test_connection(self, mock_get, rest_config):
        mock_get.return_value = mock_response({"status": "ok"})
        conn = RESTConnector(rest_config)
        assert conn.test_connection() is True

    @patch("app.connectors.rest_connector.httpx.get")
    def test_test_connection_failure(self, mock_get, rest_config):
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        conn = RESTConnector(rest_config)
        assert conn.test_connection() is False
