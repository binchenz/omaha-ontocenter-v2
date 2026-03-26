# P0 优先级任务实施方案

## 概述

本文档详细描述 P0 优先级任务的技术实施方案，包括：
1. default_filters 自动过滤功能
2. computed_properties 自动展开功能
3. 字段语义类型验证功能

## 1. default_filters 自动过滤功能

### 1.1 设计决策

**策略：强制合并（Mandatory Merge）**
- 用户的 filters 通过 AND 追加到 default_filters
- default_filters 始终生效，无法被用户覆盖
- 例如：
  ```
  default_filters: "platform_id IS NOT NULL AND platform_id != ''"
  用户 filters: "city='北京'"
  最终 SQL: WHERE platform_id IS NOT NULL AND platform_id != '' AND city='北京'
  ```

### 1.2 实现方案

**修改文件：** `backend/app/services/query_builder.py`

**核心逻辑：**
```python
class SemanticQueryBuilder:
    def _build_where_clause(self, filters: Optional[str], object_config: Dict) -> str:
        """构建 WHERE 子句，合并 default_filters 和用户 filters"""
        conditions = []

        # 1. 添加 default_filters（如果存在）
        default_filters = object_config.get('default_filters')
        if default_filters:
            conditions.append(f"({default_filters})")

        # 2. 添加用户 filters（如果存在）
        if filters:
            conditions.append(f"({filters})")

        # 3. 合并所有条件
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""
```

**测试用例：**
```python
def test_default_filters_merge():
    """测试 default_filters 与用户 filters 的合并"""
    # 场景1：只有 default_filters
    result = builder.build_query(
        object_name="CompetitorComparison",
        fields=["sku_name", "city"],
        filters=None
    )
    assert "WHERE platform_id IS NOT NULL AND platform_id != ''" in result

    # 场景2：default_filters + 用户 filters
    result = builder.build_query(
        object_name="CompetitorComparison",
        fields=["sku_name", "city"],
        filters="city='北京'"
    )
    assert "WHERE (platform_id IS NOT NULL AND platform_id != '') AND (city='北京')" in result

    # 场景3：用户无法覆盖 default_filters
    result = builder.build_query(
        object_name="CompetitorComparison",
        fields=["sku_name", "city"],
        filters="platform_id=''"  # 尝试覆盖
    )
    # default_filters 仍然生效，但用户 filter 也会追加
    assert "platform_id IS NOT NULL" in result
```

### 1.3 技术风险

**风险1：SQL 注入**
- **问题：** 用户 filters 直接拼接到 SQL 中
- **解决方案：**
  - 使用参数化查询（推荐）
  - 或者对 filters 进行严格的语法验证（使用 sqlparse）

**风险2：default_filters 与用户 filters 冲突**
- **问题：** 例如 `default_filters: "city='北京'"` + 用户 `filters: "city='上海'"` → 结果为空
- **解决方案：**
  - 在文档中明确说明 default_filters 的作用
  - 提供 `override_default_filters=True` 选项（P1 功能）

### 1.4 与竞品对比

| 产品 | default_filters 策略 |
|------|---------------------|
| **dbt** | 使用 `where` 配置，强制合并 |
| **Cube.dev** | 使用 `sql` 配置，强制合并 |
| **Omaha** | 使用 `default_filters`，强制合并 ✅ |

**差异化：** 与 dbt/Cube.dev 保持一致，符合行业标准。

---

## 2. computed_properties 自动展开功能

### 2.1 设计决策

**策略：完全展开（Full Expansion）**
- 聚合函数中的计算字段自动展开为完整表达式
- 例如：`AVG(actual_price_gap)` → `AVG(ppy_price - mall_price)`
- 保证 SQL 执行效率，无需子查询

### 2.2 实现方案

**修改文件：** `backend/app/services/query_builder.py`

