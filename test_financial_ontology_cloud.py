"""
测试 financial-ontology-cloud skill 的各种场景
使用真实的 financial_stock_analysis.yaml 配置
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("DATABASE_URL", "sqlite:///./omaha.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATAHUB_GMS_URL", "http://localhost:8080")

import pytest
from app.services.omaha import omaha_service
from app.services.semantic_formatter import SemanticTypeFormatter

# 读取真实配置文件
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configs/financial_stock_analysis.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    REAL_CONFIG = f.read()


class TestFinancialOntologyCloud:

    def test_1_list_objects(self):
        """测试1: 列出所有对象类型"""
        print("\n=== 测试1: 列出所有对象类型 ===")
        result = omaha_service.build_ontology(REAL_CONFIG)
        assert result.get("valid") == True
        objects = result["ontology"].get("objects", [])
        print(f"找到 {len(objects)} 个对象类型:")
        for obj in objects:
            print(f"  - {obj['name']}: {obj.get('description', '')}")
        assert len(objects) >= 5

    def test_2_get_schema_stock(self):
        """测试2: 获取 Stock 对象的字段结构"""
        print("\n=== 测试2: 获取 Stock 字段结构 ===")
        result = omaha_service.get_object_schema(REAL_CONFIG, "Stock")
        assert result.get("success") == True
        fields = result.get("columns") or result.get("fields", [])
        print(f"Stock 有 {len(fields)} 个字段:")
        for f in fields:
            print(f"  - {f['name']}: {f.get('semantic_type', f.get('type', 'N/A'))}")
        assert len(fields) >= 5

    def test_3_query_stock_no_limit(self):
        """测试3: 查询所有上市股票（不限制数量）"""
        print("\n=== 测试3: 查询所有上市股票（无 limit）===")
        result = omaha_service.query_objects(
            config_yaml=REAL_CONFIG,
            object_type="Stock",
            selected_columns=["ts_code", "name", "industry", "area"],
            limit=None
        )
        assert result.get("success") == True, result.get("error")
        rows = result.get("data", [])
        print(f"查询到 {len(rows)} 条记录")
        print("前3条:")
        for row in rows[:3]:
            print(f"  {row}")
        assert len(rows) > 100

    def test_4_query_stock_by_industry(self):
        """测试4: 按行业筛选股票"""
        print("\n=== 测试4: 筛选银行股 ===")
        result = omaha_service.query_objects(
            config_yaml=REAL_CONFIG,
            object_type="Stock",
            selected_columns=["ts_code", "name", "area"],
            filters=[{"field": "industry", "operator": "=", "value": "银行"}],
            limit=None
        )
        assert result.get("success") == True, result.get("error")
        rows = result.get("data", [])
        print(f"银行股共 {len(rows)} 只:")
        for row in rows[:5]:
            print(f"  {row}")

    def test_5_query_daily_quote(self):
        """测试5: 查询平安银行日线行情"""
        print("\n=== 测试5: 查询平安银行(000001.SZ)日线行情 ===")
        result = omaha_service.query_objects(
            config_yaml=REAL_CONFIG,
            object_type="DailyQuote",
            selected_columns=["ts_code", "trade_date", "close", "pct_chg", "vol"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"},
                {"field": "trade_date", "operator": ">=", "value": "20250101"}
            ],
            limit=None
        )
        assert result.get("success") == True, result.get("error")
        rows = result.get("data", [])
        print(f"查询到 {len(rows)} 条记录")
        for row in rows[:5]:
            print(f"  {row}")

    def test_6_query_valuation(self):
        """测试6: 查询估值指标"""
        print("\n=== 测试6: 查询平安银行估值指标 ===")
        result = omaha_service.query_objects(
            config_yaml=REAL_CONFIG,
            object_type="ValuationMetric",
            selected_columns=["ts_code", "trade_date", "pe_ttm", "pb", "total_mv", "dv_ratio"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "000001.SZ"},
                {"field": "trade_date", "operator": ">=", "value": "20250101"}
            ],
            limit=None
        )
        assert result.get("success") == True, result.get("error")
        rows = result.get("data", [])
        print(f"查询到 {len(rows)} 条记录")
        for row in rows[:5]:
            print(f"  {row}")

    def test_7_query_financial_indicator(self):
        """测试7: 查询财务指标（ROE、毛利率等）"""
        print("\n=== 测试7: 查询贵州茅台(600519.SH)财务指标 ===")
        result = omaha_service.query_objects(
            config_yaml=REAL_CONFIG,
            object_type="FinancialIndicator",
            selected_columns=["ts_code", "end_date", "roe", "grossprofit_margin", "netprofit_margin", "debt_to_assets"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "600519.SH"}
            ],
            limit=None
        )
        assert result.get("success") == True, result.get("error")
        rows = result.get("data", [])
        print(f"查询到 {len(rows)} 条记录")
        for row in rows[:5]:
            print(f"  {row}")

    def test_8_query_technical_indicator(self):
        """测试8: 查询技术指标（MA、MACD、RSI）"""
        print("\n=== 测试8: 查询宁德时代(300750.SZ)技术指标 ===")
        result = omaha_service.query_objects(
            config_yaml=REAL_CONFIG,
            object_type="TechnicalIndicator",
            selected_columns=["ts_code", "trade_date", "close", "ma5", "ma20", "rsi14", "macd_bar", "ma_signal"],
            filters=[
                {"field": "ts_code", "operator": "=", "value": "300750.SZ"}
            ],
            limit=None
        )
        assert result.get("success") == True, result.get("error")
        rows = result.get("data", [])
        print(f"查询到 {len(rows)} 条记录")
        for row in rows[:5]:
            print(f"  {row}")

    def test_9_semantic_formatting(self):
        """测试9: 语义类型格式化"""
        print("\n=== 测试9: 语义类型格式化 ===")
        cases = [
            ("percentage", 12.5, "12.50%"),
            ("currency_cny", 100.5, "¥100.50"),
            ("growth_rate", 5.2, "+5.20%"),
            ("ratio", 15.5, "15.50x"),
            ("multiplier", 3.2, "3.20倍"),
        ]
        for semantic_type, value, expected in cases:
            result = SemanticTypeFormatter.format_value(value, semantic_type)
            print(f"  {semantic_type}: {value} -> {result}")
            assert result == expected

    def test_10_get_relationships(self):
        """测试10: 获取对象关系"""
        print("\n=== 测试10: 获取 Stock 的关系 ===")
        rels = omaha_service.get_relationships(REAL_CONFIG, "Stock")
        print(f"Stock 有 {len(rels)} 个关系:")
        for rel in rels:
            print(f"  - {rel.get('name')}: {rel.get('from_object')} -> {rel.get('to_object')}")
        assert len(rels) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
