# Ontology 重新设计说明

## 设计目标

基于 Foundry 平台的设计哲学和 Ontology 设计原则，重新设计拼便宜价格分析系统的 Ontology，使其：
1. 对象代表业务实体，而不是数据表
2. 明确标注数据粒度
3. 分离不同粒度的数据
4. 关系反映业务语义

## 核心变化

### 1. 对象重新分类

**原设计的问题：**
- `PlatformProductRel` - 名字像关系表
- `PriceAnalysis` - "分析"是动作，不是对象
- `MonitorSummary` - "汇总"是结果，不是对象
- `GoodsMallMapping` - "映射"是关系，不是对象

**新设计：**

#### 核心对象（业务实体）
- **Product** - 商品主数据（只含基础属性，不含价格）
- **Category** - 品类（新增）
- **City** - 城市（新增）
- **Platform** - 竞品平台（新增）
- **BusinessCenter** - 业务中心（新增）

#### 价格对象（不同粒度）
- **ProductPrice** - 商品价格（城市+日期粒度）
- **ProductCost** - 商品成本（城市+日期粒度）
- **ProductSales** - 商品销售（城市+日期粒度）
- **CompetitorPrice** - 竞品价格（城市+平台+日期粒度）

#### 分析对象
- **PriceAlert** - 价格预警（替代 MonitorSummary）
- **ProductMapping** - 商品映射（替代 GoodsMallMapping）

### 2. 粒度标注

每个对象都明确标注了粒度信息：

```yaml
granularity:
  dimensions: [sku_id, city, p_date]
  level: city_daily
  description: 城市+日期粒度的价格数据
```

**粒度对比：**
| 对象 | 粒度 | 说明 |
|------|------|------|
| Product | [sku_id] | 主数据，一个 SKU 一条记录 |
| ProductPrice | [sku_id, city, p_date] | 城市+日期粒度 |
| ProductCost | [sku_id, city, p_date] | 城市+日期粒度 |
| ProductSales | [sku_id, city, p_date] | 城市+日期粒度 |
| CompetitorPrice | [sku_id, city, platform, p_date] | 城市+平台+日期粒度 |

### 3. 业务语义增强

每个对象和属性都增加了 `business_context` 字段：

```yaml
- name: ppy_price
  description: 拼便宜售价
  business_context: 商品在该城市的正常售价
```

### 4. 关系设计

关系不再只是 JOIN 条件，而是有业务含义：

```yaml
- name: price_of_product
  description: 价格属于哪个商品
  from_object: ProductPrice
  to_object: Product
  type: many_to_one
  business_context: 一个商品在不同城市、不同日期有多个价格记录
```

## 设计原则应用

### 原则1：对象代表事物，不是数据

**Before:**
```yaml
Object: PriceAnalysis  # "分析"是动作
```

**After:**
```yaml
Object: ProductPrice   # "价格"是事物
Object: CompetitorPrice  # "竞品价格"是事物
```

### 原则2：对象有稳定身份

**Before:**
```yaml
Object: Product
  Properties:
    - city  # 城市作为属性
```

**After:**
```yaml
Object: City  # 城市作为独立对象
  Properties:
    - city_name

Object: ProductPrice  # 价格引用城市
  Links:
    - price_in_city: City
```

### 原则3：粒度匹配业务概念

**Before:**
```yaml
Object: Product  # 混合了主数据和价格数据
  Properties:
    - sku_name
    - ppy_price  # 价格
    - ppy_current_cost  # 成本
    - v_order_goods_amount  # 销售额
```

**After:**
```yaml
Object: Product  # 只有主数据
  Properties:
    - sku_name
    - specification
    - brand_name

Object: ProductPrice  # 价格数据
  Properties:
    - ppy_price

Object: ProductCost  # 成本数据
  Properties:
    - ppy_current_cost

Object: ProductSales  # 销售数据
  Properties:
    - v_order_goods_amount
```