**核心逻辑：**
```python
class SemanticQueryBuilder:
    def _expand_computed_property(self, field: str, object_config: Dict) -> str:
        """展开计算字段为完整表达式"""
        computed_props = object_config.get('computed_properties', {})

        if field in computed_props:
            expression = computed_props[field]
            # 递归展开嵌套的计算字段
            return self._recursive_expand(expression, computed_props)
        return field

    def _recursive_expand(self, expression: str, computed_props: Dict) -> str:
        """递归展开表达式中的计算字段"""
        import re

        # 查找表达式中的所有字段名
        field_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        fields = re.findall(field_pattern, expression)

        result = expression
        for field in fields:
            if field in computed_props:
                # 递归展开
                expanded = self._recursive_expand(computed_props[field], computed_props)
                result = result.replace(field, f"({expanded})")

        return result

    def _build_select_clause(self, fields: List[str], object_config: Dict) -> str:
        """构建 SELECT 子句，自动展开计算字段"""
        select_items = []

        for field in fields:
            # 检查是否是聚合函数
            if self._is_aggregate_function(field):
                # 提取聚合函数内的字段名
                inner_field = self._extract_inner_field(field)
                # 展开计算字段
                expanded = self._expand_computed_property(inner_field, object_config)
                # 替换回聚合函数
                expanded_agg = field.replace(inner_field, expanded)
                select_items.append(expanded_agg)
            else:
                # 普通字段，直接展开
                expanded = self._expand_computed_property(field, object_config)
                select_items.append(f"{expanded} AS {field}")

        return "SELECT " + ", ".join(select_items)

    def _is_aggregate_function(self, field: str) -> bool:
        """判断是否是聚合函数"""
        agg_functions = ['AVG', 'SUM', 'COUNT', 'MIN', 'MAX', 'STDDEV', 'VARIANCE']
        return any(field.upper().startswith(f"{func}(") for func in agg_functions)

    def _extract_inner_field(self, agg_expr: str) -> str:
        """从聚合函数中提取内部字段名"""
        import re
        match = re.search(r'\(([^)]+)\)', agg_expr)
        return match.group(1) if match else agg_expr
```

**测试用例：**
```python
def test_computed_properties_expansion():
    """测试计算字段的自动展开"""
    # 场景1：简单计算字段
    result = builder.build_query(
        object_name="CompetitorComparison",
        fields=["AVG(actual_price_gap)"],
        group_by=["city"]
    )
    assert "AVG(ppy_price - mall_price)" in result
    assert "actual_price_gap" not in result  # 不应该出现原始字段名

    # 场景2：嵌套计算字段
    # 假设 price_gap_percentage = (actual_price_gap / mall_price) * 100
    result = builder.build_query(
        object_name="CompetitorComparison",
        fields=["AVG(price_gap_percentage)"],
        group_by=["city"]
    )
    assert "AVG(((ppy_price - mall_price) / mall_price) * 100)" in result

    # 场景3：混合普通字段和计算字段
    result = builder.build_query(
        object_name="CompetitorComparison",
        fields=["city", "AVG(actual_price_gap)", "COUNT(*)"],
        group_by=["city"]
    )
    assert "city" in result
    assert "AVG(ppy_price - mall_price)" in result
    assert "COUNT(*)" in result
```

### 2.3 技术风险

**风险1：循环依赖**
- **问题：** 计算字段 A 依赖 B，B 依赖 A
- **解决方案：**
  - 在递归展开时检测循环依赖
  - 抛出明确的错误信息

**风险2：复杂表达式解析错误**
- **问题：** 表达式中包含函数调用、括号嵌套等
- **解决方案：**
  - 使用 sqlparse 进行语法解析
  - 提供详细的错误信息和调试日志

**风险3：性能问题**
- **问题：** 复杂的嵌套展开可能导致 SQL 过长
- **解决方案：**
  - 限制嵌套深度（最多 3 层）
  - 提供性能监控和优化建议

### 2.4 与竞品对比

| 产品 | computed_properties 策略 |
|------|-------------------------|
| **dbt** | 使用 `derived columns`，完全展开 |
| **Cube.dev** | 使用 `measures`，完全展开 |
| **Secoda** | AI 自动识别，动态生成 |
| **Omaha** | 使用 `computed_properties`，完全展开 ✅ |

**差异化：**
- 与 dbt/Cube.dev 保持一致，符合行业标准
- 相比 Secoda 的 AI 自动识别，我们提供更可控的 YAML 定义

---

## 3. 字段语义类型验证功能

### 3.1 设计决策

**策略：后处理格式化（Post-Processing Formatting）**
- SQL 查询返回原始数据
- Python 层对结果进行格式化和验证
- 例如：
  - `currency` → `¥123.45`
  - `percentage` → `12.34%`
  - `enum` → 验证值是否在允许列表中

### 3.2 实现方案

**修改文件：** `backend/app/services/semantic.py`

