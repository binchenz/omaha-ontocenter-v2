"""
测试 ComputedPropertyEngine
"""

import pytest
import pandas as pd
from app.services.computed_property_engine import ComputedPropertyEngine


class TestComputedPropertyEngine:
    """测试计算属性引擎"""

    def test_simple_computation(self):
        """测试简单计算"""
        engine = ComputedPropertyEngine()

        # 创建测试数据
        df = pd.DataFrame({
            'revenue': [100, 200, 300],
            'cost': [60, 120, 180]
        })

        # 定义计算属性
        computed_props = [
            {
                'name': 'profit',
                'expression': '{revenue} - {cost}'
            }
        ]

        # 执行计算
        result = engine.compute_properties(df, computed_props)

        # 验证结果
        assert 'profit' in result.columns
        assert list(result['profit']) == [40, 80, 120]

    def test_nested_computation(self):
        """测试嵌套计算"""
        engine = ComputedPropertyEngine()

        # 创建测试数据
        df = pd.DataFrame({
            'revenue': [100, 200, 300],
            'cost': [60, 120, 180]
        })

        # 定义嵌套计算属性
        computed_props = [
            {
                'name': 'profit',
                'expression': '{revenue} - {cost}'
            },
            {
                'name': 'profit_margin',
                'expression': '{profit} / {revenue}'
            }
        ]

        # 执行计算
        result = engine.compute_properties(df, computed_props)

        # 验证结果
        assert 'profit' in result.columns
        assert 'profit_margin' in result.columns
        assert list(result['profit']) == [40, 80, 120]
        assert list(result['profit_margin']) == [0.4, 0.4, 0.4]

    def test_multiple_level_nesting(self):
        """测试多层嵌套计算"""
        engine = ComputedPropertyEngine()

        # 创建测试数据
        df = pd.DataFrame({
            'a': [10, 20, 30],
            'b': [5, 10, 15]
        })

        # 定义多层嵌套计算属性
        computed_props = [
            {'name': 'c', 'expression': '{a} + {b}'},
            {'name': 'd', 'expression': '{c} * 2'},
            {'name': 'e', 'expression': '{d} / {a}'}
        ]

        # 执行计算
        result = engine.compute_properties(df, computed_props)

        # 验证结果
        assert list(result['c']) == [15, 30, 45]
        assert list(result['d']) == [30, 60, 90]
        assert list(result['e']) == [3.0, 3.0, 3.0]

    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        engine = ComputedPropertyEngine()

        df = pd.DataFrame({'a': [1, 2, 3]})

        # 定义循环依赖的计算属性
        computed_props = [
            {'name': 'b', 'expression': '{c} + 1'},
            {'name': 'c', 'expression': '{b} + 1'}
        ]

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="循环依赖"):
            engine.compute_properties(df, computed_props)

    def test_empty_computed_props(self):
        """测试空计算属性列表"""
        engine = ComputedPropertyEngine()

        df = pd.DataFrame({'a': [1, 2, 3]})

        # 空列表应该返回原数据框
        result = engine.compute_properties(df, [])
        assert result.equals(df)

    def test_complex_expression(self):
        """测试复杂表达式"""
        engine = ComputedPropertyEngine()

        df = pd.DataFrame({
            'revenue': [100, 200, 300],
            'cost': [60, 120, 180],
            'tax_rate': [0.1, 0.15, 0.2]
        })

        computed_props = [
            {
                'name': 'profit_after_tax',
                'expression': '({revenue} - {cost}) * (1 - {tax_rate})'
            }
        ]

        result = engine.compute_properties(df, computed_props)

        assert 'profit_after_tax' in result.columns
        assert list(result['profit_after_tax']) == [36.0, 68.0, 96.0]
