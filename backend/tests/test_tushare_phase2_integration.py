"""
Phase 2 集成测试：财务分析场景
测试完整的财务分析流程
"""
import pytest
import os


class TestPhase2Integration:
    """Test Phase 2 integration scenarios."""

    def test_financial_analysis_workflow(self):
        """测试完整的财务分析流程"""
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

        # Step 1: 查询股票基本信息
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

        # Step 2: 查询财务指标
        fi_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            selected_columns=["ts_code", "end_date", "roe", "roa", "debt_to_assets"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": stock["ts_code"]}
            ],
            limit=1
        )

        assert fi_result["success"] is True
        assert len(fi_result["data"]) > 0
        fi = fi_result["data"][0]

        # Step 3: 查询利润表
        is_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="IncomeStatement",
            selected_columns=["ts_code", "end_date", "total_revenue", "n_income"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": stock["ts_code"]}
            ],
            limit=1
        )

        assert is_result["success"] is True
        assert len(is_result["data"]) > 0
        income = is_result["data"][0]

        # Verify data consistency
        assert stock["ts_code"] == fi["ts_code"] == income["ts_code"]

        print(f"\n✅ 完整财务分析流程测试通过")
        print(f"股票: {stock['name']} ({stock['ts_code']})")
        print(f"行业: {stock['industry']}")
        print(f"ROE: {fi.get('roe')}%")
        print(f"资产负债率: {fi.get('debt_to_assets')}%")
        print(f"营业总收入: {income.get('total_revenue')}")
        print(f"净利润: {income.get('n_income')}")

    def test_multi_period_comparison(self):
        """测试多期财务数据对比"""
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

        # Query multiple periods of financial indicators
        fi_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            selected_columns=["ts_code", "end_date", "roe", "roa"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"}
            ],
            limit=4
        )

        assert fi_result["success"] is True
        assert len(fi_result["data"]) >= 2

        # Verify multiple periods
        periods = [record["end_date"] for record in fi_result["data"]]
        assert len(set(periods)) >= 2  # At least 2 different periods

        print(f"\n✅ 多期财务数据对比测试通过")
        print(f"查询到 {len(fi_result['data'])} 期财务指标")
        for record in fi_result["data"]:
            print(f"  {record['end_date']}: ROE={record.get('roe')}%, ROA={record.get('roa')}%")

    def test_fundamental_screening(self):
        """测试基本面选股"""
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

        # Step 1: 查询银行业股票
        stock_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry"],
            filters=[
                {"field": "industry", "operator": "=", "value": "银行"}
            ],
            limit=5
        )

        assert stock_result["success"] is True
        assert len(stock_result["data"]) > 0

        # Step 2: 查询这些股票的财务指标
        for stock in stock_result["data"][:2]:  # Only check first 2 to save API calls
            fi_result = service.query_objects(
                config_yaml=config_yaml,
                object_type="FinancialIndicator",
                selected_columns=["ts_code", "end_date", "roe", "debt_to_assets"],
                filters=[
                    {"field": "ts_code", "operator": "=", "value": stock["ts_code"]}
                ],
                limit=1
            )

            assert fi_result["success"] is True
            if len(fi_result["data"]) > 0:
                fi = fi_result["data"][0]
                print(f"  {stock['name']}: ROE={fi.get('roe')}%, 资产负债率={fi.get('debt_to_assets')}%")

        print(f"\n✅ 基本面选股测试通过")
        print(f"查询到 {len(stock_result['data'])} 只银行股")
