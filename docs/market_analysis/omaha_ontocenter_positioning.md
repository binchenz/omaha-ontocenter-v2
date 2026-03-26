# Omaha OntoCenter 市场定位与技术路线

> 更新时间：2026-03-17
> 基于轻量级本体市场格局分析

## 一、项目定位

### 核心定位

**Omaha OntoCenter 是一个"轻量级本体 + AI Agent"的混合型数据智能平台**，定位于：

- **阵营一（语义层基建）+ 阵营二（AI Native）的融合**
- 通过 YAML 定义轻量级本体（类似 dbt Semantic Layer）
- 通过 Chat Agent 提供 AI 驱动的数据查询（类似 Secoda/Dot）
- 面向中国市场，结合 BI 能力（类似 Kyligence）

### 与三大阵营的对比

| 维度 | 阵营一（基建层） | 阵营二（AI Native） | 阵营三（国内市场） | **Omaha OntoCenter** |
|------|-----------------|-------------------|------------------|---------------------|
| **定义方式** | YAML/代码 | AI 自动扫描 | 混合 | ✅ YAML + AI 增强 |
| **查询方式** | SQL/API | AI Agent | BI 界面 | ✅ Chat Agent + API |
| **上下文对齐** | 手动配置 | AI 学习 | 手动配置 | ✅ YAML 定义 + 未来 AI 学习 |
| **可视化** | 依赖第三方 BI | 依赖第三方 BI | 内置 BI | ✅ 内置 ECharts |
| **目标用户** | 数据工程师 | 业务分析师 | 业务分析师 | ✅ 数据工程师 + 业务分析师 |

---

## 二、技术架构

### 2.1 轻量级本体层（Lightweight Ontology）

**设计理念：**
- 不搬运数据，不重构底层数仓
- 通过 YAML 在物理数据和业务逻辑之间建立"翻译网"
- 支持多数据源（MySQL, PostgreSQL, SQLite）

**核心能力：**

1. **对象定义（Objects）**
   ```yaml
   objects:
     - name: CompetitorComparison
       description: 竞品价格对比专用对象
       table: dm_ppy_platform_product_info_rel_ymd
       default_filters:  # 自动过滤
         - field: platform_id
           operator: "IS NOT NULL"
   ```

2. **计算字段（Computed Properties）**
   ```yaml
   computed_properties:
     - name: actual_price_gap
       formula: "ppy_price - mall_price"
       return_type: currency
   ```

3. **关系定义（Relationships）**
   ```yaml
   relationships:
     - name: competitor_comparison_city
       from_object: CompetitorComparison
       to_object: City
       type: many_to_one
   ```

4. **业务指标（Metrics）**
   ```yaml
   metrics:
     - name: price_advantage_rate
       formula: "SUM(CASE WHEN price_advantage_flag = 1 THEN 1 ELSE 0 END) / ..."
   ```

**与 dbt Semantic Layer 的对比：**
- ✅ 类似的 YAML 定义方式
- ✅ 统一指标口径
- ✅ 支持计算字段
- ➕ 额外支持 default_filters（自动过滤）
- ➕ 额外支持多数据源

---

### 2.2 AI Agent 层（AI Native）

**设计理念：**
- 通过 Chat Agent 降低数据查询门槛
- 支持自然语言查询
- 基于 Ontology 上下文生成 SQL

**核心能力：**

1. **自然语言查询**
   - 用户："哪些商品比竞品贵？"
   - Agent：自动查询 CompetitorComparison 对象，过滤 price_advantage_flag=2

2. **上下文对齐**
   - 通过 YAML 的 `business_context` 字段定义业务术语
   - 例如："价格优势"在本系统中特指 price_advantage_flag=1

3. **智能 JOIN**
   - Agent 根据 relationships 自动生成 JOIN 语句
   - 无需用户手动编写复杂 SQL

4. **图表生成**
   - 基于查询结果自动推荐 ECharts 配置
   - 支持柱状图、折线图、饼图等

