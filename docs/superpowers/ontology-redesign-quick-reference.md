# Ontology 重新设计 - 快速参考指南

## 新特性概览

### 1. 粒度标注（Granularity）

**用途：** 明确标注数据的粒度，帮助 Agent 理解数据的聚合级别

**语法：**
```yaml
granularity:
  dimensions: [sku_id, city, p_date]  # 维度列表
  level: city_daily                    # 粒度级别（自定义）
  description: 城市+日期粒度的价格数据  # 说明
  note: 可选的额外说明                 # 可选
```

**示例：**
```yaml
- name: ProductPrice
  granularity:
    dimensions: [sku_id, city, p_date]
    level: city_daily
    description: 城市+日期粒度的价格数据
```

### 2. 业务上下文（Business Context）

**用途：** 提供业务语义，帮助 Agent 理解对象和字段的业务含义

**对象级别：**
```yaml
- name: Product
  business_context: |
    商品是核心业务对象，包含商品的基础属性。
    价格、成本、销量等动态数据在其他对象中维护。
```

**字段级别：**
```yaml
properties:
  - name: sku_id
    business_context: 商品唯一标识
```

### 3. 自定义查询（Query Field）

**用途：** 对于不直接映射到单个表的对象，使用自定义 SQL 查询

**语法：**
```yaml
- name: Category
  query: |
    SELECT DISTINCT
      category_name,
      level
    FROM categories
  primary_key: category_name
```

**注意：**
- `query` 和 `table` 二选一
- 查询会被包装为子查询
- 支持 UNION、DISTINCT 等复杂查询

### 4. 计算属性独立配置

**旧方式（仍然支持）：**
```yaml
properties:
  - name: gross_margin
    semantic_type: computed
    formula: "(price - cost) / price"
```

**新方式（推荐）：**
```yaml
computed_properties:
  - name: gross_margin
    formula: "(price - cost) / price"
    return_type: percentage
    description: 毛利率
    business_context: 反映商品的盈利能力
```

## 完整示例

```yaml
datasources:
  - id: ppy_mysql
    type: mysql
    connection:
      host: 60.190.243.69
      port: 9030
      database: agent
      user: agent_write
      password: ${DB_PASSWORD}

ontology:
  objects:
    # 主数据对象（使用 table）
    - name: Product
      description: 商品主数据
      datasource: ppy_mysql
      table: dm_ppy_product_info_ymd
      primary_key: sku_id
      business_context: |
        商品是核心业务对象，包含商品的基础属性。
        价格、成本、销量等动态数据在其他对象中维护。
      granularity:
        dimensions: [sku_id]
        level: master_data
        description: 商品主数据，一个 SKU 一条记录
      properties:
        - name: sku_id
          column: sku_id
          type: integer
          semantic_type: id
          description: SKU ID
          business_context: 商品唯一标识
        - name: sku_name
          column: sku_name
          type: string
          description: SKU名称

    # 维度对象（使用 query）
    - name: City
      description: 销售城市
      datasource: ppy_mysql
      query: |
        SELECT DISTINCT city as city_name
        FROM dm_ppy_product_info_ymd
        WHERE city IS NOT NULL
      primary_key: city_name
      business_context: |
        城市是重要的业务维度，不同城市有不同的价格策略。
      properties:
        - name: city_name
          type: string
          description: 城市名称

    # 事实对象（使用 table + granularity）
    - name: ProductPrice
      description: 商品价格
      datasource: ppy_mysql
      table: dm_ppy_product_info_ymd
      primary_key: [sku_id, city, p_date]
      business_context: |
        记录商品在不同城市、不同日期的售价。
      granularity:
        dimensions: [sku_id, city, p_date]
        level: city_daily
        description: 城市+日期粒度的价格数据
      properties:
        - name: sku_id
          column: sku_id
          type: integer
          semantic_type: id
          description: SKU ID
        - name: city
          column: city
          type: string
          description: 城市
        - name: price
          column: ppy_price
          type: decimal
          semantic_type: currency
          currency: CNY
          description: 售价
          business_context: 商品在该城市的正常售价
      computed_properties:
        - name: price_with_tax
          formula: "price * 1.13"
          return_type: currency
          description: 含税价格
          business_context: 价格加上13%增值税

  relationships:
    - name: price_of_product
      description: 价格属于哪个商品
      from_object: ProductPrice
      to_object: Product
      type: many_to_one
      join_condition:
        from_field: sku_id
        to_field: sku_id
      business_context: 一个商品在不同城市、不同日期有多个价格记录
```

