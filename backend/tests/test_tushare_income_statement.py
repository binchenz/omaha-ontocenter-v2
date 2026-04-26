"""
测试 IncomeStatement 对象（利润表）
基于 Tushare Pro 数据源
"""
import pytest
import os


class TestIncomeStatement:
    """Test IncomeStatement queries."""

    def test_query_income_statement_basic(self):
        """测试基础查询：查询平安银行的利润表"""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

        # Set environment variables before importing
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'
        os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

        from app.services.legacy.financial.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/legacy/financial/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="IncomeStatement",
            selected_columns=["ts_code", "end_date", "total_revenue", "revenue",
                            "operate_profit", "total_profit", "n_income"],
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

        print(f"\n✅ 查询到 {len(result['data'])} 条利润表记录")
        print(f"最新报告期: {first_record.get('end_date')}")

    def test_query_income_statement_with_filters(self):
        """测试过滤条件：查询特定报告期的利润表"""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

        # Set environment variables before importing
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'
        os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

        from app.services.legacy.financial.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/legacy/financial/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="IncomeStatement",
            selected_columns=["ts_code", "end_date", "total_revenue", "n_income"],
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
            assert record["end_date"] >= "2023-01-01" or record["end_date"] >= "20230101"

        print(f"\n✅ 查询到 {len(result['data'])} 条 2023 年以后的利润表")

    def test_income_statement_fields(self):
        """测试字段验证：验证关键利润表字段"""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

        # Set environment variables before importing
        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'
        os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

        from app.services.legacy.financial.omaha import OmahaService

        # Load config
        config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/legacy/financial/financial_stock_analysis.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="IncomeStatement",
            selected_columns=["ts_code", "end_date", "total_revenue", "revenue",
                            "operate_profit", "total_profit", "n_income", "n_income_attr_p"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"}
            ],
            limit=1
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        record = result["data"][0]

        # 验证收入字段
        assert "total_revenue" in record  # 营业总收入
        assert "revenue" in record  # 营业收入

        # 验证利润字段
        assert "operate_profit" in record  # 营业利润
        assert "total_profit" in record  # 利润总额
        assert "n_income" in record  # 净利润
        assert "n_income_attr_p" in record  # 归属于母公司的净利润

        print(f"\n✅ 利润表字段验证通过")
        print(f"报告期: {record.get('end_date')}")
        print(f"营业总收入: {record.get('total_revenue')}")
        print(f"营业利润: {record.get('operate_profit')}")
        print(f"净利润: {record.get('n_income')}")