**核心逻辑：**
```python
class SemanticService:
    def format_query_result(self, result: List[Dict], object_config: Dict) -> List[Dict]:
        """格式化查询结果，应用语义类型验证"""
        fields_config = object_config.get('fields', {})
        formatted_result = []

        for row in result:
            formatted_row = {}
            for field, value in row.items():
                field_config = fields_config.get(field, {})
                semantic_type = field_config.get('semantic_type')

                # 应用格式化
                formatted_value = self._format_value(value, semantic_type, field_config)
                formatted_row[field] = formatted_value

            formatted_result.append(formatted_row)

        return formatted_result

    def _format_value(self, value, semantic_type: Optional[str], field_config: Dict):
        """根据语义类型格式化值"""
        if value is None:
            return None

        if semantic_type == 'currency':
            return self._format_currency(value, field_config)
        elif semantic_type == 'percentage':
            return self._format_percentage(value, field_config)
        elif semantic_type == 'enum':
            return self._validate_enum(value, field_config)
        else:
            return value

    def _format_currency(self, value: float, field_config: Dict) -> str:
        """格式化货币字段"""
        currency_symbol = field_config.get('currency_symbol', '¥')
        precision = field_config.get('precision', 2)
        return f"{currency_symbol}{value:,.{precision}f}"

    def _format_percentage(self, value: float, field_config: Dict) -> str:
        """格式化百分比字段"""
        precision = field_config.get('precision', 2)
        return f"{value:.{precision}f}%"

    def _validate_enum(self, value: str, field_config: Dict) -> str:
        """验证枚举字段"""
        allowed_values = field_config.get('allowed_values', [])
        if allowed_values and value not in allowed_values:
            raise ValueError(f"Invalid enum value: {value}. Allowed: {allowed_values}")
        return value
```

**YAML 配置示例：**
```yaml
objects:
  CompetitorComparison:
    fields:
      mall_price:
        semantic_type: currency
        currency_symbol: "¥"
        precision: 2

      price_gap_percentage:
        semantic_type: percentage
        precision: 2

      product_type_first_level:
        semantic_type: enum
        allowed_values: ["生鲜", "日配", "食品", "百货"]
```

**测试用例：**
```python
def test_semantic_type_formatting():
    """测试语义类型格式化"""
    # 场景1：currency 格式化
    result = [{"mall_price": 123.456}]
    formatted = service.format_query_result(result, object_config)
    assert formatted[0]["mall_price"] == "¥123.46"

    # 场景2：percentage 格式化
    result = [{"price_gap_percentage": 12.3456}]
    formatted = service.format_query_result(result, object_config)
    assert formatted[0]["price_gap_percentage"] == "12.35%"

    # 场景3：enum 验证
    result = [{"product_type_first_level": "生鲜"}]
    formatted = service.format_query_result(result, object_config)
    assert formatted[0]["product_type_first_level"] == "生鲜"

    # 场景4：enum 验证失败
    result = [{"product_type_first_level": "无效类型"}]
    with pytest.raises(ValueError):
        service.format_query_result(result, object_config)
```

### 3.3 技术风险

**风险1：格式化后无法用于计算**
- **问题：** 格式化后的字符串无法用于数学运算
- **解决方案：**
  - 提供 `raw_value` 和 `formatted_value` 两个字段
  - 或者提供 `format=False` 选项

**风险2：性能开销**
- **问题：** 大量数据的格式化可能影响性能
- **解决方案：**
  - 使用批量格式化
  - 提供缓存机制

**风险3：国际化支持**
- **问题：** 不同地区的货币符号、日期格式不同
- **解决方案：**
  - 支持 `locale` 配置
  - 使用 Python 的 `locale` 模块

### 3.4 与竞品对比

| 产品 | 字段语义类型验证策略 |
|------|---------------------|
| **dbt** | 使用 `tests`，在数据加载时验证 |
| **Cube.dev** | 使用 `format`，在查询时格式化 |
| **Secoda** | AI 自动识别，动态格式化 |
| **Omaha** | 使用 `semantic_type`，后处理格式化 ✅ |

**差异化：**
- 与 Cube.dev 类似，在查询时格式化
- 相比 dbt 的数据加载时验证，我们更灵活
- 相比 Secoda 的 AI 自动识别，我们更可控

---

## 4. 实施计划

### 4.1 开发顺序

**第1周：default_filters**
- Day 1-2: 实现 `_build_where_clause` 方法
- Day 3: 编写单元测试
- Day 4: 集成测试和文档更新
- Day 5: Code Review 和修复

**第2周：computed_properties + 字段语义类型验证**
- Day 1-3: 实现 `_expand_computed_property` 和 `_recursive_expand` 方法
- Day 4-5: 实现 `format_query_result` 方法
- Day 6: 编写单元测试
- Day 7: 集成测试和文档更新

### 4.2 测试策略

**单元测试：**
- 每个方法独立测试
- 覆盖边界情况和异常情况

**集成测试：**
- 使用 CompetitorComparison 对象进行端到端测试
- 验证 Agent 查询体验

