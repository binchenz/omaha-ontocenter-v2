"""
Semantic Type Formatter

提供基于语义类型的数据格式化功能。
"""

from typing import Any, Optional
from datetime import datetime


class SemanticTypeFormatter:
    """语义类型格式化器"""

    SUPPORTED_TYPES = {
        'percentage',
        'currency_cny',
        'date',
        'stock_code',
        'text',
        'number'
    }

    @staticmethod
    def format_value(value: Any, semantic_type: str) -> str:
        """
        根据语义类型格式化值

        Args:
            value: 原始值
            semantic_type: 语义类型

        Returns:
            格式化后的字符串
        """
        if value is None or value == '':
            return ''

        if semantic_type == 'percentage':
            return SemanticTypeFormatter._format_percentage(value)
        elif semantic_type == 'currency_cny':
            return SemanticTypeFormatter._format_currency_cny(value)
        elif semantic_type == 'date':
            return SemanticTypeFormatter._format_date(value)
        elif semantic_type == 'stock_code':
            return str(value)
        elif semantic_type == 'text':
            return str(value)
        elif semantic_type == 'number':
            return SemanticTypeFormatter._format_number(value)
        else:
            return str(value)

    @staticmethod
    def _format_percentage(value: Any) -> str:
        """格式化百分比"""
        try:
            num = float(value)
            return f"{num * 100:.2f}%"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_currency_cny(value: Any) -> str:
        """格式化人民币金额"""
        try:
            num = float(value)
            if abs(num) >= 1e8:  # 亿
                return f"¥{num / 1e8:.2f}亿"
            elif abs(num) >= 1e4:  # 万
                return f"¥{num / 1e4:.2f}万"
            else:
                return f"¥{num:.2f}"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_date(value: Any) -> str:
        """格式化日期"""
        if isinstance(value, str):
            # 处理 YYYYMMDD 格式
            if len(value) == 8 and value.isdigit():
                return f"{value[:4]}-{value[4:6]}-{value[6:]}"
            # 处理 YYYY-MM-DD 格式（已经是目标格式）
            return value
        elif isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        else:
            return str(value)

    @staticmethod
    def _format_number(value: Any) -> str:
        """格式化数值"""
        try:
            num = float(value)
            # 如果是整数，不显示小数点
            if num == int(num):
                return str(int(num))
            # 否则保留 2 位小数
            return f"{num:.2f}"
        except (ValueError, TypeError):
            return str(value)