**与 Secoda/Dot 的对比：**
- ✅ 类似的 AI Agent 查询能力
- ✅ 解决上下文对齐问题
- ➖ 暂未实现自动扫描数据库结构（未来规划）
- ➖ 暂未实现历史 SQL 日志学习（未来规划）

---

### 2.3 MCP Server 层（API 基建）

**设计理念：**
- 通过 Model Context Protocol (MCP) 暴露标准化 API
- 支持第三方 AI Agent 接入
- 支持 Claude Desktop 等工具集成

**核心工具：**

1. `list_objects` - 列出所有对象类型
2. `get_schema` - 获取对象字段定义
3. `get_relationships` - 获取对象关系
4. `query_data` - 执行数据查询
5. `save_asset` - 保存查询为资产
6. `get_lineage` - 获取数据血缘
7. `generate_chart` - 生成图表配置

**与 Cube.dev 的对比：**
- ✅ 类似的 API 层设计
- ✅ 支持多种客户端接入
- ➕ 额外支持 MCP 协议（更现代）
- ➕ 额外支持数据血缘追踪

---

## 三、核心优势

### 3.1 技术优势

1. **轻量级 + AI Native 的融合**
   - 既有 YAML 的可控性和可维护性
   - 又有 AI Agent 的易用性和智能化

2. **最小识别集设计**
   - CompetitorComparison 对象只包含 sku_name, city, product_type_first_level
   - 90% 的查询无需 JOIN，提升性能

3. **自动过滤机制**
   - default_filters 自动应用，避免用户错误
   - 保证对象语义的正确性

4. **计算字段自动展开**
   - 用户无需手动编写复杂 SQL 表达式
   - 降低查询门槛

### 3.2 市场优势

1. **面向中国市场**
   - 支持中文自然语言查询
   - 适配国内企业数据基建现状

2. **开箱即用**
   - 内置 ECharts 可视化
   - 无需依赖第三方 BI 工具

3. **灵活部署**
   - 支持本地部署（私有化）
   - 支持云端部署（SaaS）

4. **低成本起步**
   - 不需要庞大交付团队
   - 数据工程师即可快速配置

---

## 四、与 Palantir 的对比

| 维度 | Palantir Foundry | Omaha OntoCenter |
|------|-----------------|------------------|
| **本体类型** | 重型本体 | 轻量级本体 |
| **交付成本** | 需要庞大团队 | 数据工程师即可 |
| **数据搬运** | 需要重构数仓 | 不搬运数据 |
| **定义方式** | GUI + 代码 | YAML |
| **AI 能力** | AIP Function Calling | Chat Agent |
| **可视化** | 内置 | 内置 ECharts |
| **目标市场** | 大型企业/政府 | 中小型企业 |
| **价格** | 高昂 | 低成本 |

**核心差异：**
- Palantir 是"大一统"的重型本体，适合大型企业
- Omaha OntoCenter 是"极薄翻译网"的轻量级本体，适合快速迭代

---

## 五、技术路线图

### Phase 1-3（已完成）✅

- ✅ Ontology 定义与解析
- ✅ 多数据源支持
- ✅ 自动 JOIN 查询
- ✅ MCP Server（7个工具）
- ✅ Chat Agent + ECharts
- ✅ 68个测试全部通过

### Phase 4（进行中）🔄

**Phase 4.1: 语义层增强**
- ⏳ default_filters 功能实现
- ⏳ computed_properties 自动展开
- ⏳ 字段语义类型（currency, percentage, enum）
- ⏳ 业务规则验证

**Phase 4.2: 前端语义层编辑器**
- ⏳ 三栏式编辑器（对象列表 + 字段编辑 + 预览）
- ⏳ 公式构建器（可视化编辑计算字段）
- ⏳ 关系可视化
- ⏳ 实时 SQL 预览

### Phase 5（规划中）📋

**AI 自动化增强**
- 🔮 自动扫描数据库结构
- 🔮 分析历史 SQL 查询日志
- 🔮 自动推断表关系
- 🔮 自动识别字段业务含义
- 🔮 动态元数据图谱

**数据写回能力**
- 🔮 支持数据更新（UPDATE）
- 🔮 支持数据插入（INSERT）
- 🔮 支持数据删除（DELETE）
- 🔮 权限控制（RBAC）