## Agent 上下文输出示例

当 Agent 查询对象时，会看到：

```
### Product
商品主数据

业务上下文: 商品是核心业务对象，包含商品的基础属性。
价格、成本、销量等动态数据在其他对象中维护。

数据粒度: sku_id (master_data)
  说明: 商品主数据，一个 SKU 一条记录

可用字段（查询时使用 ObjectName.field_name 格式）：
  - sku_id: SKU ID
    业务含义: 商品唯一标识
  - sku_name: SKU名称

### ProductPrice
商品价格

业务上下文: 记录商品在不同城市、不同日期的售价。

数据粒度: sku_id, city, p_date (city_daily)
  说明: 城市+日期粒度的价格数据

可用字段（查询时使用 ObjectName.field_name 格式）：
  - sku_id: SKU ID
  - city: 城市
  - price (货币, CNY): 售价
    业务含义: 商品在该城市的正常售价
  - price_with_tax [计算字段，可直接查询]: 含税价格
    业务含义: 价格加上13%增值税
```

## 迁移指南

### 从旧 Ontology 迁移

1. **添加粒度标注**
   ```yaml
   # 旧
   - name: Product
     table: products

   # 新
   - name: Product
     table: products
     granularity:
       dimensions: [sku_id]
       level: master_data
   ```

2. **添加业务上下文**
   ```yaml
   # 旧
   - name: Product
     description: 商品

   # 新
   - name: Product
     description: 商品主数据
     business_context: |
       商品是核心业务对象，包含商品的基础属性。
   ```

3. **分离不同粒度的数据**
   ```yaml
   # 旧（混合在一起）
   - name: Product
     properties:
       - name: sku_id
       - name: price
       - name: cost

   # 新（分离）
   - name: Product
     properties:
       - name: sku_id

   - name: ProductPrice
     granularity:
       dimensions: [sku_id, city, p_date]
     properties:
       - name: price

   - name: ProductCost
     granularity:
       dimensions: [sku_id, city, p_date]
     properties:
       - name: cost
   ```

4. **提取维度对象**
   ```yaml
   # 新增独立的维度对象
   - name: City
     query: |
       SELECT DISTINCT city as city_name
       FROM products
   ```

## 最佳实践

### 1. 对象命名

- ✅ 使用名词：Product, City, Platform
- ❌ 避免动作：PriceAnalysis, MonitorSummary
- ❌ 避免关系：ProductMapping（可接受但不推荐）

### 2. 粒度标注

- 主数据对象：`level: master_data`
- 日期粒度：`level: daily`, `level: monthly`
- 城市粒度：`level: city_daily`, `level: city_monthly`
- 平台粒度：`level: city_platform_daily`

### 3. 业务上下文

- 对象级别：说明对象的业务含义和用途
- 字段级别：说明字段的业务含义（特别是枚举、货币字段）
- 计算字段：说明计算逻辑的业务含义

### 4. 自定义查询

- 用于维度对象（City, Platform, Category）
- 用于复杂的数据转换
- 确保查询性能可接受

## 常见问题

### Q: 旧的配置还能用吗？

A: 可以！完全向后兼容。旧的 `table` 字段、`semantic_type: computed` 都仍然支持。

### Q: query 和 table 可以同时使用吗？

A: 不可以，二选一。如果同时存在，`query` 优先。

### Q: 粒度标注是必须的吗？

A: 不是必须的，但强烈推荐。粒度标注可以帮助 Agent 更好地理解数据。

### Q: business_context 应该写多详细？

A: 2-3 句话即可，重点说明业务含义和使用场景。

### Q: 计算字段应该用哪种方式？

A: 推荐使用新的 `computed_properties` 独立配置，更清晰。但旧方式仍然支持。

## 相关文档

- [Ontology 重新设计文档](./ontology_redesign_v2.yaml)
- [实施计划](./plans/2026-03-16-ontology-redesign.md)
- [审计报告](./plans/2026-03-16-ontology-redesign-audit.md)
- [Phase 2 完成报告](./plans/2026-03-17-ontology-redesign-phase2-completion.md)
