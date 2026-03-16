# Ontology 重新设计实施计划

**创建时间：** 2026-03-16
**状态：** 待审核
**优先级：** 高

## 1. 背景与目标

### 1.1 当前问题

当前 Ontology 设计存在以下问题：

1. **对象命名不规范**
   - `PlatformProductRel` - 名字像关系表，不像业务对象
   - `PriceAnalysis` - "分析"是动作，不是对象
   - `MonitorSummary` - "汇总"是结果，不是对象
   - `GoodsMallMapping` - "映射"是关系，不是对象

2. **粒度混乱**
   - `Product` 对象混合了主数据、价格、成本、销量
   - 没有明确标注数据粒度
   - 无法清晰区分城市级、门店级数据

3. **缺少核心对象**
   - 没有 Platform（竞品平台）对象
   - 没有 City（城市）对象
   - 没有 Category（品类）对象

4. **关系设计问题**
   - 关系都是通过 sku_id JOIN，没有体现业务语义
   - 缺少业务上下文说明

### 1.2 设计目标

基于 Foundry 平台的设计哲学，重新设计 Ontology：

1. **对象代表业务实体**：对象名称直接反映业务概念
2. **明确标注粒度**：每个对象明确标注数据粒度
3. **分离不同粒度数据**：价格、成本、销量分离为独立对象
4. **关系反映业务语义**：关系有业务含义，不只是 JOIN 条件
5. **增强业务上下文**：每个对象和属性都有业务说明

## 2. 新设计概览

### 2.1 对象分类

#### 核心对象（业务实体）
- **Product** - 商品主数据（只含基础属性）
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

### 2.2 粒度标注

| 对象 | 粒度 | 说明 |
|------|------|------|
| Product | [sku_id] | 主数据 |
| ProductPrice | [sku_id, city, p_date] | 城市+日期 |
| ProductCost | [sku_id, city, p_date] | 城市+日期 |
| ProductSales | [sku_id, city, p_date] | 城市+日期 |
| CompetitorPrice | [sku_id, city, platform, p_date] | 城市+平台+日期 |

### 2.3 关键改进

1. **Product 对象瘦身**：只保留基础属性，价格/成本/销量分离
2. **新增维度对象**：City, Platform, Category 作为独立对象
3. **粒度明确**：每个对象都有 `granularity` 字段标注
4. **业务语义**：每个对象都有 `business_context` 说明
5. **关系语义化**：如 `price_of_product`, `price_in_city`

## 3. 实施计划

### Phase 1: 准备阶段（1天）

**任务：**
- [x] 完成新 Ontology 设计
- [ ] 审查设计，确认符合业务需求
- [ ] 备份当前配置

**产出：**
- 新 Ontology YAML 配置文件
- 设计说明文档

### Phase 2: 后端适配（2-3天）

**任务：**

1. **更新 semantic.py**
   - 支持 `granularity` 字段解析
   - 支持 `business_context` 字段
   - 更新 `build_agent_context()` 方法

2. **更新 omaha.py**
   - 支持新的对象结构
   - 支持 `query` 字段（用于 Category, City 等对象）
   - 更新对象查询逻辑

3. **更新 chat.py**
   - 更新 `_build_ontology_context()` 方法
   - 增强 Agent 上下文生成
   - 支持粒度信息展示

4. **编写测试**
   - 测试新对象能正确查询
   - 测试关系能正确 JOIN
   - 测试计算字段能正确计算

**产出：**
- 更新的后端代码
- 单元测试（覆盖率 >80%）

### Phase 3: 数据验证（1天）

**任务：**

1. **验证对象查询**
   ```python
   # 验证 Product 对象
   SELECT * FROM Product LIMIT 10

   # 验证 ProductPrice 对象
   SELECT * FROM ProductPrice WHERE city='北京' LIMIT 10

   # 验证 CompetitorPrice 对象
   SELECT * FROM CompetitorPrice WHERE platform_name='京东' LIMIT 10
   ```

2. **验证关系 JOIN**
   ```python
   # 验证 Product -> ProductPrice
   SELECT p.sku_name, pp.ppy_price
   FROM Product p
   JOIN ProductPrice pp ON p.sku_id = pp.sku_id
   LIMIT 10

   # 验证跨粒度 JOIN
   SELECT pp.sku_id, pp.ppy_price, pc.ppy_current_cost
   FROM ProductPrice pp
   JOIN ProductCost pc
     ON pp.sku_id = pc.sku_id
     AND pp.city = pc.city
   LIMIT 10
   ```

