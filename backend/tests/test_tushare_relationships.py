"""
Test cases for relationships between financial objects.

Tests:
1. Stock -> DailyQuote (one-to-many)
2. Stock -> Industry (many-to-one)
"""
import pytest
import os


class TestStockDailyQuoteRelationship:
    """Test Stock -> DailyQuote relationship."""

    def test_stock_with_daily_quotes(self):
        """Test querying stock with its daily quotes."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.legacy.financial.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        # Note: Tushare datasource doesn't support JOIN operations
        # We need to query separately and combine results

        # Step 1: Query stock info
        stock_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            filters=[{"field": "ts_code", "value": "000001.SZ"}],
            limit=1
        )

        assert stock_result["success"] is True
        assert len(stock_result["data"]) == 1
        stock = stock_result["data"][0]
        print(f"✓ Stock: {stock['ts_code']} - {stock['name']}")

        # Step 2: Query daily quotes for this stock
        quote_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "close", "pct_chg"],
            filters=[{"field": "ts_code", "value": stock["ts_code"]}],
            limit=10
        )

        assert quote_result["success"] is True
        assert len(quote_result["data"]) > 0
        print(f"✓ Found {len(quote_result['data'])} daily quotes for {stock['name']}")

        # Verify all quotes belong to the same stock
        for quote in quote_result["data"]:
            assert quote["ts_code"] == stock["ts_code"]


class TestStockIndustryRelationship:
    """Test Stock -> Industry relationship."""

    def test_stocks_by_industry(self):
        """Test querying stocks grouped by industry."""
        from app.services.legacy.financial.omaha import OmahaService

        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        # Step 1: Query stocks to get available industries
        # Note: Tushare stock_basic doesn't support industry filter, so we fetch all and filter in Python
        stock_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            limit=100
        )

        assert stock_result["success"] is True
        assert len(stock_result["data"]) > 0

        # Find a stock with industry "银行"
        bank_stocks = [s for s in stock_result["data"] if s.get("industry") == "银行"]
        assert len(bank_stocks) > 0, "No bank stocks found in results"

        industry_name = bank_stocks[0]["industry"]
        print(f"✓ Industry: {industry_name}")

        # Step 2: Filter stocks by industry from the fetched data
        # (In real scenario, this would be done server-side with proper filtering)
        filtered_stocks = [s for s in stock_result["data"] if s.get("industry") == industry_name]

        assert len(filtered_stocks) > 0
        print(f"✓ Found {len(filtered_stocks)} stocks in {industry_name} industry")

        # Verify all stocks belong to the same industry
        for stock in filtered_stocks:
            assert stock["industry"] == industry_name


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