### 原则4：关系反映业务语义

**Before:**
```yaml
relationships:
  - name: product_to_platform_rel  # 技术性命名
    from_object: Product
    to_object: PlatformProductRel
```

**After:**
```yaml
relationships:
  - name: price_of_product  # 业务性命名
    description: 价格属于哪个商品
    from_object: ProductPrice
    to_object: Product
    business_context: 一个商品在不同城市、不同日期有多个价格记录
```

## 实际应用示例

### 场景1：查询毛利率低于20%的商品

**Agent 理解：**
```
用户问："哪些商品的毛利率低于20%？"

系统理解：
1. 毛利率 = (价格 - 成本) / 价格
2. 价格在 ProductPrice 对象（城市+日期粒度）
3. 成本在 ProductCost 对象（城市+日期粒度）
4. 需要 JOIN 这两个对象（通过 sku_id + city）
5. 筛选 gross_margin < 0.2
```

**生成 SQL：**
```sql
SELECT
  p.sku_name,
  pp.city,
  pp.ppy_price,
  pc.ppy_current_cost,
  (pp.ppy_price - pc.ppy_current_cost) / pp.ppy_price as gross_margin
FROM ProductPrice pp
JOIN ProductCost pc
  ON pp.sku_id = pc.sku_id
  AND pp.city = pc.city
  AND pp.p_date = pc.p_date
JOIN Product p ON pp.sku_id = p.sku_id
WHERE (pp.ppy_price - pc.ppy_current_cost) / pp.ppy_price < 0.2
  AND pp.on_sell_status = '1'
```

### 场景2：对比不同平台的价格

**Agent 理解：**
```
用户问："北京地区，哪些商品比京东贵？"

系统理解：
1. 我方价格在 ProductPrice（城市粒度）
2. 竞品价格在 CompetitorPrice（城市+平台粒度）
3. 需要聚合 ProductPrice 到城市级（AVG）
4. 筛选 platform_name = '京东'
5. 对比价格
```

**生成 SQL：**
```sql
SELECT
  p.sku_name,
  my.avg_price as ppy_price,
  comp.mall_price as jd_price,
  my.avg_price - comp.mall_price as price_gap
FROM (
  SELECT sku_id, AVG(ppy_price) as avg_price
  FROM ProductPrice
  WHERE city = '北京' AND on_sell_status = '1'
  GROUP BY sku_id
) my
JOIN CompetitorPrice comp
  ON my.sku_id = comp.sku_id
  AND comp.city = '北京'
  AND comp.platform_name = '京东'
JOIN Product p ON my.sku_id = p.sku_id
WHERE my.avg_price > comp.mall_price
```

## 迁移建议

### 阶段1：验证新设计

1. 在测试环境部署新 Ontology
2. 验证所有对象能正确查询
3. 验证关系能正确 JOIN
4. 验证计算字段能正确计算

### 阶段2：更新 Agent 上下文

1. 更新 `chat.py` 中的 `_build_ontology_context()`
2. 确保 Agent 能理解新的对象结构
3. 测试常见查询场景

### 阶段3：更新前端

1. 更新 Object Explorer 显示新对象
2. 更新查询构建器支持新关系
3. 更新图表引擎支持新指标

### 阶段4：数据迁移

1. 保留旧对象作为兼容层
2. 逐步迁移现有查询到新对象
3. 废弃旧对象

## 优势总结

1. **更清晰的业务语义**：对象名称直接反映业务概念
2. **更灵活的粒度处理**：明确标注粒度，支持跨粒度查询
3. **更好的 Agent 理解**：业务上下文帮助 Agent 生成正确查询
4. **更易维护**：关系和计算逻辑集中管理
5. **更好的扩展性**：新增对象和关系不影响现有结构

## 下一步

1. 审查新设计，确认符合业务需求
2. 在测试环境部署
3. 编写迁移脚本
4. 更新文档和培训材料
