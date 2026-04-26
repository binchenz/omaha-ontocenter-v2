from pathlib import Path
"""
Integration tests for financial data objects.

End-to-end tests covering:
1. Complete query flow from config to results
2. Real-world analysis scenarios
3. Data consistency across objects
"""
import pytest
import os


class TestFinancialDataIntegration:
    """Integration tests for financial data analysis."""

    def test_stock_analysis_workflow(self):
        """Test complete stock analysis workflow."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(Path(__file__).resolve().parents[2] / 'configs' / 'legacy' / 'financial' / 'financial_stock_analysis.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        # Scenario: Analyze banking stocks
        print("\n=== Scenario: Analyze Banking Stocks ===")

        # Step 1: Find banking stocks
        stocks = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry", "area"],
            filters=[{"field": "industry", "value": "银行"}],
            limit=5
        )

        assert stocks["success"] is True
        assert len(stocks["data"]) > 0
        print(f"✓ Found {len(stocks['data'])} banking stocks")

        # Step 2: Get recent quotes for first stock
        first_stock = stocks["data"][0]
        quotes = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["trade_date", "close", "pct_chg", "vol"],
            filters=[{"field": "ts_code", "value": first_stock["ts_code"]}],
            limit=5
        )

        assert quotes["success"] is True
        print(f"✓ Retrieved {len(quotes['data'])} recent quotes for {first_stock['name']}")

        # Step 3: Verify data consistency
        for quote in quotes["data"]:
            assert "trade_date" in quote
            assert "close" in quote
            print(f"  - {quote['trade_date']}: ¥{quote['close']} ({quote.get('pct_chg', 0)}%)")

    def test_industry_comparison_workflow(self):
        """Test industry comparison workflow."""
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(Path(__file__).resolve().parents[2] / 'configs' / 'legacy' / 'financial' / 'financial_stock_analysis.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        print("\n=== Scenario: Compare Industries ===")

        # Step 1: Get list of industries
        industries = service.query_objects(
            config_yaml=config_yaml,
            object_type="Industry",
            selected_columns=["industry"],
            filters=[],
            limit=10
        )

        assert industries["success"] is True
        assert len(industries["data"]) > 0
        print(f"✓ Found {len(industries['data'])} industries")

        # Step 2: Count stocks in each industry
        for industry in industries["data"][:3]:  # Test first 3 industries
            stocks = service.query_objects(
                config_yaml=config_yaml,
                object_type="Stock",
                selected_columns=["ts_code", "name"],
                filters=[{"field": "industry", "value": industry["industry"]}],
                limit=100
            )

            assert stocks["success"] is True
            print(f"  - {industry['industry']}: {len(stocks['data'])} stocks")

    def test_price_trend_analysis(self):
        """Test price trend analysis for a specific stock."""
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(Path(__file__).resolve().parents[2] / 'configs' / 'legacy' / 'financial' / 'financial_stock_analysis.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()

        print("\n=== Scenario: Price Trend Analysis ===")

        # Get stock info
        stock = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            filters=[{"field": "ts_code", "value": "000001.SZ"}],
            limit=1
        )

        assert stock["success"] is True
        assert len(stock["data"]) == 1
        stock_info = stock["data"][0]
        print(f"✓ Analyzing: {stock_info['name']} ({stock_info['ts_code']})")

        # Get recent price data
        quotes = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["trade_date", "close", "pct_chg", "vol", "amount"],
            filters=[{"field": "ts_code", "value": stock_info["ts_code"]}],
            limit=10
        )

        assert quotes["success"] is True
        assert len(quotes["data"]) > 0
        print(f"✓ Retrieved {len(quotes['data'])} trading days")

        # Calculate simple statistics
        closes = [float(q["close"]) for q in quotes["data"]]
        avg_price = sum(closes) / len(closes)
        max_price = max(closes)
        min_price = min(closes)

        print(f"  - Average: ¥{avg_price:.2f}")
        print(f"  - High: ¥{max_price:.2f}")
        print(f"  - Low: ¥{min_price:.2f}")

    def test_config_validation(self):
        """Test that configuration is valid and complete."""
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(Path(__file__).resolve().parents[2] / 'configs' / 'legacy' / 'financial' / 'financial_stock_analysis.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()

        # Parse config
        result = service.parse_config(config_yaml)
        assert result["valid"] is True
        assert "config" in result

        config = result["config"]

        # Verify datasources
        assert "datasources" in config
        assert len(config["datasources"]) > 0
        assert config["datasources"][0]["type"] == "tushare"

        # Verify ontology
        assert "ontology" in config
        ontology = config["ontology"]

        # Verify objects
        assert "objects" in ontology
        object_names = [obj["name"] for obj in ontology["objects"]]
        assert "Stock" in object_names
        assert "DailyQuote" in object_names
        assert "Industry" in object_names

        # Verify relationships
        assert "relationships" in ontology
        rel_names = [rel["name"] for rel in ontology["relationships"]]
        assert "stock_daily_quotes" in rel_names
        assert "stock_industry" in rel_names

        print("✓ Configuration is valid and complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


def test_financial_config_uses_environment_token():
    """Assert the financial config uses ${TUSHARE_TOKEN} and not a hardcoded token."""
    from pathlib import Path

    config_path = Path(__file__).resolve().parents[2] / "configs" / "legacy" / "financial" / "financial_stock_analysis.yaml"
    content = config_path.read_text(encoding="utf-8")

    assert "${TUSHARE_TOKEN}" in content, "Expected ${TUSHARE_TOKEN} placeholder in config"
    assert "044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90" not in content, (
        "Hardcoded Tushare token must not appear in config"
    )
