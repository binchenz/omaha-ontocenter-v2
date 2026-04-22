import pytest
from unittest.mock import patch, MagicMock
from app.connectors.mongodb_connector import MongoDBConnector
from app.connectors.base import ColumnDef
from app.connectors import get_connector


@pytest.fixture
def config():
    return {"uri": "mongodb://localhost:27017", "database": "testdb"}


def _make_docs(*docs):
    """Return a mock cursor that iterates over docs."""
    cursor = MagicMock()
    cursor.__iter__ = MagicMock(return_value=iter(list(docs)))
    cursor.limit = MagicMock(return_value=cursor)
    return cursor


class TestMongoDBConnectorRegistry:
    def test_registered(self):
        # Re-import to ensure registration runs even if _CONNECTORS was cleared by other tests
        import importlib
        import app.connectors
        importlib.reload(app.connectors)
        conn = get_connector("mongodb", {"uri": "mongodb://localhost", "database": "db"})
        assert isinstance(conn, MongoDBConnector)


class TestMongoDBConnectorConnection:
    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_connection_success(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        conn = MongoDBConnector(config)
        assert conn.test_connection() is True
        mock_client.admin.command.assert_called_once_with("ping")
        mock_client.close.assert_called_once()

    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_connection_failure(self, mock_client_cls, config):
        mock_client_cls.side_effect = Exception("Connection refused")
        conn = MongoDBConnector(config)
        assert conn.test_connection() is False


class TestMongoDBConnectorDiscoverSchema:
    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_discover_schema(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_col = MagicMock()
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_col.find.return_value = [
            {"_id": "x", "name": "Widget", "price": 9.99, "qty": 100, "active": True},
            {"_id": "y", "name": "Gadget", "price": 19.99, "qty": 50},
        ]

        conn = MongoDBConnector(config)
        cols = conn.discover_schema("products")
        names = [c.name for c in cols]
        assert "name" in names
        assert "price" in names
        assert "qty" in names
        assert "_id" not in names

    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_discover_schema_empty_collection(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_col = MagicMock()
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_col.find.return_value = []

        conn = MongoDBConnector(config)
        cols = conn.discover_schema("empty")
        assert cols == []

    def test_type_inference(self, config):
        conn = MongoDBConnector(config)
        assert conn._infer_type(True) == "boolean"
        assert conn._infer_type(42) == "integer"
        assert conn._infer_type(3.14) == "decimal"
        assert conn._infer_type("hello") == "string"


class TestMongoDBConnectorQuery:
    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_query_all(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_col = MagicMock()
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_col.find.return_value = _make_docs(
            {"name": "Widget", "price": 9.99},
            {"name": "Gadget", "price": 19.99},
        )

        conn = MongoDBConnector(config)
        rows = conn.query("products")
        assert len(rows) == 2
        assert rows[0]["name"] == "Widget"

    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_query_with_limit(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_col = MagicMock()
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        cursor = _make_docs({"name": "Widget"})
        mock_col.find.return_value = cursor

        conn = MongoDBConnector(config)
        conn.query("products", limit=1)
        cursor.limit.assert_called_once_with(1)

    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_query_with_eq_filter(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_col = MagicMock()
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_col.find.return_value = _make_docs({"name": "Widget", "price": 9.99})

        conn = MongoDBConnector(config)
        conn.query("products", filters=[{"field": "name", "operator": "=", "value": "Widget"}])
        call_filter = mock_col.find.call_args[0][0]
        assert call_filter == {"name": "Widget"}

    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_query_with_gt_filter(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_col = MagicMock()
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_col.find.return_value = _make_docs()

        conn = MongoDBConnector(config)
        conn.query("products", filters=[{"field": "price", "operator": ">", "value": "10"}])
        call_filter = mock_col.find.call_args[0][0]
        assert call_filter == {"price": {"$gt": "10"}}

    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_query_with_columns_projection(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_col = MagicMock()
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_col.find.return_value = _make_docs({"name": "Widget"})

        conn = MongoDBConnector(config)
        conn.query("products", columns=["name", "price"])
        call_projection = mock_col.find.call_args[0][1]
        assert call_projection == {"name": 1, "price": 1, "_id": 0}

    @patch("app.connectors.mongodb_connector.MongoClient")
    def test_query_strips_id_field(self, mock_client_cls, config):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_col = MagicMock()
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_col.find.return_value = _make_docs({"_id": "abc123", "name": "Widget"})

        conn = MongoDBConnector(config)
        rows = conn.query("products")
        assert "_id" not in rows[0]
        assert rows[0]["name"] == "Widget"
