import pytest
from app.connectors.base import BaseConnector, ColumnDef
from app.connectors.registry import register, get_connector, _CONNECTORS


class FakeConnector(BaseConnector):
    def test_connection(self) -> bool:
        return self.config.get("valid", True)

    def discover_schema(self, source: str) -> list[ColumnDef]:
        return [ColumnDef(name="id", type="integer", nullable=False)]

    def query(self, source, columns=None, filters=None, limit=None):
        return [{"id": 1, "name": "test"}]


class TestColumnDef:
    def test_defaults(self):
        col = ColumnDef(name="price", type="decimal")
        assert col.nullable is True
        assert col.description == ""

    def test_all_fields(self):
        col = ColumnDef(name="ts_code", type="string", nullable=False, description="股票代码")
        assert col.name == "ts_code"
        assert col.nullable is False


class TestBaseConnector:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseConnector(config={})

    def test_concrete_implementation(self):
        conn = FakeConnector(config={"valid": True})
        assert conn.test_connection() is True
        assert len(conn.discover_schema("test")) == 1
        assert conn.query("test")[0]["id"] == 1

    def test_close_is_noop_by_default(self):
        conn = FakeConnector(config={})
        conn.close()


class TestRegistry:
    def setup_method(self):
        _CONNECTORS.clear()

    def test_register_and_get(self):
        register("fake", FakeConnector)
        conn = get_connector("fake", {"valid": True})
        assert isinstance(conn, FakeConnector)
        assert conn.test_connection() is True

    def test_get_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown datasource type"):
            get_connector("nonexistent", {})

    def test_register_multiple_types_same_class(self):
        register("type_a", FakeConnector)
        register("type_b", FakeConnector)
        assert isinstance(get_connector("type_a", {}), FakeConnector)
        assert isinstance(get_connector("type_b", {}), FakeConnector)