**性能测试：**
- 测试大数据量下的格式化性能
- 测试复杂嵌套展开的性能

### 4.3 文档更新

**需要更新的文档：**
1. `docs/superpowers/ontology_redesign_v2.yaml` - 添加配置示例
2. `docs/design/semantic_layer_design.md` - 更新设计文档
3. `README.md` - 更新功能列表
4. `docs/api/query_builder_api.md` - 更新 API 文档

---

## 5. 成功标准

### 5.1 功能完整性

- ✅ default_filters 在所有查询中自动生效
- ✅ computed_properties 在聚合查询中自动展开
- ✅ 字段语义类型验证和格式化正常工作

### 5.2 测试覆盖率

- ✅ 单元测试覆盖率 > 90%
- ✅ 集成测试覆盖所有核心场景
- ✅ 性能测试通过（大数据量下响应时间 < 1s）

### 5.3 Agent 查询体验

- ✅ Agent 可以直接使用计算字段进行聚合查询
- ✅ Agent 查询结果自动过滤无效数据
- ✅ Agent 查询结果自动格式化为人类可读格式

### 5.4 与竞品对比

- ✅ 功能对齐 dbt/Cube.dev 的语义层基础能力
- ✅ 提供比 Secoda 更可控的 YAML 定义
- ✅ 为 P1（AI Native 能力）打下坚实基础

---

## 6. 风险缓解

### 6.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| SQL 注入 | 高 | 使用参数化查询或严格验证 |
| 循环依赖 | 中 | 检测循环依赖并抛出错误 |
| 性能问题 | 中 | 限制嵌套深度，提供性能监控 |
| 格式化后无法计算 | 低 | 提供 raw_value 和 formatted_value |

### 6.2 项目风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 开发时间超期 | 中 | 优先实现核心功能，延后优化 |
| 测试覆盖不足 | 高 | 严格执行测试策略，Code Review |
| 文档更新滞后 | 低 | 开发过程中同步更新文档 |

---

## 7. 下一步行动

1. **立即开始：** 实现 default_filters 功能
2. **本周完成：** default_filters 的单元测试和集成测试
3. **下周开始：** 实现 computed_properties 和字段语义类型验证
4. **两周后：** 完成所有 P0 功能，准备进入 P1（AI Native 能力）

---

## 附录：代码示例

### A. default_filters 完整实现

```python
# backend/app/services/query_builder.py

class SemanticQueryBuilder:
    def _build_where_clause(self, filters: Optional[str], object_config: Dict) -> str:
        """构建 WHERE 子句，合并 default_filters 和用户 filters"""
        conditions = []

        # 1. 添加 default_filters（如果存在）
        default_filters = object_config.get('default_filters')
        if default_filters:
            conditions.append(f"({default_filters})")

        # 2. 添加用户 filters（如果存在）
        if filters:
            # TODO: 使用参数化查询防止 SQL 注入
            conditions.append(f"({filters})")

        # 3. 合并所有条件
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""
```

### B. computed_properties 完整实现

```python
# backend/app/services/query_builder.py

import re
from typing import Dict, List, Optional

class SemanticQueryBuilder:
    def _expand_computed_property(
        self,
        field: str,
        object_config: Dict,
        depth: int = 0,
        max_depth: int = 3
    ) -> str:
        """展开计算字段为完整表达式"""
        if depth > max_depth:
            raise ValueError(f"Computed property nesting too deep: {field}")

        computed_props = object_config.get('computed_properties', {})

        if field in computed_props:
            expression = computed_props[field]
            return self._recursive_expand(expression, computed_props, depth + 1, max_depth)
        return field

    def _recursive_expand(
        self,
        expression: str,
        computed_props: Dict,
        depth: int = 0,
        max_depth: int = 3
    ) -> str:
        """递归展开表达式中的计算字段"""
        if depth > max_depth:
            raise ValueError(f"Computed property nesting too deep")

        # 查找表达式中的所有字段名（排除 SQL 关键字）
        field_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        sql_keywords = {'AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'}

        fields = re.findall(field_pattern, expression)
        result = expression

        for field in fields:
            if field.upper() not in sql_keywords and field in computed_props:
                # 递归展开
                expanded = self._recursive_expand(
                    computed_props[field],
                    computed_props,
                    depth + 1,
                    max_depth
                )
                # 使用正则替换，确保只替换完整的字段名
                result = re.sub(r'\b' + field + r'\b', f"({expanded})", result)

        return result

    def _build_select_clause(self, fields: List[str], object_config: Dict) -> str:
        """构建 SELECT 子句，自动展开计算字段"""
        select_items = []

        for field in fields:
            # 检查是否是聚合函数
            if self._is_aggregate_function(field):
                # 提取聚合函数内的字段名
                inner_field = self._extract_inner_field(field)
                # 展开计算字段
                expanded = self._expand_computed_property(inner_field, object_config)
                # 替换回聚合函数
                agg_func = field.split('(')[0]
                expanded_agg = f"{agg_func}({expanded})"
                select_items.append(f"{expanded_agg} AS {field.replace('(', '_').replace(')', '')}")
            else:
                # 普通字段，直接展开
                expanded = self._expand_computed_property(field, object_config)
                if expanded != field:
                    select_items.append(f"{expanded} AS {field}")
                else:
                    select_items.append(field)

        return "SELECT " + ", ".join(select_items)

    def _is_aggregate_function(self, field: str) -> bool:
        """判断是否是聚合函数"""
        agg_functions = ['AVG', 'SUM', 'COUNT', 'MIN', 'MAX', 'STDDEV', 'VARIANCE']
        field_upper = field.upper()
        return any(field_upper.startswith(f"{func}(") for func in agg_functions)

    def _extract_inner_field(self, agg_expr: str) -> str:
        """从聚合函数中提取内部字段名"""
        match = re.search(r'\(([^)]+)\)', agg_expr)
        return match.group(1).strip() if match else agg_expr
```

