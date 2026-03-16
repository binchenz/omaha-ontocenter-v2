# Ontology 重新设计审计清单

**审计日期：** 2026-03-16
**审计人：** 待指定
**审计版本：** v2.0

## 1. 设计原则审计

### 1.1 对象代表业务实体

| 检查项 | 标准 | 结果 | 备注 |
|--------|------|------|------|
| 对象命名是否为名词 | 所有对象都应该是名词 | ✅ PASS | Product, City, Platform 等都是名词 |
| 对象是否代表业务概念 | 业务人员能理解对象含义 | ✅ PASS | 所有对象都有清晰的业务含义 |
| 是否有动作类对象 | 不应该有"分析"、"汇总"等动作 | ✅ PASS | 已移除 PriceAnalysis, MonitorSummary |
| 是否有关系类对象 | 不应该有"映射"、"关联"等关系 | ⚠️ WARNING | ProductMapping 保留，但已重命名 |

**建议：** ProductMapping 可以考虑进一步优化，但当前可接受。

### 1.2 对象有稳定身份

| 检查项 | 标准 | 结果 | 备注 |
|--------|------|------|------|
| 每个对象有 primary_key | 必须有唯一标识 | ✅ PASS | 所有对象都定义了 primary_key |
| 维度对象独立存在 | City, Platform 等应该是独立对象 | ✅ PASS | 已独立为对象 |
| 对象可被引用 | 通过关系可以引用其他对象 | ✅ PASS | 定义了完整的关系 |

### 1.3 粒度匹配业务概念

| 检查项 | 标准 | 结果 | 备注 |
|--------|------|------|------|
| 每个对象标注粒度 | 必须有 granularity 字段 | ✅ PASS | 所有价格对象都标注了粒度 |
| 粒度清晰无歧义 | dimensions 明确列出 | ✅ PASS | 如 [sku_id, city, p_date] |
| 不同粒度分离 | 不同粒度数据在不同对象 | ✅ PASS | ProductPrice, CompetitorPrice 粒度不同 |
| 主数据与事实数据分离 | Product 只含主数据 | ✅ PASS | 价格、成本、销量已分离 |

### 1.4 关系反映业务语义

| 检查项 | 标准 | 结果 | 备注 |
|--------|------|------|------|
| 关系命名语义化 | 如 price_of_product | ✅ PASS | 所有关系都有业务含义 |
| 关系有描述 | description 字段 | ✅ PASS | 所有关系都有描述 |
| 关系有业务上下文 | business_context 字段 | ✅ PASS | 关键关系都有业务上下文 |
| 关系类型正确 | one_to_many, many_to_one | ✅ PASS | 关系类型定义正确 |

### 1.5 逻辑封装

| 检查项 | 标准 | 结果 | 备注 |
|--------|------|------|------|
| 计算字段有业务含义 | 如 effective_price | ✅ PASS | 所有计算字段都有业务含义 |
| 计算字段有公式 | formula 字段 | ✅ PASS | 公式清晰 |
| 计算字段有业务上下文 | business_context 字段 | ✅ PASS | 说明了业务含义 |

## 2. 数据完整性审计

### 2.1 对象定义完整性

| 对象 | description | business_context | granularity | properties | 结果 |
|------|-------------|------------------|-------------|------------|------|
| Product | ✅ | ✅ | ✅ | ✅ | PASS |
| Category | ✅ | ✅ | N/A | ✅ | PASS |
| City | ✅ | ✅ | N/A | ✅ | PASS |
| Platform | ✅ | ✅ | N/A | ✅ | PASS |
| BusinessCenter | ✅ | ✅ | N/A | ✅ | PASS |
| ProductPrice | ✅ | ✅ | ✅ | ✅ | PASS |
| ProductCost | ✅ | ✅ | ✅ | ✅ | PASS |
| ProductSales | ✅ | ✅ | ✅ | ✅ | PASS |
| CompetitorPrice | ✅ | ✅ | ✅ | ✅ | PASS |
| PriceAlert | ✅ | ✅ | ✅ | ✅ | PASS |
| ProductMapping | ✅ | ✅ | N/A | ✅ | PASS |

### 2.2 属性定义完整性

抽查关键属性：

| 对象.属性 | type | semantic_type | description | business_context | 结果 |
|-----------|------|---------------|-------------|------------------|------|
| ProductPrice.ppy_price | ✅ | ✅ currency | ✅ | ✅ | PASS |
| ProductCost.ppy_current_cost | ✅ | ✅ currency | ✅ | ✅ | PASS |
| CompetitorPrice.price_gap | ✅ | ✅ currency | ✅ | ✅ | PASS |
| ProductSales.v_order_goods_amount | ✅ | ✅ currency | ✅ | ❌ | WARNING |

**问题：** ProductSales.v_order_goods_amount 缺少 business_context
**建议：** 补充业务上下文说明

### 2.3 关系定义完整性

| 关系 | from_object | to_object | type | join_condition | description | 结果 |
|------|-------------|-----------|------|----------------|-------------|------|
| price_of_product | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| price_in_city | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| competitor_price_on_platform | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |

**总体评估：** 关系定义完整，无缺失。

## 3. 技术可行性审计

### 3.1 数据源支持

