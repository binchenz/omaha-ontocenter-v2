"""
测试 Phase 2 财务对象的关系
测试 Stock 与 FinancialIndicator、IncomeStatement 的关联查询
"""
import pytest
import os


class TestPhase2Relationships:
    """Test Phase 2 object relationships."""

    def test_stock_with_financial_indicators(self):
        """测试 Stock 与 FinancialIndicator 的关联查询"""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

        # Set environment variables before importing
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'
        os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

        from app.services.legacy.financial.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()

        # Query Stock
        stock_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"}
            ],
            limit=1
        )

        assert stock_result["success"] is True
        assert len(stock_result["data"]) > 0
        stock = stock_result["data"][0]

        # Query FinancialIndicator for the same stock
        fi_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            selected_columns=["ts_code", "end_date", "roe", "roa"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": stock["ts_code"]}
            ],
            limit=3
        )

        assert fi_result["success"] is True
        assert len(fi_result["data"]) > 0

        # Verify relationship
        for fi in fi_result["data"]:
            assert fi["ts_code"] == stock["ts_code"]

        print(f"\n✅ 股票 {stock['name']} 关联了 {len(fi_result['data'])} 条财务指标")

    def test_stock_with_income_statements(self):
        """测试 Stock 与 IncomeStatement 的关联查询"""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

        # Set environment variables before importing
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'
        os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

        from app.services.legacy.financial.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()

        # Query Stock
        stock_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"}
            ],
            limit=1
        )

        assert stock_result["success"] is True
        assert len(stock_result["data"]) > 0
        stock = stock_result["data"][0]

        # Query IncomeStatement for the same stock
        is_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="IncomeStatement",
            selected_columns=["ts_code", "end_date", "total_revenue", "n_income"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": stock["ts_code"]}
            ],
            limit=3
        )

        assert is_result["success"] is True
        assert len(is_result["data"]) > 0

        # Verify relationship
        for income in is_result["data"]:
            assert income["ts_code"] == stock["ts_code"]

        print(f"\n✅ 股票 {stock['name']} 关联了 {len(is_result['data'])} 条利润表")
