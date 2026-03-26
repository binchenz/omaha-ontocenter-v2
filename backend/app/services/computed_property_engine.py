"""
Computed Property Engine

提供计算属性的解析、依赖分析和执行功能。
"""

import re
from typing import List, Dict, Any, Set
import pandas as pd


class ComputedPropertyEngine:
    """计算属性引擎"""

    def __init__(self):
        self.field_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')

    def compute_properties(self, df: pd.DataFrame,
                          computed_props: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        计算所有计算属性

        Args:
            df: 数据框
            computed_props: 计算属性配置列表

        Returns:
            添加了计算属性的数据框
        """
        if not computed_props:
            return df

        # 1. 构建依赖图
        dep_graph = self._build_dependency_graph(computed_props)

        # 2. 拓扑排序
        sorted_props = self._topological_sort(dep_graph, computed_props)

        # 3. 按顺序执行计算
        for prop in sorted_props:
            df = self._compute_single_property(df, prop)

        return df

    def _build_dependency_graph(self,
                               computed_props: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """
        构建依赖图

        Args:
            computed_props: 计算属性配置列表

        Returns:
            依赖图 {property_name: set(依赖的字段名)}
        """
        dep_graph = {}

        for prop in computed_props:
            name = prop['name']
            expression = prop['expression']

            # 提取表达式中引用的字段
            dependencies = set(self.field_pattern.findall(expression))
            dep_graph[name] = dependencies

        return dep_graph

    def _topological_sort(self,
                         dep_graph: Dict[str, Set[str]],
                         computed_props: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        拓扑排序计算属性

        Args:
            dep_graph: 依赖图 {property_name: set(依赖的字段名)}
            computed_props: 计算属性配置列表

        Returns:
            排序后的计算属性列表

        Raises:
            ValueError: 如果存在循环依赖
        """
        # 创建属性名到配置的映射
        prop_map = {prop['name']: prop for prop in computed_props}

        # 获取所有计算属性的名称
        computed_prop_names = set(prop_map.keys())

        # 计算入度（只考虑计算属性之间的依赖）
        in_degree = {name: 0 for name in computed_prop_names}
        for name, deps in dep_graph.items():
            # 只统计依赖于其他计算属性的情况
            computed_deps = deps & computed_prop_names
            in_degree[name] = len(computed_deps)

        # 找到所有入度为 0 的节点（不依赖其他计算属性）
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # 取出一个入度为 0 的节点
            current = queue.pop(0)
            result.append(prop_map[current])

            # 减少依赖于当前节点的节点的入度
            for name, deps in dep_graph.items():
                if current in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        # 检查是否存在循环依赖
        if len(result) != len(computed_props):
            raise ValueError("检测到循环依赖")

        return result

    def _compute_single_property(self,
                                df: pd.DataFrame,
                                prop: Dict[str, Any]) -> pd.DataFrame:
        """
        计算单个属性

        Args:
            df: 数据框
            prop: 属性配置

        Returns:
            添加了计算属性的数据框
        """
        name = prop['name']
        expression = prop['expression']

        # 替换表达式中的字段引用
        eval_expr = self.field_pattern.sub(
            lambda m: f"df['{m.group(1)}']",
            expression
        )

        try:
            # 执行计算
            df[name] = eval(eval_expr)
        except Exception as e:
            raise ValueError(f"计算属性 '{name}' 失败: {str(e)}")

        return df