| 对象 | 数据源类型 | 是否支持 | 备注 |
|------|-----------|---------|------|
| Product | table | ✅ | dm_ppy_product_info_ymd |
| Category | query | ⚠️ | 需要验证 UNION 查询支持 |
| City | query | ⚠️ | 需要验证 DISTINCT 查询支持 |
| Platform | query | ⚠️ | 需要验证 DISTINCT 查询支持 |
| ProductPrice | table | ✅ | dm_ppy_product_info_ymd |
| CompetitorPrice | table | ✅ | dm_ppy_platform_product_info_rel_ymd |

**风险：** Category, City, Platform 使用 `query` 字段，需要验证数据源是否支持。

**建议：** 在 Phase 2 中优先验证这些对象的查询。

### 3.2 性能影响

| 场景 | 涉及对象 | JOIN 数量 | 预估影响 | 优化建议 |
|------|---------|----------|---------|---------|
| 查询毛利率 | ProductPrice + ProductCost | 1 | 低 | 添加索引 (sku_id, city, p_date) |
| 竞对比价 | ProductPrice + CompetitorPrice | 1 | 低 | 添加索引 (sku_id, city, platform_name) |
| 品类销售分析 | Product + ProductSales + Category | 2 | 中 | 考虑物化视图 |

**总体评估：** 性能影响可控，需要添加必要索引。

### 3.3 向后兼容性

| 旧对象 | 新对象映射 | 兼容性 | 迁移难度 |
|--------|-----------|--------|---------|
| Product | Product + ProductPrice + ProductCost + ProductSales | 部分兼容 | 中 |
| PlatformProductRel | CompetitorPrice | 完全兼容 | 低 |
| PriceAnalysis | CompetitorPrice | 完全兼容 | 低 |
| MonitorSummary | PriceAlert | 完全兼容 | 低 |
| GoodsMallMapping | ProductMapping | 完全兼容 | 低 |

**建议：** 保留旧对象作为兼容层，逐步迁移现有查询。

## 4. 业务价值审计

### 4.1 业务场景覆盖

| 业务场景 | 是否支持 | 涉及对象 | 备注 |
|---------|---------|---------|------|
| 查询商品毛利率 | ✅ | ProductPrice + ProductCost | 支持 |
| 竞对价格对比 | ✅ | ProductPrice + CompetitorPrice | 支持 |
| 品类销售分析 | ✅ | Product + Category + ProductSales | 支持 |
| 城市销售排名 | ✅ | ProductSales + City | 支持 |
| 价格预警处理 | ✅ | PriceAlert | 支持 |
| 商品映射管理 | ✅ | ProductMapping | 支持 |

**总体评估：** 所有核心业务场景都得到支持。

### 4.2 Agent 理解能力

| 能力 | 是否增强 | 证据 |
|------|---------|------|
| 理解对象含义 | ✅ | 所有对象都有 business_context |
| 理解字段含义 | ✅ | 关键字段都有 business_context |
| 理解粒度差异 | ✅ | 明确标注 granularity |
| 理解关系语义 | ✅ | 关系有业务描述 |
| 生成正确查询 | ⚠️ | 需要实际测试验证 |

**建议：** 在 Phase 5 中重点测试 Agent 的查询生成能力。

## 5. 风险评估

### 5.1 高风险项

| 风险 | 影响 | 概率 | 缓解措施 | 状态 |
|------|------|------|---------|------|
| 数据源不支持 query 字段 | 高 | 中 | 提前验证，准备降级方案 | ⚠️ 待验证 |
| 性能下降 | 中 | 中 | 性能测试，添加索引 | ⚠️ 待测试 |
| 现有查询失效 | 高 | 低 | 保留兼容层 | ✅ 已缓解 |

### 5.2 中风险项

| 风险 | 影响 | 概率 | 缓解措施 | 状态 |
|------|------|------|---------|------|
| 用户不适应新结构 | 中 | 高 | 提供文档和培训 | ⚠️ 待执行 |
| Agent 理解偏差 | 中 | 中 | 充分测试，优化上下文 | ⚠️ 待测试 |

## 6. 审计结论

### 6.1 总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 设计原则符合度 | 95/100 | 高度符合 Foundry 设计哲学 |
| 数据完整性 | 90/100 | 少量属性缺少 business_context |
| 技术可行性 | 85/100 | 需要验证 query 字段支持 |
| 业务价值 | 95/100 | 覆盖所有核心业务场景 |
| 风险可控性 | 80/100 | 有中等风险，但有缓解措施 |

**总体评分：** 89/100

### 6.2 审计意见

**优点：**
1. 设计原则清晰，高度符合 Foundry 设计哲学
2. 对象分类合理，粒度标注明确
3. 业务语义丰富，Agent 理解能力增强
4. 覆盖所有核心业务场景

**待改进：**
1. 部分属性缺少 business_context，需要补充
2. query 字段的数据源支持需要验证
3. 性能影响需要实际测试
4. 用户培训计划需要细化

**建议：**
1. ✅ **批准实施**，但需要在 Phase 2 中优先验证技术可行性
2. 补充缺失的 business_context
3. 在 Phase 3 中进行充分的性能测试
4. 制定详细的用户培训计划

### 6.3 审批

- [ ] **设计审批**：产品负责人
- [ ] **技术审批**：技术负责人
- [ ] **业务审批**：业务负责人

---

**审计人签名：** _待填写_
**审计日期：** 2026-03-16
**下次审计日期：** Phase 3 完成后
