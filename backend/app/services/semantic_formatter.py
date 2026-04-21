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
        'number',
        'ratio',
        'growth_rate',
        'score',
        'multiplier'
    }

    @staticmethod
    def format_value(value: Any, semantic_type: str) -> str:
        """根据语义类型格式化值

        Args:
            value: 原始值
            semantic_type: 语义类型

        Returns:
            格式化后的字符串
        """
        if value is None or value == '':
            return ''

        formatters = {
            'percentage': SemanticTypeFormatter._format_percentage,
            'currency_cny': SemanticTypeFormatter._format_currency_cny,
            'date': SemanticTypeFormatter._format_date,
            'number': SemanticTypeFormatter._format_number,
            'ratio': SemanticTypeFormatter._format_ratio,
            'growth_rate': SemanticTypeFormatter._format_growth_rate,
            'score': SemanticTypeFormatter._format_score,
            'multiplier': SemanticTypeFormatter._format_multiplier,
        }

        formatter = formatters.get(semantic_type)
        return formatter(value) if formatter else str(value)

    @staticmethod
    def _format_percentage(value: Any) -> str:
        """格式化百分比"""
        try:
            num = float(value) * 100
            return f"{num:.2f}%"
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

    @staticmethod
    def _format_with_suffix(value: Any, precision: int, suffix: str, sign: bool = False) -> str:
        """通用格式化方法：转换为浮点数并添加后缀"""
        try:
            num = float(value)
            formatted = f"{num:.{precision}f}"
            if sign and num > 0:
                formatted = f"+{formatted}"
            return f"{formatted}{suffix}"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_ratio(value: Any) -> str:
        """格式化比率（如市盈率、市净率）"""
        return SemanticTypeFormatter._format_with_suffix(value, 2, "x")

    @staticmethod
    def _format_growth_rate(value: Any) -> str:
        """格式化增长率（带正负号的百分比）"""
        return SemanticTypeFormatter._format_with_suffix(value, 2, "%", sign=True)

    @staticmethod
    def _format_score(value: Any) -> str:
        """格式化评分（0-100分）"""
        return SemanticTypeFormatter._format_with_suffix(value, 1, "分")

    @staticmethod
    def _format_multiplier(value: Any) -> str:
        """格式化倍数（如市销率、市现率）"""
        return SemanticTypeFormatter._format_with_suffix(value, 2, "倍")

    @staticmethod
    def compute_property(expression: str, data: dict) -> Any:
        """计算属性值
        
        Args:
            expression: 计算表达式，如 "{roe} * 0.4 + {roa} * 0.3"
            data: 数据字典
            
        Returns:
            计算结果
        """
        try:
            # 替换表达式中的字段引用
            import re
            expr = expression
            for match in re.finditer(r'\{(\w+)\}', expression):
                field = match.group(1)
                value = data.get(field)
                # 处理 None 和空字符串
                if value is None or value == '' or str(value).lower() == 'nan':
                    return None
                expr = expr.replace(f'{{{field}}}', str(float(value)))
            # 安全计算表达式
            result = eval(expr, {"__builtins__": {}}, {})
            return float(result)
        except Exception:
            return None