**Pipeline/Transform 系统**
- 🔮 数据转换流程定义
- 🔮 调度与监控
- 🔮 数据质量检查

---

## 六、投资价值与叙事

### 6.1 技术叙事

**"轻量级本体 + AI Agent"的完美结合**

1. **底层硬核**：数据工程师的基建能力
   - YAML 定义 Ontology
   - 多数据源支持
   - 自动 JOIN 查询

2. **上层智能**：AI 开发者的创新思维
   - Chat Agent 自然语言查询
   - 自动图表生成
   - 未来：AI 自动化元数据管理

3. **中间桥梁**：MCP Server 标准化 API
   - 支持第三方 AI Agent 接入
   - 支持 Claude Desktop 等工具集成

### 6.2 市场叙事

**"从古典 BI 到 AI Native 数据栈的演进"**

1. **痛点明确**：
   - 古典 BI 工具学习成本高
   - 数据工程师成为瓶颈
   - 业务分析师无法自助查询

2. **解决方案**：
   - 轻量级本体降低配置成本
   - AI Agent 降低查询门槛
   - 内置可视化降低使用门槛

3. **市场空间**：
   - 国内市场数据基建参差不齐
   - 需要"语义层 + BI"结合的解决方案
   - 从中小型企业切入，逐步向上

### 6.3 差异化优势

1. **技术门槛高**：
   - 需要同时掌握数据工程和 AI 技术
   - 竞争对手难以快速复制

2. **市场需求强**：
   - 从古典 BI 到 AI Native 的必经之路
   - 企业数字化转型的刚需

3. **可扩展性强**：
   - 从语义层基建到 AI Agent 的完整链路
   - 未来可扩展到数据写回、Pipeline 等

4. **定位清晰**：
   - 轻量级 vs 重型本体的明确差异
   - 面向中国市场的本地化优势

---

## 七、竞争分析

### 7.1 国际竞品

| 竞品 | 优势 | 劣势 | 我们的应对 |
|------|------|------|-----------|
| **dbt Semantic Layer** | 成熟的语义层基建 | 无 AI Agent | ✅ 我们有 Chat Agent |
| **Cube.dev** | 开源，社区活跃 | 无 AI Agent | ✅ 我们有 Chat Agent |
| **Secoda** | AI 自动化强 | 无语义层定义 | ✅ 我们有 YAML 定义 |
| **Dot** | 上下文对齐好 | 无语义层定义 | ✅ 我们有 YAML 定义 |

### 7.2 国内竞品

| 竞品 | 优势 | 劣势 | 我们的应对 |
|------|------|------|-----------|
| **Kyligence Zen** | 品牌知名度高 | 重型 OLAP 引擎 | ✅ 我们更轻量级 |
| **传统 BI 工具** | 市场占有率高 | 无 AI Agent | ✅ 我们有 Chat Agent |

### 7.3 核心竞争力

**"轻量级本体 + AI Agent"的独特组合**

- 既有 dbt/Cube.dev 的语义层基建能力
- 又有 Secoda/Dot 的 AI Native 能力
- 还有 Kyligence 的本地化和 BI 能力

---

## 八、总结

Omaha OntoCenter 定位于**"轻量级本体 + AI Agent"的混合型数据智能平台**，通过：

1. **YAML 定义轻量级本体**（阵营一的基建能力）
2. **Chat Agent 提供 AI 查询**（阵营二的智能能力）
3. **内置 ECharts 可视化**（阵营三的 BI 能力）

形成了一套**技术门槛高、市场需求强、可扩展性强、差异化明显**的解决方案，在向投资人展示时，是一套**逻辑自洽且极具爆发力**的叙事。

---

## 参考文档

- [轻量级本体市场格局分析](./lightweight_ontology_landscape.md)
- [Phase 4 Semantic Layer Spec](../superpowers/specs/2026-03-16-phase4-semantic-layer.md)
- [CompetitorComparison 测试报告](../test_reports/competitor_comparison_test_report.md)