### C. 字段语义类型验证完整实现

```python
# backend/app/services/semantic.py

from typing import List, Dict, Optional
import locale

class SemanticService:
    def format_query_result(
        self,
        result: List[Dict],
        object_config: Dict,
        format_enabled: bool = True
    ) -> List[Dict]:
        """格式化查询结果，应用语义类型验证"""
        if not format_enabled:
            return result

        fields_config = object_config.get('fields', {})
        formatted_result = []

        for row in result:
            formatted_row = {}
            for field, value in row.items():
                field_config = fields_config.get(field, {})
                semantic_type = field_config.get('semantic_type')

                # 应用格式化
                try:
                    formatted_value = self._format_value(value, semantic_type, field_config)
                    formatted_row[field] = formatted_value
                except Exception as e:
                    # 格式化失败时，保留原始值并记录警告
                    formatted_row[field] = value
                    print(f"Warning: Failed to format field {field}: {e}")

            formatted_result.append(formatted_row)

        return formatted_result

    def _format_value(self, value, semantic_type: Optional[str], field_config: Dict):
        """根据语义类型格式化值"""
        if value is None:
            return None

        if semantic_type == 'currency':
            return self._format_currency(value, field_config)
        elif semantic_type == 'percentage':
            return self._format_percentage(value, field_config)
        elif semantic_type == 'enum':
            return self._validate_enum(value, field_config)
        elif semantic_type == 'date':
            return self._format_date(value, field_config)
        elif semantic_type == 'datetime':
            return self._format_datetime(value, field_config)
        else:
            return value

    def _format_currency(self, value: float, field_config: Dict) -> str:
        """格式化货币字段"""
        currency_symbol = field_config.get('currency_symbol', '¥')
        precision = field_config.get('precision', 2)

        # 使用千位分隔符
        formatted = f"{value:,.{precision}f}"
        return f"{currency_symbol}{formatted}"

    def _format_percentage(self, value: float, field_config: Dict) -> str:
        """格式化百分比字段"""
        precision = field_config.get('precision', 2)
        return f"{value:.{precision}f}%"

    def _validate_enum(self, value: str, field_config: Dict) -> str:
        """验证枚举字段"""
        allowed_values = field_config.get('allowed_values', [])
        if allowed_values and value not in allowed_values:
            raise ValueError(
                f"Invalid enum value: {value}. "
                f"Allowed values: {', '.join(allowed_values)}"
            )
        return value

    def _format_date(self, value, field_config: Dict) -> str:
        """格式化日期字段"""
        date_format = field_config.get('date_format', '%Y-%m-%d')
        if isinstance(value, str):
            return value  # 假设已经是字符串格式
        return value.strftime(date_format)

    def _format_datetime(self, value, field_config: Dict) -> str:
        """格式化日期时间字段"""
        datetime_format = field_config.get('datetime_format', '%Y-%m-%d %H:%M:%S')
        if isinstance(value, str):
            return value  # 假设已经是字符串格式
        return value.strftime(datetime_format)
```

---

**文档版本：** v1.0
**创建日期：** 2025-01-XX
**最后更新：** 2025-01-XX
**作者：** Omaha OntoCenter Team
