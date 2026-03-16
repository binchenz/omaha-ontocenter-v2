# Ontology 重新设计 - Phase 3 问题清单和修复建议

**创建时间：** 2026-03-17
**状态：** 待修复

## 问题概览

Phase 3 数据验证发现了 4 个需要修复的问题：

| 问题 | 优先级 | 影响范围 | 预计工作量 |
|------|--------|---------|-----------|
| 1. 自动 JOIN 功能缺失 | 🔴 高 | 高 | 2-3 小时 |
| 2. 计算字段展开不完整 | 🟡 中 | 中 | 1-2 小时 |
| 3. 数据质量问题 | 🟢 低 | 低 | 需协调 |

## 问题 1：自动 JOIN 功能缺失 🔴

### 问题描述

当 `selected_columns` 包含其他对象的字段时（如 `Product.sku_name`），系统无法自动识别并生成 JOIN 子句，导致查询失败。

### 失败的测试用例

1. **Product -> ProductPrice**
   ```python
   omaha_service.query_objects(
       config_yaml=config,
       object_type="ProductPrice",
       selected_columns=[
           "ProductPrice.sku_id",
           "ProductPrice.ppy_price",
           "Product.sku_name"  # ❌ 需要自动 JOIN
       ]
   )
   ```
   **错误：** `Column 'Product.sku_name' cannot be resolved`

2. **ProductPrice -> ProductCost**
   ```python
   omaha_service.query_objects(
       config_yaml=config,
       object_type="ProductPrice",
       selected_columns=[
           "ProductPrice.ppy_price",
           "ProductCost.ppy_current_cost"  # ❌ 需要自动 JOIN
       ]
   )
   ```
   **错误：** `Column 'ProductCost.ppy_current_cost' cannot be resolved`

3. **ProductPrice -> CompetitorPrice**
   ```python
   omaha_service.query_objects(
       config_yaml=config,
       object_type="ProductPrice",
       selected_columns=[
           "ProductPrice.ppy_price",
           "CompetitorPrice.mall_price"  # ❌ 需要自动 JOIN
       ]
   )
   ```
   **错误：** `Column 'CompetitorPrice.mall_price' cannot be resolved`

### 根本原因

`SemanticQueryBuilder.resolve_column()` 方法只处理当前对象的字段，不会：
1. 检测跨对象的字段引用
2. 查找相关的关系定义
3. 自动生成 JOIN 子句

### 期望行为

**输入：**
```python
selected_columns = [
    "ProductPrice.sku_id",
    "ProductPrice.ppy_price",
    "Product.sku_name"
]
```

**期望生成的 SQL：**
```sql
SELECT
  ProductPrice.sku_id,
  ProductPrice.ppy_price,
  Product.sku_name
FROM dm_ppy_product_info_ymd AS ProductPrice
LEFT JOIN dm_ppy_product_info_ymd AS Product
  ON ProductPrice.sku_id = Product.sku_id
LIMIT 100
```

### 修复方案

#### 方案 A：增强 SemanticQueryBuilder（推荐）

**步骤 1：添加 `_detect_needed_joins()` 方法**

```python
def _detect_needed_joins(self, selected_columns: List[str]) -> Set[str]:
    """
    分析 selected_columns，识别需要 JOIN 的对象。

    Args:
        selected_columns: 选择的列列表，如 ["ProductPrice.sku_id", "Product.sku_name"]

    Returns:
        需要 JOIN 的对象名称集合，如 {"Product"}
    """
    needed_objects = set()

    for col in selected_columns:
        if "." in col:
            obj_name = col.split(".")[0]
            # 如果对象名不是当前对象，需要 JOIN
            if obj_name != self.object_type:
                needed_objects.add(obj_name)

    return needed_objects
```

**步骤 2：添加 `_find_relationship()` 方法**

```python
def _find_relationship(self, target_object: str) -> Optional[Dict[str, Any]]:
    """
    查找从当前对象到目标对象的关系。

    Args:
        target_object: 目标对象名称

    Returns:
        关系定义字典，如果找不到返回 None
    """
    # 查找从当前对象到目标对象的关系
    for rel in self.relationships:
        if (rel.get("from_object") == self.object_type and
            rel.get("to_object") == target_object):
            return rel

    # 查找从目标对象到当前对象的关系（反向）
    for rel in self.relationships:
        if (rel.get("from_object") == target_object and
            rel.get("to_object") == self.object_type):
            # 返回反向关系
            return {
                "name": rel.get("name"),
                "from_object": self.object_type,
                "to_object": target_object,
                "type": "many_to_one" if rel.get("type") == "one_to_many" else "one_to_many",
                "join_condition": {
                    "from_field": rel["join_condition"]["to_field"],
                    "to_field": rel["join_condition"]["from_field"]
                }
            }

    return None
```

