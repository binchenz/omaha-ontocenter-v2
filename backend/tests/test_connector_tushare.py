import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from app.connectors.tushare_connector import TushareConnector
from app.connectors.base import ColumnDef


@pytest.fixture
def tushare_config():
    return {"token": "test_token_123"}


@pytest.fixture
def obj_def():
    return {
        "api_name": "stock_basic",
        "properties": [
            {"name": "ts_code", "column": "ts_code", "type": "string"},
            {"name": "name", "column": "name", "type": "string"},
            {"name": "industry", "column": "industry", "type": "string"},
        ],
    }


class TestTushareConnector:
    @patch("app.connectors.tushare_connector.ts")
    def test_test_connection_success(self, mock_ts, tushare_config):
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.stock_basic.return_value = pd.DataFrame({"ts_code": ["000001.SZ"]})
        conn = TushareConnector(tushare_config)
        assert conn.test_connection() is True

    @patch("app.connectors.tushare_connector.ts")
    def test_test_connection_bad_token(self, mock_ts, tushare_config):
        mock_ts.pro_api.side_effect = Exception("Invalid token")
        conn = TushareConnector(tushare_config)
        assert conn.test_connection() is False

    def test_discover_schema_from_properties(self, tushare_config, obj_def):
        conn = TushareConnector(tushare_config)
        cols = conn.discover_schema("stock_basic", properties=obj_def["properties"])
        assert len(cols) == 3
        assert cols[0].name == "ts_code"

    @patch("app.connectors.tushare_connector.ts")
    def test_query_basic(self, mock_ts, tushare_config):
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.stock_basic.return_value = pd.DataFrame({
            "ts_code": ["000001.SZ", "600000.SH"],
            "name": ["平安银行", "浦发银行"],
        })
        conn = TushareConnector(tushare_config)
        rows = conn.query(source="stock_basic", columns=["ts_code", "name"], limit=2)
        assert len(rows) == 2
        assert rows[0]["ts_code"] == "000001.SZ"

    @patch("app.connectors.tushare_connector.ts")
    def test_query_with_api_filter(self, mock_ts, tushare_config):
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.stock_basic.return_value = pd.DataFrame({"ts_code": ["000001.SZ"], "name": ["平安银行"]})
        conn = TushareConnector(tushare_config)
        conn.query(source="stock_basic", filters=[{"field": "ts_code", "operator": "=", "value": "000001.SZ"}])
        call_kwargs = mock_pro.stock_basic.call_args[1]
        assert call_kwargs.get("ts_code") == "000001.SZ"

    @patch("app.connectors.tushare_connector.ts")
    def test_query_with_client_side_filter(self, mock_ts, tushare_config):
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.stock_basic.return_value = pd.DataFrame({
            "ts_code": ["000001.SZ", "600000.SH"],
            "name": ["平安银行", "浦发银行"],
        })
        conn = TushareConnector(tushare_config)
        rows = conn.query(source="stock_basic", filters=[{"field": "name", "operator": "=", "value": "平安银行"}])
        assert len(rows) == 1
        assert rows[0]["name"] == "平安银行"
