"""
Semantic Type Validator

提供语义类型配置的验证功能。
"""

from typing import List, Dict, Any, Set
import re
from app.services.semantic_formatter import SemanticTypeFormatter


class SemanticTypeValidator:
    """语义类型验证器"""

    def __init__(self):
        self.field_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')

    def validate_object_config(self, obj_config: Dict[str, Any]) -> List[str]:
        """
        验证对象配置

        Args:
            obj_config: 对象配置

        Returns:
            错误列表（空列表表示验证通过）
        """
        errors = []

        # 获取所有属性名
        properties = obj_config.get('properties', [])
        prop_names = {prop['name'] for prop in properties}

        # 验证 semantic_type
        errors.extend(self._validate_semantic_types(properties))

        # 验证 computed_properties
        computed_props = obj_config.get('computed_properties', [])
        if computed_props:
            errors.extend(
                self._validate_computed_properties(
                    computed_props, prop_names
                )
            )

        return errors

    def _validate_semantic_types(self, properties: List[Dict[str, Any]]) -> List[str]:
        """验证语义类型"""
        errors = []

        for prop in properties:
            semantic_type = prop.get('semantic_type')
            if semantic_type:
                if semantic_type not in SemanticTypeFormatter.SUPPORTED_TYPES:
                    errors.append(
                        f"属性 '{prop['name']}' 的 semantic_type '{semantic_type}' "
                        f"不是支持的类型。支持的类型: "
                        f"{', '.join(SemanticTypeFormatter.SUPPORTED_TYPES)}"
                    )

        return errors

    def _validate_computed_properties(self,
                                      computed_props: List[Dict[str, Any]],
                                      available_fields: Set[str]) -> List[str]:
        """验证计算属性"""
        errors = []

        # 获取所有计算属性的名称
        computed_prop_names = {prop['name'] for prop in computed_props}

        # 将计算属性也加入可用字段
        all_available_fields = available_fields | computed_prop_names

        for prop in computed_props:
            name = prop['name']
            expression = prop.get('expression', '')

            # 验证表达式不为空
            if not expression:
                errors.append(f"计算属性 '{name}' 的 expression 不能为空")
                continue

            # 提取表达式中引用的字段
            referenced_fields = set(self.field_pattern.findall(expression))

            # 验证引用的字段是否存在
            for field in referenced_fields:
                if field not in all_available_fields:
                    errors.append(
                        f"计算属性 '{name}' 引用了不存在的字段 '{field}'"
                    )

            # 验证 semantic_type（如果有）
            semantic_type = prop.get('semantic_type')
            if semantic_type:
                if semantic_type not in SemanticTypeFormatter.SUPPORTED_TYPES:
                    errors.append(
                        f"计算属性 '{name}' 的 semantic_type '{semantic_type}' "
                        f"不是支持的类型"
                    )

        # 检测循环依赖
        cycle_errors = self._detect_circular_dependencies(computed_props)
        errors.extend(cycle_errors)

        return errors

    def _detect_circular_dependencies(self,
                                     computed_props: List[Dict[str, Any]]) -> List[str]:
        """检测循环依赖"""
        errors = []

        # 构建依赖图
        dep_graph = {}
        for prop in computed_props:
            name = prop['name']
            expression = prop.get('expression', '')
            dependencies = set(self.field_pattern.findall(expression))
            dep_graph[name] = dependencies

        # 获取所有计算属性的名称
        computed_prop_names = set(dep_graph.keys())

        # 使用 DFS 检测循环
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            # 只检查依赖于其他计算属性的情况
            for neighbor in dep_graph.get(node, set()):
                if neighbor not in computed_prop_names:
                    continue

                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in computed_prop_names:
            if node not in visited:
                if has_cycle(node):
                    errors.append(f"检测到循环依赖，涉及计算属性 '{node}'")
                    break

        return errors