**步骤 3：添加 `_build_join_clause()` 方法**

```python
def _build_join_clause(self, relationship: Dict[str, Any]) -> str:
    """
    根据关系定义构建 JOIN 子句。

    Args:
        relationship: 关系定义

    Returns:
        JOIN 子句字符串
    """
    to_object = relationship.get("to_object")
    join_condition = relationship.get("join_condition", {})
    from_field = join_condition.get("from_field")
    to_field = join_condition.get("to_field")

    # 查找目标对象的表名或查询
    to_obj_def = next((o for o in self.all_objects if o.get("name") == to_object), None)
    if not to_obj_def:
        return ""

    # 支持 table 和 query 两种方式
    if to_obj_def.get("table"):
        to_table = to_obj_def["table"]
    elif to_obj_def.get("query"):
        # 如果是自定义查询，包装为子查询
        to_table = f"({to_obj_def['query'].strip()})"
    else:
        return ""

    # 确定 JOIN 类型（默认 LEFT JOIN）
    join_type = "LEFT JOIN"

    return f"{join_type} {to_table} AS {to_object} ON {self.object_type}.{from_field} = {to_object}.{to_field}"
```

**步骤 4：更新 `build()` 方法**

```python
def build(
    self,
    selected_columns: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    joins: Optional[List[Dict[str, Any]]] = None,
    limit: int = 100,
    db_type: str = "mysql",
) -> Tuple[str, List[Any]]:
    """Build SQL query with semantic awareness."""
    self.db_type = db_type

    # 1. 检测需要 JOIN 的对象
    needed_joins = self._detect_needed_joins(selected_columns or [])

    # 2. 构建 JOIN 子句
    join_clauses = []
    for obj_name in needed_joins:
        relationship = self._find_relationship(obj_name)
        if relationship:
            join_clause = self._build_join_clause(relationship)
            if join_clause:
                join_clauses.append(join_clause)

    # 3. 解析列
    if selected_columns:
        columns = [self.resolve_column(col) for col in selected_columns]
        columns_str = ", ".join(columns)
    else:
        # 默认选择所有基础属性
        columns = [f"{self.object_type}.{col}" for col in self.property_map.values()]
        columns_str = ", ".join(columns)

    # 4. 构建 FROM 子句
    if self.custom_query:
        from_clause = f"FROM ({self.custom_query.strip()}) AS {self.object_type}"
    else:
        from_clause = f"FROM {self.table_name} AS {self.object_type}"

    # 5. 添加 JOIN 子句
    if join_clauses:
        from_clause += " " + " ".join(join_clauses)

    # 6. 构建 WHERE 子句
    where_clause, params = self._build_where_clause(filters or [])

    # 7. 构建完整 SQL
    query = f"SELECT {columns_str} {from_clause}"
    if where_clause:
        query += f" WHERE {where_clause}"
    query += f" LIMIT {limit}"

    return query, params
```

**步骤 5：添加单元测试**

```python
def test_auto_join_product_to_price():
    """测试自动 JOIN Product 到 ProductPrice"""
    config_yaml = """
    datasources:
      - id: test_db
        type: mysql
    ontology:
      objects:
        - name: Product
          table: products
          properties:
            - name: sku_id
              column: sku_id
            - name: sku_name
              column: sku_name
        - name: ProductPrice
          table: prices
          properties:
            - name: sku_id
              column: sku_id
            - name: price
              column: price
      relationships:
        - name: price_of_product
          from_object: ProductPrice
          to_object: Product
          type: many_to_one
          join_condition:
            from_field: sku_id
            to_field: sku_id
    """

    builder = SemanticQueryBuilder(config_yaml, "ProductPrice")
    query, params = builder.build(
        selected_columns=[
            "ProductPrice.sku_id",
            "ProductPrice.price",
            "Product.sku_name"  # 应该自动 JOIN
        ],
        limit=10
    )

    assert "LEFT JOIN products AS Product" in query
    assert "ON ProductPrice.sku_id = Product.sku_id" in query
    assert "Product.sku_name" in query
```

#### 方案 B：使用显式 joins 参数（临时方案）

如果自动 JOIN 实现复杂，可以先要求用户显式指定 joins：

```python
omaha_service.query_objects(
    config_yaml=config,
    object_type="ProductPrice",
    selected_columns=[
        "ProductPrice.sku_id",
        "ProductPrice.ppy_price",
        "Product.sku_name"
    ],
    joins=[
        {
            "relationship_name": "price_of_product",
            "join_type": "LEFT"
        }
    ]
)
```

