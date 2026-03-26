"""
测试 SemanticTypeValidator
"""

import pytest
from app.services.semantic_validator import SemanticTypeValidator


class TestSemanticTypeValidator:
    """测试语义类型验证器"""

    def test_validate_valid_semantic_types(self):
        """测试有效的语义类型"""
        validator = SemanticTypeValidator()

        obj_config = {
            'properties': [
                {'name': 'roe', 'type': 'float', 'semantic_type': 'percentage'},
                {'name': 'revenue', 'type': 'float', 'semantic_type': 'currency_cny'},
                {'name': 'end_date', 'type': 'string', 'semantic_type': 'date'},
            ]
        }

        errors = validator.validate_object_config(obj_config)
        assert len(errors) == 0

    def test_validate_invalid_semantic_type(self):
        """测试无效的语义类型"""
        validator = SemanticTypeValidator()

        obj_config = {
            'properties': [
                {'name': 'field1', 'semantic_type': 'invalid_type'},
            ]
        }

        errors = validator.validate_object_config(obj_config)
        assert len(errors) == 1
        assert 'invalid_type' in errors[0]
        assert 'field1' in errors[0]

    def test_validate_computed_property_with_valid_dependencies(self):
        """测试有效依赖的计算属性"""
        validator = SemanticTypeValidator()

        obj_config = {
            'properties': [
                {'name': 'revenue', 'type': 'float'},
                {'name': 'cost', 'type': 'float'},
            ],
            'computed_properties': [
                {
                    'name': 'profit',
                    'expression': '{revenue} - {cost}',
                    'semantic_type': 'currency_cny'
                }
            ]
        }

        errors = validator.validate_object_config(obj_config)
        assert len(errors) == 0

    def test_validate_computed_property_with_missing_dependency(self):
        """测试缺少依赖的计算属性"""
        validator = SemanticTypeValidator()

        obj_config = {
            'properties': [
                {'name': 'revenue', 'type': 'float'},
            ],
            'computed_properties': [
                {
                    'name': 'profit',
                    'expression': '{revenue} - {cost}'  # cost 不存在
                }
            ]
        }

        errors = validator.validate_object_config(obj_config)
        assert len(errors) == 1
        assert 'cost' in errors[0]
        assert 'profit' in errors[0]

    def test_validate_nested_computed_properties(self):
        """测试嵌套计算属性"""
        validator = SemanticTypeValidator()

        obj_config = {
            'properties': [
                {'name': 'revenue', 'type': 'float'},
                {'name': 'cost', 'type': 'float'},
            ],
            'computed_properties': [
                {'name': 'profit', 'expression': '{revenue} - {cost}'},
                {'name': 'profit_margin', 'expression': '{profit} / {revenue}'}
            ]
        }

        errors = validator.validate_object_config(obj_config)
        assert len(errors) == 0

    def test_validate_circular_dependency(self):
        """测试循环依赖检测"""
        validator = SemanticTypeValidator()

        obj_config = {
            'properties': [
                {'name': 'a', 'type': 'float'},
            ],
            'computed_properties': [
                {'name': 'b', 'expression': '{c} + 1'},
                {'name': 'c', 'expression': '{b} + 1'}
            ]
        }

        errors = validator.validate_object_config(obj_config)
        assert len(errors) == 1
        assert '循环依赖' in errors[0]

    def test_validate_empty_expression(self):
        """测试空表达式"""
        validator = SemanticTypeValidator()

        obj_config = {
            'properties': [
                {'name': 'a', 'type': 'float'},
            ],
            'computed_properties': [
                {'name': 'b', 'expression': ''}
            ]
        }

        errors = validator.validate_object_config(obj_config)
        assert len(errors) == 1
        assert 'expression 不能为空' in errors[0]

    def test_validate_computed_property_with_invalid_semantic_type(self):
        """测试计算属性的无效语义类型"""
        validator = SemanticTypeValidator()

        obj_config = {
            'properties': [
                {'name': 'a', 'type': 'float'},
            ],
            'computed_properties': [
                {
                    'name': 'b',
                    'expression': '{a} * 2',
                    'semantic_type': 'invalid_type'
                }
            ]
        }

        errors = validator.validate_object_config(obj_config)
        assert len(errors) == 1
        assert 'invalid_type' in errors[0]
        assert 'b' in errors[0]
