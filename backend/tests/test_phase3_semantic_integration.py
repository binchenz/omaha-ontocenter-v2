"""
Phase 3 集成测试：语义类型和计算属性
"""

import pytest
import yaml
from app.services.omaha import OmahaService


class TestPhase3SemanticIntegration:
    """测试 Phase 3 语义增强功能的集成"""

    @pytest.fixture
    def omaha_service(self):
        """创建 OmahaService 实例"""
        return OmahaService()

    @pytest.fixture
    def config_yaml(self):
        """加载配置文件"""
        import os
        # 获取项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(project_root, 'configs', 'financial_stock_analysis.yaml')

        with open(config_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_financial_indicator_with_semantic_types(self, omaha_service, config_yaml):
        """测试财务指标的语义类型格式化"""
        result = omaha_service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            filters=[
                {"field": "ts_code", "value": "000001.SZ"},
                {"field": "end_date", "value": "20231231"}
            ],
            limit=1
        )

        assert result["success"] is True
        assert result["count"] > 0

        data = result["data"][0]

        # 验证语义类型格式化
        # stock_code 应该保持原样
        assert data["ts_code"] == "000001.SZ"

        # date 应该格式化为 YYYY-MM-DD
        assert data["end_date"] == "2023-12-31"

        # percentage 应该格式化为百分比字符串
        if "roe" in data and data["roe"]:
            assert "%" in str(data["roe"])

        # currency_cny 应该格式化为人民币
        if "ebit" in data and data["ebit"]:
            assert "¥" in str(data["ebit"])

    def test_financial_indicator_with_computed_properties(self, omaha_service, config_yaml):
        """测试财务指标的计算属性"""
        result = omaha_service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            filters=[
                {"field": "ts_code", "value": "000001.SZ"},
                {"field": "end_date", "value": "20231231"}
            ],
            limit=1
        )

        assert result["success"] is True
        assert result["count"] > 0

        data = result["data"][0]

        # 验证计算属性存在
        assert "financial_health_score" in data

        # 验证计算属性已格式化
        if data["financial_health_score"]:
            assert "%" in str(data["financial_health_score"])

    def test_income_statement_with_semantic_types(self, omaha_service, config_yaml):
        """测试利润表的语义类型格式化"""
        result = omaha_service.query_objects(
            config_yaml=config_yaml,
            object_type="IncomeStatement",
            filters=[
                {"field": "ts_code", "value": "000001.SZ"}
            ],
            limit=1
        )

        assert result["success"] is True
        assert result["count"] > 0

        data = result["data"][0]

        # 验证语义类型格式化
        assert data["ts_code"] == "000001.SZ"

        # 验证日期格式化（格式应该是 YYYY-MM-DD）
        assert "-" in data["end_date"]
        assert len(data["end_date"]) == 10

        # 验证金额格式化
        if "total_revenue" in data and data["total_revenue"]:
            assert "¥" in str(data["total_revenue"])

    def test_income_statement_with_computed_properties(self, omaha_service, config_yaml):
        """测试利润表的计算属性"""
        result = omaha_service.query_objects(
            config_yaml=config_yaml,
            object_type="IncomeStatement",
            filters=[
                {"field": "ts_code", "value": "000001.SZ"},
                {"field": "end_date", "value": "20231231"}
            ],
            limit=1
        )

        assert result["success"] is True
        assert result["count"] > 0

        data = result["data"][0]

        # 验证计算属性存在
        assert "profit_margin" in data
        assert "operating_margin" in data

        # 验证计算属性已格式化
        if data["profit_margin"]:
            assert "%" in str(data["profit_margin"])
        if data["operating_margin"]:
            assert "%" in str(data["operating_margin"])