**优点：**
- 实现简单
- 用户有更多控制权

**缺点：**
- 用户体验差
- 需要用户了解关系名称
- 不符合"智能"查询的设计理念

### 推荐方案

**推荐方案 A（自动 JOIN）**，理由：
1. 用户体验更好
2. 符合语义层的设计理念
3. 实现难度适中（2-3 小时）
4. 长期收益高

### 实施计划

1. **第1步：** 实现 `_detect_needed_joins()` 方法（30分钟）
2. **第2步：** 实现 `_find_relationship()` 方法（30分钟）
3. **第3步：** 实现 `_build_join_clause()` 方法（30分钟）
4. **第4步：** 更新 `build()` 方法（30分钟）
5. **第5步：** 添加单元测试（30分钟）
6. **第6步：** 集成测试和调试（30分钟）

**总计：** 3 小时

### 验收标准

- ✅ 所有 3 个失败的 JOIN 测试用例通过
- ✅ 单元测试覆盖率 > 80%
- ✅ 支持多级 JOIN（A -> B -> C）
- ✅ 支持反向关系（B -> A）
- ✅ 性能无明显下降

---

## 问题 2：计算字段展开不完整 🟡

### 问题描述

`ProductPrice.effective_price` 计算字段未能正确展开为 SQL 表达式。

### 失败的测试用例

```python
omaha_service.query_objects(
    config_yaml=config,
    object_type="ProductPrice",
    selected_columns=[
        "ProductPrice.sku_id",
        "ProductPrice.ppy_price",
        "ProductPrice.ppy_promotion_price",
        "ProductPrice.effective_price"  # ❌ 计算字段未展开
    ]
)
```

**错误：** `Column 'effective_price' cannot be resolved`

### 计算字段定义

```yaml
computed_properties:
  - name: effective_price
    formula: "COALESCE(ppy_promotion_price, ppy_price)"
    return_type: currency
    description: 有效售价
```

### 期望行为

**期望生成的 SQL：**
```sql
SELECT
  ProductPrice.sku_id,
  ProductPrice.ppy_price,
  ProductPrice.ppy_promotion_price,
  (COALESCE(ppy_promotion_price, ppy_price)) AS effective_price
FROM dm_ppy_product_info_ymd AS ProductPrice
LIMIT 100
```

### 对比：成功的计算字段

`CompetitorPrice.price_gap_percentage` 成功展开：

```yaml
computed_properties:
  - name: price_gap_percentage
    formula: "price_gap / mall_price"
```

**生成的 SQL：**
```sql
SELECT
  CompetitorPrice.sku_id,
  CompetitorPrice.price_gap,
  CompetitorPrice.mall_price,
  (price_gap / mall_price) AS price_gap_percentage
FROM dm_ppy_platform_product_info_rel_ymd AS CompetitorPrice
```

### 根本原因分析

可能的原因：

1. **字段名映射问题**
   - `ppy_promotion_price` 在 `property_map` 中可能没有正确映射
   - `expand_formula()` 无法找到字段对应的列名

2. **COALESCE 函数处理问题**
   - `expand_formula()` 可能不支持 COALESCE 函数
   - 需要检查 SQL 函数的处理逻辑

3. **解析顺序问题**
   - 计算字段可能在 `property_map` 构建之前解析
   - 导致依赖的字段无法找到

### 调试步骤

**步骤 1：检查 property_map**

```python
# 在 SemanticQueryBuilder.__init__() 中添加调试日志
print(f"Object: {self.object_type}")
print(f"Property Map: {self.property_map}")
print(f"Computed Properties: {self.computed_properties}")
```

**步骤 2：检查 expand_formula()**

```python
# 在 semantic_service.expand_formula() 中添加调试日志
def expand_formula(self, formula: str, property_map: Dict[str, str]) -> str:
    print(f"Formula: {formula}")
    print(f"Property Map: {property_map}")

    # 展开逻辑
    result = self._expand_coalesce(formula, property_map)
    result = self._expand_if(result, property_map)
    result = self._substitute_properties(result, property_map)

    print(f"Expanded: {result}")
    return result
```

**步骤 3：检查 COALESCE 处理**

```python
# 检查 _expand_coalesce() 方法是否存在
# 如果不存在，需要添加
def _expand_coalesce(self, formula: str, property_map: Dict[str, str]) -> str:
    """Expand COALESCE function."""
    # COALESCE 不需要特殊处理，直接替换字段名即可
    return formula
```

### 修复方案

