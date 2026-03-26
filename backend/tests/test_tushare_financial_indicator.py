"""
测试 FinancialIndicator 对象（财务指标）
基于 Tushare Pro 数据源
"""
import pytest
import os


class TestFinancialIndicator:
    """Test FinancialIndicator queries."""

    def test_query_financial_indicator_basic(self):
        """测试基础查询：查询平安银行的财务指标"""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

        # Set environment variables before importing
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'
        os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

        from app.services.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            selected_columns=["ts_code", "end_date", "eps", "roe", "roa", "gross_margin", "debt_to_assets"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"}
            ],
            limit=5
        )

        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) > 0

        # 验证关键字段存在
        first_record = result["data"][0]
        assert "ts_code" in first_record
        assert "end_date" in first_record
        assert first_record["ts_code"] == "000001.SZ"

        print(f"\n✅ 查询到 {len(result['data'])} 条财务指标记录")
        print(f"最新报告期: {first_record.get('end_date')}")

    def test_query_financial_indicator_with_filters(self):
        """测试过滤条件：查询特定报告期的财务指标"""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

        # Set environment variables before importing
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'
        os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

        from app.services.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            selected_columns=["ts_code", "end_date", "roe", "roa"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"},
                {"field": "start_date", "operator": "=", "value": "20230101"}
            ],
            limit=10
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        # 验证所有记录都满足过滤条件
        for record in result["data"]:
            assert record["ts_code"] == "000001.SZ"
            # start_date 参数会返回该日期之后的数据
            assert record["end_date"] >= "20230101"

        print(f"\n✅ 查询到 {len(result['data'])} 条 2023 年以后的财务指标")

    def test_financial_indicator_fields(self):
        """测试字段验证：验证关键财务指标字段"""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

        # Set environment variables before importing
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'
        os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

        from app.services.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            selected_columns=["ts_code", "end_date", "eps", "roe", "roa", "gross_margin",
                            "debt_to_assets", "current_ratio", "quick_ratio"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"}
            ],
            limit=1
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        record = result["data"][0]

        # 验证盈利能力指标
        assert "roe" in record  # 净资产收益率
        assert "roa" in record  # 总资产报酬率
        assert "gross_margin" in record  # 销售毛利率

        # 验证偿债能力指标
        assert "debt_to_assets" in record  # 资产负债率
        assert "current_ratio" in record  # 流动比率
        assert "quick_ratio" in record  # 速动比率

        # 验证每股指标
        assert "eps" in record  # 每股收益

        print(f"\n✅ 财务指标字段验证通过")
        print(f"报告期: {record.get('end_date')}")
        print(f"ROE: {record.get('roe')}%")
        print(f"ROA: {record.get('roa')}%")
        print(f"资产负债率: {record.get('debt_to_assets')}%")
        print(f"EPS: {record.get('eps')}")
