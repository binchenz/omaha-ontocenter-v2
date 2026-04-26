from pathlib import Path
"""
Test cases for DailyQuote object via Tushare datasource.

Tests the DailyQuote object to verify:
1. Basic queries work with Tushare API
2. All OHLC properties are accessible
3. Date filtering works correctly
4. Stock code filtering works
"""
import pytest
import os


class TestDailyQuoteBasic:
    """Test basic DailyQuote queries."""

    def test_query_daily_quote_basic(self):
        """Test basic query returns daily quote data."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(Path(__file__).resolve().parents[2] / 'configs' / 'legacy' / 'financial' / 'financial_stock_analysis.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "open", "high", "low", "close", "pct_chg"],
            filters=[{"field": "ts_code", "value": "000001.SZ"}],
            limit=10
        )

        # Check result structure
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) > 0

        # Check first row has OHLC data
        first_row = result["data"][0]
        assert "ts_code" in first_row
        assert "trade_date" in first_row
        assert "open" in first_row
        assert "high" in first_row
        assert "low" in first_row
        assert "close" in first_row
        print(f"✓ First quote: {first_row['trade_date']} - Close: {first_row['close']}")

    def test_daily_quote_filter_by_date(self):
        """Test filtering daily quotes by trade date."""
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(Path(__file__).resolve().parents[2] / 'configs' / 'legacy' / 'financial' / 'financial_stock_analysis.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "close", "pct_chg"],
            filters=[
                {"field": "ts_code", "value": "000001.SZ"},
                {"field": "trade_date", "value": "20240101"}
            ],
            limit=5
        )

        # Check result
        assert result["success"] is True
        if len(result["data"]) > 0:
            for row in result["data"]:
                assert row["trade_date"] == "20240101"
            print(f"✓ Found {len(result['data'])} quotes for 2024-01-01")
        else:
            print("✓ No trading on 2024-01-01 (holiday/weekend)")

    def test_daily_quote_volume_data(self):
        """Test that volume and amount data are present."""
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(Path(__file__).resolve().parents[2] / 'configs' / 'legacy' / 'financial' / 'financial_stock_analysis.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "vol", "amount"],
            filters=[{"field": "ts_code", "value": "000001.SZ"}],
            limit=5
        )

        # Check volume data exists
        assert result["success"] is True
        assert len(result["data"]) > 0
        for row in result["data"]:
            assert "vol" in row
            assert "amount" in row
        print(f"✓ Volume data present for {len(result['data'])} records")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