#### 方案 A：增强 expand_formula()（推荐）

**步骤 1：确保 property_map 包含所有字段**

```python
# 在 SemanticService.parse_config() 中
for prop in obj_def.get("properties", []):
    prop_name = prop.get("name")
    if not prop_name:
        continue
    if prop.get("semantic_type") != "computed":
        col = prop.get("column", prop_name)
        base_props[prop_name] = prop
        prop_map[prop_name] = col  # ✅ 确保所有字段都在 prop_map 中
```

**步骤 2：增强 _substitute_properties()**

```python
def _substitute_properties(self, expanded: str, property_map: Dict[str, str]) -> str:
    """Substitute property names with column names."""
    result = expanded

    # 按字段名长度排序，避免短字段名覆盖长字段名
    for prop_name, col_name in sorted(property_map.items(), key=lambda x: -len(x[0])):
        # 使用单词边界匹配，避免部分匹配
        result = re.sub(r'\b' + re.escape(prop_name) + r'\b', col_name, result)

    return result
```

**步骤 3：添加单元测试**

```python
def test_expand_formula_with_coalesce():
    """测试 COALESCE 函数的展开"""
    property_map = {
        "ppy_promotion_price": "ppy_promotion_price",
        "ppy_price": "ppy_price"
    }

    formula = "COALESCE(ppy_promotion_price, ppy_price)"
    expanded = semantic_service.expand_formula(formula, property_map)

    assert expanded == "COALESCE(ppy_promotion_price, ppy_price)"
```

#### 方案 B：检查列名映射

如果问题是列名映射，需要检查配置：

```yaml
properties:
  - name: ppy_price
    column: ppy_price  # ✅ 确保 column 字段存在
    type: decimal
  - name: ppy_promotion_price
    column: ppy_promotion_price  # ✅ 确保 column 字段存在
    type: decimal
```

### 推荐方案

**推荐方案 A（增强 expand_formula()）**，理由：
1. 根本解决问题
2. 提升计算字段的健壮性
3. 实现难度低（1-2 小时）

### 实施计划

1. **第1步：** 添加调试日志，定位问题（30分钟）
2. **第2步：** 修复 property_map 构建逻辑（30分钟）
3. **第3步：** 增强 _substitute_properties()（30分钟）
4. **第4步：** 添加单元测试（30分钟）

**总计：** 2 小时

### 验收标准

- ✅ `ProductPrice.effective_price` 测试通过
- ✅ 所有计算字段都能正确展开
- ✅ 单元测试覆盖率 > 80%
- ✅ 支持常见 SQL 函数（COALESCE、CASE、IF 等）

---

## 问题 3：数据质量问题 🟢

### 问题描述

部分数据字段为 NULL，可能影响查询和分析。

### 观察到的问题

1. **CompetitorPrice.platform_name 为 NULL**
   ```json
   {
     "sku_id": 44,
     "platform_name": null,  // ❌ 应该有平台名称
     "mall_price": "0.920000"
   }
   ```

2. **CompetitorPrice.price_gap 为 NULL**
   ```json
   {
     "sku_id": 41,
     "price_gap": null,  // ❌ 价差为空
     "mall_price": null
   }
   ```

### 影响范围

- 低：不影响核心功能
- 可能影响某些分析和报表

### 建议行动

1. **与数据团队沟通**
   - 了解 NULL 值的原因
   - 确认是否是数据质量问题

2. **在 Ontology 中添加说明**
   ```yaml
   properties:
     - name: platform_name
       type: string
       description: 竞品平台名称
       business_context: 如\"京东到家\"、\"永辉\"、\"小象超市\"。注意：部分记录可能为空。
   ```

3. **在查询时过滤 NULL 值**
   ```python
   filters = [
       {
           "field": "platform_name",
           "operator": "IS NOT NULL"
       }
   ]
   ```

### 优先级

🟢 低优先级 - 不阻塞 Phase 3 完成

---

## 总结

### 优先级排序

1. 🔴 **高优先级：** 自动 JOIN 功能（2-3 小时）
2. 🟡 **中优先级：** 计算字段展开（1-2 小时）
3. 🟢 **低优先级：** 数据质量问题（需协调）

### 总工作量

- **核心功能修复：** 3-5 小时
- **测试和验证：** 1-2 小时
- **总计：** 4-7 小时

### 建议行动顺序

1. 先修复自动 JOIN 功能（影响最大）
2. 再修复计算字段展开（相对独立）
3. 最后处理数据质量问题（需要协调）

### 预期结果

修复后，Phase 3 测试通过率应该达到 **100%**（14/14）。