3. **验证计算字段**
   ```python
   # 验证毛利率计算
   SELECT
     pp.sku_id,
     pp.ppy_price,
     pc.ppy_current_cost,
     (pp.ppy_price - pc.ppy_current_cost) / pp.ppy_price as gross_margin
   FROM ProductPrice pp
   JOIN ProductCost pc
     ON pp.sku_id = pc.sku_id
     AND pp.city = pc.city
   WHERE pp.on_sell_status = '1'
   LIMIT 10
   ```

**产出：**
- 验证报告
- 问题清单（如有）

### Phase 4: 前端适配（2-3天）

**任务：**

1. **更新 Object Explorer**
   - 显示新的对象列表
   - 显示粒度信息
   - 显示业务上下文

2. **更新查询构建器**
   - 支持新的关系
   - 支持跨粒度查询
   - 优化 JOIN 逻辑

3. **更新图表引擎**
   - 支持新的指标
   - 支持按新维度聚合

**产出：**
- 更新的前端代码
- UI 截图

### Phase 5: 测试与优化（2天）

**任务：**

1. **功能测试**
   - 测试常见查询场景
   - 测试 Agent 对话
   - 测试图表生成

2. **性能测试**
   - 测试查询性能
   - 优化慢查询
   - 添加必要的索引

3. **用户验收测试**
   - 邀请业务用户测试
   - 收集反馈
   - 修复问题

**产出：**
- 测试报告
- 性能优化报告
- 用户反馈汇总

### Phase 6: 部署与迁移（1天）

**任务：**

1. **灰度发布**
   - 在测试环境部署
   - 小范围用户测试
   - 监控错误日志

2. **全量发布**
   - 更新生产环境配置
   - 通知所有用户
   - 提供迁移指南

3. **废弃旧对象**
   - 标记旧对象为 deprecated
   - 设置废弃时间表
   - 迁移现有查询

**产出：**
- 部署文档
- 迁移指南
- 用户通知

## 4. 风险与应对

### 4.1 风险识别

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|---------|
| 数据源不支持新查询 | 高 | 中 | 提前验证所有查询，准备降级方案 |
| 性能下降 | 中 | 中 | 性能测试，优化慢查询，添加索引 |
| 用户不适应新结构 | 中 | 高 | 提供详细文档，培训，保留兼容层 |
| 现有查询失效 | 高 | 低 | 保留旧对象作为兼容层，逐步迁移 |

### 4.2 回滚计划

如果新设计出现严重问题：

1. **立即回滚**：恢复旧配置文件
2. **问题分析**：定位根本原因
3. **修复后重新部署**：解决问题后再次尝试

## 5. 成功标准

### 5.1 功能标准

- [ ] 所有对象能正确查询
- [ ] 所有关系能正确 JOIN
- [ ] 所有计算字段能正确计算
- [ ] Agent 能理解新的对象结构
- [ ] 图表能正确生成

### 5.2 性能标准

- [ ] 查询响应时间 < 3秒（P95）
- [ ] Agent 对话响应时间 < 10秒（P95）
- [ ] 图表生成时间 < 5秒（P95）

### 5.3 质量标准

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过率 100%
- [ ] 用户验收测试通过

### 5.4 用户满意度

- [ ] 用户反馈评分 > 4.0/5.0
- [ ] 无严重 bug 报告
- [ ] 查询成功率 > 95%

## 6. 资源需求

### 6.1 人力资源

- 后端开发：1人 × 3天
- 前端开发：1人 × 3天
- 测试：1人 × 2天
- 产品/业务：0.5人 × 2天（审查和验收）

### 6.2 时间资源

- 总工期：10个工作日
- 关键路径：后端适配 → 数据验证 → 前端适配 → 测试

### 6.3 技术资源

- 测试环境
- 数据库访问权限
- 监控和日志系统

## 7. 附录

### 7.1 相关文档

- 新 Ontology 配置：`/tmp/ontology_redesign.yaml`
- 设计说明：`/tmp/ontology_redesign_doc.md`
- Foundry 设计哲学：（本次对话记录）

### 7.2 关键决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-03-16 | 采用方案2（核心对象+多粒度价格对象） | 平衡灵活性和实现复杂度 |
| 2026-03-16 | 保留旧对象作为兼容层 | 降低迁移风险 |
| 2026-03-16 | 明确标注粒度信息 | 解决粒度不一致问题 |

### 7.3 待确认问题

1. **数据源支持**：Category, City, Platform 对象使用 `query` 字段，需要确认数据源支持
2. **性能影响**：多表 JOIN 可能影响性能，需要实际测试
3. **用户培训**：新结构需要用户培训，培训方式待定

---

**审核人：** _待填写_
**审核日期：** _待填写_
**审核意见：** _待填写_
