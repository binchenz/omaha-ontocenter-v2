"""
测试 SemanticTypeFormatter
"""

import pytest
from app.services.semantic.formatter import SemanticTypeFormatter


class TestSemanticTypeFormatter:
    """测试语义类型格式化器"""

    def test_format_percentage(self):
        """测试百分比格式化"""
        formatter = SemanticTypeFormatter()

        # 测试正常值
        assert formatter.format_value(0.1089, 'percentage') == '10.89%'
        assert formatter.format_value(0.15, 'percentage') == '15.00%'
        assert formatter.format_value(1.0, 'percentage') == '100.00%'
        assert formatter.format_value(0.0, 'percentage') == '0.00%'

        # 测试负值
        assert formatter.format_value(-0.05, 'percentage') == '-5.00%'

    def test_format_currency_cny(self):
        """测试人民币格式化"""
        formatter = SemanticTypeFormatter()

        # 测试亿级别
        assert formatter.format_value(123456789, 'currency_cny') == '¥1.23亿'
        assert formatter.format_value(1000000000, 'currency_cny') == '¥10.00亿'

        # 测试万级别
        assert formatter.format_value(12345, 'currency_cny') == '¥1.23万'
        assert formatter.format_value(100000, 'currency_cny') == '¥10.00万'

        # 测试普通金额
        assert formatter.format_value(1234, 'currency_cny') == '¥1234.00'
        assert formatter.format_value(100, 'currency_cny') == '¥100.00'

        # 测试负值
        assert formatter.format_value(-123456789, 'currency_cny') == '¥-1.23亿'

    def test_format_date(self):
        """测试日期格式化"""
        formatter = SemanticTypeFormatter()

        # 测试 YYYYMMDD 格式
        assert formatter.format_value('20231231', 'date') == '2023-12-31'
        assert formatter.format_value('20240101', 'date') == '2024-01-01'

        # 测试已经是目标格式的日期
        assert formatter.format_value('2023-12-31', 'date') == '2023-12-31'

    def test_format_stock_code(self):
        """测试股票代码格式化"""
        formatter = SemanticTypeFormatter()

        assert formatter.format_value('000001.SZ', 'stock_code') == '000001.SZ'
        assert formatter.format_value('600000.SH', 'stock_code') == '600000.SH'

    def test_format_text(self):
        """测试文本格式化"""
        formatter = SemanticTypeFormatter()

        assert formatter.format_value('平安银行', 'text') == '平安银行'
        assert formatter.format_value('Test', 'text') == 'Test'

    def test_format_number(self):
        """测试数值格式化"""
        formatter = SemanticTypeFormatter()

        # 测试整数
        assert formatter.format_value(100, 'number') == '100'
        assert formatter.format_value(0, 'number') == '0'

        # 测试小数
        assert formatter.format_value(123.45, 'number') == '123.45'
        assert formatter.format_value(0.5, 'number') == '0.50'

    def test_format_none_value(self):
        """测试 None 值格式化"""
        formatter = SemanticTypeFormatter()

        assert formatter.format_value(None, 'percentage') == ''
        assert formatter.format_value('', 'currency_cny') == ''
        assert formatter.format_value(None, 'date') == ''

    def test_format_invalid_type(self):
        """测试无效类型"""
        formatter = SemanticTypeFormatter()

        # 未知类型应该返回字符串表示
        assert formatter.format_value(123, 'unknown_type') == '123'
        assert formatter.format_value('test', 'unknown_type') == 'test'
